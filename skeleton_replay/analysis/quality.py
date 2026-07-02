"""Architecture quality signals derived from Skeleton snapshots."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

JsonObject = dict[str, Any]
Severity = Literal["high", "medium", "low", "info"]


@dataclass(frozen=True)
class QualityFinding:
    """One evidence-backed architecture quality signal."""

    severity: Severity
    category: str
    title: str
    actor_id: str
    actor_label: str
    evidence: tuple[str, ...]
    interpretation: str
    suggested_refactors: tuple[str, ...]

    def to_json(self) -> JsonObject:
        """Return a JSON-safe finding representation."""
        return {
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "actor_id": self.actor_id,
            "actor_label": self.actor_label,
            "evidence": list(self.evidence),
            "interpretation": self.interpretation,
            "suggested_refactors": list(self.suggested_refactors),
        }


@dataclass(frozen=True)
class ModuleRuntimeStats:
    """Runtime and static measurements for one module."""

    module: str
    touches: int = 0
    fan_in: int = 0
    fan_out: int = 0
    loc: int = 0
    classes: int = 0
    functions: int = 0
    imports: int = 0

    @property
    def public_surface(self) -> int:
        """Return the approximate public class/function surface size."""
        return self.classes + self.functions


@dataclass(frozen=True)
class ArchitectureQualityAnalyzer:
    """Derives quiet design-quality signals from one runtime snapshot."""

    high_callable_fan_out: int = 12
    hotspot_event_ratio: float = 0.2
    large_module_loc: int = 1_000
    very_large_module_loc: int = 2_500
    broad_surface_size: int = 30
    broad_import_count: int = 24
    max_findings: int = 12

    def analyze(self, snapshot: JsonObject) -> JsonObject:
        """Analyze a snapshot and return JSON-ready architecture quality evidence."""
        nodes = self._dict_items(snapshot.get("nodes", []))
        edges = self._dict_items(snapshot.get("edges", []))
        events = self._dict_items(snapshot.get("events", []))
        node_by_id = {str(node.get("id", "")): node for node in nodes}
        module_stats = self._module_stats(nodes=nodes, edges=edges, events=events, node_by_id=node_by_id)
        findings = self._findings(snapshot=snapshot, nodes=nodes, edges=edges, events=events, module_stats=module_stats, node_by_id=node_by_id)
        summary = {
            "events": int(snapshot.get("event_count", len(events)) or 0),
            "nodes": len(nodes),
            "edges": len(edges),
            "runtime_modules": sum(1 for stats in module_stats.values() if stats.touches > 0),
            "resource_events": self._resource_event_count(events),
            "redacted_values": self._redacted_value_count(events),
            "top_runtime_modules": [self._module_stat_json(stats) for stats in sorted(module_stats.values(), key=lambda stats: stats.touches, reverse=True)[:5] if stats.touches > 0],
            "top_runtime_packages": self._top_runtime_packages(module_stats),
            "finding_count": len(findings),
        }
        return {
            "schema_version": 1,
            "summary": summary,
            "findings": [finding.to_json() for finding in findings[: self.max_findings]],
            "llm_guidance": [
                "Use findings as prompts for code review, not as absolute quality scores.",
                "Prioritize high fan-out runtime workflows and oversized modules first; they tend to hide orchestration, policy, and I/O responsibilities.",
                "Cross-check every finding against source ownership before refactoring because Skeleton observes one scenario, not every path.",
            ],
        }

    def _findings(
        self,
        *,
        snapshot: JsonObject,
        nodes: list[JsonObject],
        edges: list[JsonObject],
        events: list[JsonObject],
        module_stats: dict[str, ModuleRuntimeStats],
        node_by_id: dict[str, JsonObject],
    ) -> list[QualityFinding]:
        findings: list[QualityFinding] = []
        findings.extend(self._callable_fan_out_findings(nodes))
        findings.extend(self._hot_module_findings(snapshot=snapshot, module_stats=module_stats))
        findings.extend(self._large_module_findings(module_stats))
        findings.extend(self._broad_surface_findings(module_stats))
        findings.extend(self._package_concentration_findings(snapshot=snapshot, module_stats=module_stats))
        findings.extend(self._test_runtime_findings(module_stats))
        findings.extend(self._resource_boundary_findings(events=events, edges=edges, node_by_id=node_by_id))
        return sorted(findings, key=self._finding_sort_key)

    def _callable_fan_out_findings(self, nodes: list[JsonObject]) -> list[QualityFinding]:
        findings: list[QualityFinding] = []
        for node in nodes:
            if node.get("type") not in {"function", "method"}:
                continue
            fan_out = int(node.get("fan_out", 0) or 0)
            call_count = int(node.get("call_count", 0) or 0)
            if fan_out < self.high_callable_fan_out:
                continue
            label = str(node.get("qualified_name") or node.get("label") or node.get("id"))
            findings.append(
                QualityFinding(
                    severity="high",
                    category="orchestration",
                    title="High fan-out runtime workflow",
                    actor_id=str(node.get("id", "")),
                    actor_label=label,
                    evidence=(f"fan_out={fan_out}", f"call_count={call_count}"),
                    interpretation=(
                        "This callable coordinates many observed actors in one scenario. It may be a legitimate composition root, "
                        "or it may be collecting business policy, adapter calls, and workflow branching in one place."
                    ),
                    suggested_refactors=(
                        "Check whether orchestration, domain policy, persistence, and adapter concerns are separated behind explicit ports.",
                        "If this is not a composition root, consider extracting smaller application-service steps with clear input/output contracts.",
                    ),
                )
            )
        return findings

    def _hot_module_findings(self, *, snapshot: JsonObject, module_stats: dict[str, ModuleRuntimeStats]) -> list[QualityFinding]:
        event_count = int(snapshot.get("event_count", 0) or 0)
        threshold = max(12, int(event_count * self.hotspot_event_ratio))
        findings: list[QualityFinding] = []
        for stats in sorted(module_stats.values(), key=lambda item: item.touches, reverse=True)[:4]:
            if stats.touches < threshold:
                continue
            findings.append(
                QualityFinding(
                    severity="medium",
                    category="runtime_hotspot",
                    title="Runtime hotspot module",
                    actor_id=f"module:{stats.module}",
                    actor_label=stats.module,
                    evidence=(f"touches={stats.touches}", f"fan_in={stats.fan_in}", f"fan_out={stats.fan_out}"),
                    interpretation="A large share of this scenario flows through this module. Hotspots are good review anchors because coupling and responsibility drift often accumulate there first.",
                    suggested_refactors=(
                        "Review whether this module owns one clear responsibility.",
                        "Look for hidden I/O, broad adapter knowledge, or domain rules that could move behind narrower collaborators.",
                    ),
                )
            )
        return findings

    def _large_module_findings(self, module_stats: dict[str, ModuleRuntimeStats]) -> list[QualityFinding]:
        findings: list[QualityFinding] = []
        for stats in sorted(module_stats.values(), key=lambda item: item.loc, reverse=True)[:6]:
            if stats.loc < self.large_module_loc:
                continue
            severity: Severity = "high" if stats.loc >= self.very_large_module_loc else "medium"
            findings.append(
                QualityFinding(
                    severity=severity,
                    category="module_size",
                    title="Large module surface",
                    actor_id=f"module:{stats.module}",
                    actor_label=stats.module,
                    evidence=(f"loc={stats.loc}", f"classes={stats.classes}", f"functions={stats.functions}"),
                    interpretation="Large modules raise the cost of local reasoning and tend to mix orchestration, policy, adapters, and test scaffolding unless the ownership boundary is very deliberate.",
                    suggested_refactors=(
                        "Split by owned actor or responsibility rather than by generic helper buckets.",
                        "Move I/O adapters, repositories, and workflow policies behind explicit classes with narrow public methods.",
                    ),
                )
            )
        return findings

    def _broad_surface_findings(self, module_stats: dict[str, ModuleRuntimeStats]) -> list[QualityFinding]:
        findings: list[QualityFinding] = []
        for stats in sorted(module_stats.values(), key=lambda item: (item.public_surface, item.imports), reverse=True)[:6]:
            if stats.public_surface < self.broad_surface_size and stats.imports < self.broad_import_count:
                continue
            findings.append(
                QualityFinding(
                    severity="medium",
                    category="module_surface",
                    title="Broad module API surface",
                    actor_id=f"module:{stats.module}",
                    actor_label=stats.module,
                    evidence=(f"classes_plus_functions={stats.public_surface}", f"imports={stats.imports}"),
                    interpretation="A broad module surface can make ownership unclear. In large Python projects this often weakens dependency direction and makes refactoring harder.",
                    suggested_refactors=(
                        "Identify the primary public actor for the module and move secondary actors into owned modules.",
                        "Prefer constructor-injected collaborators over modules that import many peer implementation details directly.",
                    ),
                )
            )
        return findings

    def _package_concentration_findings(self, *, snapshot: JsonObject, module_stats: dict[str, ModuleRuntimeStats]) -> list[QualityFinding]:
        event_count = int(snapshot.get("event_count", 0) or 0)
        if event_count < 20:
            return []
        package_touches: dict[str, int] = {}
        for stats in module_stats.values():
            package = self._package_name(stats.module)
            if package:
                package_touches[package] = package_touches.get(package, 0) + stats.touches
        if not package_touches:
            return []
        package, touches = max(package_touches.items(), key=lambda item: item[1])
        if touches < event_count * 0.55:
            return []
        return [
            QualityFinding(
                severity="low",
                category="package_concentration",
                title="Scenario concentrated in one package",
                actor_id=f"package:{package}",
                actor_label=package,
                evidence=(f"package_touches={touches}", f"events={event_count}"),
                interpretation="This trace is dominated by one package. That can be healthy for a focused workflow, but it is worth checking whether outward dependencies are explicit and narrow.",
                suggested_refactors=(
                    "Use the package as the first review frame for scenario ownership.",
                    "Look for package-internal calls that should be stable public actor methods rather than incidental helper calls.",
                ),
            )
        ]

    def _test_runtime_findings(self, module_stats: dict[str, ModuleRuntimeStats]) -> list[QualityFinding]:
        touched_tests = [stats for stats in module_stats.values() if stats.touches > 0 and (stats.module == "tests" or stats.module.startswith("tests."))]
        if not touched_tests:
            return []
        total_touches = sum(stats.touches for stats in touched_tests)
        return [
            QualityFinding(
                severity="info",
                category="scenario_boundary",
                title="Test harness participated in the trace",
                actor_id="tests",
                actor_label="tests",
                evidence=(f"test_module_touches={total_touches}",),
                interpretation="The scenario includes test harness actors. That is useful evidence for test workflow understanding, but should not be mistaken for production architecture.",
                suggested_refactors=("When reviewing production design, mentally separate test fixtures from runtime application actors.",),
            )
        ]

    def _resource_boundary_findings(self, *, events: list[JsonObject], edges: list[JsonObject], node_by_id: dict[str, JsonObject]) -> list[QualityFinding]:
        resource_events = self._resource_event_count(events)
        if resource_events == 0:
            return [
                QualityFinding(
                    severity="info",
                    category="boundary_evidence",
                    title="No external resource boundary observed",
                    actor_id="resources",
                    actor_label="external resources",
                    evidence=("resource_events=0",),
                    interpretation="This scenario did not touch traced filesystem, stdout, database, or external-service endpoints. That may be expected, or the scenario may be too narrow to reveal I/O boundaries.",
                    suggested_refactors=("Run a scenario that crosses persistence or integration boundaries when reviewing adapter design.",),
                )
            ]
        categories: dict[str, int] = {}
        for event in events:
            callee = event.get("callee")
            if not isinstance(callee, dict):
                continue
            if callee.get("endpoint_type") not in {"resource", "external_service"}:
                continue
            category = str(callee.get("resource_category") or callee.get("endpoint_type") or "resource")
            categories[category] = categories.get(category, 0) + 1
        edge_count = sum(1 for edge in edges if self._edge_touches_resource(edge, node_by_id))
        return [
            QualityFinding(
                severity="info",
                category="boundary_evidence",
                title="External boundary evidence observed",
                actor_id="resources",
                actor_label="external resources",
                evidence=(f"resource_events={resource_events}", f"resource_edges={edge_count}", f"categories={categories}"),
                interpretation="The trace contains concrete I/O or external-service boundaries. These are useful anchors for checking whether adapters isolate infrastructure from domain logic.",
                suggested_refactors=(
                    "Verify that domain objects do not call resources directly.",
                    "Prefer ports/adapters or repositories around persistence, stdout, queues, HTTP services, and model providers.",
                ),
            )
        ]

    def _module_stats(self, *, nodes: list[JsonObject], edges: list[JsonObject], events: list[JsonObject], node_by_id: dict[str, JsonObject]) -> dict[str, ModuleRuntimeStats]:
        raw_stats: dict[str, dict[str, int | str]] = {}
        for node in nodes:
            if node.get("type") != "module":
                continue
            module = str(node.get("module") or node.get("label") or "")
            if not module:
                continue
            raw_stats[module] = {
                "module": module,
                "touches": 0,
                "fan_in": int(node.get("fan_in", 0) or 0),
                "fan_out": int(node.get("fan_out", 0) or 0),
                "loc": int(node.get("loc", 0) or 0),
                "classes": self._metric_count(node.get("classes", 0)),
                "functions": self._metric_count(node.get("functions", 0)),
                "imports": self._metric_count(node.get("imports", 0)),
            }
        self._collect_runtime_module_touches(events=events, raw_stats=raw_stats)
        self._collect_runtime_module_edges(edges=edges, node_by_id=node_by_id, raw_stats=raw_stats)
        return {
            module: ModuleRuntimeStats(
                module=module,
                touches=int(values.get("touches", 0) or 0),
                fan_in=int(values.get("fan_in", 0) or 0),
                fan_out=int(values.get("fan_out", 0) or 0),
                loc=int(values.get("loc", 0) or 0),
                classes=int(values.get("classes", 0) or 0),
                functions=int(values.get("functions", 0) or 0),
                imports=int(values.get("imports", 0) or 0),
            )
            for module, values in raw_stats.items()
        }

    def _collect_runtime_module_touches(self, *, events: list[JsonObject], raw_stats: dict[str, dict[str, int | str]]) -> None:
        for event in events:
            for endpoint_key in ("caller", "callee"):
                endpoint = event.get(endpoint_key)
                if not isinstance(endpoint, dict) or endpoint.get("endpoint_type") not in {None, "function"}:
                    continue
                module = str(endpoint.get("module") or "")
                if not module:
                    continue
                stats = raw_stats.setdefault(module, {"module": module, "touches": 0, "fan_in": 0, "fan_out": 0, "loc": 0, "classes": 0, "functions": 0, "imports": 0})
                stats["touches"] = int(stats.get("touches", 0) or 0) + 1

    def _collect_runtime_module_edges(self, *, edges: list[JsonObject], node_by_id: dict[str, JsonObject], raw_stats: dict[str, dict[str, int | str]]) -> None:
        incoming: dict[str, set[str]] = {}
        outgoing: dict[str, set[str]] = {}
        for edge in edges:
            source_module = self._module_for_node_id(str(edge.get("source", "")), node_by_id)
            target_module = self._module_for_node_id(str(edge.get("target", "")), node_by_id)
            if not source_module or not target_module or source_module == target_module:
                continue
            outgoing.setdefault(source_module, set()).add(target_module)
            incoming.setdefault(target_module, set()).add(source_module)
        for module, targets in outgoing.items():
            stats = raw_stats.setdefault(module, {"module": module, "touches": 0, "fan_in": 0, "fan_out": 0, "loc": 0, "classes": 0, "functions": 0, "imports": 0})
            stats["fan_out"] = max(int(stats.get("fan_out", 0) or 0), len(targets))
        for module, sources in incoming.items():
            stats = raw_stats.setdefault(module, {"module": module, "touches": 0, "fan_in": 0, "fan_out": 0, "loc": 0, "classes": 0, "functions": 0, "imports": 0})
            stats["fan_in"] = max(int(stats.get("fan_in", 0) or 0), len(sources))

    def _top_runtime_packages(self, module_stats: dict[str, ModuleRuntimeStats]) -> list[JsonObject]:
        package_touches: dict[str, int] = {}
        package_fan_out: dict[str, set[str]] = {}
        for stats in module_stats.values():
            package = self._package_name(stats.module)
            if not package:
                continue
            package_touches[package] = package_touches.get(package, 0) + stats.touches
            package_fan_out.setdefault(package, set())
            if stats.fan_out:
                package_fan_out[package].add(stats.module)
        return [
            {"package": package, "touches": touches, "fan_out_modules": len(package_fan_out.get(package, set()))}
            for package, touches in sorted(package_touches.items(), key=lambda item: item[1], reverse=True)[:5]
            if touches > 0
        ]

    def _module_for_node_id(self, node_id: str, node_by_id: dict[str, JsonObject]) -> str | None:
        if node_id == "entrypoint":
            return None
        node = node_by_id.get(node_id)
        if not node:
            return None
        if node.get("type") in {"io", "external_service"}:
            return None
        module = node.get("module")
        return str(module) if module else None

    def _metric_count(self, value: object) -> int:
        if isinstance(value, list | tuple | set | frozenset):
            return len(value)
        if value is None:
            return 0
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str) and value.strip():
            return int(value)
        return 0

    def _resource_event_count(self, events: list[JsonObject]) -> int:
        count = 0
        for event in events:
            callee = event.get("callee")
            if isinstance(callee, dict) and callee.get("endpoint_type") in {"resource", "external_service"}:
                count += 1
        return count

    def _redacted_value_count(self, value: object) -> int:
        if isinstance(value, dict):
            current = 1 if value.get("type") == "redacted" else 0
            return current + sum(self._redacted_value_count(item) for item in value.values())
        if isinstance(value, list):
            return sum(self._redacted_value_count(item) for item in value)
        return 0

    def _edge_touches_resource(self, edge: JsonObject, node_by_id: dict[str, JsonObject]) -> bool:
        source = node_by_id.get(str(edge.get("source", "")), {})
        target = node_by_id.get(str(edge.get("target", "")), {})
        return source.get("type") in {"io", "external_service"} or target.get("type") in {"io", "external_service"}

    def _module_stat_json(self, stats: ModuleRuntimeStats) -> JsonObject:
        return {
            "module": stats.module,
            "touches": stats.touches,
            "fan_in": stats.fan_in,
            "fan_out": stats.fan_out,
            "loc": stats.loc,
            "classes": stats.classes,
            "functions": stats.functions,
            "imports": stats.imports,
        }

    def _package_name(self, module: str) -> str | None:
        parts = [part for part in module.split(".") if part]
        if len(parts) < 3:
            return None
        return ".".join(parts[:2])

    def _finding_sort_key(self, finding: QualityFinding) -> tuple[int, str, str]:
        severity_rank = {"high": 0, "medium": 1, "low": 2, "info": 3}
        return (severity_rank[finding.severity], finding.category, finding.actor_label)

    def _dict_items(self, value: object) -> list[JsonObject]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]


@dataclass(frozen=True)
class ArchitectureQualityWriter:
    """Writes machine-readable and human-readable architecture quality reports."""

    def write_json(self, quality: JsonObject, out_path: Path) -> None:
        """Write quality evidence as stable JSON."""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(quality, indent=2, sort_keys=True), encoding="utf-8")

    def write_markdown(self, quality: JsonObject, out_path: Path) -> None:
        """Write quality evidence as markdown for humans and LLMs."""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(self.render_markdown(quality), encoding="utf-8")

    def render_markdown(self, quality: JsonObject) -> str:
        """Render a compact markdown architecture quality report."""
        summary = quality.get("summary", {})
        findings = quality.get("findings", [])
        lines = [
            "# Skeleton Architecture Quality",
            "",
            "This file is generated from one observed runtime scenario plus lightweight static facts. It is designed to help humans and LLMs identify review anchors, not to produce an absolute score.",
            "",
            "## Summary",
            "",
            f"- Events observed: `{self._summary_value(summary, 'events')}`",
            f"- Runtime modules touched: `{self._summary_value(summary, 'runtime_modules')}`",
            f"- Resource boundary events: `{self._summary_value(summary, 'resource_events')}`",
            f"- Redacted values: `{self._summary_value(summary, 'redacted_values')}`",
            "",
            "## Top Runtime Modules",
            "",
            *self._top_module_lines(summary),
            "",
            "## Findings",
            "",
            *self._finding_lines(findings),
            "",
            "## LLM Refactoring Notes",
            "",
            *self._guidance_lines(quality),
        ]
        return "\n".join(lines) + "\n"

    def _top_module_lines(self, summary: object) -> list[str]:
        if not isinstance(summary, dict):
            return ["- No runtime module evidence available."]
        modules = summary.get("top_runtime_modules")
        if not isinstance(modules, list) or not modules:
            return ["- No runtime module evidence available."]
        lines: list[str] = []
        for item in modules:
            if not isinstance(item, dict):
                continue
            lines.append(f"- `{item.get('module', '')}` touches={item.get('touches', 0)} fan_in={item.get('fan_in', 0)} fan_out={item.get('fan_out', 0)} loc={item.get('loc', 0)}")
        return lines or ["- No runtime module evidence available."]

    def _finding_lines(self, findings: object) -> list[str]:
        if not isinstance(findings, list) or not findings:
            return ["- No quality findings generated for this scenario."]
        lines: list[str] = []
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            lines.extend(
                [
                    f"### {finding.get('title', 'Finding')}",
                    "",
                    f"- Severity: `{finding.get('severity', '')}`",
                    f"- Category: `{finding.get('category', '')}`",
                    f"- Actor: `{finding.get('actor_label', finding.get('actor_id', ''))}`",
                    f"- Evidence: {self._inline_list(finding.get('evidence', []))}",
                    f"- Interpretation: {finding.get('interpretation', '')}",
                    f"- Refactor prompts: {self._inline_list(finding.get('suggested_refactors', []))}",
                    "",
                ]
            )
        return lines

    def _guidance_lines(self, quality: JsonObject) -> list[str]:
        guidance = quality.get("llm_guidance", [])
        if not isinstance(guidance, list) or not guidance:
            return ["- Treat these findings as scenario evidence and verify against source before changing code."]
        return [f"- {item}" for item in guidance if isinstance(item, str)]

    def _summary_value(self, summary: object, key: str) -> object:
        if not isinstance(summary, dict):
            return 0
        return summary.get(key, 0)

    def _inline_list(self, value: object) -> str:
        if not isinstance(value, list) or not value:
            return "`none`"
        return "; ".join(f"`{item}`" for item in value)
