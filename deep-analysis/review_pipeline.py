from __future__ import annotations

import concurrent.futures
import errno
import logging
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List

from config import AnalysisConfig, ReviewRole

logger = logging.getLogger(__name__)

SEVERITY_ORDER = ["심각", "높음", "중간", "낮음"]


@dataclass
class StageResult:
    stage_name: str
    report_paths: List[Path]
    summary_path: Path


class ReviewPipeline:
    def __init__(self, config: AnalysisConfig, reviewer_runner: Callable[[str], str] | None = None) -> None:
        self.config = config
        self.reviewer_runner = reviewer_runner or self._run_claude

    def run(
        self,
        stage1_xml_paths: Iterable[Path],
        stage2_xml_paths: Iterable[Path],
        project_xml_path: Path,
        output_dir: Path,
    ) -> Dict[str, StageResult]:
        output_dir.mkdir(parents=True, exist_ok=True)

        stage1 = self._run_stage(
            stage_name="stage1-file-review",
            xml_paths=list(stage1_xml_paths),
            context_text="",
            output_dir=output_dir / "stage1",
        )

        stage1_summary = stage1.summary_path.read_text(encoding="utf-8")
        stage2 = self._run_stage(
            stage_name="stage2-domain-review",
            xml_paths=list(stage2_xml_paths),
            context_text=stage1_summary,
            output_dir=output_dir / "stage2",
        )

        stage2_summary = stage2.summary_path.read_text(encoding="utf-8")
        stage3 = self._run_stage(
            stage_name="stage3-project-review",
            xml_paths=[project_xml_path],
            context_text=f"{stage1_summary}\n\n{stage2_summary}",
            output_dir=output_dir / "stage3",
        )

        final_report = output_dir / "final-report.md"
        final_report.write_text(
            self._build_final_report([stage1.summary_path, stage2.summary_path, stage3.summary_path]),
            encoding="utf-8",
        )

        return {
            "stage1": stage1,
            "stage2": stage2,
            "stage3": stage3,
            "final": StageResult("final", [final_report], final_report),
        }

    def run_single_stage(self, stage_name: str, xml_paths: List[Path], context_text: str, output_dir: Path) -> StageResult:
        return self._run_stage(stage_name, xml_paths, context_text, output_dir)

    def build_final_report(self, stage_results: List[StageResult], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            self._build_final_report([r.summary_path for r in stage_results]),
            encoding="utf-8",
        )
        return output_path

    def _run_stage(self, stage_name: str, xml_paths: List[Path], context_text: str, output_dir: Path) -> StageResult:
        output_dir.mkdir(parents=True, exist_ok=True)
        report_paths: List[Path] = []

        for xml_path in xml_paths:
            xml_text = xml_path.read_text(encoding="utf-8")
            prompt = self._build_prompt(stage_name, xml_text, context_text)
            review_text = self._run_parallel_reviewers(prompt)
            report_path = output_dir / f"{xml_path.stem}.md"
            report_path.write_text(review_text, encoding="utf-8")
            report_paths.append(report_path)

        summary_path = output_dir / "summary.md"
        summary_path.write_text(self._summarize_reports(stage_name, report_paths), encoding="utf-8")
        return StageResult(stage_name=stage_name, report_paths=report_paths, summary_path=summary_path)

    def _run_parallel_reviewers(self, prompt: str) -> str:
        outputs: List[str] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.config.reviewers)) as pool:
            futures = {
                pool.submit(self.reviewer_runner, self._reviewer_prompt(role, prompt)): role
                for role in self.config.reviewers
            }
            for future in concurrent.futures.as_completed(futures):
                role = futures[future]
                try:
                    outputs.append(future.result())
                except Exception as exc:  # noqa: BLE001
                    logger.warning("reviewer '%s' failed: %s", role.name, exc)
                    outputs.append(
                        f"[중간] {role.name} 리뷰어 실행 실패\n"
                        f"- error: {exc}"
                    )

        deduped = self._dedupe_issues(outputs)
        return "\n\n".join(deduped)

    def _reviewer_prompt(self, role: ReviewRole, prompt: str) -> str:
        return (
            f"당신은 {role.name} 리뷰어입니다.\n"
            f"리뷰 관점: {role.focus}\n"
            "출력 형식: [심각도] 제목\n- 근거\n- 개선 제안\n"
            "이미 context에 있는 중복 지적은 피하고 새로운 발견 위주로 작성하세요.\n\n"
            f"{prompt}"
        )

    def _build_prompt(self, stage_name: str, xml_text: str, context_text: str) -> str:
        context_block = context_text.strip() if context_text.strip() else "(없음)"
        return (
            f"단계: {stage_name}\n"
            "목표: XML 번들을 기반으로 Deep Analysis 리뷰를 수행하세요.\n"
            "규칙: 코드 변경 제안은 구체적 경로와 개선안을 포함하세요.\n"
            f"이전 단계 context:\n{context_block}\n\n"
            f"입력 XML:\n{xml_text}"
        )

    def _run_claude(self, prompt: str) -> str:
        timeout = self.config.claude_timeout_seconds
        base_command = shlex.split(self.config.claude_command)
        command_with_arg = [*base_command, "-p", prompt]
        try:
            completed = subprocess.run(
                command_with_arg, capture_output=True, text=True, check=False, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return (
                "[심각] Claude CLI 타임아웃\n"
                f"- {timeout}초 내에 응답하지 않았습니다"
            )
        except OSError as exc:
            if exc.errno != errno.E2BIG:
                return (
                    "[중간] Claude CLI 호출 실패\n"
                    f"- error: {exc}"
                )
            try:
                completed = subprocess.run(
                    base_command, input=prompt, capture_output=True, text=True, check=False, timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                return (
                    "[심각] Claude CLI 타임아웃 (stdin 폴백)\n"
                    f"- {timeout}초 내에 응답하지 않았습니다"
                )
        if completed.returncode != 0:
            return (
                "[중간] Claude CLI 호출 실패\n"
                f"- error: exit code={completed.returncode}, stderr={completed.stderr.strip()}"
            )
        output = completed.stdout.strip()
        if not output:
            logger.warning("Claude CLI returned empty output")
        return output

    def _summarize_reports(self, stage_name: str, report_paths: List[Path]) -> str:
        severity_counter = {key: 0 for key in SEVERITY_ORDER}
        collected: List[str] = []

        for path in report_paths:
            text = path.read_text(encoding="utf-8")
            collected.append(f"## {path.stem}\n\n{text}")
            for key in severity_counter:
                severity_counter[key] += len(re.findall(rf"\[{key}\]", text))

        severity_lines = "\n".join(f"- {key}: {count}" for key, count in severity_counter.items())
        body = "\n\n".join(collected)

        budget = self.config.max_summary_chars
        header = f"# {stage_name} summary\n\n{severity_lines}\n\n"

        if len(header) + len(body) <= budget:
            return header + body

        available = budget - len(header)
        truncated = self._truncate_by_severity(collected, available)
        omitted = len(collected) - len(truncated)
        truncated_body = "\n\n".join(truncated)
        if omitted > 0:
            truncated_body += f"\n\n[... {omitted}개 리포트 생략 (budget 초과)]"
        return header + truncated_body

    def _truncate_by_severity(self, sections: List[str], budget: int) -> List[str]:
        scored: List[tuple[int, int, str]] = []
        for idx, section in enumerate(sections):
            score = 0
            for rank, key in enumerate(SEVERITY_ORDER):
                count = len(re.findall(rf"\[{key}\]", section))
                score += count * (100 - rank * 20)
            scored.append((score, idx, section))

        scored.sort(key=lambda t: t[0], reverse=True)

        kept: List[tuple[int, str]] = []
        total = 0
        for score, idx, section in scored:
            if total + len(section) > budget:
                break
            kept.append((idx, section))
            total += len(section)

        kept.sort(key=lambda t: t[0])
        return [section for _, section in kept]

    def _dedupe_issues(self, reviewer_outputs: List[str]) -> List[str]:
        seen: set[str] = set()
        deduped: List[str] = []
        for output in reviewer_outputs:
            normalized = re.sub(r"\s+", " ", output).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                deduped.append(output.strip())
        return deduped

    def _build_final_report(self, summary_paths: List[Path]) -> str:
        sections = []
        for summary_path in summary_paths:
            sections.append(summary_path.read_text(encoding="utf-8"))

        merged = "\n\n---\n\n".join(sections)
        total = {key: len(re.findall(rf"\[{key}\]", merged)) for key in SEVERITY_ORDER}

        header = (
            "# Deep Analysis Final Report\n\n"
            "## Severity Summary\n"
            + "\n".join(f"- {key}: {count}" for key, count in total.items())
            + "\n\n## Stage Details\n\n"
        )
        return header + merged
