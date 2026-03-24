# OpenCode Worktree 분석

`opencode-worktree`는 [OpenCode](https://github.com/sst/opencode) 플러그인으로, AI 개발 세션을 위한 **격리된 git worktree를 자동 생성하고 터미널을
스폰**하는 도구입니다.

---

## 문서 구성

| 문서                                                     | 내용                                                                   |
|--------------------------------------------------------|----------------------------------------------------------------------|
| [아키텍처 다이어그램](/opencode-worktree/00-diagram.md)         | 11개 mermaid 다이어그램 — 모듈 구조, 생성/삭제 파이프라인, 터미널 감지, 상태 모델, 보안 체인, E2E 흐름 |
| [설계 및 실행 플로우 상세 분석](/opencode-worktree/01-analysis.md) | 핵심 설계 결정, 크로스 플랫폼 전략, 보안 다층 방어, 설정 시스템, 강점/트레이드오프                    |

### 섹션 대응표

두 문서는 동일한 11개 섹션 구조를 공유하며, 다이어그램과 텍스트 분석이 1:1로 대응됩니다.

| §  | 다이어그램 (00)             | 분석 (01)                                    |
|----|------------------------|--------------------------------------------|
| 1  | 초기화 플로우 + 모듈 의존성 그래프   | 모듈별 역할, 초기화 순서, 공유 라이브러리 재사용               |
| 2  | 6단계 생성 파이프라인           | 단계별 상세 로직, 세션 포크 원자적 롤백                    |
| 3  | 지연 삭제 + 정리 프로세스        | Deferred Delete 패턴, 싱글턴 pending, Result 타입 |
| 4  | ER 다이어그램 + 상태 전이       | SQLite 스키마, 생명주기 상태 설명                     |
| 5  | 플랫폼 감지 폴백 트리           | 터미널별 스폰 전략, tmux 뮤텍스, Linux 6단계 폴백         |
| 6  | 동기/비동기/Windows 스크립트 흐름 | 레이스 컨디션 방지, trap 자기 삭제, 실패 시 정리            |
| 7  | 메인 ↔ 워크트리 동기화          | copyFiles vs symlinkDirs, 훅 시스템, 설정 자동 생성  |
| 8  | 3-Layer 보안 검증          | Zod 검증 항목, 경로 안전성, 명령 실행 보안                |
| 9  | 프로젝트 ID 생성 플로우         | git 루트 커밋 전략, worktree 지원, 캐싱 메커니즘         |
| 10 | 데이터 경로 맵               | 경로별 용도, 설계 의도, XDG 미지원 배경                  |
| 11 | End-to-End 파이프라인       | 강점 4가지, 트레이드오프 7가지                         |

---

## 요약

OpenCode Worktree는 AI 에이전트가 `worktree_create` / `worktree_delete` 두 개의 도구만으로 격리된 개발 환경을 관리할 수 있게 해주는 플러그인입니다.

- **자동화된 격리**: worktree 생성 → 파일 동기화 → 세션 포크 → 터미널 스폰이 단일 도구 호출로 완료
- **크로스 플랫폼 터미널 감지**: macOS 6종, Linux 10종, Windows/WSL, tmux/cmux를 자동 감지하여 적절한 터미널 스폰
- **안전한 생명주기 관리**: SQLite 기반 상태 추적, 자동 커밋 후 정리, 프로세스 종료 시 graceful cleanup
- **다층 보안 설계**: Zod 브랜치 검증, 경로 순회 방지, 배열 기반 spawn으로 셸 인젝션 차단

---

## 핵심 특징

| 항목     | 설명                                                                           |
|--------|------------------------------------------------------------------------------|
| 언어     | TypeScript (Bun 런타임)                                                         |
| 라이선스   | MIT                                                                          |
| 설치 방식  | [OCX](https://github.com/kdcokenny/ocx) 패키지 매니저                              |
| 도구 수   | 2개 (`worktree_create`, `worktree_delete`)                                    |
| 상태 저장  | SQLite (bun:sqlite, WAL 모드)                                                  |
| 플랫폼    | macOS, Linux, Windows, WSL                                                   |
| 터미널 지원 | Ghostty, iTerm2, Kitty, WezTerm, Alacritty, Warp, Terminal.app, tmux, cmux 등 |

---

## 참고 자료

- [kdcokenny/opencode-worktree (GitHub)](https://github.com/kdcokenny/opencode-worktree)
- [OpenCode](https://github.com/sst/opencode) — 호스트 플랫폼
- [OCX Registry](https://github.com/kdcokenny/ocx) — 플러그인 패키지 매니저
- [opencode-worktree-session](https://github.com/felixAnhalt/opencode-worktree-session) — 원본 영감을 준 프로젝트
- [git worktree 문서](https://git-scm.com/docs/git-worktree) — git worktree 공식 문서

### 관련 플러그인

- [opencode-workspace](https://github.com/kdcokenny/opencode-workspace) — 구조화된 계획 + 규칙 주입
- [opencode-background-agents](https://github.com/kdcokenny/opencode-background-agents) — 비동기 위임 + 영속 출력
- [opencode-notify](https://github.com/kdcokenny/opencode-notify) — 네이티브 OS 알림
