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
        """Return the static report HTML."""
        return self._template().replace("__SKELETON_SNAPSHOT_JSON__", snapshot_json)

    def _template(self) -> str:
        """Return the dark cinematic report template."""
        return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Skeleton Architecture Replay</title>
  <script src="https://unpkg.com/cytoscape@3.30.4/dist/cytoscape.min.js"></script>
  <style>
    :root {
      color-scheme: dark;
      --bg: #070a12;
      --panel: rgba(13, 18, 31, 0.94);
      --panel-strong: rgba(17, 24, 39, 0.98);
      --line: rgba(148, 163, 184, 0.18);
      --line-strong: rgba(94, 234, 212, 0.35);
      --ink: #e5eefc;
      --muted: #8ea0b8;
      --faint: #536174;
      --cyan: #38dce2;
      --teal: #14b8a6;
      --violet: #8b5cf6;
      --amber: #f59e0b;
      --rose: #fb7185;
      --green: #22c55e;
      --shadow: 0 22px 70px rgba(0, 0, 0, 0.38);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      overflow: hidden;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        linear-gradient(rgba(20, 184, 166, 0.05) 1px, transparent 1px),
        linear-gradient(90deg, rgba(20, 184, 166, 0.05) 1px, transparent 1px),
        var(--bg);
      background-size: 42px 42px;
      color: var(--ink);
    }
    .app {
      height: 100vh;
      display: grid;
      grid-template-rows: 72px minmax(0, 1fr);
    }
    header {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: center;
      gap: 20px;
      padding: 14px 20px;
      border-bottom: 1px solid var(--line);
      background: rgba(7, 10, 18, 0.82);
      backdrop-filter: blur(18px);
    }
    .brand {
      display: flex;
      align-items: center;
      min-width: 0;
      gap: 13px;
    }
    .mark {
      width: 42px;
      height: 42px;
      border: 1px solid rgba(56, 220, 226, 0.48);
      border-radius: 12px;
      display: grid;
      place-items: center;
      color: var(--cyan);
      font-weight: 800;
      box-shadow: 0 0 28px rgba(56, 220, 226, 0.2), inset 0 0 20px rgba(56, 220, 226, 0.08);
    }
    h1 {
      margin: 0;
      font-size: 17px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    .subtitle {
      margin-top: 4px;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .metrics {
      display: grid;
      grid-auto-flow: column;
      gap: 10px;
    }
    .metric {
      min-width: 92px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px 10px;
      background: rgba(15, 23, 42, 0.78);
      box-shadow: inset 0 0 20px rgba(56, 220, 226, 0.04);
    }
    .metric strong {
      display: block;
      font-size: 16px;
      line-height: 1;
    }
    .metric span {
      display: block;
      margin-top: 5px;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
    }
    main {
      min-height: 0;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 430px;
    }
    .stage {
      position: relative;
      min-width: 0;
      min-height: 0;
      overflow: hidden;
    }
    #cy {
      position: absolute;
      inset: 0;
      background:
        radial-gradient(circle at center, rgba(56, 220, 226, 0.08), transparent 45%),
        linear-gradient(135deg, rgba(56, 220, 226, 0.05), rgba(139, 92, 246, 0.04) 42%, transparent 68%);
    }
    .legend {
      position: absolute;
      left: 18px;
      bottom: 18px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      max-width: calc(100% - 36px);
      pointer-events: none;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      min-height: 28px;
      padding: 6px 9px;
      border: 1px solid var(--line);
      border-radius: 999px;
      color: var(--muted);
      background: rgba(7, 10, 18, 0.68);
      backdrop-filter: blur(12px);
      font-size: 12px;
      box-shadow: var(--shadow);
    }
    .dot {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: var(--cyan);
      box-shadow: 0 0 16px currentColor;
    }
    .dot.module { background: var(--cyan); color: var(--cyan); }
    .dot.class { background: var(--violet); color: var(--violet); }
    .dot.method { background: var(--amber); color: var(--amber); }
    .sidebar {
      min-width: 0;
      min-height: 0;
      display: grid;
      grid-template-rows: minmax(0, 1fr) auto;
      border-left: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
    }
    .inspector {
      min-height: 0;
      overflow: auto;
      padding: 18px;
    }
    .eyebrow {
      color: var(--cyan);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    h2 {
      margin: 7px 0 10px;
      font-size: 20px;
      line-height: 1.18;
      letter-spacing: 0;
    }
    .node-kind {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }
    .section {
      margin-top: 16px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
    }
    .section h3 {
      margin: 0 0 10px;
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }
    .kv {
      display: grid;
      grid-template-columns: 118px minmax(0, 1fr);
      gap: 7px 10px;
      font-size: 13px;
    }
    .kv div:nth-child(odd) { color: var(--muted); }
    .kv div:nth-child(even) {
      min-width: 0;
      overflow-wrap: anywhere;
      color: var(--ink);
    }
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .chip {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 6px 9px;
      color: var(--ink);
      background: rgba(15, 23, 42, 0.9);
      font-size: 12px;
      cursor: pointer;
    }
    .chip:hover {
      border-color: var(--line-strong);
      color: var(--cyan);
    }
    pre {
      margin: 0;
      max-height: 260px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 11px;
      color: #cbd5e1;
      background: rgba(2, 6, 23, 0.72);
      font-size: 12px;
      line-height: 1.48;
    }
    .empty {
      color: var(--faint);
      font-size: 13px;
      line-height: 1.5;
    }
    .replay {
      border-top: 1px solid var(--line);
      padding: 14px;
      background: var(--panel-strong);
    }
    .timeline {
      width: 100%;
      accent-color: var(--cyan);
    }
    .controls {
      display: grid;
      grid-template-columns: auto auto auto minmax(0, 1fr);
      align-items: center;
      gap: 8px;
      margin: 10px 0;
    }
    button {
      min-height: 34px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 7px 10px;
      color: var(--ink);
      background: rgba(15, 23, 42, 0.94);
      cursor: pointer;
      font-size: 13px;
    }
    button:hover {
      border-color: var(--line-strong);
      box-shadow: 0 0 22px rgba(56, 220, 226, 0.16);
    }
    .counter {
      justify-self: end;
      color: var(--muted);
      font-size: 12px;
    }
    .narrative {
      margin-top: 8px;
      color: var(--ink);
      font-size: 13px;
      line-height: 1.45;
    }
    .narrative strong {
      color: var(--cyan);
      font-weight: 700;
    }
    @media (max-width: 980px) {
      body { overflow: auto; }
      .app { height: auto; min-height: 100vh; }
      header { grid-template-columns: 1fr; }
      .metrics { grid-auto-flow: row; grid-template-columns: repeat(3, minmax(0, 1fr)); }
      main { grid-template-columns: 1fr; grid-template-rows: 58vh minmax(420px, auto); }
      .sidebar { border-left: 0; border-top: 1px solid var(--line); }
    }
  </style>
</head>
<body>
  <div class="app">
    <header>
      <div class="brand">
        <div class="mark">{ }</div>
        <div>
          <h1>Skeleton Architecture Replay</h1>
          <div class="subtitle" id="project-root"></div>
        </div>
      </div>
      <div class="metrics">
        <div class="metric"><strong id="event-count">0</strong><span>events</span></div>
        <div class="metric"><strong id="actor-count">0</strong><span>actors</span></div>
        <div class="metric"><strong id="edge-count">0</strong><span>calls</span></div>
      </div>
    </header>
    <main>
      <section class="stage">
        <div id="cy"></div>
        <div class="legend">
          <span class="pill"><span class="dot module"></span>module</span>
          <span class="pill"><span class="dot class"></span>class</span>
          <span class="pill"><span class="dot method"></span>method appears on focus/replay</span>
        </div>
      </section>
      <aside class="sidebar">
        <section class="inspector">
          <div class="eyebrow" id="detail-kind">Architecture</div>
          <h2 id="detail-title">Runtime actors</h2>
          <div class="node-kind" id="detail-summary">Classes and modules are shown first. Select an actor or step through replay to reveal the methods involved.</div>
          <div id="details"></div>
        </section>
        <section class="replay">
          <input class="timeline" id="timeline" min="0" max="0" value="0" type="range">
          <div class="controls">
            <button id="back" type="button">Prev</button>
            <button id="play" type="button">Play</button>
            <button id="forward" type="button">Next</button>
            <span class="counter" id="counter">0 / 0</span>
          </div>
          <div class="eyebrow">Current Event</div>
          <div class="narrative" id="event-narrative">No event selected.</div>
          <div class="section">
            <h3>Trace Evidence</h3>
            <pre id="event-details">No event selected.</pre>
          </div>
        </section>
      </aside>
    </main>
  </div>
  <script id="snapshot-data" type="application/json">__SKELETON_SNAPSHOT_JSON__</script>
  <script>
    const snapshot = JSON.parse(document.getElementById("snapshot-data").textContent);
    const rawNodes = new Map((snapshot.nodes || []).map((node) => [node.id, node]));
    const rawEdges = snapshot.edges || [];
    const events = snapshot.events || [];
    const ownerMethods = new Map();
    const archEdgeCounts = new Map();
    const archAdjacency = new Map();

    document.getElementById("project-root").textContent = snapshot.project_root || "project";
    document.getElementById("event-count").textContent = String(snapshot.event_count || events.length || 0);

    function ownerForEndpoint(endpoint) {
      if (!endpoint) return "entrypoint";
      if (endpoint.class_name) return `class:${endpoint.module}.${endpoint.class_name}`;
      return `module:${endpoint.module}`;
    }

    function ownerForNode(node) {
      if (!node || node.type === "entrypoint") return "entrypoint";
      if (node.type === "class") return node.id;
      if (node.type === "module") return node.id;
      if (node.class_name) return `class:${node.module}.${node.class_name}`;
      return `module:${node.module}`;
    }

    function ownerLabel(ownerId) {
      if (ownerId === "entrypoint") return "entrypoint";
      const node = rawNodes.get(ownerId);
      return node?.label || ownerId.replace(/^(class|module):/, "");
    }

    function addOwnerMethod(ownerId, methodId) {
      if (!ownerMethods.has(ownerId)) ownerMethods.set(ownerId, new Set());
      ownerMethods.get(ownerId).add(methodId);
    }

    function addArchEdge(source, target, event) {
      const key = `${source}->${target}`;
      const record = archEdgeCounts.get(key) || {
        id: `arch:${key}`,
        source,
        target,
        call_count: 0,
        first_seen: event.order,
        last_seen: event.order
      };
      record.call_count += 1;
      record.first_seen = Math.min(record.first_seen, event.order);
      record.last_seen = Math.max(record.last_seen, event.order);
      archEdgeCounts.set(key, record);
      if (!archAdjacency.has(source)) archAdjacency.set(source, { incoming: new Set(), outgoing: new Set() });
      if (!archAdjacency.has(target)) archAdjacency.set(target, { incoming: new Set(), outgoing: new Set() });
      archAdjacency.get(source).outgoing.add(target);
      archAdjacency.get(target).incoming.add(source);
    }

    for (const node of rawNodes.values()) {
      if (node.type === "function") addOwnerMethod(ownerForNode(node), node.id);
    }
    for (const event of events) {
      if (event.event_type !== "call") continue;
      const source = ownerForEndpoint(event.caller);
      const target = ownerForEndpoint(event.callee);
      addArchEdge(source, target, event);
      addOwnerMethod(target, event.callee.node_id);
      if (event.caller) addOwnerMethod(source, event.caller.node_id);
    }

    function ownerMetric(ownerId, field) {
      if (ownerId === "entrypoint") return archAdjacency.get(ownerId)?.outgoing.size || 0;
      const node = rawNodes.get(ownerId);
      const methodTotal = Array.from(ownerMethods.get(ownerId) || []).reduce((total, methodId) => {
        const method = rawNodes.get(methodId);
        return total + Number(method?.[field] || 0);
      }, 0);
      return Number(node?.[field] || 0) + methodTotal;
    }

    const actorNodes = Array.from(rawNodes.values())
      .filter((node) => ["module", "class", "entrypoint"].includes(node.type))
      .map((node) => {
        const adjacency = archAdjacency.get(node.id) || { incoming: new Set(), outgoing: new Set() };
        const loc = Number(node.loc || 0);
        const callCount = ownerMetric(node.id, "call_count");
        const degree = adjacency.incoming.size + adjacency.outgoing.size;
        return {
          data: {
            id: node.id,
            label: node.label || node.id,
            type: node.type,
            loc,
            call_count: callCount,
            fan_in: adjacency.incoming.size,
            fan_out: adjacency.outgoing.size,
            degree,
            size: 42 + Math.min(54, callCount * 7 + degree * 9 + Math.min(18, loc / 3))
          }
        };
      });

    const methodNodes = Array.from(rawNodes.values())
      .filter((node) => node.type === "function")
      .map((node) => ({
        data: {
          id: node.id,
          owner: ownerForNode(node),
          label: node.function || node.label || node.id,
          type: "method",
          call_count: Number(node.call_count || 0),
          fan_in: Number(node.fan_in || 0),
          fan_out: Number(node.fan_out || 0),
          size: 22 + Math.min(22, Number(node.call_count || 0) * 5 + Number(node.fan_out || 0) * 4)
        },
        classes: "detail hidden"
      }));

    const archEdges = Array.from(archEdgeCounts.values()).map((edge) => ({
      data: {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: "architecture-call",
        weight: edge.call_count,
        first_seen: edge.first_seen,
        last_seen: edge.last_seen
      }
    }));

    const detailEdges = rawEdges.map((edge) => ({
      data: {
        id: `detail:${edge.id}`,
        source: edge.source,
        target: edge.target,
        type: "method-call",
        weight: edge.call_count
      },
      classes: "detail hidden"
    }));

    document.getElementById("actor-count").textContent = String(actorNodes.length);
    document.getElementById("edge-count").textContent = String(archEdges.length);

    const cy = cytoscape({
      container: document.getElementById("cy"),
      elements: [...actorNodes, ...methodNodes, ...archEdges, ...detailEdges],
      style: [
        { selector: "node", style: {
          "label": "data(label)",
          "font-size": 11,
          "font-weight": 700,
          "text-valign": "center",
          "text-halign": "center",
          "text-wrap": "wrap",
          "text-max-width": 96,
          "color": "#e5eefc",
          "text-outline-width": 2,
          "text-outline-color": "#070a12",
          "width": "data(size)",
          "height": "data(size)",
          "border-width": "mapData(degree, 0, 8, 1, 7)",
          "border-color": "rgba(229, 238, 252, 0.38)",
          "shadow-blur": 24,
          "shadow-opacity": 0.28,
          "shadow-offset-x": 0,
          "shadow-offset-y": 0
        } },
        { selector: 'node[type = "module"]', style: {
          "shape": "round-rectangle",
          "background-color": "#0f766e",
          "border-color": "#5eead4",
          "shadow-color": "#38dce2"
        } },
        { selector: 'node[type = "class"]', style: {
          "shape": "hexagon",
          "background-color": "#6d28d9",
          "border-color": "#c4b5fd",
          "shadow-color": "#8b5cf6"
        } },
        { selector: 'node[type = "entrypoint"]', style: {
          "shape": "ellipse",
          "background-color": "#be123c",
          "border-color": "#fda4af",
          "shadow-color": "#fb7185"
        } },
        { selector: 'node[type = "method"]', style: {
          "shape": "ellipse",
          "background-color": "#b45309",
          "border-color": "#fcd34d",
          "font-size": 9,
          "shadow-color": "#f59e0b"
        } },
        { selector: "edge", style: {
          "curve-style": "bezier",
          "target-arrow-shape": "triangle",
          "line-color": "rgba(148, 163, 184, 0.55)",
          "target-arrow-color": "rgba(148, 163, 184, 0.68)",
          "width": "mapData(weight, 1, 12, 1.8, 10)",
          "opacity": 0.62,
          "arrow-scale": 1.1
        } },
        { selector: 'edge[type = "architecture-call"]', style: {
          "line-color": "#38dce2",
          "target-arrow-color": "#38dce2",
          "opacity": 0.72
        } },
        { selector: 'edge[type = "method-call"]', style: {
          "line-style": "dashed",
          "line-color": "#f59e0b",
          "target-arrow-color": "#f59e0b",
          "opacity": 0.76
        } },
        { selector: ".hidden", style: { "display": "none" } },
        { selector: ".dimmed", style: { "opacity": 0.18 } },
        { selector: ".current", style: {
          "opacity": 1,
          "z-index": 50,
          "line-color": "#fb7185",
          "target-arrow-color": "#fb7185",
          "background-color": "#fb7185",
          "border-color": "#fecdd3",
          "shadow-blur": 46,
          "shadow-opacity": 0.72,
          "shadow-color": "#fb7185"
        } },
        { selector: ".focus", style: {
          "opacity": 1,
          "z-index": 30,
          "border-color": "#ffffff",
          "shadow-blur": 36,
          "shadow-opacity": 0.52
        } }
      ],
      layout: {
        name: "cose",
        animate: false,
        fit: true,
        padding: 78,
        nodeRepulsion: 9000,
        idealEdgeLength: 140,
        edgeElasticity: 100,
        gravity: 0.55,
        numIter: 1400
      }
    });

    cy.on("tap", "node", (event) => selectNode(event.target.id()));
    document.getElementById("back").addEventListener("click", () => step(-1));
    document.getElementById("forward").addEventListener("click", () => step(1));
    document.getElementById("play").addEventListener("click", togglePlay);
    document.getElementById("timeline").max = String(Math.max(0, events.length - 1));
    document.getElementById("timeline").addEventListener("input", (event) => {
      current = Number(event.target.value);
      renderEvent();
    });

    let current = events.length ? 0 : -1;
    let playTimer = null;
    if (events.length) renderEvent();
    else showOverview();

    function selectNode(id) {
      stopPlay();
      revealForOwner(id);
      showNode(id);
    }

    function revealForOwner(ownerId, extraIds = []) {
      cy.elements().removeClass("focus current dimmed");
      cy.$(".detail").addClass("hidden");
      const owners = new Set([ownerId]);
      for (const id of extraIds) owners.add(ownerForNode(rawNodes.get(id)) || id);
      for (const owner of owners) {
        cy.getElementById(owner).addClass("focus");
        for (const methodId of ownerMethods.get(owner) || []) cy.getElementById(methodId).removeClass("hidden");
      }
      for (const edge of detailEdges) {
        const sourceVisible = !cy.getElementById(edge.data.source).hasClass("hidden");
        const targetVisible = !cy.getElementById(edge.data.target).hasClass("hidden");
        if (sourceVisible && targetVisible) cy.getElementById(edge.data.id).removeClass("hidden");
      }
    }

    function showOverview() {
      document.getElementById("detail-kind").textContent = "Architecture";
      document.getElementById("detail-title").textContent = "Runtime actors";
      document.getElementById("detail-summary").textContent = "Classes and modules are shown first. Select an actor or step through replay to reveal the methods involved.";
      const topActors = actorNodes
        .map((node) => node.data)
        .sort((left, right) => (right.call_count + right.degree) - (left.call_count + left.degree))
        .slice(0, 6)
        .map((node) => `<button class="chip" data-node="${escapeAttr(node.id)}">${escapeHtml(node.label)} · calls ${node.call_count}</button>`)
        .join("");
      document.getElementById("details").innerHTML = `
        <div class="section"><h3>Most Active Actors</h3><div class="chips">${topActors || '<span class="empty">No runtime actors observed.</span>'}</div></div>
        <div class="section"><h3>How To Read This</h3><div class="node-kind">
          Node size combines observed call count, in-degree, out-degree, and approximate LOC.
          Edge width represents observed runtime call count.
          Method nodes stay hidden until they explain a selected actor or replay event.
        </div></div>
      `;
      bindChipClicks();
    }

    function showNode(id) {
      const node = rawNodes.get(id) || methodData(id);
      if (!node) return;
      const isMethod = node.type === "function" || node.type === "method";
      const ownerId = isMethod ? ownerForNode(node) : id;
      const adjacency = archAdjacency.get(ownerId) || { incoming: new Set(), outgoing: new Set() };
      const methods = Array.from(ownerMethods.get(ownerId) || [])
        .map((methodId) => rawNodes.get(methodId))
        .filter(Boolean);
      document.getElementById("detail-kind").textContent = isMethod ? "Method Trace" : `${node.type || "actor"} Actor`;
      document.getElementById("detail-title").textContent = node.label || node.function || id;
      document.getElementById("detail-summary").textContent = summaryForNode(node, ownerId, adjacency);
      document.getElementById("details").innerHTML = `
        <div class="section"><h3>Metrics</h3>${metricsTable(node, ownerId, adjacency)}</div>
        <div class="section"><h3>Observed Calls</h3>${callList(ownerId)}</div>
        <div class="section"><h3>Methods</h3>${methodChips(methods)}</div>
        <div class="section"><h3>Examples</h3><pre>${escapeHtml(JSON.stringify(examplesForNode(node, methods), null, 2))}</pre></div>
      `;
      bindChipClicks();
    }

    function methodData(id) {
      const element = cy.getElementById(id);
      if (!element || element.empty()) return null;
      return element.data();
    }

    function summaryForNode(node, ownerId, adjacency) {
      const label = node.qualified_name || node.module || node.id;
      return `${label} · fan-in ${adjacency.incoming.size} · fan-out ${adjacency.outgoing.size}`;
    }

    function metricsTable(node, ownerId, adjacency) {
      const rows = [
        ["type", node.type],
        ["module", node.module],
        ["class", node.class_name],
        ["function", node.function],
        ["file", node.file],
        ["line", node.line],
        ["loc", node.loc],
        ["call_count", ownerMetric(ownerId, "call_count")],
        ["fan_in", adjacency.incoming.size],
        ["fan_out", adjacency.outgoing.size],
        ["first_seen", node.first_seen],
        ["last_seen", node.last_seen]
      ].filter((row) => row[1] !== undefined && row[1] !== null && row[1] !== "");
      return `<div class="kv">${rows.map(([key, value]) => `<div>${escapeHtml(String(key))}</div><div>${escapeHtml(String(value))}</div>`).join("")}</div>`;
    }

    function callList(ownerId) {
      const incoming = Array.from(archAdjacency.get(ownerId)?.incoming || []).map((id) => `called by ${ownerLabel(id)}`);
      const outgoing = Array.from(archAdjacency.get(ownerId)?.outgoing || []).map((id) => `calls ${ownerLabel(id)}`);
      const rows = [...incoming, ...outgoing];
      if (!rows.length) return '<div class="empty">No architecture-level calls observed for this actor.</div>';
      return `<div class="chips">${rows.map((row) => `<span class="chip">${escapeHtml(row)}</span>`).join("")}</div>`;
    }

    function methodChips(methods) {
      if (!methods.length) return '<div class="empty">No public method calls observed.</div>';
      return `<div class="chips">${methods.map((method) => `<button class="chip" data-node="${escapeAttr(method.id)}">${escapeHtml(method.label || method.function || method.id)}</button>`).join("")}</div>`;
    }

    function examplesForNode(node, methods) {
      if (node.type === "function") {
        return { arg_examples: node.arg_examples || [], return_examples: node.return_examples || [] };
      }
      return {
        methods: methods.map((method) => ({
          id: method.id,
          arg_examples: method.arg_examples || [],
          return_examples: method.return_examples || []
        }))
      };
    }

    function step(direction) {
      if (!events.length) return;
      current = Math.max(0, Math.min(events.length - 1, current + direction));
      renderEvent();
    }

    function togglePlay() {
      if (playTimer) {
        stopPlay();
        return;
      }
      document.getElementById("play").textContent = "Pause";
      playTimer = window.setInterval(() => {
        if (current >= events.length - 1) {
          stopPlay();
          return;
        }
        step(1);
      }, 900);
    }

    function stopPlay() {
      if (!playTimer) return;
      window.clearInterval(playTimer);
      playTimer = null;
      document.getElementById("play").textContent = "Play";
    }

    function renderEvent() {
      cy.elements().removeClass("current dimmed focus");
      const event = events[current];
      if (!event) return;
      const sourceOwner = ownerForEndpoint(event.caller);
      const targetOwner = ownerForEndpoint(event.callee);
      revealForOwner(targetOwner, [event.callee.node_id, event.caller?.node_id].filter(Boolean));
      const sourceNode = event.caller ? event.caller.node_id : sourceOwner;
      const targetNode = event.callee.node_id;
      const archEdge = cy.getElementById(`arch:${sourceOwner}->${targetOwner}`);
      const detailEdge = cy.getElementById(`detail:${sourceNode}->${targetNode}`);
      cy.getElementById(sourceOwner).addClass("current");
      cy.getElementById(targetOwner).addClass("current");
      cy.getElementById(sourceNode).removeClass("hidden").addClass("current");
      cy.getElementById(targetNode).removeClass("hidden").addClass("current");
      if (archEdge) archEdge.addClass("current");
      if (detailEdge) detailEdge.removeClass("hidden").addClass("current");
      document.getElementById("timeline").value = String(current);
      document.getElementById("counter").textContent = `${current + 1} / ${events.length}`;
      document.getElementById("event-narrative").innerHTML = narrativeForEvent(event);
      document.getElementById("event-details").textContent = JSON.stringify(event, null, 2);
      showNode(targetNode);
      cy.animate({ fit: { eles: cy.$(".current"), padding: 130 } }, { duration: 280 });
    }

    function narrativeForEvent(event) {
      const caller = event.caller ? event.caller.qualified_name : "entrypoint";
      const callee = event.callee.qualified_name;
      if (event.event_type === "call") {
        return `<strong>${escapeHtml(caller)}</strong> called <strong>${escapeHtml(callee)}</strong>${argsSummary(event.args)}`;
      }
      return `<strong>${escapeHtml(callee)}</strong> returned${returnSummary(event.return_value)}`;
    }

    function argsSummary(args) {
      if (!args || !Object.keys(args).length) return ".";
      return ` with ${escapeHtml(Object.keys(args).join(", "))}.`;
    }

    function returnSummary(value) {
      if (!value) return ".";
      if (value.type === "str" && value.value !== undefined) return ` ${escapeHtml(JSON.stringify(value.value))}.`;
      return ` ${escapeHtml(value.type || "value")}.`;
    }

    function bindChipClicks() {
      for (const chip of document.querySelectorAll("[data-node]")) {
        chip.addEventListener("click", () => selectNode(chip.getAttribute("data-node")));
      }
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
      }[char]));
    }

    function escapeAttr(value) {
      return escapeHtml(value).replace(/`/g, "&#96;");
    }
  </script>
</body>
</html>
"""
