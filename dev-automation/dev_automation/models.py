from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class PlanArtifacts:
    plan_path: Path
    review_summary_path: Path
    review_detail_paths: List[Path]


@dataclass
class ExecutionResult:
    success: bool
    report_path: Path
    attempts: int
