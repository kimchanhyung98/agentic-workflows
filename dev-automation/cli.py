#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List


DEFAULT_GATES = ["make check"]


@dataclass
class PlanContext:
    requirement: str
    repo_root: Path
    referenced_files: List[str]
    ambiguous_points: List[str]
    test_outline: List[str]


def sanitize_markdown_bullet(text: str) -> str:
    clean = " ".join(text.replace("\r", " ").splitlines()).strip()
    return clean.replace("`", "'")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Human-in-the-loop local dev automation pipeline"
    )
    parser.add_argument("--requirement", required=True, help="Task requirement text")
    parser.add_argument(
        "--repo-root",
        default=str(Path.cwd()),
        help="Repository root path (default: current directory)",
    )
    parser.add_argument(
        "--plan-path",
        default="dev-automation/PLAN.md",
        help="Path to write generated plan markdown",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="Maximum execute retries before escalation",
    )
    parser.add_argument(
        "--gate",
        action="append",
        dest="gates",
        default=[],
        help="Deterministic gate command (repeatable). Default: make check",
    )
    parser.add_argument(
        "--ralph-loop-cmd",
        default="ralph-loop",
        help="Command used to invoke Ralph Loop",
    )
    return parser.parse_args()


def collect_context(requirement: str, repo_root: Path) -> PlanContext:
    draft_docs = sorted(
        str(path.relative_to(repo_root))
        for path in repo_root.glob("docs/_draft/dev-automation/*.md")
    )
    referenced = draft_docs[:]
    if not referenced:
        referenced = ["docs/_draft/dev-automation/ (not found)"]
    ambiguous = [
        "Ralph Loop CLI 옵션(--plan, --gate 등)의 정확한 인터페이스 확인 필요",
        "실행 환경(로컬/VM/Docker) 선택 정책을 이번 실행에서 어떻게 고정할지 확인 필요",
    ]
    test_outline = [
        "기획 문서 생성 여부 및 필수 섹션 포함 확인",
        "Human Review 입력(y/r/n) 분기 동작 확인",
        "승인 시 Ralph Loop 호출 및 gate 통과 시 성공 처리 확인",
        "실패 시 최대 N회 이후 실패 리포트 생성 확인",
    ]
    return PlanContext(
        requirement=requirement.strip(),
        repo_root=repo_root,
        referenced_files=referenced,
        ambiguous_points=ambiguous,
        test_outline=test_outline,
    )


