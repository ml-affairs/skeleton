"""Shared artifact generation pipeline for CLI and Python API runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from skeleton_replay.analysis import ArchitectureQualityAnalyzer, ArchitectureQualityWriter, SnapshotBuilder, SnapshotMetrics
from skeleton_replay.reporting import HtmlReportWriter, WorkflowNarrativeWriter

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class ArtifactPaths:
    """Concrete output paths for one generated Skeleton artifact set."""

    trace_path: Path
    snapshot_path: Path
    workflow_path: Path
    quality_path: Path
    quality_markdown_path: Path
    report_path: Path | None


@dataclass(frozen=True)
class ArtifactGenerationResult:
    """Snapshot and metrics produced by the artifact generation pipeline."""

    snapshot: JsonObject
    metrics: SnapshotMetrics
    report_path: Path | None


@dataclass(frozen=True)
class ArtifactGenerationPipeline:
    """Build trace-derived snapshot, quality, workflow, and report artifacts."""

    report_writer: HtmlReportWriter = field(default_factory=HtmlReportWriter)
    workflow_writer: WorkflowNarrativeWriter = field(default_factory=WorkflowNarrativeWriter)
    quality_analyzer: ArchitectureQualityAnalyzer = field(default_factory=ArchitectureQualityAnalyzer)
    quality_writer: ArchitectureQualityWriter = field(default_factory=ArchitectureQualityWriter)

    def generate(self, *, project_root: Path, paths: ArtifactPaths) -> ArtifactGenerationResult:
        """Generate all requested artifacts from an existing trace file."""
        snapshot = SnapshotBuilder(project_root).build(paths.trace_path, paths.snapshot_path)
        metrics = SnapshotMetrics.from_snapshot(snapshot)
        quality = self.quality_analyzer.analyze(snapshot)
        snapshot["quality"] = quality
        paths.snapshot_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")
        self.quality_writer.write_json(quality, paths.quality_path)
        self.quality_writer.write_markdown(quality, paths.quality_markdown_path)
        self.workflow_writer.write(snapshot, paths.workflow_path)
        if paths.report_path is not None:
            self.report_writer.write(snapshot, paths.report_path)
        return ArtifactGenerationResult(snapshot=snapshot, metrics=metrics, report_path=paths.report_path)
