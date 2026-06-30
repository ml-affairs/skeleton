"""Static HTML report generation."""

from __future__ import annotations

import json
from dataclasses import dataclass
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
        return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Skeleton Architecture Replay</title>
  <link rel="icon" href="__SKELETON_FAVICON__">
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
      display: grid;
      gap: 9px;
      max-width: calc(100% - 36px);
      pointer-events: none;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 11px;
      background: rgba(7, 10, 18, 0.74);
      backdrop-filter: blur(12px);
      box-shadow: var(--shadow);
    }
    .legend-title {
      color: var(--cyan);
      font-size: 11px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .legend-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, auto));
      gap: 8px;
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
    }
    .schema {
      width: 20px;
      height: 14px;
      flex: 0 0 auto;
      border: 2px solid currentColor;
      background: currentColor;
      box-shadow: 0 0 16px currentColor;
    }
    .schema.module {
      color: var(--teal);
      border-radius: 5px;
      background: rgba(20, 184, 166, 0.45);
    }
    .schema.class {
      color: var(--violet);
      clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%);
      background: rgba(139, 92, 246, 0.62);
    }
    .schema.method {
      color: var(--amber);
      border-radius: 5px;
      background: rgba(245, 158, 11, 0.68);
    }
    .schema.function {
      color: var(--green);
      border-radius: 5px;
      border-style: dashed;
      background: rgba(34, 197, 94, 0.34);
    }
    .schema.call {
      width: 25px;
      height: 0;
      color: var(--rose);
      border: 0;
      border-top: 3px solid currentColor;
      border-radius: 0;
      background: transparent;
      box-shadow: 0 0 16px currentColor;
    }
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
    .event-card {
      margin-top: 10px;
      border: 1px solid rgba(94, 234, 212, 0.22);
      border-radius: 8px;
      overflow: hidden;
      background: rgba(2, 6, 23, 0.5);
    }
    .event-card-header {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
      align-items: center;
      gap: 8px;
      padding: 11px;
      border-bottom: 1px solid var(--line);
    }
    .entity-token {
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 9px;
      background: rgba(15, 23, 42, 0.88);
    }
    .entity-token .kind {
      display: block;
      margin-bottom: 4px;
      color: var(--muted);
      font-size: 10px;
      font-weight: 800;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .entity-token .name {
      display: block;
      overflow-wrap: anywhere;
      color: var(--ink);
      font-size: 13px;
      font-weight: 750;
      line-height: 1.25;
    }
    .entity-token.module { border-color: rgba(20, 184, 166, 0.48); box-shadow: inset 3px 0 0 var(--teal); }
    .entity-token.class { border-color: rgba(139, 92, 246, 0.52); box-shadow: inset 3px 0 0 var(--violet); }
    .entity-token.method { border-color: rgba(245, 158, 11, 0.5); box-shadow: inset 3px 0 0 var(--amber); }
    .entity-token.function { border-color: rgba(34, 197, 94, 0.5); box-shadow: inset 3px 0 0 var(--green); }
    .event-arrow {
      color: var(--rose);
      font-weight: 900;
      text-align: center;
      text-shadow: 0 0 16px rgba(251, 113, 133, 0.5);
    }
    .event-delta {
      display: grid;
      gap: 8px;
      padding: 11px;
    }
    .delta-line {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.4;
    }
    .delta-line strong {
      color: var(--ink);
      font-weight: 750;
    }
    .delta-label {
      width: 76px;
      flex: 0 0 auto;
      color: var(--faint);
      font-weight: 800;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    .arg-grid {
      display: grid;
      gap: 6px;
    }
    .arg-row {
      display: grid;
      grid-template-columns: 92px minmax(0, 1fr);
      gap: 8px;
      border: 1px solid rgba(148, 163, 184, 0.14);
      border-radius: 7px;
      padding: 7px;
      background: rgba(15, 23, 42, 0.52);
      font-size: 12px;
    }
    .arg-key {
      color: var(--ink);
      font-weight: 800;
      overflow-wrap: anywhere;
    }
    .arg-value {
      color: #b8c4d6;
      overflow-wrap: anywhere;
    }
    .arg-value.redacted {
      color: var(--rose);
      font-weight: 750;
    }
    .json-view {
      font-family: "SFMono-Regular", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      color: #aebbd0;
    }
    .json-key {
      color: var(--cyan);
      font-weight: 800;
    }
    .json-string { color: #d6e4ff; }
    .json-number { color: #f8d68a; }
    .json-boolean { color: #c4b5fd; }
    .json-null { color: #718096; }
    .json-entity-module { color: var(--teal); font-weight: 800; }
    .json-entity-class { color: var(--violet); font-weight: 800; }
    .json-entity-method { color: var(--amber); font-weight: 800; }
    .json-entity-function { color: var(--green); font-weight: 800; }
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
          <div class="legend-title">Schemas</div>
          <div class="legend-grid">
            <span class="pill"><span class="schema module"></span>module shell</span>
            <span class="pill"><span class="schema class"></span>class shell</span>
            <span class="pill"><span class="schema method"></span>method</span>
            <span class="pill"><span class="schema function"></span>function</span>
            <span class="pill"><span class="schema call"></span>runtime call</span>
          </div>
        </div>
      </section>
      <aside class="sidebar">
        <section class="inspector">
          <div class="eyebrow" id="detail-kind">Architecture</div>
          <h2 id="detail-title">Runtime actors</h2>
          <div class="node-kind" id="detail-summary">Modules contain classes and functions. Classes contain their methods. Calls connect the nested callable nodes.</div>
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
          <div id="event-focus"></div>
          <div class="section">
            <h3>Trace Evidence</h3>
            <pre class="json-view" id="event-details">No event selected.</pre>
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
    const moduleClassCounts = new Map();
    const actorRoles = new Map();
    const classNodesById = new Set();

    document.getElementById("project-root").textContent = snapshot.project_root || "project";
    document.getElementById("event-count").textContent = String(snapshot.event_count || events.length || 0);

    for (const node of rawNodes.values()) {
      if (node.type === "class") classNodesById.add(node.id);
      if (node.type === "class" && node.module) {
        moduleClassCounts.set(node.module, (moduleClassCounts.get(node.module) || 0) + 1);
      }
    }

    function addActorRole(ownerId, role) {
      if (!ownerId) return;
      if (!actorRoles.has(ownerId)) actorRoles.set(ownerId, new Set());
      actorRoles.get(ownerId).add(role);
    }

    function rolesForActor(ownerId) {
      return Array.from(actorRoles.get(ownerId) || []);
    }

    function isVisibleActor(node) {
      if (!node) return false;
      return node.type === "module" || node.type === "class";
    }

    function classIdForFunction(node) {
      if (!node || node.type !== "function") return null;
      if (node.class_name) return `class:${node.module}.${node.class_name}`;
      const qualified = node.qualified_name || node.id.replace(/^function:/, "");
      const modulePrefix = `${node.module}.`;
      if (!qualified.startsWith(modulePrefix)) return null;
      const localParts = qualified.slice(modulePrefix.length).split(".");
      if (localParts.length < 2) return null;
      const candidate = `class:${node.module}.${localParts[0]}`;
      return classNodesById.has(candidate) ? candidate : null;
    }

    function moduleIdForName(moduleName) {
      return `module:${moduleName}`;
    }

    function parentForFunction(node) {
      return classIdForFunction(node) || moduleIdForName(node.module);
    }

    function ownerForEndpoint(endpoint) {
      if (!endpoint) return null;
      if (endpoint.class_name) return `class:${endpoint.module}.${endpoint.class_name}`;
      return `module:${endpoint.module}`;
    }

    function ownerForNode(node) {
      if (!node || node.type === "entrypoint") return null;
      if (node.type === "class") return node.id;
      if (node.type === "module") return node.id;
      return classIdForFunction(node) || moduleIdForName(node.module);
    }

    function ownerLabel(ownerId) {
      if (!ownerId) return "entrypoint";
      const node = rawNodes.get(ownerId);
      return node?.label || ownerId.replace(/^(class|module):/, "");
    }

    function addOwnerMethod(ownerId, methodId) {
      if (!ownerId) return;
      if (!ownerMethods.has(ownerId)) ownerMethods.set(ownerId, new Set());
      ownerMethods.get(ownerId).add(methodId);
    }

    function addArchEdge(source, target, event) {
      if (!source || !target || source === target) return;
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
      const target = ownerForEndpoint(event.callee);
      if (!event.caller) addActorRole(target, "entrypoint");
      const source = ownerForEndpoint(event.caller);
      addArchEdge(source, target, event);
      addOwnerMethod(target, event.callee.node_id);
      if (event.caller) addOwnerMethod(source, event.caller.node_id);
    }

    function ownerMetric(ownerId, field) {
      const node = rawNodes.get(ownerId);
      const methodTotal = Array.from(ownerMethods.get(ownerId) || []).reduce((total, methodId) => {
        const method = rawNodes.get(methodId);
        return total + Number(method?.[field] || 0);
      }, 0);
      return Number(node?.[field] || 0) + methodTotal;
    }

    const actorNodes = Array.from(rawNodes.values())
      .filter((node) => isVisibleActor(node))
      .map((node) => {
        const adjacency = archAdjacency.get(node.id) || { incoming: new Set(), outgoing: new Set() };
        const loc = Number(node.loc || 0);
        const callCount = ownerMetric(node.id, "call_count");
        const degree = adjacency.incoming.size + adjacency.outgoing.size;
        const roles = rolesForActor(node.id);
        return {
          data: {
            id: node.id,
            label: node.label || node.id,
            type: node.type,
            parent: node.type === "class" ? moduleIdForName(node.module) : undefined,
            roles: roles.join(", "),
            loc,
            call_count: callCount,
            fan_in: adjacency.incoming.size,
            fan_out: adjacency.outgoing.size,
            degree,
            size: 42 + Math.min(54, callCount * 7 + degree * 9 + Math.min(18, loc / 3))
          },
          classes: [
            "container",
            node.type === "module" ? "module-container" : "class-container",
            roles.includes("entrypoint") ? "role-entrypoint" : ""
          ].filter(Boolean).join(" ")
        };
      });

    const visibleActorIds = new Set(actorNodes.map((node) => node.data.id));

    const methodNodes = Array.from(rawNodes.values())
      .filter((node) => node.type === "function")
      .map((node) => ({
        data: {
          id: node.id,
          owner: ownerForNode(node),
          parent: parentForFunction(node),
          label: node.function || node.label || node.id,
          type: classIdForFunction(node) ? "method" : "function",
          call_count: Number(node.call_count || 0),
          fan_in: Number(node.fan_in || 0),
          fan_out: Number(node.fan_out || 0),
          size: 22 + Math.min(22, Number(node.call_count || 0) * 5 + Number(node.fan_out || 0) * 4)
        }
      }));

    const renderedNodeIds = new Set([
      ...visibleActorIds,
      ...methodNodes.map((node) => node.data.id)
    ]);

    const archEdges = Array.from(archEdgeCounts.values())
      .filter((edge) => visibleActorIds.has(edge.source) && visibleActorIds.has(edge.target))
      .map((edge) => ({
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

    const callEdges = rawEdges
      .filter((edge) => renderedNodeIds.has(edge.source) && renderedNodeIds.has(edge.target))
      .map((edge) => ({
        data: {
          id: `call:${edge.id}`,
          source: edge.source,
          target: edge.target,
          type: "runtime-call",
          weight: edge.call_count
        }
      }));

    document.getElementById("actor-count").textContent = String(actorNodes.length);
    document.getElementById("edge-count").textContent = String(callEdges.length);

    const cy = cytoscape({
      container: document.getElementById("cy"),
      elements: [...actorNodes, ...methodNodes, ...callEdges],
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
        { selector: ".container", style: {
          "text-valign": "top",
          "text-halign": "center",
          "padding": 28,
          "compound-sizing-wrt-labels": "include",
          "min-width": 130,
          "min-height": 96,
          "background-opacity": 0.18,
          "border-width": 2,
          "border-style": "solid",
          "font-size": 13,
          "font-weight": 800,
          "text-margin-y": -10
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
        { selector: ".role-entrypoint", style: {
          "border-color": "#fda4af",
          "border-width": 5,
          "shadow-color": "#fb7185",
          "shadow-blur": 34,
          "shadow-opacity": 0.42
        } },
        { selector: 'node[type = "method"]', style: {
          "shape": "round-rectangle",
          "background-color": "#b45309",
          "border-color": "#fcd34d",
          "font-size": 9,
          "shadow-color": "#f59e0b"
        } },
        { selector: 'node[type = "function"]', style: {
          "shape": "round-rectangle",
          "background-color": "#15803d",
          "border-color": "#86efac",
          "border-style": "dashed",
          "font-size": 9,
          "shadow-color": "#22c55e"
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
        { selector: 'edge[type = "runtime-call"]', style: {
          "line-style": "solid",
          "line-color": "#fb7185",
          "target-arrow-color": "#fb7185",
          "opacity": 0.82
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

    let current = -1;
    let playTimer = null;
    document.getElementById("counter").textContent = `0 / ${events.length}`;
    showOverview();

    function selectNode(id) {
      stopPlay();
      const selected = rawNodes.get(id) || methodData(id);
      const ownerId = ownerForNode(selected) || id;
      revealForOwner(ownerId, [id]);
      showNode(id);
    }

    function revealForOwner(ownerId, extraIds = []) {
      if (!ownerId) return;
      cy.elements().removeClass("focus current dimmed");
      const owners = new Set([ownerId]);
      for (const id of extraIds) {
        const owner = ownerForNode(rawNodes.get(id));
        if (owner) owners.add(owner);
      }
      for (const owner of owners) {
        cy.getElementById(owner).addClass("focus");
        for (const methodId of ownerMethods.get(owner) || []) cy.getElementById(methodId).removeClass("hidden");
      }
    }

    function showOverview() {
      document.getElementById("detail-kind").textContent = "Architecture";
      document.getElementById("detail-title").textContent = "Runtime actors";
      document.getElementById("detail-summary").textContent = "Modules are outer shells. Classes and public callables are visually contained by the module or class that owns them.";
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
          Entrypoint and service are roles on actors, not standalone actors.
          Call edges connect public functions and methods inside their owning shells.
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
      const roles = rolesForActor(ownerId);
      const methods = Array.from(ownerMethods.get(ownerId) || [])
        .map((methodId) => rawNodes.get(methodId))
        .filter(Boolean);
      document.getElementById("detail-kind").textContent = isMethod ? "Method Trace" : `${node.type || "actor"} Actor`;
      document.getElementById("detail-title").textContent = node.label || node.function || id;
      document.getElementById("detail-summary").textContent = summaryForNode(node, ownerId, adjacency);
      document.getElementById("details").innerHTML = `
        <div class="section"><h3>Metrics</h3>${metricsTable(node, ownerId, adjacency)}</div>
        <div class="section"><h3>Roles</h3>${roleChips(roles)}</div>
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

    function roleChips(roles) {
      if (!roles.length) return '<div class="empty">No runtime role inferred yet.</div>';
      return `<div class="chips">${roles.map((role) => `<span class="chip">${escapeHtml(role)}</span>`).join("")}</div>`;
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
      if (!targetOwner) return;
      revealForOwner(targetOwner, [event.callee.node_id, event.caller?.node_id].filter(Boolean));
      const sourceNode = event.caller ? event.caller.node_id : null;
      const targetNode = event.callee.node_id;
      const callEdge = sourceNode ? cy.getElementById(`call:${sourceNode}->${targetNode}`) : null;
      if (sourceOwner) cy.getElementById(sourceOwner).addClass("current");
      cy.getElementById(targetOwner).addClass("current");
      if (sourceNode) cy.getElementById(sourceNode).removeClass("hidden").addClass("current");
      cy.getElementById(targetNode).removeClass("hidden").addClass("current");
      if (callEdge) callEdge.addClass("current");
      document.getElementById("timeline").value = String(current);
      document.getElementById("counter").textContent = `${current + 1} / ${events.length}`;
      document.getElementById("event-narrative").innerHTML = narrativeForEvent(event);
      document.getElementById("event-focus").innerHTML = eventFocusCard(event, sourceOwner, targetOwner);
      document.getElementById("event-details").innerHTML = syntaxHighlightJson(event);
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

    function eventFocusCard(event, sourceOwner, targetOwner) {
      const caller = event.caller;
      const callee = event.callee;
      const callerToken = caller
        ? entityToken(caller.qualified_name, endpointKind(caller), ownerLabel(sourceOwner))
        : entityToken("entrypoint", "module", ownerLabel(targetOwner));
      const calleeToken = entityToken(callee.qualified_name, endpointKind(callee), ownerLabel(targetOwner));
      const delta = event.event_type === "call"
        ? `Highlighted runtime call edge into <strong>${escapeHtml(callee.function || callee.qualified_name)}</strong>.`
        : `Captured return summary from <strong>${escapeHtml(callee.function || callee.qualified_name)}</strong>.`;
      const evidence = event.event_type === "call" ? argsTable(event.args) : returnEvidence(event.return_value);
      return `
        <div class="event-card">
          <div class="event-card-header">
            ${callerToken}
            <div class="event-arrow">${event.event_type === "call" ? "called" : "returned"}</div>
            ${calleeToken}
          </div>
          <div class="event-delta">
            <div class="delta-line"><span class="delta-label">Change</span><span>${delta}</span></div>
            <div class="delta-line"><span class="delta-label">Scope</span><span>${escapeHtml(ownerLabel(targetOwner))} is in focus; its owning shells are emphasized.</span></div>
            ${evidence}
          </div>
        </div>
      `;
    }

    function entityToken(name, kind, owner) {
      return `
        <div class="entity-token ${escapeAttr(kind)}">
          <span class="kind">${escapeHtml(kind)} · ${escapeHtml(owner || "runtime")}</span>
          <span class="name">${escapeHtml(name)}</span>
        </div>
      `;
    }

    function endpointKind(endpoint) {
      if (endpoint.class_name) return "method";
      return "function";
    }

    function argsTable(args) {
      if (!args || !Object.keys(args).length) {
        return '<div class="delta-line"><span class="delta-label">Args</span><span>No public arguments captured for this event.</span></div>';
      }
      const rows = Object.entries(args)
        .map(([key, value]) => `<div class="arg-row"><span class="arg-key">${escapeHtml(key)}</span><span class="arg-value ${value?.type === "redacted" ? "redacted" : ""}">${escapeHtml(summaryText(value))}</span></div>`)
        .join("");
      return `<div class="delta-line"><span class="delta-label">Args</span><div class="arg-grid">${rows}</div></div>`;
    }

    function returnEvidence(value) {
      if (!value) return '<div class="delta-line"><span class="delta-label">Return</span><span>No return summary captured.</span></div>';
      return `<div class="delta-line"><span class="delta-label">Return</span><strong>${escapeHtml(summaryText(value))}</strong></div>`;
    }

    function summaryText(value) {
      if (!value) return "none";
      if (value.type === "redacted") return "redacted";
      if (value.value !== undefined) return `${value.type}: ${JSON.stringify(value.value)}`;
      if (value.len !== undefined) return `${value.type} len=${value.len}`;
      if (value.object_id) return `${value.type} ${value.object_id}`;
      if (value.summary) return `${value.type}: ${value.summary}`;
      return value.type || JSON.stringify(value);
    }

    function syntaxHighlightJson(value) {
      const escaped = escapeHtml(JSON.stringify(value, null, 2));
      return escaped.replace(
        /(&quot;[^&]*?&quot;)(\\s*:)?|\\b(true|false|null)\\b|-?\\d+(?:\\.\\d+)?(?:[eE][+-]?\\d+)?/g,
        (match, quoted, colon, booleanValue) => {
          if (quoted && colon) return `<span class="json-key">${quoted}</span>${colon}`;
          if (quoted) return `<span class="${jsonStringClass(quoted)}">${quoted}</span>`;
          if (booleanValue === "true" || booleanValue === "false") return `<span class="json-boolean">${match}</span>`;
          if (booleanValue === "null") return `<span class="json-null">${match}</span>`;
          return `<span class="json-number">${match}</span>`;
        }
      );
    }

    function jsonStringClass(quoted) {
      const value = quoted.replace(/^&quot;|&quot;$/g, "");
      if (value.startsWith("module:")) return "json-entity-module";
      if (value.startsWith("class:")) return "json-entity-class";
      if (value.startsWith("function:")) return "json-entity-function";
      if (value.includes(".") && value.includes("Greeter")) return "json-entity-method";
      return "json-string";
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
