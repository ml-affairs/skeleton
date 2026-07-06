"""Human-facing command line interface components."""

from skeleton_replay.interface.artifacts import ArtifactGenerationPipeline, ArtifactGenerationResult, ArtifactPaths
from skeleton_replay.interface.console import ColorMode, SkeletonConsole
from skeleton_replay.interface.output_paths import OutputPathResolver, PytestOutputPathResolver
from skeleton_replay.interface.report_opener import HtmlReportOpener

__all__ = [
    "ArtifactGenerationPipeline",
    "ArtifactGenerationResult",
    "ArtifactPaths",
    "ColorMode",
    "HtmlReportOpener",
    "OutputPathResolver",
    "PytestOutputPathResolver",
    "SkeletonConsole",
]
