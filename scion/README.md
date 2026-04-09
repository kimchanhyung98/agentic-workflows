# Google Scion 분석

`GoogleCloudPlatform/scion`의 공개 저장소와 공식 문서를 기반으로, 멀티 에이전트 실행 모델과 운영 구조를 정리한 문서입니다.

Scion은 Claude Code/Gemini/Codex 같은 에이전트 하네스를 컨테이너 단위로 격리해 병렬 실행하고, 로컬 모드(worktree)와 Hub 모드(중앙 제어) 모두를 지원하는 실험적 오케스트레이션 테스트베드입니다.

---

## 문서 구성

| 문서                               | 내용                                                        |
|----------------------------------|-----------------------------------------------------------|
| [아키텍처 다이어그램](/scion/00-diagram.md) | 계층 구조, 로컬/Hub 실행 흐름, Kubernetes 런타임 흐름                 |
| [심층 분석](/scion/01-analysis.md)       | 핵심 개념, 설계 철학, 실행 모델, 장단점, 도입 체크리스트, 실무 적용 관점 분석 |

---

## 아키텍처 개요

```text
User / Operator
  ↓
Scion CLI (start, attach, message, logs, sync)
  ↓
Grove (.scion) + Template + Profile
  ↓
Runtime Layer (Docker / Podman / Apple container / Kubernetes)
  ↓
Agent Containers (Gemini / Claude / Codex / OpenCode harness)
  ├─ isolated home/credentials
  ├─ isolated workspace (worktree or git init+fetch)
  └─ tmux session + OTEL telemetry

[Optional]
Scion Hub (control plane) + Runtime Broker (distributed execution)
```

### 핵심 포인트

- **격리 우선 멀티 에이전트**: 에이전트별 컨테이너/자격증명/작업공간 분리
- **Harness agnostic**: Gemini, Claude, Codex, OpenCode 등 하네스 추상화
- **2가지 워크스페이스 전략**: 로컬은 git worktree, Hub 연동은 git init+fetch
- **확장형 런타임**: 로컬 Docker/Podman부터 Kubernetes까지 동일 CLI로 제어
- **운영 중심 기능**: attach/detach, 메시지 큐잉, resume, telemetry/metrics

---

## 참고 자료

- [Scion GitHub 저장소](https://github.com/GoogleCloudPlatform/scion)
- [Scion Overview](https://googlecloudplatform.github.io/scion/overview/)
- [Scion Concepts](https://googlecloudplatform.github.io/scion/concepts/)
- [Scion Philosophy](https://googlecloudplatform.github.io/scion/philosophy/)
- [Supported Harnesses](https://googlecloudplatform.github.io/scion/supported-harnesses/)
- [Installation Guide](https://googlecloudplatform.github.io/scion/getting-started/install/)
- [Kubernetes Runtime](https://googlecloudplatform.github.io/scion/hub-admin/kubernetes/)
- [뉴스 링크(원문)](https://news.hada.io/topic?id=28307)
