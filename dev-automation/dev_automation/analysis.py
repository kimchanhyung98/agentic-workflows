from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterable, List

_EXTENSION_TO_LANGUAGE = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".md": "Markdown",
    ".json": "JSON",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".sh": "Shell",
}


class ProjectAnalyzer:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def list_files(self) -> List[Path]:
        files: List[Path] = []
        for path in self.repo_root.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts:
                continue
            files.append(path)
        return files

    def detect_languages(self, files: Iterable[Path]) -> Counter:
        counts: Counter = Counter()
        for file_path in files:
            language = _EXTENSION_TO_LANGUAGE.get(file_path.suffix.lower())
            if language:
                counts[language] += 1
        return counts

    def find_integration_points(self) -> List[str]:
        checks = [
            (self.repo_root / "Makefile", "Makefile 기반 check 훅 통합 가능"),
            (self.repo_root / "package.json", "npm 기반 툴/스크립트와 함께 동작 가능"),
            (
                self.repo_root / "docs" / "_draft" / "dev-automation" / "00-diagram.md",
                "dev-automation 설계 다이어그램 존재",
            ),
            (
                self.repo_root / "docs" / "_draft" / "dev-automation" / "01-detail.md",
                "dev-automation 상세 요구사항 존재",
            ),
        ]
        return [message for file_path, message in checks if file_path.exists()]

    def summarize_structure(self) -> str:
        files = self.list_files()
        langs = self.detect_languages(files)
        top_dirs = sorted(
            [
                item.name
                for item in self.repo_root.iterdir()
                if item.is_dir() and item.name not in {".git"}
            ]
        )

        language_line = ", ".join(f"{lang}({count})" for lang, count in langs.most_common())
        if not language_line:
            language_line = "식별된 주요 언어 없음"

        return (
            f"- 최상위 디렉토리: {', '.join(top_dirs)}\n"
            f"- 파일 기반 언어 분포: {language_line}\n"
            f"- 총 파일 수(.git 제외): {len(files)}"
        )
