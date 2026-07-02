from pathlib import Path

from skeleton_replay.analysis import ArchitectureQualityAnalyzer, ArchitectureQualityWriter


class TestArchitectureQualityAnalyzer:
    """Architecture quality evidence generation behavior."""

    def test_detects_runtime_hotspots_large_modules_and_boundary_evidence(self) -> None:
        # Given
        snapshot = {
            "event_count": 40,
            "nodes": [
                {"id": "module:shop.checkout", "type": "module", "module": "shop.checkout", "label": "shop.checkout", "loc": 2800, "classes": 4, "functions": 28, "imports": 31},
                {"id": "module:shop.payments", "type": "module", "module": "shop.payments", "label": "shop.payments", "loc": 300, "classes": 1, "functions": 4, "imports": 5},
                {
                    "id": "function:shop.checkout.CheckoutService.run",
                    "type": "function",
                    "module": "shop.checkout",
                    "label": "run",
                    "qualified_name": "shop.checkout.CheckoutService.run",
                    "fan_out": 13,
                    "call_count": 7,
                },
                {"id": "io:database", "type": "io", "label": "database", "resource_category": "db"},
            ],
            "edges": [
                {"source": "function:shop.checkout.CheckoutService.run", "target": "io:database"},
                {"source": "function:shop.checkout.CheckoutService.run", "target": "function:shop.payments.charge"},
            ],
            "events": [
                {
                    "event_type": "call",
                    "callee": {
                        "module": "shop.checkout",
                        "qualified_name": "shop.checkout.CheckoutService.run",
                        "endpoint_type": "function",
                    },
                    "args": {"api_token": {"type": "redacted", "reason": "sensitive-name"}},
                },
                {
                    "event_type": "call",
                    "caller": {
                        "module": "shop.checkout",
                        "qualified_name": "shop.checkout.CheckoutService.run",
                        "endpoint_type": "function",
                    },
                    "callee": {
                        "module": "sqlite3",
                        "qualified_name": "sqlite3.connect",
                        "endpoint_type": "resource",
                        "resource_category": "db",
                    },
                },
            ],
        }

        # When
        quality = ArchitectureQualityAnalyzer().analyze(snapshot)

        # Then
        titles = {finding["title"] for finding in quality["findings"]}
        assert "High fan-out runtime workflow" in titles
        assert "Large module surface" in titles
        assert "External boundary evidence observed" in titles
        assert quality["summary"]["resource_events"] == 1
        assert quality["summary"]["redacted_values"] == 1


class TestArchitectureQualityWriter:
    """Architecture quality artifact writer behavior."""

    def test_writes_markdown_and_json_reports(self, tmp_path: Path) -> None:
        # Given
        quality = {
            "summary": {
                "events": 3,
                "runtime_modules": 1,
                "resource_events": 0,
                "redacted_values": 0,
                "top_runtime_modules": [{"module": "app", "touches": 3, "fan_in": 0, "fan_out": 1, "loc": 30}],
            },
            "findings": [
                {
                    "severity": "info",
                    "category": "boundary_evidence",
                    "title": "No external resource boundary observed",
                    "actor_label": "external resources",
                    "actor_id": "resources",
                    "evidence": ["resource_events=0"],
                    "interpretation": "No resource calls appeared.",
                    "suggested_refactors": ["Run a wider scenario."],
                }
            ],
            "llm_guidance": ["Verify against source."],
        }
        json_path = tmp_path / "quality.json"
        markdown_path = tmp_path / "architecture_quality.md"
        writer = ArchitectureQualityWriter()

        # When
        writer.write_json(quality, json_path)
        writer.write_markdown(quality, markdown_path)

        # Then
        assert json_path.read_text(encoding="utf-8").startswith("{")
        markdown = markdown_path.read_text(encoding="utf-8")
        assert "# Skeleton Architecture Quality" in markdown
        assert "No external resource boundary observed" in markdown
        assert "Verify against source." in markdown
