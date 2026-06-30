"""Output path resolution for Skeleton artifact directories."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class OutputPathResolver:
    """Resolves artifact output directories for traced applications."""

    home_override: Path | None = None

    def resolve(self, *, project_root: Path, requested_out_dir: Path | None) -> Path:
        """Return the output directory for one Skeleton run."""
        if requested_out_dir:
            return requested_out_dir.expanduser().resolve()
        raw_out_dir = os.environ.get("SKELETON_OUT_DIR")
        if raw_out_dir:
            return Path(raw_out_dir).expanduser().resolve()
        return self.skeleton_home / self._application_name(project_root)

    @property
    def skeleton_home(self) -> Path:
        """Return the root directory used for implicit Skeleton artifacts."""
        if self.home_override:
            return self.home_override.expanduser().resolve()
        raw_home = os.environ.get("SKELETON_HOME")
        if raw_home:
            return Path(raw_home).expanduser().resolve()
        return (Path.home() / ".skeleton").resolve()

    @staticmethod
    def _application_name(project_root: Path) -> str:
        name = project_root.resolve().name
        return name or "application"
