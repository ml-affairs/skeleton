"""Browser-opening behavior for generated Skeleton reports."""

from __future__ import annotations

import webbrowser
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HtmlReportOpener:
    """Opens generated HTML reports in the user's default browser."""

    def open(self, report_path: Path) -> bool:
        """Open a local HTML report and return whether the browser accepted it."""
        return webbrowser.open(report_path.resolve().as_uri(), new=2)
