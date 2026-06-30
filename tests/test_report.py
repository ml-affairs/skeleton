from pathlib import Path

from skeleton.reporting import HtmlReportWriter


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
        assert "instance shell" in html
        assert '<span class="pill"><span class="schema method"></span>method</span>' in html
        assert '<span class="pill"><span class="schema function"></span>function</span>' in html
        assert '<span class="pill"><span class="schema instance"></span>instance shell</span>' in html
        assert "runtime call" in html
        assert "return value" in html
        assert "Node size combines observed call count" in html
        assert "function isVisibleActor" in html
        assert "if (!source || !target || source === target) return;" in html
        assert 'addActorRole(target, "entrypoint")' in html
        assert "Entrypoint and service are roles on actors" in html
        assert "let current = events.length ? 0 : -1" in html
        assert "renderEvent();" in html
        assert "let currentReplayMetrics = null" in html
        assert "function parentForFunction" in html
        assert "function parentForActor" in html
        assert "function instanceForEndpoint" in html
        assert "function syncVisibilityToReplay" in html
        assert "function replayMetricsAt" in html
        assert "function applyReplayMetrics" in html
        assert 'node.type === "module" || node.type === "instance" ? "container" : ""' in html
        assert "parent: parentForFunction(node)" in html
        assert '"compound-sizing-wrt-labels": "include"' in html
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
        assert '"control-point-distances": 90' in html
        assert '"control-point-weights": 0.5' in html
        assert '"line-style": "solid"' in html
        assert '"line-style": "dashed"' in html
        assert "renderedNodeIds.has(source)" in html
        assert "elements: [...actorNodes, ...methodNodes, ...callEdges, ...returnEdges]" in html
        assert "return:${targetNode}->${sourceNode}" in html
        assert 'cy.elements().addClass("unseen")' in html
        assert '"events": "no"' in html
        assert "layoutVisibleElements" not in html
        assert 'window.setTimeout(() => active.removeClass("pulse"), 420)' in html
        assert 'id="event-focus"' in html
        assert "function eventFocusCard" in html
        assert "function syntaxHighlightJson" in html
        assert "json-key" in html
