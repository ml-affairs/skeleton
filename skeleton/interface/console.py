"""TTY-aware console presentation for Skeleton commands."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TextIO

ColorMode = Literal["auto", "always", "never"]


@dataclass(frozen=True)
class ConsoleTheme:
    """ANSI colors used by the Skeleton CLI."""

    reset: str = "\033[0m"
    bold: str = "\033[1m"
    dim: str = "\033[2m"
    blue: str = "\033[34m"
    cyan: str = "\033[36m"
    green: str = "\033[32m"
    yellow: str = "\033[33m"
    red: str = "\033[31m"


class SkeletonConsole:
    """Renders concise, polished CLI output for Skeleton."""

    def __init__(self, stream: TextIO | None = None, *, color_mode: ColorMode = "auto") -> None:
        """Create a console bound to a stream."""
        self.stream = stream or sys.stdout
        self.color_mode = color_mode
        self.theme = ConsoleTheme()

    def banner(self, *, project_root: Path, out_dir: Path) -> None:
        """Render the command banner and resolved output paths."""
        self.write("")
        self.write(f"{self._style('Skeleton', self.theme.bold, self.theme.cyan)}  Replay the living architecture")
        self.write(f"{self._muted('Project')} {project_root}")
        self.write(f"{self._muted('Output ')} {out_dir}")
        self.write("")

    def step(self, message: str) -> None:
        """Render an in-progress command phase."""
        self.write(f"{self._style('●', self.theme.blue)} {message}")

    def success(self, message: str) -> None:
        """Render a successful command phase."""
        self.write(f"{self._style('✓', self.theme.green)} {message}")

    def warning(self, message: str) -> None:
        """Render a warning message."""
        self.write(f"{self._style('!', self.theme.yellow)} {message}")

    def error(self, message: str) -> None:
        """Render an error message."""
        self.write(f"{self._style('✗', self.theme.red)} {message}")

    def summary(
        self,
        *,
        event_count: int,
        node_count: int,
        edge_count: int,
        trace_path: Path,
        snapshot_path: Path,
        workflow_path: Path,
        report_path: Path | None,
    ) -> None:
        """Render the final run summary."""
        self.write("")
        self.write(self._style("Artifacts", self.theme.bold, self.theme.cyan))
        self.write(f"  {self._muted('trace   ')} {trace_path}")
        self.write(f"  {self._muted('snapshot')} {snapshot_path}")
        self.write(f"  {self._muted('workflow')} {workflow_path}")
        if report_path:
            self.write(f"  {self._muted('report  ')} {report_path}")
        self.write("")
        self.write(
            f"{self._style('✓', self.theme.green)} Captured {self._style(str(event_count), self.theme.bold)} events across "
            f"{self._style(str(node_count), self.theme.bold)} nodes and {self._style(str(edge_count), self.theme.bold)} runtime edges."
        )
        if report_path:
            self.write(f"{self._muted('Next')} open {report_path}")

    def write(self, message: str) -> None:
        """Write one line to the console stream."""
        self.stream.write(f"{message}\n")

    def _muted(self, value: str) -> str:
        return self._style(value, self.theme.dim)

    def _style(self, value: str, *styles: str) -> str:
        if not self._uses_color:
            return value
        return f"{''.join(styles)}{value}{self.theme.reset}"

    @property
    def _uses_color(self) -> bool:
        if self.color_mode == "always":
            return True
        if self.color_mode == "never" or os.environ.get("NO_COLOR"):
            return False
        return self.stream.isatty()
