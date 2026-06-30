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
                    "callee": {
                        "module": "checkout",
                        "class_name": "CheckoutService",
                        "qualified_name": "checkout.CheckoutService.reserve",
                        "node_id": "function:checkout.CheckoutService.reserve",
                    },
                }
            ],
        }
        out_path = tmp_path / "report.html"

        # When
        HtmlReportWriter().write(snapshot, out_path)

        # Then
        html = out_path.read_text(encoding="utf-8")
        assert "color-scheme: dark" in html
        assert "cytoscape@3.30.4" in html
        assert "architecture-call" in html
        assert "module shell" in html
        assert "class shell" in html
        assert '<span class="pill"><span class="schema method"></span>method</span>' in html
        assert '<span class="pill"><span class="schema function"></span>function</span>' in html
        assert "runtime call" in html
        assert "Node size combines observed call count" in html
        assert "function isVisibleActor" in html
        assert "if (!source || !target || source === target) return;" in html
        assert 'addActorRole(target, "entrypoint")' in html
        assert "Entrypoint and service are roles on actors" in html
        assert "let current = -1" in html
        assert "function classIdForFunction" in html
        assert "function parentForFunction" in html
        assert 'parent: node.type === "class" ? moduleIdForName(node.module) : undefined' in html
        assert "parent: parentForFunction(node)" in html
        assert '"compound-sizing-wrt-labels": "include"' in html
        assert 'node[type = "function"]' in html
        assert '"border-style": "dashed"' in html
        assert 'node[type = "method"]' in html
        assert '"line-style": "solid"' in html
        assert "renderedNodeIds.has(edge.source)" in html
