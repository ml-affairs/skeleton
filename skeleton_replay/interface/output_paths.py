"""Output path resolution for Skeleton artifact directories."""

from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
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


@dataclass(frozen=True)
class PytestOutputPathResolver:
    """Resolves pytest artifact directories from explicit settings or selected test targets."""

    base_resolver: OutputPathResolver = field(default_factory=OutputPathResolver)

    def resolve(self, *, project_root: Path, requested_out_dir: Path | None, pytest_args: Sequence[str]) -> Path:
        """Return the output directory for one traced pytest invocation."""
        if requested_out_dir or os.environ.get("SKELETON_OUT_DIR"):
            return self.base_resolver.resolve(project_root=project_root, requested_out_dir=requested_out_dir)

        target_directory = self._selected_test_directory(project_root=project_root, pytest_args=pytest_args)
        if target_directory is not None:
            return (target_directory / ".skeleton").resolve()

        return self.base_resolver.resolve(project_root=project_root, requested_out_dir=requested_out_dir)

    def _selected_test_directory(self, *, project_root: Path, pytest_args: Sequence[str]) -> Path | None:
        for raw_arg in pytest_args:
            candidate = self._target_path_from_pytest_arg(raw_arg)
            if candidate is None:
                continue
            resolved_target = self._resolve_existing_target(project_root=project_root, candidate=candidate)
            if resolved_target is None:
                continue
            if resolved_target.is_dir():
                return resolved_target
            return resolved_target.parent
        return None

    @staticmethod
    def _target_path_from_pytest_arg(raw_arg: str) -> Path | None:
        text = raw_arg.split("::", 1)[0]
        if not text or text.startswith("-"):
            return None
        return Path(text).expanduser()

    @staticmethod
    def _resolve_existing_target(*, project_root: Path, candidate: Path) -> Path | None:
        candidates = (candidate,) if candidate.is_absolute() else (Path.cwd() / candidate, project_root / candidate)
        for possible_target in candidates:
            try:
                resolved_target = possible_target.resolve()
            except OSError:
                continue
            if resolved_target.exists():
                return resolved_target
        return None
