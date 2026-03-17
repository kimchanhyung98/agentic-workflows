from __future__ import annotations

import subprocess


class ExecutionBackend:
    def execute(self, plan_text: str, attempt: int, previous_error: str) -> str:
        raise NotImplementedError


class EchoBackend(ExecutionBackend):
    def execute(self, plan_text: str, attempt: int, previous_error: str) -> str:
        _ = plan_text
        _ = previous_error
        return f"echo-backend-attempt-{attempt}"


class ClaudeCodeBackend(ExecutionBackend):
    def __init__(self, command: list[str] | None = None):
        self.command = command or ["claude", "-p"]

    def execute(self, plan_text: str, attempt: int, previous_error: str) -> str:
        if "\x00" in plan_text:
            raise ValueError(
                "Plan text contains null bytes which cannot be passed as command-line arguments."
            )
        if "\x00" in previous_error:
            raise ValueError(
                "Previous error log contains null bytes which cannot be passed as command-line arguments."
            )
        prompt = (
            "Approved implementation plan:\n"
            f"{plan_text}\n\n"
            f"Attempt: {attempt}\n"
            f"Previous verification error: {previous_error or 'N/A'}\n"
            "Apply required code changes in the current repository and return a short summary."
        )
        completed = subprocess.run(
            [*self.command, prompt],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "Claude backend execution failed")
        return completed.stdout.strip()
