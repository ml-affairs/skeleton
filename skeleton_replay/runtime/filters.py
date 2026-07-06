"""Filtering rules for project-local runtime tracing."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

IGNORED_DIRS = {".git", ".hg", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".skeleton", ".venv", "venv", "__pycache__"}


@dataclass(frozen=True)
class TraceFilter:
    """Decides whether a frame belongs in the architecture trace."""

    project_root: Path
    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()
    ignored_dirs: frozenset[str] = field(default_factory=lambda: frozenset(IGNORED_DIRS))

    def allows_file(self, filename: str) -> bool:
        """Return whether a file should be included in the runtime trace."""
        path = Path(filename)
        if not filename or filename.startswith("<"):
            return False
        try:
            resolved = path.resolve()
            relative = resolved.relative_to(self.project_root)
        except (OSError, ValueError):
            return False

        parts = set(relative.parts)
        if parts.intersection(self.ignored_dirs):
            return False

        relative_text = relative.as_posix()
        module_text = self.module_from_path(resolved)
        if self.include and not self._matches_any(relative_text, module_text, self.include):
            return False
        return not self._matches_any(relative_text, module_text, self.exclude)

    @staticmethod
    def allows_function(name: str) -> bool:
        """Return whether a callable name belongs in the architecture trace."""
        return not name.startswith("<") and not (name.startswith("__") and name.endswith("__"))

    @staticmethod
    def is_private_function(name: str) -> bool:
        """Return whether a callable name is private/internal application surface."""
        return name.startswith("_") and TraceFilter.allows_function(name)

    def module_from_path(self, filename: Path) -> str:
        """Return a dotted module name for a project-local file path."""
        try:
            relative = filename.resolve().relative_to(self.project_root)
        except (OSError, ValueError):
            return filename.stem
        parts = relative.parts[:-1] if relative.name == "__init__.py" else (*relative.parts[:-1], relative.stem)
        return ".".join(part for part in parts if part)

    @staticmethod
    def _matches_any(relative_text: str, module_text: str, patterns: tuple[str, ...]) -> bool:
        return any(fnmatch(relative_text, pattern) or fnmatch(module_text, pattern) for pattern in patterns)
