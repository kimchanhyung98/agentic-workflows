from __future__ import annotations

import concurrent.futures
import errno
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List

from config import AnalysisConfig, ReviewRole


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
            futures = [pool.submit(self.reviewer_runner, self._reviewer_prompt(role, prompt)) for role in self.config.reviewers]
            for future in concurrent.futures.as_completed(futures):
                outputs.append(future.result())

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
        base_command = shlex.split(self.config.claude_command)
        command_with_arg = [*base_command, "-p", prompt]
        try:
            completed = subprocess.run(command_with_arg, capture_output=True, text=True, check=False)
        except OSError as exc:
            if exc.errno != errno.E2BIG:
                return (
                    "[중간] Claude CLI 호출 실패\n"
                    f"- error: {exc}"
                )
            command_with_stdin = [*base_command, "-p"]
            completed = subprocess.run(command_with_stdin, input=prompt, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            return (
                "[중간] Claude CLI 호출 실패\n"
                f"- error: exit code={completed.returncode}, stderr={completed.stderr.strip()}"
            )
        return completed.stdout.strip()

    def _summarize_reports(self, stage_name: str, report_paths: List[Path]) -> str:
        severity_counter = {"심각": 0, "높음": 0, "중간": 0, "낮음": 0}
        collected = []

        for path in report_paths:
            text = path.read_text(encoding="utf-8")
            collected.append(f"## {path.stem}\n\n{text}")
            for key in severity_counter:
                severity_counter[key] += len(re.findall(rf"\[{key}\]", text))

        severity_lines = "\n".join(f"- {key}: {count}" for key, count in severity_counter.items())
        return f"# {stage_name} summary\n\n{severity_lines}\n\n" + "\n\n".join(collected)

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
        total = {
            "심각": len(re.findall(r"\[심각\]", merged)),
            "높음": len(re.findall(r"\[높음\]", merged)),
            "중간": len(re.findall(r"\[중간\]", merged)),
            "낮음": len(re.findall(r"\[낮음\]", merged)),
        }

        header = (
            "# Deep Analysis Final Report\n\n"
            "## Severity Summary\n"
            f"- 심각: {total['심각']}\n"
            f"- 높음: {total['높음']}\n"
            f"- 중간: {total['중간']}\n"
            f"- 낮음: {total['낮음']}\n\n"
            "## Stage Details\n\n"
        )
        return header + merged
