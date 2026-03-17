from __future__ import annotations

import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .collector import build_domains, collect_project_files, resolve_imports, CONFIG_FILE_NAMES
from .config import AnalysisConfig
from .review_backend import ClaudeCodeCLIBackend, ReviewBackend, StubReviewBackend
from .xml_bundler import build_domain_bundle, build_file_bundle, build_project_bundle

logger = logging.getLogger(__name__)

SEVERITY_ORDER = ["심각", "높음", "중간", "낮음"]
SEVERITY_PATTERN = re.compile(r"\[(심각|높음|중간|낮음)\]\s*(.+)")
MAX_CONTEXT_FILES = 2
STAGE2_SUMMARY_LIMIT = 1200
STAGE3_SUMMARY_LIMIT = 1800
MAX_REVIEWER_WORKERS = 3


def _truncate_to_line(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_newline = truncated.rfind("\n")
    if last_newline > 0:
        return truncated[:last_newline]
    return truncated


def _extract_severity_lines(text: str, max_chars: int) -> str:
    lines = []
    total = 0
    for line in text.splitlines():
        if SEVERITY_PATTERN.search(line):
            if total + len(line) + 1 > max_chars:
                break
            lines.append(line)
            total += len(line) + 1
    return "\n".join(lines) if lines else _truncate_to_line(text, max_chars)


def _extract_domain_stage1(stage1_doc: str, domain_files: list[Path], project_path: Path, max_chars: int) -> str:
    """Stage 1 문서에서 도메인에 속한 파일의 리뷰 섹션만 추출한다."""
    domain_paths = {f.relative_to(project_path).as_posix() for f in domain_files}
    result_lines: list[str] = []
    total = 0
    capturing = False

    for line in stage1_doc.splitlines():
        if line.startswith("## "):
            file_path = line[3:].strip()
            capturing = file_path in domain_paths
        if capturing:
            if total + len(line) + 1 > max_chars:
                break
            result_lines.append(line)
            total += len(line) + 1

    return "\n".join(result_lines) if result_lines else _extract_severity_lines(stage1_doc, max_chars)


@dataclass
class AnalysisResult:
    output_path: Path
    stage1_path: Path
    stage2_path: Path
    stage3_path: Path
    final_report_path: Path


class DeepAnalysisPipeline:
    def __init__(self, config: AnalysisConfig, backend: ReviewBackend | None = None):
        self.config = config
        self.backend = backend or self._default_backend(config.backend)

    def _default_backend(self, backend_name: str) -> ReviewBackend:
        if backend_name == "stub":
            return StubReviewBackend()
        return ClaudeCodeCLIBackend()

    def run(self) -> AnalysisResult:
        files = collect_project_files(
            self.config.project_path,
            self.config.exclude_patterns,
            self.config.target_languages,
        )
        domains = build_domains(files, self.config.project_path, self.config.domains)

        output_path = self.config.output_path
        output_path.mkdir(parents=True, exist_ok=True)

        stage1_path = output_path / "stage1-file-review.md"
        stage2_path = output_path / "stage2-domain-review.md"
        stage3_path = output_path / "stage3-project-review.md"
        final_report_path = output_path / "final-review-report.md"

        logger.info("1단계 파일 리뷰 시작 (%d개 파일)", len(files))
        stage1_doc = self._run_stage1(files)
        stage1_path.write_text(stage1_doc, encoding="utf-8")

        logger.info("2단계 도메인 리뷰 시작 (%d개 도메인)", len(domains))
        stage2_doc = self._run_stage2(domains, stage1_doc)
        stage2_path.write_text(stage2_doc, encoding="utf-8")

        logger.info("3단계 프로젝트 리뷰 시작")
        stage3_doc = self._run_stage3(files, stage1_doc, stage2_doc)
        stage3_path.write_text(stage3_doc, encoding="utf-8")

        final_doc = self._build_final_report(stage1_doc, stage2_doc, stage3_doc)
        final_report_path.write_text(final_doc, encoding="utf-8")
        logger.info("최종 리포트 생성 완료: %s", final_report_path)

        return AnalysisResult(output_path, stage1_path, stage2_path, stage3_path, final_report_path)

    def _review_parallel(self, stage: str, bundle: str) -> dict[str, str]:
        results: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=MAX_REVIEWER_WORKERS) as executor:
            futures = {
                executor.submit(self.backend.review, stage, reviewer, bundle): reviewer
                for reviewer in self.config.reviewers
            }
            for future in as_completed(futures):
                reviewer = futures[future]
                try:
                    results[reviewer] = future.result()
                except RuntimeError as e:
                    logger.error("%s 리뷰 실패: reviewer=%s — %s", stage, reviewer, e)
                    results[reviewer] = f"[리뷰 실패: {e}]"
        return results

    def _run_stage1(self, files: list[Path]) -> str:
        lines = ["# 1단계 파일 리뷰"]
        for idx, file_path in enumerate(files, 1):
            relative = file_path.relative_to(self.config.project_path).as_posix()
            logger.info("stage1: 파일 %d/%d 리뷰 중: %s", idx, len(files), relative)
            lines.append(f"\n## {relative}")
            context_files = resolve_imports(file_path, files, MAX_CONTEXT_FILES)
            bundle = build_file_bundle(self.config.project_path, file_path, context_files)
            for reviewer, result in self._review_parallel("stage1", bundle).items():
                lines.append(f"\n### [{reviewer}]")
                lines.append(result)
        return "\n".join(lines)

    def _run_stage2(self, domains: dict[str, list[Path]], stage1_doc: str) -> str:
        lines = ["# 2단계 도메인 리뷰"]
        for domain, domain_files in domains.items():
            logger.info("stage2: 도메인 리뷰 중: %s (%d개 파일)", domain, len(domain_files))
            lines.append(f"\n## {domain}")
            domain_summary = _extract_domain_stage1(
                stage1_doc, domain_files, self.config.project_path, STAGE2_SUMMARY_LIMIT,
            )
            bundle = build_domain_bundle(
                self.config.project_path, domain, domain_files, domain_summary,
            )
            for reviewer, result in self._review_parallel("stage2", bundle).items():
                lines.append(f"\n### [{reviewer}]")
                lines.append(result)
        return "\n".join(lines)

    def _run_stage3(self, files: list[Path], stage1_doc: str, stage2_doc: str) -> str:
        lines = ["# 3단계 프로젝트 리뷰"]
        config_files = [
            file_path
            for file_path in files
            if file_path.name in CONFIG_FILE_NAMES
        ]
        bundle = build_project_bundle(
            self.config.project_name,
            self.config.project_path,
            files,
            config_files,
            _extract_severity_lines(stage1_doc, STAGE3_SUMMARY_LIMIT),
            _extract_severity_lines(stage2_doc, STAGE3_SUMMARY_LIMIT),
        )
        for reviewer, result in self._review_parallel("stage3", bundle).items():
            lines.append(f"\n## [{reviewer}]")
            lines.append(result)
        return "\n".join(lines)

    def _build_final_report(self, stage1_doc: str, stage2_doc: str, stage3_doc: str) -> str:
        findings = []
        for document in (stage1_doc, stage2_doc, stage3_doc):
            for line in document.splitlines():
                matched = SEVERITY_PATTERN.search(line)
                if matched:
                    findings.append((matched.group(1), matched.group(2).strip()))

        severity_count = {severity: 0 for severity in SEVERITY_ORDER}
        for severity, _ in findings:
            severity_count[severity] += 1

        report_lines = [
            "# Deep Analysis 최종 리뷰 리포트",
            "",
            "## 요약",
            f"- 총 이슈 수: {len(findings)}",
        ]
        for severity in SEVERITY_ORDER:
            report_lines.append(f"- {severity}: {severity_count[severity]}")

        report_lines.extend(["", "## 이슈 목록 (심각도순)"])
        for severity in SEVERITY_ORDER:
            report_lines.append(f"\n### {severity}")
            issue_lines = [description for item_severity, description in findings if item_severity == severity]
            if not issue_lines:
                report_lines.append("- 없음")
                continue
            for issue in issue_lines:
                report_lines.append(f"- {issue}")

        report_lines.extend(
            [
                "",
                "## Assumption / TODO",
                "- 기능 도메인 자동 그룹핑은 디렉토리 기반 기본값을 사용하고, config.domains로 수동 오버라이드한다.",
                "- Claude Code CLI 호출 형식은 `claude --print`를 기본 가정으로 구현했다.",
                "- Ralph loop는 필수 런타임 의존성으로 도입하지 않았다(반복 실행 구조 참고는 문서 TODO로 남김).",
            ]
        )
        return "\n".join(report_lines)
