from __future__ import annotations

import argparse
from pathlib import Path

from .config import AnalysisConfig
from .pipeline import DeepAnalysisPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Deep Analysis for a project")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config = AnalysisConfig.from_json_file(Path(args.config))
    result = DeepAnalysisPipeline(config).run()

    print("[deep-analysis] completed")
    print(f"- output: {result.output_path}")
    print(f"- stage1: {result.stage1_path}")
    print(f"- stage2: {result.stage2_path}")
    print(f"- stage3: {result.stage3_path}")
    print(f"- final: {result.final_report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
