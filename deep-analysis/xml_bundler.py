from __future__ import annotations

import fnmatch
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set
from xml.etree import ElementTree as ET

from config import AnalysisConfig

logger = logging.getLogger(__name__)


BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp4",
    ".mp3",
    ".mov",
    ".avi",
    ".exe",
    ".dll",
    ".so",
    ".bin",
}


@dataclass
class SourceFile:
    path: Path
    language: str
    content: str


class XmlBundler:
    def __init__(self, config: AnalysisConfig) -> None:
        self.config = config
        self.gitignore_patterns = self._load_gitignore_patterns(config.project_root)
        self.exclude_patterns = self.gitignore_patterns + config.excludes
        self._auto_exclude_output_dir()

    def collect_source_files(self) -> List[SourceFile]:
        files: List[SourceFile] = []
        for path in self.config.project_root.rglob("*"):
            if not path.is_file():
                continue

            rel = path.relative_to(self.config.project_root)
            rel_str = rel.as_posix()
            if self._is_excluded(rel_str):
                continue
            if path.suffix.lower() in BINARY_SUFFIXES:
                continue
            if any(fnmatch.fnmatch(path.name, pattern) for pattern in self.config.generated_file_patterns):
                continue

            content = self._safe_read_text(path)
            if content is None or not content.strip():
                continue

            if self.config.include_extensions and path.suffix not in self.config.include_extensions:
                continue

            files.append(SourceFile(path=rel, language=self._language_for(path), content=content))

        files.sort(key=lambda item: item.path.as_posix())
        return files

    def bundle_file_stage(self, source_files: List[SourceFile], output_dir: Path) -> List[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        file_map = {item.path.as_posix(): item for item in source_files}
        written: List[Path] = []

        for target in source_files:
            root = ET.Element("review", {"target": target.path.as_posix()})
            structure = ET.SubElement(root, "structure")
            structure.text = self.render_tree(source_files)

            self._append_file_node(root, target, role="target")

            for context_path in self._find_context_files(target, file_map):
                if context_path == target.path.as_posix():
                    continue
                context_file = file_map.get(context_path)
                if context_file:
                    self._append_file_node(root, context_file, role="context")

            output_path = output_dir / f"{target.path.as_posix().replace('/', '__')}.xml"
            output_path.write_text(self._to_xml(root), encoding="utf-8")
            written.append(output_path)

        return written

    def bundle_domain_stage(self, source_files: List[SourceFile], output_dir: Path) -> List[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        domains = self._group_domains(source_files)
        written: List[Path] = []

        for domain, files in sorted(domains.items()):
            root = ET.Element("review", {"domain": domain})
            structure = ET.SubElement(root, "structure")
            structure.text = self.render_tree(files)

            for item in sorted(files, key=lambda f: f.path.as_posix()):
                self._append_file_node(root, item, role="target")

            output_path = output_dir / f"{domain}.xml"
            output_path.write_text(self._to_xml(root), encoding="utf-8")
            written.append(output_path)

        return written

    def bundle_project_stage(
        self,
        source_files: List[SourceFile],
        stage1_summary: str,
        stage2_summary: str,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        root = ET.Element("review", {"scope": "project", "name": self.config.project_name})

        structure = ET.SubElement(root, "structure")
        structure.text = self.render_tree(source_files)

        source_map = {item.path.as_posix(): item for item in source_files}
        for config_path in self.config.config_files:
            normalized = Path(config_path).as_posix()
            source_file = source_map.get(normalized)
            if not source_file:
                continue
            node = ET.SubElement(
                root,
                "config",
                {
                    "path": source_file.path.as_posix(),
                    "language": source_file.language,
                },
            )
            content = ET.SubElement(node, "content", {"encoding": "xml-escaped"})
            content.text = source_file.content

        previous = ET.SubElement(root, "previous-reviews")
        stage1 = ET.SubElement(previous, "stage1-summary")
        stage1.text = stage1_summary
        stage2 = ET.SubElement(previous, "stage2-summary")
        stage2.text = stage2_summary

        output_path.write_text(self._to_xml(root), encoding="utf-8")
        return output_path

    def render_tree(self, source_files: Iterable[SourceFile]) -> str:
        return "\n".join(f.path.as_posix() for f in sorted(source_files, key=lambda s: s.path.as_posix()))

    def _append_file_node(self, root: ET.Element, item: SourceFile, role: str) -> None:
        file_node = ET.SubElement(
            root,
            "file",
            {
                "path": item.path.as_posix(),
                "role": role,
                "language": item.language,
            },
        )
        content_node = ET.SubElement(file_node, "content", {"encoding": "xml-escaped"})
        content_node.text = item.content

    def _find_context_files(self, target: SourceFile, file_map: Dict[str, SourceFile]) -> List[str]:
        referenced = self._extract_references(target)
        context: Set[str] = set()

        for ref in referenced:
            for candidate in self._resolve_reference(ref, file_map):
                context.add(candidate)

        same_dir = target.path.parent.as_posix()
        for path in file_map:
            if path.startswith(f"{same_dir}/") and path != target.path.as_posix():
                context.add(path)

        context.discard(target.path.as_posix())
        return sorted(context)[: self.config.max_context_files]

    def _extract_references(self, target: SourceFile) -> Set[str]:
        refs: Set[str] = set()
        if target.language == "python":
            for match in re.finditer(r"^\s*from\s+([a-zA-Z0-9_\.]+)\s+import\s+", target.content, re.MULTILINE):
                refs.add(match.group(1))
            for match in re.finditer(r"^\s*import\s+([a-zA-Z0-9_\.]+)", target.content, re.MULTILINE):
                refs.add(match.group(1).split(",")[0].strip())
        elif target.language in {"javascript", "typescript"}:
            for match in re.finditer(r"import\s+.*?from\s+['\"](.+?)['\"]", target.content):
                refs.add(match.group(1))
            for match in re.finditer(r"require\(['\"](.+?)['\"]\)", target.content):
                refs.add(match.group(1))
        return refs

    def _resolve_reference(self, ref: str, file_map: Dict[str, SourceFile]) -> List[str]:
        candidates: List[str] = []
        if ref.startswith("."):
            normalized = ref.strip("./")
            if normalized:
                candidates.extend(self._candidates_from_ref(normalized))
        else:
            candidates.extend(self._candidates_from_ref(ref.replace(".", "/")))

        existing = [candidate for candidate in candidates if candidate in file_map]
        if existing:
            return existing

        suffix_match: List[str] = []
        for path in file_map:
            if path.endswith(f"/{ref}.py") or path.endswith(f"/{ref}.ts") or path.endswith(f"/{ref}.js"):
                suffix_match.append(path)
        return suffix_match

    def _candidates_from_ref(self, ref: str) -> List[str]:
        return [
            f"{ref}.py",
            f"{ref}.js",
            f"{ref}.ts",
            f"{ref}/__init__.py",
            f"{ref}/index.ts",
            f"{ref}/index.js",
        ]

    def _load_gitignore_patterns(self, project_root: Path) -> List[str]:
        gitignore = project_root / ".gitignore"
        if not gitignore.exists():
            return []
        patterns: List[str] = []
        for line in gitignore.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("!"):
                continue
            patterns.append(stripped)
        return patterns

    def _auto_exclude_output_dir(self) -> None:
        try:
            rel = self.config.output_dir.relative_to(self.config.project_root)
            pattern = rel.as_posix() + "/"
            if pattern not in self.exclude_patterns:
                self.exclude_patterns.append(pattern)
        except ValueError:
            pass

    def _is_excluded(self, rel_path: str) -> bool:
        parts = Path(rel_path).parts
        for pattern in self.exclude_patterns:
            p = pattern.strip()
            if not p:
                continue
            if p.endswith("/"):
                dir_name = p.rstrip("/")
                if rel_path == dir_name or rel_path.startswith(p):
                    return True
                if any(part == dir_name for part in parts):
                    return True
            if p.startswith("/") and fnmatch.fnmatch(f"/{rel_path}", p):
                return True
            if fnmatch.fnmatch(rel_path, p):
                return True
            if "/" not in p and fnmatch.fnmatch(Path(rel_path).name, p):
                return True
        return False

    def _safe_read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None

    def _language_for(self, path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix == ".py":
            return "python"
        if suffix in {".js", ".jsx", ".mjs", ".cjs"}:
            return "javascript"
        if suffix in {".ts", ".tsx"}:
            return "typescript"
        if suffix in {".md", ".mdx"}:
            return "markdown"
        if suffix in {".json"}:
            return "json"
        if suffix in {".yml", ".yaml"}:
            return "yaml"
        if suffix in {".toml"}:
            return "toml"
        return "text"

    def _group_domains(self, source_files: List[SourceFile]) -> Dict[str, List[SourceFile]]:
        if self.config.domain_map:
            grouped: Dict[str, List[SourceFile]] = {domain: [] for domain in self.config.domain_map}
            for item in source_files:
                path = item.path.as_posix()
                matched = False
                for domain, patterns in self.config.domain_map.items():
                    if any(fnmatch.fnmatch(path, pattern) for pattern in patterns):
                        grouped.setdefault(domain, []).append(item)
                        matched = True
                        break
                if not matched:
                    grouped.setdefault("misc", []).append(item)
            return {k: v for k, v in grouped.items() if v}

        logger.warning(
            "domain_map이 설정되지 않아 디렉토리 기반 자동 그룹핑을 사용합니다. "
            "정확한 기능 도메인 리뷰를 위해 config에 domain_map을 설정하세요."
        )
        grouped: Dict[str, List[SourceFile]] = {}
        for item in source_files:
            parts = item.path.parts
            if len(parts) >= 2:
                domain = parts[0] if parts[0] not in {"src", "lib", "app"} else parts[1]
            else:
                domain = item.path.stem
            domain = re.split(r"[-_.]", domain)[0] or "misc"
            grouped.setdefault(domain, []).append(item)
        return grouped

    def _to_xml(self, root: ET.Element) -> str:
        return ET.tostring(root, encoding="unicode")
