from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone
from pathlib import Path

from main import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ralph Loop style Deep Analysis entrypoint")
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("./deep-analysis/output"))
    parser.add_argument("--config", type=Path)
    parser.add_argument("--loop", action="store_true", help="지속 실행 모드")
    parser.add_argument("--interval-seconds", type=int, default=1800, help="loop 주기")
    return parser.parse_args()


def run_once(project_root: Path, output_dir: Path, config_path: Path | None) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_dir / stamp
    return run_pipeline(project_root=project_root, output_dir=run_dir, config_path=config_path)


def main() -> int:
    args = parse_args()
    if not args.loop:
        final_report = run_once(args.project_root, args.output_dir, args.config)
        print(f"one-shot completed: {final_report}")
        return 0

    while True:
        try:
            final_report = run_once(args.project_root, args.output_dir, args.config)
            print(f"loop completed: {final_report}")
        except Exception as exc:  # noqa: BLE001
            print(f"loop error: {exc}")
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
