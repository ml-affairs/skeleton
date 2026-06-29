"""Static HTML report generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Skeleton Architecture Replay</title>
  <script src="https://unpkg.com/cytoscape@3.30.4/dist/cytoscape.min.js"></script>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --ink: #17202a;
      --muted: #607080;
      --line: #d9e0e7;
      --accent: #256f9c;
      --accent-2: #b44d34;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    header {{
      height: 56px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    header h1 {{ font-size: 17px; margin: 0; font-weight: 650; letter-spacing: 0; }}
    header .meta {{ color: var(--muted); font-size: 13px; }}
    main {{
      height: calc(100vh - 56px);
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
    }}
    #cy {{ min-height: 0; background: #eef2f5; }}
    aside {{
      border-left: 1px solid var(--line);
      background: var(--panel);
      display: grid;
      grid-template-rows: minmax(0, 1fr) auto;
      min-width: 0;
    }}
    .panel {{ padding: 14px; overflow: auto; }}
    .panel h2 {{ margin: 0 0 10px; font-size: 15px; }}
    .kv {{ display: grid; grid-template-columns: 110px minmax(0, 1fr); gap: 6px 10px; font-size: 13px; }}
    .kv div:nth-child(odd) {{ color: var(--muted); }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #f2f4f7;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      font-size: 12px;
      line-height: 1.45;
    }}
    .replay {{
      border-top: 1px solid var(--line);
      padding: 12px;
      display: grid;
      gap: 10px;
    }}
    .controls {{ display: flex; gap: 8px; align-items: center; }}
    button {{
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 6px;
      padding: 7px 10px;
      cursor: pointer;
      font-size: 13px;
    }}
    button:hover {{ border-color: var(--accent); }}
    .counter {{ color: var(--muted); font-size: 13px; margin-left: auto; }}
    @media (max-width: 860px) {{
      main {{ grid-template-columns: 1fr; grid-template-rows: 58vh minmax(0, 1fr); }}
      aside {{ border-left: 0; border-top: 1px solid var(--line); }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Skeleton Architecture Replay</h1>
    <div class="meta" id="summary"></div>
  </header>
  <main>
    <div id="cy"></div>
    <aside>
      <div class="panel">
        <h2 id="detail-title">Select a node</h2>
        <div id="details"></div>
      </div>
      <section class="replay">
        <div class="controls">
          <button id="back" type="button">Back</button>
          <button id="forward" type="button">Forward</button>
          <span class="counter" id="counter">0 / 0</span>
        </div>
        <pre id="event-details">No event selected.</pre>
      </section>
    </aside>
  </main>
  <script id="snapshot-data" type="application/json">{snapshot_json}</script>
  <script>
    const snapshot = JSON.parse(document.getElementById("snapshot-data").textContent);
    const nodesById = new Map(snapshot.nodes.map((node) => [node.id, node]));
    const edgesByPair = new Map(snapshot.edges.map((edge) => [`${{edge.source}}->${{edge.target}}`, edge]));
    document.getElementById("summary").textContent =
      `${{snapshot.event_count}} events, ${{snapshot.nodes.length}} nodes, ${{snapshot.edges.length}} edges`;

    const maxFanOut = Math.max(1, ...snapshot.nodes.map((node) => node.fan_out || 0));
    const maxLoc = Math.max(1, ...snapshot.nodes.map((node) => node.loc || 0));
    const cy = cytoscape({{
      container: document.getElementById("cy"),
      elements: [
        ...snapshot.nodes.map((node) => ({{
          data: {{
            id: node.id,
            label: node.label || node.id,
            type: node.type,
            size: 28 + Math.min(34, ((node.fan_out || 0) / maxFanOut) * 24 + ((node.loc || 0) / maxLoc) * 10)
          }}
        }})),
        ...snapshot.edges.map((edge) => ({{
          data: {{
            id: edge.id,
            source: edge.source,
            target: edge.target,
            label: String(edge.call_count),
            weight: edge.call_count
          }}
        }}))
      ],
      style: [
        {{ selector: "node", style: {{
          "label": "data(label)",
          "font-size": 10,
          "text-valign": "center",
          "text-halign": "center",
          "background-color": "#496a7a",
          "color": "#17202a",
          "text-outline-width": 2,
          "text-outline-color": "#eef2f5",
          "width": "data(size)",
          "height": "data(size)"
        }} }},
        {{ selector: 'node[type = "module"]', style: {{ "background-color": "#6c8f4f", "shape": "round-rectangle" }} }},
        {{ selector: 'node[type = "class"]', style: {{ "background-color": "#8a6f9b", "shape": "hexagon" }} }},
        {{ selector: 'node[type = "instance"]', style: {{ "background-color": "#b88746", "shape": "diamond" }} }},
        {{ selector: 'node[type = "entrypoint"]', style: {{ "background-color": "#b44d34" }} }},
        {{ selector: "edge", style: {{
          "curve-style": "bezier",
          "target-arrow-shape": "triangle",
          "line-color": "#8ea0ad",
          "target-arrow-color": "#8ea0ad",
          "width": "mapData(weight, 1, 8, 1.5, 7)",
          "opacity": 0.75
        }} }},
        {{ selector: ".current", style: {{
          "line-color": "#b44d34",
          "target-arrow-color": "#b44d34",
          "background-color": "#b44d34",
          "opacity": 1,
          "z-index": 10
        }} }}
      ],
      layout: {{ name: "cose", animate: false, fit: true, padding: 40 }}
    }});

    cy.on("tap", "node", (event) => showNode(event.target.id()));
    function showNode(id) {{
      const node = nodesById.get(id);
      if (!node) return;
      document.getElementById("detail-title").textContent = node.label || id;
      const fields = ["type", "module", "class_name", "function", "qualified_name", "file", "line", "loc", "call_count", "fan_in", "fan_out", "first_seen", "last_seen"];
      const rows = fields
        .filter((field) => node[field] !== undefined && node[field] !== null)
        .map((field) => `<div>${{field}}</div><div>${{escapeHtml(String(node[field]))}}</div>`)
        .join("");
      const examples = {{
        arg_examples: node.arg_examples || [],
        return_examples: node.return_examples || []
      }};
      document.getElementById("details").innerHTML =
        `<div class="kv">${{rows}}</div><h2>Examples</h2><pre>${{escapeHtml(JSON.stringify(examples, null, 2))}}</pre>`;
    }}

    let current = -1;
    const events = snapshot.events || [];
    document.getElementById("counter").textContent = `0 / ${{events.length}}`;
    document.getElementById("back").addEventListener("click", () => step(-1));
    document.getElementById("forward").addEventListener("click", () => step(1));
    function step(direction) {{
      if (!events.length) return;
      current = Math.max(0, Math.min(events.length - 1, current + direction));
      renderEvent();
    }}
    function renderEvent() {{
      cy.elements().removeClass("current");
      const event = events[current];
      if (!event) return;
      const source = event.caller ? event.caller.node_id : "entrypoint";
      const target = event.callee.node_id;
      cy.getElementById(source).addClass("current");
      cy.getElementById(target).addClass("current");
      const edge = edgesByPair.get(`${{source}}->${{target}}`);
      if (edge) cy.getElementById(edge.id).addClass("current");
      document.getElementById("counter").textContent = `${{current + 1}} / ${{events.length}}`;
      document.getElementById("event-details").textContent = JSON.stringify(event, null, 2);
      showNode(target);
    }}
    function escapeHtml(value) {{
      return value.replace(/[&<>"']/g, (char) => ({{
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }}[char]));
    }}
  </script>
</body>
</html>
"""
