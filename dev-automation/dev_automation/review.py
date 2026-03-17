from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass
class ReviewResult:
    reviewer: str
    passed: bool
    comments: List[str]


class Reviewer:
    name = "reviewer"

    def review(self, plan_markdown: str) -> ReviewResult:
        raise NotImplementedError


class ChecklistReviewer(Reviewer):
    name = "checklist"

    _required_sections = [
        "## 현재 프로젝트 구조와 사용 언어",
        "## 기존 CLI / 설정 / 문서 구조와의 통합 지점",
        "## dev-automation 기능 권장 구조",
        "## MVP 범위",
        "## 작업 계획",
        "## 테스트 개요",
        "## Assumption / TODO",
    ]

    def review(self, plan_markdown: str) -> ReviewResult:
        missing = [section for section in self._required_sections if section not in plan_markdown]
        comments = [f"필수 섹션 누락: {section}" for section in missing]
        if not comments:
            comments.append("필수 섹션이 모두 포함되어 있습니다.")
        return ReviewResult(reviewer=self.name, passed=not missing, comments=comments)


class MultiReviewer:
    def __init__(self, reviewers: Iterable[Reviewer]):
        self.reviewers = list(reviewers)

    def run(self, plan_markdown: str) -> List[ReviewResult]:
        return [reviewer.review(plan_markdown) for reviewer in self.reviewers]

    @staticmethod
    def write_results(results: List[ReviewResult], output_dir: Path, plan_stem: str) -> tuple[Path, List[Path]]:
        detail_paths: List[Path] = []
        for result in results:
            detail_path = output_dir / f"{plan_stem}.review.{result.reviewer}.md"
            detail_path.write_text(
                "\n".join(
                    [
                        f"# Review - {result.reviewer}",
                        "",
                        f"- 판정: {'PASS' if result.passed else 'FAIL'}",
                        "- 코멘트:",
                        *[f"  - {comment}" for comment in result.comments],
                    ]
                ),
                encoding="utf-8",
            )
            detail_paths.append(detail_path)

        summary_path = output_dir / f"{plan_stem}.review.summary.md"
        overall_passed = all(result.passed for result in results)
        summary_path.write_text(
            "\n".join(
                [
                    "# Multi Review Summary",
                    "",
                    f"- Overall: {'PASS' if overall_passed else 'FAIL'}",
                    "- Results:",
                    *[
                        f"  - {result.reviewer}: {'PASS' if result.passed else 'FAIL'}"
                        for result in results
                    ],
                    "",
                    "## 다음 단계",
                    "- 사용자에게 기획 문서를 전달하고 승인/수정 요청을 받으세요.",
                    "- 승인 전에는 execute 단계를 실행하지 않습니다.",
                ]
            ),
            encoding="utf-8",
        )
        return summary_path, detail_paths
