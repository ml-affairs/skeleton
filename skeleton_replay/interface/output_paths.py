"""Output path resolution for Skeleton artifact directories."""

from __future__ import annotations

import os
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from hashlib import sha1
from pathlib import Path


@dataclass(frozen=True)
class _PytestTargetSelection:
    """Pytest target path plus any node-id segments selected inside that path."""

    path: Path
    node_segments: tuple[str, ...]


@dataclass(frozen=True)
class _ArtifactPathSlugger:
    """Creates stable filesystem-safe artifact path segments from user-facing targets."""

    reserved_pytest_node_segments: frozenset[str] = frozenset({"directory", "file", "latest", "runs"})

    def target_slug(self, value: str) -> str:
        """Return a readable, deterministic slug for one path segment."""
        raw_value = value.strip() or "target"
        slug = re.sub(r"[^A-Za-z0-9._-]+", "_", raw_value).strip("._-")
        if not slug:
            slug = "target"
        if slug != raw_value:
            slug = f"{slug}-{self._short_hash(raw_value)}"
        return slug

    def pytest_node_slug(self, value: str) -> str:
        """Return a pytest node segment that cannot collide with pytest sentinel directories."""
        slug = self.target_slug(value)
        if slug in self.reserved_pytest_node_segments:
            return f"node-{slug}"
        return slug

    @staticmethod
    def _short_hash(value: str) -> str:
        return sha1(value.encode("utf-8")).hexdigest()[:8]


@dataclass(frozen=True)
class OutputPathResolver:
    """Resolves artifact output directories for traced applications."""

    home_override: Path | None = None
    slugger: _ArtifactPathSlugger = field(default_factory=_ArtifactPathSlugger)

    def resolve(self, *, project_root: Path, requested_out_dir: Path | None, target_path: Path | None = None) -> Path:
        """Return the output directory for one Skeleton run."""
        if requested_out_dir:
            return requested_out_dir.expanduser().resolve()
        raw_out_dir = os.environ.get("SKELETON_OUT_DIR")
        if raw_out_dir:
            return Path(raw_out_dir).expanduser().resolve()
        configured_home = self.configured_skeleton_home
        if configured_home is not None:
            return configured_home / self._application_name(project_root)
        if target_path is not None:
            resolved_target = target_path.expanduser().resolve()
            return resolved_target.parent / ".skeleton" / self.slugger.target_slug(resolved_target.stem) / "latest"
        return self.skeleton_home / self._application_name(project_root)

    @property
    def skeleton_home(self) -> Path:
        """Return the root directory used for implicit Skeleton artifacts."""
        configured_home = self.configured_skeleton_home
        if configured_home is not None:
            return configured_home
        return (Path.home() / ".skeleton").resolve()

    @property
    def configured_skeleton_home(self) -> Path | None:
        """Return the explicitly configured Skeleton home, if the user supplied one."""
        if self.home_override:
            return self.home_override.expanduser().resolve()
        raw_home = os.environ.get("SKELETON_HOME")
        if raw_home:
            return Path(raw_home).expanduser().resolve()
        return None

    @staticmethod
    def _application_name(project_root: Path) -> str:
        name = project_root.resolve().name
        return name or "application"


@dataclass(frozen=True)
class PytestOutputPathResolver:
    """Resolves pytest artifact directories from explicit settings or selected test targets."""

    base_resolver: OutputPathResolver = field(default_factory=OutputPathResolver)
    slugger: _ArtifactPathSlugger = field(default_factory=_ArtifactPathSlugger)

    def resolve(self, *, project_root: Path, requested_out_dir: Path | None, pytest_args: Sequence[str]) -> Path:
        """Return the output directory for one traced pytest invocation."""
        if requested_out_dir or os.environ.get("SKELETON_OUT_DIR") or self.base_resolver.configured_skeleton_home is not None:
            return self.base_resolver.resolve(project_root=project_root, requested_out_dir=requested_out_dir)

        selected_target = self._selected_test_target(project_root=project_root, pytest_args=pytest_args)
        if selected_target is None:
            return project_root.resolve() / ".skeleton" / "directory" / "latest"
        if selected_target.path.is_dir():
            return selected_target.path / ".skeleton" / "directory" / "latest"

        file_slug = self.slugger.target_slug(selected_target.path.stem)
        if not selected_target.node_segments:
            return selected_target.path.parent / ".skeleton" / file_slug / "file" / "latest"

        node_path = selected_target.path.parent / ".skeleton" / file_slug
        for node_segment in selected_target.node_segments:
            node_path = node_path / self.slugger.pytest_node_slug(node_segment)
        return node_path / "latest"

    def _selected_test_target(self, *, project_root: Path, pytest_args: Sequence[str]) -> _PytestTargetSelection | None:
        for raw_arg in pytest_args:
            candidate = self._target_from_pytest_arg(raw_arg)
            if candidate is None:
                continue
            resolved_target = self._resolve_existing_target(project_root=project_root, candidate=candidate.path)
            if resolved_target is None:
                continue
            return _PytestTargetSelection(path=resolved_target, node_segments=candidate.node_segments)
        return None

    @staticmethod
    def _target_from_pytest_arg(raw_arg: str) -> _PytestTargetSelection | None:
        target_text, *node_parts = raw_arg.split("::")
        if not target_text or target_text.startswith("-"):
            return None
        return _PytestTargetSelection(path=Path(target_text).expanduser(), node_segments=tuple(part for part in node_parts if part))

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
