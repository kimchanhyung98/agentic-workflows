from __future__ import annotations

import logging
import re
import subprocess
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

REVIEW_TIMEOUT_SECONDS = 300
_SEVERITY_RE = re.compile(r"\[(심각|높음|중간|낮음)\]")


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
        cmd = ["claude", "--print", "-"]
        try:
            completed = subprocess.run(
                cmd,
                input=prompt,
                check=False,
                capture_output=True,
                text=True,
                timeout=REVIEW_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"Claude CLI 타임아웃 ({REVIEW_TIMEOUT_SECONDS}초 초과): "
                f"stage={stage}, perspective={perspective}"
            )
        except FileNotFoundError:
            raise RuntimeError(
                "claude 명령을 찾을 수 없습니다. Claude Code CLI가 설치되어 있는지 확인하세요."
            )

        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            raise RuntimeError(
                f"Claude CLI 실패 (returncode={completed.returncode}): "
                f"stage={stage}, perspective={perspective}"
                + (f" — {stderr}" if stderr else "")
            )
        output = completed.stdout.strip()
        if not output:
            logger.warning(
                "Claude CLI가 빈 응답을 반환했습니다: stage=%s, perspective=%s",
                stage, perspective,
            )
        elif not _SEVERITY_RE.search(output):
            logger.warning(
                "Claude CLI 응답에 심각도 태그([심각]/[높음]/[중간]/[낮음])가 없습니다: "
                "stage=%s, perspective=%s — 응답이 요약에서 누락될 수 있습니다",
                stage, perspective,
            )
        return output


class StubReviewBackend(ReviewBackend):
    """Deterministic backend for tests and offline sample runs."""

    def review(self, stage: str, perspective: str, bundle_xml: str) -> str:
        severity = "높음" if perspective == "security" else "중간"
        return f"[{severity}] {stage}/{perspective} 샘플 이슈"
