from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable

from .collector import language_for_path


def _structure_block(project_path: Path, files: Iterable[Path]) -> str:
    lines = sorted(path.relative_to(project_path).as_posix() for path in files)
    return "\n".join(lines)


def _file_entry(project_path: Path, file_path: Path, role: str) -> str:
    relative = file_path.relative_to(project_path).as_posix()
    content = file_path.read_text(encoding="utf-8", errors="replace")
    escaped_content = escape(content, quote=True)
    language = language_for_path(file_path)
    return (
        f'  <file path="{escape(relative, quote=True)}" role="{role}" language="{language}">\n'
        f'    <content encoding="xml-escaped">{escaped_content}</content>\n'
        "  </file>"
    )


def build_file_bundle(project_path: Path, target_file: Path, context_files: list[Path]) -> str:
    bundle_files = [target_file, *context_files]
    structure = _structure_block(project_path, bundle_files)
    entries = [_file_entry(project_path, target_file, "target")]
    entries.extend(_file_entry(project_path, file_path, "context") for file_path in context_files)
    target = escape(target_file.relative_to(project_path).as_posix(), quote=True)
    return "\n".join(
        [
            f'<review target="{target}">',
            "  <structure>",
            structure,
            "  </structure>",
            *entries,
            "</review>",
        ]
    )


def build_domain_bundle(project_path: Path, domain: str, domain_files: list[Path]) -> str:
    structure = _structure_block(project_path, domain_files)
    entries = [_file_entry(project_path, file_path, "target") for file_path in domain_files]
    return "\n".join(
        [
            f'<review domain="{escape(domain, quote=True)}">',
            "  <structure>",
            structure,
            "  </structure>",
            *entries,
            "</review>",
        ]
    )


def build_project_bundle(
    project_name: str,
    project_path: Path,
    all_files: list[Path],
    config_files: list[Path],
    stage1_summary: str,
    stage2_summary: str,
) -> str:
    structure = _structure_block(project_path, all_files)
    config_entries = []
    for config_path in config_files:
        relative = config_path.relative_to(project_path).as_posix()
        escaped = escape(config_path.read_text(encoding="utf-8", errors="replace"), quote=True)
        config_entries.append(
            "\n".join(
                [
                    f'  <config path="{escape(relative, quote=True)}" language="{language_for_path(config_path)}">',
                    f'    <content encoding="xml-escaped">{escaped}</content>',
                    "  </config>",
                ]
            )
        )

    return "\n".join(
        [
            f'<review scope="project" name="{escape(project_name, quote=True)}">',
            "  <structure>",
            structure,
            "  </structure>",
            *config_entries,
            "  <previous-reviews>",
            f"    <stage1-summary>{escape(stage1_summary, quote=True)}</stage1-summary>",
            f"    <stage2-summary>{escape(stage2_summary, quote=True)}</stage2-summary>",
            "  </previous-reviews>",
            "</review>",
        ]
    )
