from __future__ import annotations

import argparse
from pathlib import Path

from .backend import ClaudeCodeBackend, EchoBackend
from .workflow import DevAutomationWorkflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dev-automation", description="Local development automation workflow")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--workspace", default="dev-automation", help="Workspace directory path")

    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Create review-ready planning documents")
    prepare_input = prepare.add_mutually_exclusive_group(required=True)
    prepare_input.add_argument("--requirement", help="Requirement text")
    prepare_input.add_argument("--requirement-file", help="Path to requirement text file")

    approve = subparsers.add_parser("approve", help="Approve prepared plan")
    approve.add_argument("--plan", required=True, help="Plan markdown path")
    approve.add_argument("--approver", required=True, help="Approver name")
    approve.add_argument("--note", default="", help="Optional approval note")

    execute = subparsers.add_parser("execute", help="Run implementation and verification loop")
    execute.add_argument("--plan", required=True, help="Approved plan markdown path")
    execute.add_argument(
        "--verify-cmd",
        action="append",
        default=[],
        help="Verification command (repeatable). Defaults to `make check` if omitted.",
    )
    execute.add_argument("--max-attempts", type=int, default=2, help="Maximum auto-fix retries")
    execute.add_argument(
        "--backend",
        choices=["echo", "claude"],
        default="echo",
        help="Execution backend type",
    )

    show = subparsers.add_parser("show", help="Print plan document for user review")
    show.add_argument("--plan", required=True, help="Plan markdown path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    workspace = Path(args.workspace)
    if not workspace.is_absolute():
        workspace = (repo_root / workspace).resolve()

    workflow = DevAutomationWorkflow(repo_root=repo_root, workspace_dir=workspace)

    if args.command == "prepare":
        if args.requirement:
            requirement = args.requirement
        else:
            requirement = Path(args.requirement_file).read_text(encoding="utf-8")
        artifacts = workflow.prepare(requirement)
        print(f"PLAN={artifacts.plan_path}")
        print(f"REVIEW_SUMMARY={artifacts.review_summary_path}")
        for detail in artifacts.review_detail_paths:
            print(f"REVIEW_DETAIL={detail}")
        print("NEXT=사용자 리뷰 및 승인 후 execute 실행")
        return 0

    if args.command == "approve":
        approval_path = workflow.approve(Path(args.plan).resolve(), args.approver, args.note)
        print(f"APPROVAL={approval_path}")
        return 0

    if args.command == "execute":
        verify_commands = args.verify_cmd or ["make check"]
        backend = EchoBackend() if args.backend == "echo" else ClaudeCodeBackend()
        result = workflow.execute(
            plan_path=Path(args.plan).resolve(),
            verify_commands=verify_commands,
            backend=backend,
            max_attempts=args.max_attempts,
        )
        status = "SUCCESS" if result.success else "FAILURE"
        print(f"STATUS={status}")
        print(f"REPORT={result.report_path}")
        print(f"ATTEMPTS={result.attempts}")
        return 0 if result.success else 1

    if args.command == "show":
        print(Path(args.plan).read_text(encoding="utf-8"))
        return 0

    parser.error("Unknown command")


if __name__ == "__main__":
    raise SystemExit(main())
