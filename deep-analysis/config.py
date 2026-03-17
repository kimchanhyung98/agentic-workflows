from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class ReviewRole:
    name: str
    focus: str


@dataclass
class AnalysisConfig:
    project_root: Path
    output_dir: Path
    excludes: List[str] = field(default_factory=list)
    include_extensions: List[str] = field(default_factory=list)
    domain_map: Dict[str, List[str]] = field(default_factory=dict)
    config_files: List[str] = field(default_factory=lambda: [
        "pyproject.toml",
        "package.json",
        "Makefile",
        "README.md",
    ])
    project_name: str = "project"
    claude_command: str = "claude"
    claude_timeout_seconds: int = 300
    max_context_files: int = 6
    max_summary_chars: int = 50000
    generated_file_patterns: List[str] = field(default_factory=lambda: ["*.generated.*", "package-lock.json"])
    reviewers: List[ReviewRole] = field(
        default_factory=lambda: [
            ReviewRole("security", "인증/인가, 입력 검증, 시크릿 노출, 취약점"),
            ReviewRole("quality", "코드 품질, 설계, 유지보수성, 에러 처리"),
            ReviewRole("performance", "성능, 자원 사용, 동시성, 캐싱"),
        ]
    )


def load_config(config_path: Path | None, project_root: Path, output_dir: Path) -> AnalysisConfig:
    config = AnalysisConfig(project_root=project_root, output_dir=output_dir, project_name=project_root.name)
    if not config_path:
        return config

    data = json.loads(config_path.read_text(encoding="utf-8"))
    config.excludes = list(data.get("excludes", config.excludes))
    config.include_extensions = list(data.get("include_extensions", config.include_extensions))
    config.domain_map = dict(data.get("domain_map", config.domain_map))
    config.config_files = list(data.get("config_files", config.config_files))
    config.project_name = str(data.get("project_name", config.project_name))
    config.claude_command = str(data.get("claude_command", config.claude_command))
    config.claude_timeout_seconds = int(data.get("claude_timeout_seconds", config.claude_timeout_seconds))
    config.max_context_files = int(data.get("max_context_files", config.max_context_files))
    config.max_summary_chars = int(data.get("max_summary_chars", config.max_summary_chars))
    config.generated_file_patterns = list(data.get("generated_file_patterns", config.generated_file_patterns))

    reviewers = data.get("reviewers")
    if reviewers:
        config.reviewers = [ReviewRole(name=str(role["name"]), focus=str(role["focus"])) for role in reviewers]

    return config