def build_plan_markdown(context: PlanContext, revision_note: str | None = None) -> str:
    now = dt.datetime.now(dt.UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    revision = ""
    if revision_note:
        revision = f"\n## 수정 요청 반영\n- {sanitize_markdown_bullet(revision_note)}\n"
    referenced = "\n".join(f"- `{path}`" for path in context.referenced_files)
    tests = "\n".join(f"- {item}" for item in context.test_outline)
    ambiguities = "\n".join(f"- {item}" for item in context.ambiguous_points)
    return f"""# PLAN: Human-in-the-Loop 로컬 개발 자동화

## 메타데이터
- 생성 시각(UTC): {now}
- 저장소 루트: `{context.repo_root}`

## 요구사항 요약
{context.requirement}

## 컨텍스트(식별 파일)
{referenced}
{revision}
## 작업 계획
1. Prepare: 요구사항과 레포 컨텍스트를 바탕으로 PLAN 문서 생성
2. Human Review: 문서를 출력하고 승인(y)/재작성(r)/중단(n) 입력 대기
3. Execute & Gate: 승인 시 Ralph Loop 실행 후 결정론적 gate(test/lint) 검증
4. Escalation: 실패 시 최대 재시도 N회를 넘기면 실패 리포트를 생성하고 종료

## 테스트 케이스 개요
{tests}

## 애매한 판단(사람 결정 필요)
{ambiguities}
"""


def write_plan(plan_path: Path, markdown: str) -> None:
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(markdown, encoding="utf-8")


def review_plan_loop(plan_markdown: str) -> tuple[str, str | None]:
    while True:
        print("\n" + "=" * 80)
        print("생성된 기획 문서(PLAN)")
        print("=" * 80)
        print(plan_markdown)
        print("=" * 80)
        choice = input("[Human Review] 승인(y) / 수정 후 재작성(r) / 중단(n): ").strip().lower()
        if choice in {"y", "n"}:
            return choice, None
        if choice == "r":
            note = input("수정 요청 사항을 입력하세요: ").strip()
            return choice, note
        print("유효하지 않은 입력입니다. y/r/n 중 하나를 입력하세요.")


def run_command(command: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    args = shlex.split(command)
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)


def run_execute_with_gates(
    repo_root: Path,
    plan_path: Path,
    ralph_loop_cmd: str,
    gates: List[str],
    max_retries: int,
) -> int:
    # Retry policy:
    # - Ralph Loop 실행 실패면 해당 attempt를 실패로 간주하고 다음 attempt로 이동
    # - Ralph Loop가 성공한 attempt에서만 deterministic gate를 실행
    # - gate 실패도 attempt 소진으로 계산하며, 마지막 허용 attempt 실패 시 실패 리포트 생성
    failure_report = repo_root / "dev-automation" / "failure-report.md"
    env = os.environ.copy()
    env["DEV_AUTOMATION_PLAN_PATH"] = str(plan_path)
    env["DEV_AUTOMATION_GATES"] = "\n".join(gates)
    env["DEV_AUTOMATION_MAX_RETRIES"] = str(max_retries)

    for attempt in range(1, max_retries + 1):
        print(f"\n[execute] attempt {attempt}/{max_retries}: {ralph_loop_cmd}")
        proc = run_command(ralph_loop_cmd, repo_root, env)
        if proc.stdout:
            print(proc.stdout.rstrip())
        if proc.returncode != 0:
            if proc.stderr:
                print(proc.stderr.rstrip(), file=sys.stderr)
            if attempt == max_retries:
                failure_report.write_text(
                    f"# Failure Report\n\n- stage: execute (ralph-loop)\n- attempt: {attempt}\n"
                    f"- command: `{ralph_loop_cmd}`\n- return_code: {proc.returncode}\n\n"
                    f"## stderr\n```\n{proc.stderr}\n```\n",
                    encoding="utf-8",
                )
                return 1
            continue

        gate_failed = False
        for gate in gates:
            print(f"[gate] {gate}")
            gate_proc = run_command(gate, repo_root, env)
            if gate_proc.stdout:
                print(gate_proc.stdout.rstrip())
            if gate_proc.returncode != 0:
                gate_failed = True
                if gate_proc.stderr:
                    print(gate_proc.stderr.rstrip(), file=sys.stderr)
                if attempt == max_retries:
                    failure_report.write_text(
                        f"# Failure Report\n\n- stage: deterministic gate\n- attempt: {attempt}\n"
                        f"- gate: `{gate}`\n- return_code: {gate_proc.returncode}\n\n"
                        f"## stderr\n```\n{gate_proc.stderr}\n```\n",
                        encoding="utf-8",
                    )
                    return 1
                break
        if not gate_failed:
            print("[execute] success: ralph-loop + deterministic gates passed")
            return 0

    return 1  # safety fallback


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    plan_path = (repo_root / args.plan_path).resolve()
    gates = args.gates if args.gates else DEFAULT_GATES

    context = collect_context(args.requirement, repo_root)
    plan_markdown = build_plan_markdown(context)

    while True:
        write_plan(plan_path, plan_markdown)
        choice, note = review_plan_loop(plan_markdown)
        if choice == "y":
            break
        if choice == "n":
            print("[pipeline] 중단되었습니다. 코드 실행 단계로 진행하지 않습니다.")
            return 2
        plan_markdown = build_plan_markdown(context, revision_note=note)

    return run_execute_with_gates(
        repo_root=repo_root,
        plan_path=plan_path,
        ralph_loop_cmd=args.ralph_loop_cmd,
        gates=gates,
        max_retries=max(1, args.max_retries),
    )


if __name__ == "__main__":
    raise SystemExit(main())
