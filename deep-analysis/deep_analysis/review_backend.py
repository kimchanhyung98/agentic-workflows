from __future__ import annotations

import subprocess
from abc import ABC, abstractmethod


class ReviewBackend(ABC):
    @abstractmethod
    def review(self, stage: str, perspective: str, bundle_xml: str) -> str:
        raise NotImplementedError


class ClaudeCodeCLIBackend(ReviewBackend):
    """Adapter for Claude Code CLI invocation."""

    def review(self, stage: str, perspective: str, bundle_xml: str) -> str:
        prompt = (
            f"You are reviewing stage={stage} perspective={perspective}. "
            "Return findings in Korean lines with severity tags [심각]/[높음]/[중간]/[낮음].\n"
            f"\n{bundle_xml}"
        )
        cmd = ["claude", "--print", prompt]
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "Claude Code CLI failed")
        return completed.stdout.strip()


class StubReviewBackend(ReviewBackend):
    """Deterministic backend for tests and offline sample runs."""

    def review(self, stage: str, perspective: str, bundle_xml: str) -> str:
        severity = "높음" if perspective == "security" else "중간"
        return f"[{severity}] {stage}/{perspective} 샘플 이슈"
