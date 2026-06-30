"""Static HTML report generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any
from urllib.parse import quote

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class HtmlReportWriter:
    """Writes a static architecture replay report."""

    def write(self, snapshot: JsonObject, out_path: Path) -> None:
        """Write a self-contained static architecture replay report."""
        snapshot_json = json.dumps(snapshot).replace("</", "<\\/")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(self._html(snapshot_json), encoding="utf-8")

    def _html(self, snapshot_json: str) -> str:
        """Return the static report HTML."""
        return self._template().replace("__SKELETON_SNAPSHOT_JSON__", snapshot_json).replace("__SKELETON_FAVICON__", self._favicon())

    def _favicon(self) -> str:
        """Return the inline Skeleton favicon data URL."""
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            '<rect width="64" height="64" rx="14" fill="#070a12"/>'
            '<path d="M22 18c-6 3-9 8-9 14s3 11 9 14" fill="none" stroke="#38dce2" stroke-width="5" stroke-linecap="round"/>'
            '<path d="M42 18c6 3 9 8 9 14s-3 11-9 14" fill="none" stroke="#38dce2" stroke-width="5" stroke-linecap="round"/>'
            '<text x="32" y="39" text-anchor="middle" font-size="18" font-family="monospace" font-weight="700" fill="#e5eefc">sk</text>'
            "</svg>"
        )
        return f"data:image/svg+xml,{quote(svg)}"

    def _template(self) -> str:
        """Return the dark cinematic report template."""
        return resources.files("skeleton_replay.reporting.templates").joinpath("report.html").read_text(encoding="utf-8")
