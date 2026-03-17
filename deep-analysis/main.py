from __future__ import annotations

import argparse
from pathlib import Path

from config import load_config
from review_pipeline import ReviewPipeline
from xml_bundler import XmlBundler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deep Analysis pipeline")
    parser.add_argument("--project-root", type=Path, required=True, help="분석할 프로젝트 루트 경로")
    parser.add_argument("--output-dir", type=Path, default=Path("./deep-analysis/output"), help="산출물 디렉토리")
    parser.add_argument("--config", type=Path, help="JSON 설정 파일")
    parser.add_argument("--print-design", action="store_true", help="Layer 2/3 구현 설계를 출력")
    return parser


def design_text() -> str:
    return (
        "[Layer 2 - XML Bundling 설계]\n"
        "1) .gitignore + 사용자 exclude를 합쳐 텍스트 파일만 수집\n"
        "2) 1단계: 파일별 XML(review target) + import/참조 context 파일 포함\n"
        "3) 2단계: 도메인별 XML(review domain) 생성 (설정 기반 또는 자동 그룹핑)\n"
        "4) 3단계 입력 준비: 프로젝트 구조 + 설정파일 + 이전 단계 요약을 project XML에 포함\n\n"
        "[Layer 3 - 점진적 리뷰 설계]\n"
        "1) 1단계 파일 리뷰를 병렬 리뷰어(보안/품질/성능)로 실행\n"
        "2) 1단계 요약(summary.md)을 2단계 프롬프트 context로 주입\n"
        "3) 2단계 요약(summary.md)을 3단계 프롬프트 context로 주입\n"
        "4) 3개 단계 summary를 합쳐 final-report.md 생성 (심각도 집계 포함)"
    )


def run_pipeline(project_root: Path, output_dir: Path, config_path: Path | None) -> Path:
    config = load_config(config_path=config_path, project_root=project_root.resolve(), output_dir=output_dir.resolve())

    bundler = XmlBundler(config)
    source_files = bundler.collect_source_files()

    bundle_root = output_dir / "bundles"
    stage1_xml = bundler.bundle_file_stage(source_files, bundle_root / "stage1")
    stage2_xml = bundler.bundle_domain_stage(source_files, bundle_root / "stage2")

    pipeline = ReviewPipeline(config)

    stage1_result = pipeline.run_single_stage(
        stage_name="stage1-file-review",
        xml_paths=stage1_xml,
        context_text="",
        output_dir=output_dir / "reviews" / "stage1",
    )

    stage1_summary = stage1_result.summary_path.read_text(encoding="utf-8")
    stage2_result = pipeline.run_single_stage(
        stage_name="stage2-domain-review",
        xml_paths=stage2_xml,
        context_text=stage1_summary,
        output_dir=output_dir / "reviews" / "stage2",
    )

    stage2_summary = stage2_result.summary_path.read_text(encoding="utf-8")

    project_xml = bundler.bundle_project_stage(
        source_files=source_files,
        stage1_summary=stage1_summary,
        stage2_summary=stage2_summary,
        output_path=bundle_root / "stage3" / "project.xml",
    )

    stage3_result = pipeline.run_single_stage(
        stage_name="stage3-project-review",
        xml_paths=[project_xml],
        context_text=f"{stage1_summary}\n\n{stage2_summary}",
        output_dir=output_dir / "reviews" / "stage3",
    )

    final_report = pipeline.build_final_report(
        stage_results=[stage1_result, stage2_result, stage3_result],
        output_path=output_dir / "reviews" / "final-report.md",
    )

    return final_report


def main() -> int:
    args = build_parser().parse_args()

    if args.print_design:
        print(design_text())

    final_report = run_pipeline(args.project_root, args.output_dir, args.config)
    print(f"Deep Analysis complete: {final_report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
