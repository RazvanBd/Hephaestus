from __future__ import annotations

from pathlib import Path


class WorkspaceManager:
    ALLOWED_PREFIXES = ("src", "docs")

    def __init__(self, project_root: str = ".") -> None:
        self.project_root = Path(project_root).resolve()

    async def initialize_workspace(self) -> None:
        (self.project_root / "src").mkdir(parents=True, exist_ok=True)
        (self.project_root / "docs").mkdir(parents=True, exist_ok=True)
        (self.project_root / ".session").mkdir(parents=True, exist_ok=True)

    def _safe_path(self, relative_path: str) -> Path:
        candidate = (self.project_root / relative_path).resolve()
        if not any(relative_path.startswith(prefix + "/") for prefix in self.ALLOWED_PREFIXES):
            raise ValueError("Only src/ and docs/ paths are writable")
        if self.project_root not in candidate.parents and candidate != self.project_root:
            raise ValueError("Path traversal is not allowed")
        return candidate

    async def write_file(self, path: str, content: str) -> Path:
        target = self._safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    async def read_file(self, path: str) -> str:
        target = self._safe_path(path)
        return target.read_text(encoding="utf-8")

    async def resolve_doc_context(self, source_path: str) -> Path | None:
        source = Path(source_path)
        candidate = self.project_root / "docs" / source.with_suffix(".md")
        if candidate.exists():
            return candidate

        parent = source.parent
        while str(parent) not in {"", "."}:
            module_rules = self.project_root / "docs" / parent / "_module_rules.md"
            if module_rules.exists():
                return module_rules
            parent = parent.parent

        return None
