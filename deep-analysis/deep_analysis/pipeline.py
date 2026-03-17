from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .collector import build_domains, collect_project_files
from .config import AnalysisConfig
from .review_backend import ClaudeCodeCLIBackend, ReviewBackend, StubReviewBackend
from .xml_bundler import build_domain_bundle, build_file_bundle, build_project_bundle

SEVERITY_ORDER = ["심각", "높음", "중간", "낮음"]
SEVERITY_PATTERN = re.compile(r"\[(심각|높음|중간|낮음)\]\s*(.+)")
MAX_CONTEXT_FILES = 2
STAGE2_SUMMARY_LIMIT = 1200
STAGE3_SUMMARY_LIMIT = 1800
CONFIG_FILE_NAMES = {"pyproject.toml", "package.json", "settings.py", "urls.py", "Makefile"}


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

        stage1_doc = self._run_stage1(files)
        stage1_path.write_text(stage1_doc, encoding="utf-8")

        stage2_doc = self._run_stage2(domains, stage1_doc)
        stage2_path.write_text(stage2_doc, encoding="utf-8")

        stage3_doc = self._run_stage3(files, stage1_doc, stage2_doc)
        stage3_path.write_text(stage3_doc, encoding="utf-8")

        final_doc = self._build_final_report(stage1_doc, stage2_doc, stage3_doc)
        final_report_path.write_text(final_doc, encoding="utf-8")

        return AnalysisResult(output_path, stage1_path, stage2_path, stage3_path, final_report_path)

    def _run_stage1(self, files: list[Path]) -> str:
        lines = ["# 1단계 파일 리뷰"]
        for file_path in files:
            lines.append(f"\n## {file_path.relative_to(self.config.project_path).as_posix()}")
            context_files = [path for path in files if path != file_path][:MAX_CONTEXT_FILES]
            bundle = build_file_bundle(self.config.project_path, file_path, context_files)
            for reviewer in self.config.reviewers:
                lines.append(f"\n### [{reviewer}]")
                lines.append(self.backend.review("stage1", reviewer, bundle))
        return "\n".join(lines)

    def _run_stage2(self, domains: dict[str, list[Path]], stage1_doc: str) -> str:
        lines = ["# 2단계 도메인 리뷰"]
        for domain, domain_files in domains.items():
            lines.append(f"\n## {domain}")
            bundle = build_domain_bundle(self.config.project_path, domain, domain_files)
            bundle_with_previous = f"{bundle}\n<!-- stage1-summary -->\n{stage1_doc[:STAGE2_SUMMARY_LIMIT]}"
            for reviewer in self.config.reviewers:
                lines.append(f"\n### [{reviewer}]")
                lines.append(self.backend.review("stage2", reviewer, bundle_with_previous))
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
            stage1_doc[:STAGE3_SUMMARY_LIMIT],
            stage2_doc[:STAGE3_SUMMARY_LIMIT],
        )
        for reviewer in self.config.reviewers:
            lines.append(f"\n## [{reviewer}]")
            lines.append(self.backend.review("stage3", reviewer, bundle))
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
                "## 주요 발견",
                "- TODO: 도메인 간 반복 패턴을 별도 요약(Assumption: 현재는 심각도 목록 중심으로 제공)",
                "",
                "## 긍정적 측면",
                "- TODO: 리뷰어 응답에서 긍정 항목을 구조적으로 추출하도록 개선 필요",
                "",
                "## Assumption / TODO",
                "- 기능 도메인 자동 그룹핑은 디렉토리 기반 기본값을 사용하고, config.domains로 수동 오버라이드한다.",
                "- Claude Code CLI 호출 형식은 `claude --print`를 기본 가정으로 구현했다.",
                "- Ralph loop는 필수 런타임 의존성으로 도입하지 않았다(반복 실행 구조 참고는 문서 TODO로 남김).",
            ]
        )
        return "\n".join(report_lines)
