from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path
from typing import Iterable, List, Sequence

BINARY_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".jar",
    ".mp3",
    ".mp4",
    ".mov",
    ".exe",
    ".dll",
    ".so",
}
DEFAULT_EXCLUDED_FILES = {"package-lock.json"}
GENERATED_FILE_MARKERS = (".generated.",)

LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".jsx": "javascript",
    ".java": "java",
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".sql": "sql",
    ".md": "markdown",
    ".json": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
}


def language_for_path(path: Path) -> str:
    return LANGUAGE_BY_EXTENSION.get(path.suffix.lower(), "text")


def _is_excluded(relative_path: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatch(relative_path, pattern) for pattern in patterns)


def _git_tracked_files(project_path: Path) -> List[Path]:
    cmd = ["git", "-C", str(project_path), "ls-files"]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        return []
    return [project_path / line for line in completed.stdout.splitlines() if line.strip()]


def collect_project_files(
    project_path: Path,
    exclude_patterns: Sequence[str],
    target_languages: Sequence[str],
) -> List[Path]:
    files = _git_tracked_files(project_path)
    if not files:
        files = [path for path in project_path.rglob("*") if path.is_file()]

    language_filter = {language.lower() for language in target_languages}
    collected: List[Path] = []

    for file_path in files:
        relative_path = file_path.relative_to(project_path).as_posix()
        lower_name = file_path.name.lower()

        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            continue
        if lower_name in DEFAULT_EXCLUDED_FILES:
            continue
        if any(marker in lower_name for marker in GENERATED_FILE_MARKERS):
            continue
        if _is_excluded(relative_path, exclude_patterns):
            continue
        if not file_path.exists() or file_path.stat().st_size == 0:
            continue

        detected_language = language_for_path(file_path)
        if language_filter and detected_language not in language_filter:
            continue

        collected.append(file_path)

    return sorted(collected)


def build_domains(files: Iterable[Path], project_path: Path, configured_domains: dict[str, list[str]]) -> dict[str, list[Path]]:
    if configured_domains:
        domain_map: dict[str, list[Path]] = {domain: [] for domain in configured_domains}
        unmatched: list[Path] = []
        for file_path in files:
            relative = file_path.relative_to(project_path).as_posix()
            matched = False
            for domain, patterns in configured_domains.items():
                if any(fnmatch.fnmatch(relative, pattern) for pattern in patterns):
                    domain_map[domain].append(file_path)
                    matched = True
                    break
            if not matched:
                unmatched.append(file_path)
        if unmatched:
            domain_map["unmatched"] = unmatched
        return {k: sorted(v) for k, v in domain_map.items() if v}

    inferred: dict[str, list[Path]] = {}
    for file_path in files:
        rel = file_path.relative_to(project_path)
        if len(rel.parts) > 1:
            domain = rel.parts[0]
        else:
            domain = file_path.stem
        inferred.setdefault(domain, []).append(file_path)
    return {k: sorted(v) for k, v in inferred.items()}
