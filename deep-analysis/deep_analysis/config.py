from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


VALID_BACKENDS = ("claude_code_cli", "stub")


@dataclass
class AnalysisConfig:
    project_path: Path
    output_path: Path
    reviewers: List[str] = field(default_factory=lambda: ["security", "code_quality", "performance"])
    exclude_patterns: List[str] = field(default_factory=list)
    target_languages: List[str] = field(default_factory=list)
    domains: Dict[str, List[str]] = field(default_factory=dict)
    backend: str = "claude_code_cli"
    project_name: str = "project"

    def __post_init__(self) -> None:
        if not self.project_path.is_dir():
            raise ValueError(f"project_path가 존재하지 않는 디렉토리입니다: {self.project_path}")
        if self.backend not in VALID_BACKENDS:
            raise ValueError(
                f"알 수 없는 backend: {self.backend!r}. "
                f"{', '.join(VALID_BACKENDS)} 중 하나를 사용하세요."
            )
        if not self.reviewers:
            raise ValueError("최소 1명의 reviewer가 필요합니다.")

    @classmethod
    def from_json_file(cls, config_path: Path) -> "AnalysisConfig":
        data = json.loads(config_path.read_text(encoding="utf-8"))
        project_path = Path(data["project_path"]).resolve()
        output_path = Path(data.get("output_path", project_path / ".deep-analysis")).resolve()
        return cls(
            project_path=project_path,
            output_path=output_path,
            reviewers=data.get("reviewers", ["security", "code_quality", "performance"]),
            exclude_patterns=data.get("exclude_patterns", []),
            target_languages=data.get("target_languages", []),
            domains=data.get("domains", {}),
            backend=data.get("backend", "claude_code_cli"),
            project_name=data.get("project_name", project_path.name),
        )
