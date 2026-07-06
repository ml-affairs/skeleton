from pathlib import Path

from skeleton_replay.reporting import HtmlReportWriter


class TestHtmlReportWriter:
    """HTML report generation behavior."""

    def test_uses_dark_architecture_replay_surface(self, tmp_path: Path) -> None:
        # Given
        snapshot = {
            "project_root": "/example/shop",
            "event_count": 1,
            "nodes": [
                {"id": "entrypoint", "type": "entrypoint", "label": "entrypoint"},
                {"id": "module:orders", "type": "module", "label": "orders", "module": "orders", "loc": 42},
                {"id": "class:checkout.CheckoutService", "type": "class", "label": "CheckoutService", "module": "checkout", "loc": 80},
                {
                    "id": "function:orders.main",
                    "type": "function",
                    "label": "main",
                    "module": "orders",
                    "class_name": None,
                    "function": "main",
                    "qualified_name": "orders.main",
                    "arg_examples": [],
                    "return_examples": [],
                },
                {
                    "id": "function:checkout.CheckoutService.reserve",
                    "type": "function",
                    "label": "reserve",
                    "module": "checkout",
                    "class_name": "CheckoutService",
                    "function": "reserve",
                    "qualified_name": "checkout.CheckoutService.reserve",
                    "arg_examples": [],
                    "return_examples": [],
                },
            ],
            "edges": [
                {
                    "id": "function:orders.main->function:checkout.CheckoutService.reserve",
                    "source": "function:orders.main",
                    "target": "function:checkout.CheckoutService.reserve",
                    "call_count": 1,
                }
            ],
            "quality": {
                "summary": {"events": 3, "runtime_modules": 2, "resource_events": 0, "redacted_values": 0},
                "findings": [
                    {
                        "severity": "medium",
                        "title": "Runtime hotspot module",
                        "actor_label": "checkout",
                        "actor_id": "module:checkout",
                        "evidence": ["touches=12", "fan_out=3"],
                    }
                ],
            },
            "events": [
                {
                    "event_type": "call",
                    "order": 0,
                    "caller": None,
                    "args": {},
                    "callee": {
                        "module": "orders",
                        "class_name": None,
                        "function": "main",
                        "qualified_name": "orders.main",
                        "node_id": "function:orders.main",
                    },
                },
                {
                    "event_type": "call",
                    "order": 1,
                    "caller": {
                        "module": "orders",
                        "class_name": None,
                        "function": "main",
                        "qualified_name": "orders.main",
                        "node_id": "function:orders.main",
                    },
                    "callee": {
                        "module": "checkout",
                        "class_name": "CheckoutService",
                        "instance_id": "checkout.CheckoutService@0xabc",
                        "function": "reserve",
                        "qualified_name": "checkout.CheckoutService.reserve",
                        "node_id": "function:checkout.CheckoutService.reserve",
                    },
                    "args": {"order_id": {"type": "str", "value": "A-1"}},
                },
                {
                    "event_type": "return",
                    "order": 2,
                    "caller": {
                        "module": "orders",
                        "class_name": None,
                        "function": "main",
                        "qualified_name": "orders.main",
                        "node_id": "function:orders.main",
                    },
                    "callee": {
                        "module": "checkout",
                        "class_name": "CheckoutService",
                        "instance_id": "checkout.CheckoutService@0xabc",
                        "function": "reserve",
                        "qualified_name": "checkout.CheckoutService.reserve",
                        "node_id": "function:checkout.CheckoutService.reserve",
                    },
                    "return_value": {"type": "bool", "value": True},
                },
            ],
        }
        out_path = tmp_path / "report.html"

        # When
        HtmlReportWriter().write(snapshot, out_path)

        # Then
        html = out_path.read_text(encoding="utf-8")
        assert "color-scheme: dark" in html
        assert 'rel="icon"' in html
        assert "data:image/svg+xml,%3Csvg" in html
        assert "cytoscape@3.30.4" in html
        assert "architecture-call" in html
        assert "module shell" in html
        assert "package shell" in html
        assert "instance shell" in html
        assert '<span class="pill"><span class="schema method"></span>method</span>' in html
        assert '<span class="pill"><span class="schema function"></span>function</span>' in html
        assert '<span class="pill"><span class="schema private"></span>private/internal</span>' in html
        assert '<span class="pill"><span class="schema instance"></span>instance shell</span>' in html
        assert "runtime call" in html
        assert "return value" in html
        assert "Quality Signals" in html
        assert "function qualitySignals" in html
        assert "replay-dock" in html
        assert "startReplayDockDrag" in html
        assert "updateReplayDockDrag" in html
        assert 'id="trace-window"' in html
        assert 'id="trace-window-start"' in html
        assert 'id="trace-window-end"' in html
        assert 'id="export-trace"' in html
        assert 'id="private-toggle"' in html
        assert "function togglePrivateCalls" in html
        assert "private-callable" in html
        assert "shouldSuppressPrivateElement" in html
        assert "Export the exact trace events visible in the selected execution window as JSON for LLM review" in html
        assert "function exportTraceWindow" in html
        assert 'kind: "skeleton_trace_window"' in html
        assert "selected_window" in html
        assert "function startTraceWindowDrag" in html
        assert "function renderTraceWindow" in html
        assert "Module Treemap" in html
        assert '<button class="heatmap-show" id="heatmap-show" type="button">Treemap</button>' in html
        assert '<div class="heatmap hidden" id="module-heatmap">' in html
        assert '<button class="legend-show hidden" id="legend-show" type="button">Legend</button>' in html
        assert "function toggleLegend" in html
        assert "function treemapLayout" in html
        assert "function layoutTreemapSlice" in html
        assert "Size: ${module.touches} observed module touches" in html
        assert "Color hue: fan-out ${module.fan_out}" in html
        assert 'aria-label="Previous event"' in html
        assert 'aria-label="Play replay"' in html
        assert 'aria-label="Next event"' in html
        assert '<section class="replay-dock" id="replay-dock" aria-label="Execution replay controls">' in html
        assert '<div class="section" id="current-event-section">' in html
        assert "const revealSequence = new Map()" in html
        assert "const manuallyPositionedNodeIds = new Set()" in html
        assert "function resolveRootSiblingOverlaps" in html
        assert "Node size combines observed call count" in html
        assert "function isVisibleActor" in html
        assert "if (!source || !target || source === target) return;" in html
        assert 'addActorRole(target, "entrypoint")' in html
        assert "Entrypoint and service are roles on actors" in html
        assert "entrypointEventOrder !== null" in html
        assert "let current = events.length ? (entrypointEventOrder" in html
        assert "renderEvent();" in html
        assert "let currentReplayMetrics = null" in html
        assert "trace_roles: selectedTraceRoles" in html
        assert "Setup before entrypoint" in html
        assert "role-test-utility" in html
        assert "role-import-setup" in html
        assert "trace-role-pill" in html
        assert "const revealedElementIds = new Set()" in html
        assert "function parentForFunction" in html
        assert "function parentForActor" in html
        assert "function packagePrefixesForModule" in html
        assert "function packageIdForModule" in html
        assert "function moduleLabelForNode" in html
        assert "const packageNodes" in html
        assert "function instanceForEndpoint" in html
        assert "function semanticInstanceLabel" in html
        assert "function structuredReturnInstanceLabels" in html
        assert "structuredReturnLabelsByInstanceId" in html
        assert "function syncVisibilityToReplay" in html
        assert "function visibleElementIdsAt" in html
        assert "function collectEndpointElementIds" in html
        assert "function focusOwnerForEndpoint" in html
        assert "function placeNewElement" in html
        assert "function firstOpenPosition" in html
        assert "function overlapsVisibleNode" in html
        assert "function applyContainerSizeCandidate" in html
        assert "function applyAncestorContainerSizeLimits" in html
        assert "function resolveContainerPeerOverlap" in html
        assert "function parentContainerAtRenderedPoint" in html
        assert "const containerResizeEdgePx" in html
        assert 'const isProjectLocalModule = rawNodes.has(moduleIdForName(endpoint.module || ""))' in html
        assert "moduleHas(ioRulebook.file) && functionHas(ioRulebook.file)" in html
        assert "moduleHas(ioRulebook.file) || functionHas(ioRulebook.file)" not in html
        assert 'endpoint.endpoint_type === "external_service"' in html
        assert "function externalServiceCategoryFor" in html
        assert '"shape": "barrel"' in html
        assert "function ioNodeWidth" in html
        assert "function callableNodeWidth" in html
        assert "callable_width: callableWidth" in html
        assert "io_width: ioWidth" in html
        assert '"width": "data(io_width)"' in html
        assert '"height": "data(io_height)"' in html
        assert 'node[type = "io"][io_category = "file"]' in html
        assert 'node[type = "io"][io_category = "db"].current' in html
        assert 'node[type = "io"][io_category = "stdout"]' in html
        assert 'node[type = "io"][io_category = "network"]' not in html
        assert 'node[type = "external_service"]' in html
        assert '"shape": "diamond"' in html
        assert '<span class="pill"><span class="schema external"></span>external service</span>' in html
        assert 'id="module-heatmap"' in html
        assert "function renderModuleHeatmap" in html
        assert "function moduleHeatmapAt" in html
        assert "function toggleHeatmap" in html
        assert 'id="sidebar-toggle"' in html
        assert "function toggleSidebar" in html
        assert "sidebar-collapsed" in html
        assert "left: -18px;" in html
        assert "padding-top: 58px;" not in html
        assert "cy.resize();" in html
        assert "function visualNodeData" in html
        assert "function renderResizeHandles" in html
        assert "function initializeResizeHandles" in html
        assert "function startResizeDrag" in html
        assert "function onResizeDragMove" in html
        assert "function placeNewChildElement" in html
        assert "function resolveVisibleSiblingOverlaps" in html
        assert "function nodeArea" in html
        assert "function enforceNodeMoveConstraints" in html
        assert "function startManualNodeMove" in html
        assert "function updateManualNodeMove" in html
        assert "function canPlaceNodeAt" in html
        assert "node.position(draggedFrom)" in html
        assert 'id="resize-handles"' in html
        assert "function replayMetricsAt" in html
        assert "function applyReplayMetrics" in html
        assert "first_seen: metric?.first_seen ?? edge.data.first_seen" in html
        assert "window.cy = cy" in html
        assert 'node.type === "package" || node.type === "module" || node.type === "instance" ? "container" : ""' in html
        assert "parent: parentForFunction(node)" in html
        assert 'node[type = "package"]' in html
        assert '"compound-sizing-wrt-labels": "include"' in html
        assert '"min-width": "data(width)"' in html
        assert "Modules contain runtime instances and functions" in html
        assert "Instances contain the methods observed on that object" in html
        assert 'node[type = "function"]' in html
        assert '"border-style": "dashed"' in html
        assert 'node[type = "method"]' in html
        assert 'node[type = "instance"]' in html
        assert 'node[type = "class"]' not in html
        assert "class shell" not in html
        assert 'edge[type = "runtime-return"]' in html
        assert "const returnEdges" in html
        assert '"curve-style": "straight"' in html
        assert '"curve-style": "unbundled-bezier"' in html
        assert '"control-point-distances": 110' in html
        assert '"control-point-weights": 0.5' in html
        assert '"line-style": "solid"' in html
        assert '"line-style": "dashed"' in html
        assert "renderedNodeIds.has(source)" in html
        assert "elements: [...actorNodes, ...methodNodes, ...callEdges, ...returnEdges]" in html
        assert "return:${targetNode}->${sourceNode}" in html
        assert 'element.addClass("unseen hidden").removeClass("current focus pulse")' in html
        assert 'cy.elements().addClass("unseen")' not in html
        assert "firstOpenPosition(anchor, visibleNodes, element" in html
        assert '"events": "no"' in html
        assert "avoidOverlapsForCurrentStep" not in html
        assert "function avoidOverlapsForNode" not in html
        assert "function ensureContainerFits" not in html
        assert "fit: { eles: active" not in html
        assert "layoutVisibleElements" not in html
        assert 'window.setTimeout(() => active.removeClass("pulse"), 420)' in html
        assert 'id="event-focus"' in html
        assert "function eventFocusCard" in html
        assert 'id="structured-return-summary"' in html
        assert "function renderStructuredReturnSummary" in html
        assert 'id="hover-tooltip"' in html
        assert "function showHoverTooltipForEdge" in html
        assert "function showHoverTooltipForInstance" in html
        assert "function latestEventForEdge" in html
        assert "function latestEventForInstance" in html
        assert "function edgeTooltipHtml" in html
        assert "function instanceTooltipHtml" in html
        assert 'cy.on("mouseover", "edge"' in html
        assert 'cy.on("mouseover", \'node[type = "instance"]\'' in html
        assert "tip-pill" in html
        assert "function keepCurrentNodesInView" in html
        assert "activeNodes.renderedBoundingBox" in html
        assert "cy.pan({ x: pan.x + dx, y: pan.y + dy })" in html
        assert "function syntaxHighlightJson" in html
        assert "function jsonKeyClass" in html
        assert "json-key-endpoint" in html
        assert "json-entity-external" in html
        assert "json-key" in html
