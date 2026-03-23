# OpenCode Worktree 설계 및 실행 플로우 상세 분석

## 1. 프로젝트 개요

| 항목      | 내용                                                                             |
|---------|--------------------------------------------------------------------------------|
| 이름      | opencode-worktree                                                              |
| 저장소     | [kdcokenny/opencode-worktree](https://github.com/kdcokenny/opencode-worktree)  |
| 목적      | AI 개발 세션을 위한 격리된 git worktree 자동 생성 및 터미널 스폰                                   |
| 런타임     | [Bun](https://bun.sh/) (TypeScript)                                            |
| 설치      | `ocx add kdco/worktree --from https://registry.kdco.dev`                       |
| 의존성     | `@opencode-ai/plugin`, `@opencode-ai/sdk`, `jsonc-parser`, `zod`, `bun:sqlite` |
| 별점 / 포크 | 314 / 15 (2026-03-18 기준)                                                       |

### 핵심 아이디어

이 플러그인은 AI 에이전트에게 **단 2개의 도구**만 노출합니다.

| 도구                | 인자                      | 역할                                  |
|-------------------|-------------------------|-------------------------------------|
| `worktree_create` | `branch`, `baseBranch?` | 격리된 환경 생성 → 파일 동기화 → 세션 포크 → 터미널 스폰 |
| `worktree_delete` | `reason`                | 삭제 예약 → 세션 종료 후 자동 커밋 → 정리          |

내부적으로 6단계 생성 파이프라인과 5단계 정리 프로세스를 캡슐화하여, AI 에이전트가 격리 환경의 복잡한 세부사항을 알 필요 없이 사용할 수 있습니다.

> **참고**: [git worktree](https://git-scm.com/docs/git-worktree)는 하나의 리포지토리에서 여러 작업 트리를 동시에 체크아웃할 수 있게 해주는 git 기본 기능입니다.
> 이 플러그인은 그 위에 자동화 계층을 추가합니다.

---

## 2. 모듈 아키텍처 및 초기화

> 다이어그램: [00-diagram.md § 1](/opencode-worktree/00-diagram.md#1-모듈-아키텍처-및-초기화)

### 모듈 구조

```text
src/plugin/
├── worktree.ts                    # 플러그인 진입점 (WorktreePlugin)
├── worktree/
│   ├── state.ts                   # SQLite 상태 관리 (세션, 보류 작업)
│   └── terminal.ts                # 크로스 플랫폼 터미널 스폰
└── kdco-primitives/               # 공유 유틸리티 라이브러리
    ├── index.ts                   # 배럴 exports
    ├── get-project-id.ts          # git 루트 커밋 기반 프로젝트 ID
    ├── shell.ts                   # 셸 이스케이프 (bash, batch, AppleScript)
    ├── mutex.ts                   # Promise 기반 뮤텍스
    ├── terminal-detect.ts         # tmux 환경 감지
    ├── temp.ts                    # 임시 디렉토리 유틸
    ├── log-warn.ts                # 구조화된 로깅
    ├── with-timeout.ts            # 타임아웃 래퍼
    └── types.ts                   # OpencodeClient 타입
```

### 모듈별 역할

| 모듈                 | 역할       | 핵심 책임                                  |
|--------------------|----------|----------------------------------------|
| `worktree.ts`      | 플러그인 진입점 | 도구 정의, 이벤트 핸들링, 파일 동기화, 세션 포크 오케스트레이션  |
| `state.ts`         | 상태 영속화   | SQLite CRUD, 싱글턴 pending 연산, 원자적 상태 전이 |
| `terminal.ts`      | 터미널 스폰   | 플랫폼 감지, 터미널별 명령 구성, 뮤텍스 기반 tmux 직렬화    |
| `kdco-primitives/` | 공유 유틸    | 프로젝트 ID, 셸 이스케이프, 동시성 제어, 로깅           |

### 초기화 흐름

플러그인이 로드되면 다음 순서로 초기화됩니다.

1. **Plugin Context 수신**: OpenCode가 `directory`(프로젝트 루트)와 `client`(API 클라이언트)를 전달
2. **SQLite 초기화**: `initStateDb`가 DB 파일 생성, WAL 모드 설정, 스키마 마이그레이션 수행
3. **프로세스 정리 핸들러 등록**: `SIGTERM`, `SIGINT`, `beforeExit` 시그널에 WAL 체크포인트 + DB 닫기 핸들러 등록
4. **도구 및 이벤트 핸들러 등록**: `worktree_create`, `worktree_delete` 도구와 `session.idle` 이벤트 리스너 반환

DB 초기화에는 최대 3회 재시도(100ms 간격)가 포함되어, 일시적 파일시스템 오류에 대한 복원력을 확보합니다.

### 공유 라이브러리 재사용

`kdco-primitives/`는 이 플러그인에만 국한되지 않고, 동일 레지스트리의 다른 플러그인들과 공유됩니다.

- [opencode-workspace](https://github.com/kdcokenny/opencode-workspace) — 구조화된 계획 + 규칙 주입
- [opencode-background-agents](https://github.com/kdcokenny/opencode-background-agents) — 비동기 위임 + 영속 출력
- [opencode-notify](https://github.com/kdcokenny/opencode-notify) — 네이티브 OS 알림

---

## 3. Worktree 생성 파이프라인

> 다이어그램: [00-diagram.md § 2](/opencode-worktree/00-diagram.md#2-worktree-생성-파이프라인)

`worktree_create`는 6단계 파이프라인으로 실행됩니다.

### 1단계: 경계 검증

[Zod](https://zod.dev/) 스키마 `branchNameSchema`로 브랜치명을 검증합니다. 검증 실패 시 즉시 오류를 반환하며, 다음 단계로 진행하지 않습니다. 상세한 검증
항목은 [§ 8. 보안 검증 체인](#8-보안-검증-체인)을 참조하세요.

### 2단계: Git Worktree 생성

`git rev-parse --verify`로 브랜치 존재 여부를 확인한 뒤, 분기합니다.

- **브랜치 존재**: `git worktree add <path> <branch>` — 기존 브랜치 체크아웃
- **브랜치 미존재**: `git worktree add -b <branch> <path> <base>` — baseBranch(기본값: HEAD)에서 새 브랜치 생성

Worktree 경로는 리포지토리 외부(`~/.local/share/opencode/worktree/<project-id>/<branch>/`)에 생성되어 프로젝트 디렉토리를 오염시키지 않습니다.

### 3단계: 파일 동기화

`.opencode/worktree.jsonc` 설정에 따라 파일을 동기화합니다. 자세한 내용은 [§ 7. 파일 동기화 전략](#7-파일-동기화-전략)을 참조하세요.

### 4단계: 세션 포크 + 컨텍스트 전파

단순 복제가 아닌 **세션 포크**를 수행합니다.

```typescript
async function forkWithContext(client, sessionId, projectId, getRootSessionIdFn) {
    // 1. 부모 체인을 순회하여 루트 세션 ID 탐색 (최대 10단계)
    const rootSessionId = await getRootSessionIdFn(sessionId)

    // 2. 세션 포크 (OpenCode API)
    const forkedSession = await client.session.fork({ path: { id: sessionId } })

    // 3. plan.md 복사 (작업 계획 유지)
    // 4. delegations 디렉토리 복사 (위임 상태 유지)
    // 5. 실패 시 생성된 리소스 전부 정리 (원자적 롤백)
}
```

핵심 설계 결정:

- **루트 세션 탐색**: `parentID` 체인을 최대 10단계까지 순회하여 최상위 세션을 찾고, 그 세션의 plan과 delegation을 복사합니다. 이를 통해 서브에이전트에서 생성한 worktree도 원본
  세션의 맥락을 유지합니다.
- **원자적 롤백**: 복사 중 실패 시, 이미 생성된 포크 세션과 디렉토리를 모두 정리합니다. 부분적으로 생성된 상태가 남지 않습니다.

### 5단계: 터미널 스폰

`openTerminal`이 플랫폼을 자동 감지하여 적절한 터미널을 스폰합니다. 새 터미널에서 `opencode --session <forked-id>` 명령이 실행됩니다. 자세한
내용은 [§ 5. 크로스 플랫폼 터미널 감지](#5-크로스-플랫폼-터미널-감지)를 참조하세요.

### 6단계: DB 기록

`addSession`으로 세션 정보(id, branch, path, createdAt)를 SQLite에 기록합니다. 이 정보는 이후 `worktree_delete`에서 현재 세션의 worktree를 찾는 데
사용됩니다.

---

## 4. Worktree 삭제 및 지연 삭제 패턴

> 다이어그램: [00-diagram.md § 3, § 4](/opencode-worktree/00-diagram.md#3-worktree-삭제-및-지연-삭제-패턴)

### 지연 삭제 패턴 (Deferred Delete)

`worktree_delete`는 즉시 삭제하지 않고 **삭제를 예약**합니다. 이 패턴은 [Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)의
지연 실행 개념과 유사합니다.

1. `worktree_delete` 호출 → `setPendingDelete` (DB에 삭제 의도 기록)
2. 응답 즉시 반환: "세션 종료 시 정리됩니다"
3. `session.idle` 이벤트 발생 시 실제 정리 수행

이 패턴의 이점:

- **데이터 손실 방지**: 세션이 아직 활성 상태일 때 삭제되어 작업이 유실되는 상황을 원천 차단
- **자동 스냅샷**: 미커밋 변경사항이 `git add -A` + `git commit`으로 자동 보존
- **훅 실행 보장**: `preDelete` 훅(예: `docker compose down`)이 정리 전에 실행됨

### 정리 프로세스

`session.idle` 이벤트 핸들러에서 5단계로 실행됩니다.

| 단계 | 명령                            | 목적                                     |
|----|-------------------------------|----------------------------------------|
| ①  | preDelete 훅 실행                | 사용자 정의 정리 (docker, 프로세스 종료 등)          |
| ②  | `git add -A`                  | 모든 변경사항 스테이징                           |
| ③  | `git commit --allow-empty`    | 스냅샷 커밋 (변경 없어도 기록)                     |
| ④  | `git worktree remove --force` | worktree 디렉토리 제거                       |
| ⑤  | DB 정리                         | `clearPendingDelete` + `removeSession` |

### 싱글턴 Pending 연산

`pending_operations` 테이블은 `CHECK(id = 1)` 제약으로 **항상 최대 1개의 보류 작업**만 유지합니다.

```sql
CREATE TABLE IF NOT EXISTS pending_operations (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- 싱글턴 보장
    type TEXT NOT NULL,                      -- 'spawn' | 'delete'
    branch TEXT NOT NULL,
    path TEXT NOT NULL,
    session_id TEXT
);
```

- **Last-Write-Wins**: 새 요청이 기존 보류 작업을 대체하며, 대체 시 경고 로그를 기록합니다.
- `spawn`과 `delete`가 동일 슬롯을 공유하므로 충돌 없이 상태 전이가 보장됩니다.
- `INSERT OR REPLACE`로 원자적 업데이트를 수행합니다.

### Result 타입 패턴

git 명령 실행에는 예외 대신 `Result<T, E>` 유니온 타입을 사용합니다.

```typescript
type Result<T, E> = OkResult<T> | ErrResult<E>

async function git(args: string[], cwd: string): Promise<Result<string, string>> {
    const proc = Bun.spawn(["git", ...args], { cwd, stdout: "pipe", stderr: "pipe" })
    if (exitCode !== 0) return Result.err(stderr.trim())
    return Result.ok(stdout.trim())
}
```

git 명령은 실패가 빈번하므로(브랜치 미존재, 권한 부족 등) 예외보다 Result가 적합합니다. 호출부에서 `if (!result.ok)` 패턴으로 분기하여 명시적 에러 핸들링을 강제합니다.
Rust의 [`Result<T, E>`](https://doc.rust-lang.org/std/result/)에서 영감을 받은 패턴입니다.

---

## 5. 크로스 플랫폼 터미널 감지

> 다이어그램: [00-diagram.md § 5](/opencode-worktree/00-diagram.md#5-크로스-플랫폼-터미널-감지)

### 감지 우선순위

`detectTerminalType`은 다음 순서로 환경을 감지합니다.

| 우선순위 | 감지 대상 | 방법                                 | 비고                                               |
|------|-------|------------------------------------|--------------------------------------------------|
| 1    | tmux  | `TMUX` 환경변수                        | 모든 플랫폼에서 런타임 우선                                  |
| 2    | cmux  | `CMUX_WORKSPACE_ID` 또는 소켓          | 에이전트 워크플로우에 권장. [cmux](https://www.cmux.dev/) 참조 |
| 3    | WSL   | `WSL_DISTRO_NAME` / `os.release()` | Windows Terminal 인터롭                             |
| 4    | 플랫폼별  | `process.platform`                 | macOS / Linux / Windows                          |

tmux가 최우선인 이유는, 사용자가 어떤 플랫폼이든 tmux 안에서 작업 중이라면 새 tmux 윈도우를 여는 것이 가장 자연스러운 경험이기 때문입니다.

### macOS 터미널별 스폰 전략

각 터미널의 고유 특성에 맞춘 개별 구현을 제공합니다.

| 터미널          | 감지 환경변수                 | 스폰 방식                             | 특이사항                                                                 |
|--------------|-------------------------|-----------------------------------|----------------------------------------------------------------------|
| Ghostty      | `GHOSTTY_RESOURCES_DIR` | `open -na Ghostty.app --args`     | 인라인 명령으로 권한 대화상자 회피, 임시 스크립트 불필요                                     |
| iTerm2       | `ITERM_SESSION_ID`      | AppleScript `write text`          | 새 탭 생성 후 스크립트 경로 전달                                                  |
| Kitty        | `KITTY_WINDOW_ID`       | `kitty @ launch --type tab` 우선 시도 | [원격 제어](https://sw.kovidgoyal.net/kitty/remote-control/) 실패 시 새 창 폴백 |
| Alacritty    | `ALACRITTY_WINDOW_ID`   | `alacritty --working-directory`   | detached 스폰                                                          |
| Warp         | `__CFBundleIdentifier`  | `open -b dev.warp.Warp-Stable`    | detached 스폰                                                          |
| Terminal.app | `TERM_PROGRAM` 폴백       | `open -a Terminal`                | 유일하게 동기 방식(`withTempScript` 사용)                                      |

### Linux 터미널 감지 (6단계 폴백 체인)

Linux는 DE(Desktop Environment)에 따라 기본 터미널이 다르므로, 6단계 폴백 체인을 사용합니다.

| 단계 | 대상                  | 감지 방법                                                                               |
|----|---------------------|-------------------------------------------------------------------------------------|
| ①  | 현재 터미널              | `KITTY_WINDOW_ID`, `WEZTERM_PANE`, `ALACRITTY_WINDOW_ID` 등 환경변수                     |
| ②  | xdg-terminal-exec   | `which` 명령으로 존재 확인 ([XDG 표준](https://gitlab.freedesktop.org/xdg/xdg-terminal-exec)) |
| ③  | x-terminal-emulator | Debian/Ubuntu의 alternatives 시스템                                                     |
| ④  | 모던 터미널              | kitty, alacritty, wezterm, ghostty, foot 순차 시도                                      |
| ⑤  | DE 터미널              | gnome-terminal, konsole, xfce4-terminal                                             |
| ⑥  | xterm               | 최후 수단                                                                               |

### tmux 뮤텍스 보호

tmux 서버는 단일 스레드이므로 동시 명령이 소켓 레이스를 일으킬 수 있습니다. `Mutex` 클래스로 이를 방지합니다.

```typescript
const tmuxMutex = new Mutex()  // 프로세스당 싱글턴

async function openTmuxWindow(options) {
    return tmuxMutex.runExclusive(async () => {
        Bun.spawnSync(["tmux", ...tmuxArgs])  // 배열 기반 spawn
        await Bun.sleep(150)                   // 안정화 대기
    })
}
```

- `Mutex.runExclusive`로 자동 acquire/release (FIFO 순서 보장)
- 150ms 안정화 지연으로 tmux 서버가 창을 처리할 시간 확보
- 모든 tmux 명령은 배열 기반 `Bun.spawnSync`로 실행되어 셸 보간을 완전 차단

---

## 6. 임시 스크립트 생명주기

> 다이어그램: [00-diagram.md § 6](/opencode-worktree/00-diagram.md#6-임시-스크립트-생명주기)

터미널 스폰 시 임시 bash/batch 스크립트를 생성하는데, 터미널이 **동기**인지 **비동기(detached)**인지에 따라 정리 전략이 달라집니다. 이 구분은 레이스 컨디션을 방지하기 위한 핵심 설계입니다.

### 동기 터미널 (Terminal.app)

```typescript
async function withTempScript<T>(scriptContent, fn, extension) {
    const scriptPath = path.join(getTempDir(), `worktree-${Date.now()}.sh`)
    await Bun.write(scriptPath, scriptContent)
    await fs.chmod(scriptPath, 0o755)
    try {
        return await fn(scriptPath)  // 프로세스 완료까지 대기
    } finally {
        await fs.rm(scriptPath)       // 확실한 정리
    }
}
```

`try-finally` 패턴으로 스크립트 파일이 반드시 정리됩니다. 프로세스가 완료될 때까지 대기하므로 `finally` 블록이 안전하게 실행됩니다.

### 비동기 터미널 (대부분)

```bash
#!/bin/bash
trap 'rm -f "$0"' EXIT INT TERM  # 자기 삭제 트랩
cd "/path/to/worktree" && opencode --session abc123
exec bash
```

detached 프로세스에서는 `withTempScript`를 **사용하면 안 됩니다**. `finally` 블록이 detached 프로세스가 스크립트를 읽기 전에 실행되어, 아직 필요한 파일이 삭제되는 레이스
컨디션이 발생합니다. 대신 스크립트 자체에 `trap` 기반 자기 삭제를 삽입합니다.

### Windows (.bat)

```batch
@echo off
cd /d "C:\path\to\worktree"
opencode --session abc123
cmd /k
(goto) 2>nul & del "%~f0"
```

batch 파일의 `(goto) 2>nul & del "%~f0"` 관용구로 자기 삭제를 수행합니다.

### 실패 시 정리

스폰이 실패한 경우, orphaned 스크립트가 남을 수 있습니다. 각 터미널 구현의 `catch` 블록에서 `detachedScriptPath`를 추적하고 수동으로 삭제합니다.

---

## 7. 파일 동기화 전략

> 다이어그램: [00-diagram.md § 7](/opencode-worktree/00-diagram.md#7-파일-동기화-전략)

### 설정 파일

`.opencode/worktree.jsonc` ([JSONC](https://github.com/microsoft/node-jsonc-parser) 포맷으로 주석 허용):

```jsonc
{
  "$schema": "https://registry.kdco.dev/schemas/worktree.json",
  "sync": {
    "copyFiles": [".env", ".env.local"],    // 파일 복사 (독립 사본)
    "symlinkDirs": ["node_modules"],         // 디렉토리 심링크 (디스크 절약)
    "exclude": []                            // 미래 사용 예약
  },
  "hooks": {
    "postCreate": ["pnpm install"],          // 생성 후 실행
    "preDelete": ["docker compose down"]     // 삭제 전 실행
  }
}
```

첫 사용 시 설정 파일이 자동 생성됩니다. `jsonc-parser`로 주석 포함 JSONC를 파싱하고, Zod 스키마로 런타임 검증을 수행합니다. 누락 필드는 기본값이 적용됩니다.

### 동기화 방식 비교

| 방식               | 대상                     | 동작            | 사용 사례                                 |
|------------------|------------------------|---------------|---------------------------------------|
| **copyFiles**    | `.env`, `.env.local` 등 | 독립 복사본 생성     | 비밀 정보, 환경별 설정 — worktree에서 수정해도 원본 불변 |
| **symlinkDirs**  | `node_modules/` 등      | 심볼릭 링크 생성     | 대용량 디렉토리 — 디스크 절약 + 즉시 사용 가능          |
| **git worktree** | `src/` 등 소스 코드         | 브랜치별 git 체크아웃 | git이 관리하는 모든 파일 — 브랜치별 독립 코드          |

### 경로 안전성 검증

모든 동기화 경로는 `isPathSafe`로 검증됩니다. 자세한 내용은 [§ 8. 보안 검증 체인](#8-보안-검증-체인)의 Layer 2를 참조하세요.

### 훅 시스템

| 훅            | 실행 시점                   | 용도                           |
|--------------|-------------------------|------------------------------|
| `postCreate` | worktree 생성 + 파일 동기화 직후 | 의존성 설치, 컨테이너 시작, DB 마이그레이션 등 |
| `preDelete`  | worktree 삭제 직전          | 컨테이너 중지, 리소스 해제, 상태 백업 등     |

훅 명령은 `bash -c`로 실행되며, worktree 디렉토리를 `cwd`로 사용합니다. 실패 시 경고 로그를 남기지만 전체 프로세스를 중단하지는 않습니다.

---

## 8. 보안 검증 체인

> 다이어그램: [00-diagram.md § 8](/opencode-worktree/00-diagram.md#8-보안-검증-체인)

3개 레이어의 다층 방어 체계를 구성합니다.

### Layer 1: 브랜치명 검증 (Zod Schema)

[Zod](https://zod.dev/) 스키마 `branchNameSchema`로 API 경계에서 입력을 검증합니다.

| 검증 항목          | 차단 대상               | 보안 목적                                                          |
|----------------|---------------------|----------------------------------------------------------------|
| 시작 문자 `-` 차단   | `--exec` 등          | git 옵션 인젝션 방지                                                  |
| 시작/끝 `/` 차단    | `/etc/passwd`       | 경로 인젝션 방지                                                      |
| `//` 차단        | 비정상 경로              | [git ref 규칙](https://git-scm.com/docs/git-check-ref-format) 준수 |
| `@{` 차단        | reflog 구문           | git 특수 구문 방지                                                   |
| `..` 차단        | 상위 디렉토리             | 경로 순회 방지                                                       |
| 제어 문자 차단       | `\x00-\x1f`, `\x7f` | 터미널 이스케이프 방지                                                   |
| git 메타문자 차단    | `~^:?*[]\`          | git ref 규칙 준수                                                  |
| 셸 메타문자 차단      | `;&\|` 등            | 명령 인젝션 방지                                                      |
| 255자 제한        | 과도한 길이              | 버퍼 오버플로우 방지                                                    |
| `.lock` 접미사 차단 | git 잠금 파일           | git 내부 충돌 방지                                                   |

### Layer 2: 경로 안전성 검증

파일 동기화 시 경로 순회 공격을 방지합니다.

```typescript
function isPathSafe(filePath: string, baseDir: string): boolean {
    if (path.isAbsolute(filePath)) return false     // 절대 경로 거부
    if (filePath.includes("..")) return false        // 상위 순회 거부
    const resolved = path.resolve(baseDir, filePath)
    return resolved.startsWith(baseDir + path.sep)   // 기준 디렉토리 이탈 거부
}
```

3단계 검증(절대경로 → `..` 포함 → resolve 후 이탈 확인)으로 symlink를 통한 우회까지 방지합니다.

### Layer 3: 실행 보안

| 계층          | 방식                                                 | 보호 대상                                                           |
|-------------|----------------------------------------------------|-----------------------------------------------------------------|
| git/tmux 명령 | `Bun.spawn(["cmd", ...args])` 배열 기반                | 셸 보간 완전 차단 — 값에 특수문자가 있어도 리터럴로 전달                               |
| 셸 이스케이프     | `assertShellSafe` → null 바이트 검증                    | [C 문자열 취약점](https://cwe.mitre.org/data/definitions/626.html) 방지 |
| 플랫폼별 이스케이프  | `escapeBash` / `escapeBatch` / `escapeAppleScript` | 각 셸의 메타문자 이스케이프                                                 |
| 훅 명령        | `bash -c command`                                  | 사용자 정의 명령 (설정 파일 신뢰 기반)                                         |

> **주의**: 훅 명령은 `.opencode/worktree.jsonc`에서 직접 읽어 `bash -c`로 실행합니다. 악성 설정 파일에 의한 명령 인젝션이 이론적으로 가능하지만, 이는 사용자가 직접 작성하는
> 설정이므로 신뢰 기반으로 처리합니다.

---

## 9. 프로젝트 ID 생성 및 캐싱

> 다이어그램: [00-diagram.md § 9](/opencode-worktree/00-diagram.md#9-프로젝트-id-생성-및-캐싱)

### 생성 전략

프로젝트 ID는 모든 worktree가 **동일한 프로젝트 데이터를 공유**하기 위한 안정적 식별자입니다.

| 전략            | 조건                         | 결과                | 안정성                |
|---------------|----------------------------|-------------------|--------------------|
| git 루트 커밋 SHA | `.git` 디렉토리 존재 + git 이력 있음 | 40자 hex           | 프로젝트 이동/이름 변경에도 불변 |
| 경로 해시 폴백      | `.git` 없음 또는 빈 리포지토리       | SHA-256 → 16자 hex | 경로 변경 시 달라짐        |

### git worktree 지원

`.git`이 파일인 경우(worktree 내부에서 실행 시), `gitdir:` 참조를 해석하여 공유 `.git` 디렉토리를 찾습니다. `commondir` 파일이 있으면 그 경로를, 없으면 `../..`를
사용합니다. 이를 통해 모든 worktree에서 동일한 프로젝트 ID가 생성됩니다.

### 캐싱

생성된 프로젝트 ID는 `.git/opencode` 파일에 캐싱됩니다. 다음 호출 시 캐시를 먼저 확인하고, 유효한 형식(40자 또는 16자 hex)이면 즉시 반환합니다.

`git rev-list` 명령에는 5초 타임아웃(`withTimeout`)이 적용되어, 네트워크 파일시스템 등에서의 행(hang)을 방지합니다.

---

## 10. 데이터 경로

> 다이어그램: [00-diagram.md § 10](/opencode-worktree/00-diagram.md#10-데이터-경로-맵)

### 경로 맵

| 용도          | 경로                                                                    | 비고                                  |
|-------------|-----------------------------------------------------------------------|-------------------------------------|
| Worktree 파일 | `~/.local/share/opencode/worktree/<project-id>/<branch>/`             | 리포지토리 외부에 생성                        |
| 상태 DB       | `~/.local/share/opencode/plugins/worktree/<project-id>.sqlite`        | WAL 모드, 프로세스 종료 시 체크포인트             |
| Plan 복사     | `~/.local/share/opencode/workspace/<project-id>/<session-id>/plan.md` | 세션 포크 시 루트 세션에서 복사                  |
| Delegation  | `~/.local/share/opencode/delegations/<project-id>/<session-id>/`      | 세션 포크 시 루트 세션에서 복사                  |
| 프로젝트 ID 캐시  | `<repo>/.git/opencode`                                                | 40자 hex SHA, worktree에서도 공유 .git 참조 |
| 설정          | `<repo>/.opencode/worktree.jsonc`                                     | JSONC 포맷, 자동 생성                     |
| 임시 스크립트     | OS 임시 디렉토리                                                            | trap 또는 finally로 자동 삭제              |

### 설계 의도

- **Worktree 경로가 리포지토리 외부에 있는 이유**: `.gitignore` 관리 불필요, 프로젝트 디렉토리 오염 방지, 여러 프로젝트의 worktree를 일관된 위치에서 관리
- **프로젝트 ID 기반 분리**: 동일 머신에서 여러 프로젝트를 다뤄도 상태 DB와 worktree가 충돌하지 않음
- **`~/.local/share/` 고정**: [XDG Base Directory](https://specifications.freedesktop.org/basedir-spec/latest/) 스펙의
  `XDG_DATA_HOME` 환경변수를 현재 지원하지 않음 (트레이드오프 참조)

---

## 11. 강점 및 트레이드오프

> 다이어그램: [00-diagram.md § 11](/opencode-worktree/00-diagram.md#11-전체-end-to-end-파이프라인)

### 강점

**최소 인터페이스 원칙** — 도구가 2개(`worktree_create`, `worktree_delete`)뿐이므로 AI 에이전트의 도구 선택 부담이 최소화됩니다. 6단계 생성 파이프라인과 5단계 정리 프로세스가
내부로 캡슐화되어, AI가 "브랜치를 만들어 실험해봐"라는 단순한 의도만으로 격리 환경을 활용할 수 있습니다.

**크로스 플랫폼 완성도** — macOS 6종, Linux 10종, Windows/WSL/tmux를 지원합니다. 각 터미널의 고유 특성(Ghostty의 인라인 명령, Kitty의 원격 제어, iTerm의
AppleScript, tmux의 뮤텍스 보호)에 맞춘 개별 구현을 제공하며, 6단계 Linux 폴백 체인으로 거의 모든 DE를 커버합니다.

**안전한 생명주기** — 지연 삭제로 작업 중 데이터 손실 방지, 자동 `git commit`으로 미커밋 변경 보존, 프로세스 종료 시 WAL 체크포인트와 DB 닫기, 세션 포크 실패 시 원자적 롤백까지 —
생명주기 전반에 걸쳐 데이터 안전을 보장합니다.

**공유 유틸리티 추출** — `kdco-primitives/`로 프로젝트 ID 생성, 셸 이스케이프, 뮤텍스 등을 분리하여 OCX 레지스트리의 다른 플러그인들과 재사용합니다. 코드 중복 없이 일관된 보안과 동시성
제어를 제공합니다.

### 트레이드오프 및 제한사항

| 항목                | 내용                                                                       | 영향                                              |
|-------------------|--------------------------------------------------------------------------|-------------------------------------------------|
| **Bun 전용**        | `bun:sqlite`, `Bun.spawn`, `Bun.file` 등 [Bun](https://bun.sh/) 고유 API 사용 | Node.js 런타임에서 실행 불가                             |
| **단일 pending 작업** | 싱글턴 패턴으로 동시에 1개의 보류 작업만 유지                                               | 빠른 연속 요청 시 이전 요청이 경고 없이 대체됨                     |
| **훅 보안**          | `bash -c`로 사용자 정의 명령 실행                                                  | `.opencode/worktree.jsonc`가 악성으로 수정되면 명령 인젝션 가능 |
| **터미널 감지 한계**     | 환경변수 기반 감지                                                               | SSH 원격 세션, 비표준 터미널에서 감지 실패 가능                   |
| **cmux 의존**       | 에이전트 워크플로우에 [cmux](https://www.cmux.dev/) 권장                             | 미설치 시 일반 터미널로 폴백                                |
| **XDG 미지원**       | `~/.local/share/` 경로 하드코딩                                                | `XDG_DATA_HOME` 커스터마이징 불가                       |
| **OCX 필수**        | 패키지 매니저 [OCX](https://github.com/kdcokenny/ocx) 통해 설치                    | 수동 설치 시 `jsonc-parser` 직접 관리 필요                 |

---

## 참고 자료

### 프로젝트 링크

- [kdcokenny/opencode-worktree](https://github.com/kdcokenny/opencode-worktree) — 이 플러그인의 소스 코드
- [OCX Registry (kdco)](https://github.com/kdcokenny/ocx/tree/main/registry/src/kdco) — KDCO 플러그인 레지스트리
- [opencode-worktree-session](https://github.com/felixAnhalt/opencode-worktree-session) — 원본 영감을 준 프로젝트
- [OpenCode](https://github.com/sst/opencode) — 호스트 플랫폼

### 관련 플러그인

- [opencode-workspace](https://github.com/kdcokenny/opencode-workspace) — 구조화된 계획 + 규칙 주입
- [opencode-background-agents](https://github.com/kdcokenny/opencode-background-agents) — 비동기 위임 + 영속 출력
- [opencode-notify](https://github.com/kdcokenny/opencode-notify) — 네이티브 OS 알림

### 기술 참조

- [git worktree 문서](https://git-scm.com/docs/git-worktree) — git worktree 공식 문서
- [git check-ref-format](https://git-scm.com/docs/git-check-ref-format) — 브랜치명 검증 규칙의 근거
- [Bun SQLite](https://bun.sh/docs/api/sqlite) — bun:sqlite API
- [Zod](https://zod.dev/) — 런타임 스키마 검증 라이브러리
- [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/) — 데이터 경로 표준
- [CWE-626: Null Byte Interaction Error](https://cwe.mitre.org/data/definitions/626.html) — null 바이트 보안 참조
