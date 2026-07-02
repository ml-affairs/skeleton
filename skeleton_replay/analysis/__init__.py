"""Static and runtime trace analysis boundary for Skeleton."""

from skeleton_replay.analysis.quality import ArchitectureQualityAnalyzer, ArchitectureQualityWriter, QualityFinding
from skeleton_replay.analysis.snapshot import SnapshotBuilder, SnapshotMetrics, TraceReader
from skeleton_replay.analysis.static import StaticIndex, StaticModule, StaticProjectScanner, StaticSymbol
from skeleton_replay.analysis.structured_returns import StructuredReturnConfig, StructuredReturnGroupAnalyzer

__all__ = [
    "ArchitectureQualityAnalyzer",
    "ArchitectureQualityWriter",
    "QualityFinding",
    "SnapshotBuilder",
    "SnapshotMetrics",
    "StaticIndex",
    "StaticModule",
    "StaticProjectScanner",
    "StaticSymbol",
    "StructuredReturnConfig",
    "StructuredReturnGroupAnalyzer",
    "TraceReader",
]
