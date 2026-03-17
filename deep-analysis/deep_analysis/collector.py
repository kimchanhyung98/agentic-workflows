from __future__ import annotations

import fnmatch
import logging
import re
import subprocess
from pathlib import Path
from typing import Iterable, List, Sequence

logger = logging.getLogger(__name__)

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
DEFAULT_EXCLUDED_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    "dist",
    "build",
    ".next",
    "coverage",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
}

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

CONFIG_FILE_NAMES = {"pyproject.toml", "package.json", "settings.py", "urls.py", "Makefile"}

_IMPORT_RE = re.compile(
    r"^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE
)


def language_for_path(path: Path) -> str:
    return LANGUAGE_BY_EXTENSION.get(path.suffix.lower(), "text")


def _is_excluded(relative_path: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatch(relative_path, pattern) for pattern in patterns)


def _git_tracked_files(project_path: Path) -> List[Path] | None:
    cmd = ["git", "-C", str(project_path), "ls-files", "--cached", "--others", "--exclude-standard"]
    try:
        completed = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        logger.warning("git 실행 파일을 찾을 수 없습니다.")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("git ls-files 타임아웃 (30초 초과)")
        return None

    if completed.returncode != 0:
        logger.warning(
            "git ls-files 실패 (returncode=%d): %s",
            completed.returncode,
            completed.stderr.strip(),
        )
        return None

    files = [project_path / line for line in completed.stdout.splitlines() if line.strip()]
    return files if files else None


def collect_project_files(
    project_path: Path,
    exclude_patterns: Sequence[str],
    target_languages: Sequence[str],
) -> List[Path]:
    git_files = _git_tracked_files(project_path)
    if git_files is not None:
        files = git_files
    else:
        logger.warning(
            "git 추적 파일을 가져올 수 없어 rglob 폴백을 사용합니다. "
            ".gitignore 규칙이 적용되지 않습니다."
        )
        files = [path for path in project_path.rglob("*") if path.is_file()]

    language_filter = {language.lower() for language in target_languages}
    collected: List[Path] = []

    for file_path in files:
        try:
            relative_path = file_path.relative_to(project_path).as_posix()
        except ValueError:
            continue
        lower_name = file_path.name.lower()

        if any(part in DEFAULT_EXCLUDED_DIRS for part in Path(relative_path).parts):
            continue
        if file_path.suffix.lower() in BINARY_EXTENSIONS:
            continue
        if lower_name in DEFAULT_EXCLUDED_FILES:
            continue
        if any(marker in lower_name for marker in GENERATED_FILE_MARKERS):
            continue
        if _is_excluded(relative_path, exclude_patterns):
            continue
        try:
            if not file_path.exists() or file_path.stat().st_size == 0:
                continue
        except OSError:
            continue

        detected_language = language_for_path(file_path)
        is_config_file = file_path.name in CONFIG_FILE_NAMES
        if language_filter and detected_language not in language_filter and not is_config_file:
            continue

        collected.append(file_path)

    logger.info("파일 수집 완료: %d개 파일", len(collected))
    return sorted(collected)


def resolve_imports(target_file: Path, all_files: List[Path], max_context: int = 2) -> List[Path]:
    try:
        source = target_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    module_names: set[str] = set()
    for match in _IMPORT_RE.finditer(source):
        name = match.group(1) or match.group(2)
        if name:
            parts = name.split(".")
            module_names.update(parts)

    if not module_names:
        return _same_directory_fallback(target_file, all_files, max_context)

    scored: list[tuple[int, Path]] = []
    for candidate in all_files:
        if candidate == target_file:
            continue
        stem = candidate.stem
        if stem in module_names:
            scored.append((2, candidate))
        elif any(part in module_names for part in candidate.relative_to(candidate.anchor).parts):
            scored.append((1, candidate))

    if not scored:
        return _same_directory_fallback(target_file, all_files, max_context)

    scored.sort(key=lambda x: -x[0])
    return [path for _, path in scored[:max_context]]


def _same_directory_fallback(target_file: Path, all_files: List[Path], max_context: int) -> List[Path]:
    target_dir = target_file.parent
    same_dir = [p for p in all_files if p != target_file and p.parent == target_dir]
    return same_dir[:max_context]


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
