from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .config import AnalysisConfig
from .pipeline import DeepAnalysisPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Deep Analysis for a project")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="[deep-analysis] %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )

    config_path = Path(args.config)

    try:
        config = AnalysisConfig.from_json_file(config_path)
    except FileNotFoundError:
        print(f"[error] 설정 파일을 찾을 수 없습니다: {config_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"[error] JSON 파싱 실패 ({config_path}): {e}", file=sys.stderr)
        return 1
    except KeyError as e:
        print(f"[error] 필수 설정 항목 누락: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"[error] 설정 검증 실패: {e}", file=sys.stderr)
        return 1

    try:
        result = DeepAnalysisPipeline(config).run()
    except RuntimeError as e:
        print(f"[error] 분석 실패: {e}", file=sys.stderr)
        return 1

    print("[deep-analysis] completed")
    print(f"- output: {result.output_path}")
    print(f"- stage1: {result.stage1_path}")
    print(f"- stage2: {result.stage2_path}")
    print(f"- stage3: {result.stage3_path}")
    print(f"- final: {result.final_report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
