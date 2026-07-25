from pathlib import Path

from skeleton_replay.analysis import SnapshotBuilder
from skeleton_replay.reporting import HtmlReportWriter, WorkflowNarrativeWriter
from skeleton_replay.runtime import TargetScriptRunner, TraceOptions


class TestArchitectureViews:
    """High-level architecture view behavior."""

    def test_snapshot_architecture_views_include_one_level_drilldowns(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_large_graph").resolve()
        out_dir = tmp_path / ".skeleton" / "sample_large_graph"
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )

        # When
        snapshot = SnapshotBuilder(project_root).build(result.trace_path, out_dir / "snapshot.json")
        drilldowns = snapshot["architecture_views"]["drilldowns"]
        package_extract = drilldowns["package"]["package:etl.extract"]
        package_data = drilldowns["package"]["package:warehouse.data"]
        module_app = drilldowns["module"]["module:app"]
        module_data = drilldowns["module"]["module:warehouse.data.files"]
        class_rules = drilldowns["actor"]["class:etl.transform.rules.CustomerRules"]
        package_extract_edges = {(edge["source"], edge["target"]): edge for edge in package_extract["edges"]}
        package_data_edges = {(edge["source"], edge["target"]): edge for edge in package_data["edges"]}
        class_rules_edges = {(edge["source"], edge["target"]): edge for edge in class_rules["edges"]}

        # Then
        assert {node["id"] for node in package_extract["nodes"]} >= {
            "module:etl.extract.pipeline",
            "module:etl.extract.sources",
        }
        assert package_extract_edges[("module:etl.extract.pipeline", "module:etl.extract.sources")]["call_count"] == 2
        assert {node["id"] for node in package_data["nodes"]} >= {
            "module:warehouse.data.files",
            "resource:file:resource.filesystem",
            "resource:db:resource.database",
        }
        assert not any(node["id"] == "resource:stdout:resource.stdout" for node in package_data["nodes"])
        assert package_data_edges[("module:warehouse.data.files", "resource:file:resource.filesystem")]["call_count"] == 3
        assert package_data_edges[("module:warehouse.data.files", "resource:db:resource.database")]["call_count"] == 5
        assert {node["id"] for node in module_app["nodes"]} >= {
            "function:app.main",
            "resource:file:resource.filesystem",
        }
        assert {node["id"] for node in module_data["nodes"]} >= {
            "class:warehouse.data.files.LocalDataCatalog",
            "resource:file:resource.filesystem",
            "resource:db:resource.database",
        }
        assert {node["id"] for node in class_rules["nodes"]} >= {
            "function:etl.transform.rules.CustomerRules.score",
            "function:etl.transform.rules.CustomerRules._weighted",
            "function:etl.transform.rules.CustomerRules.segment",
            "function:etl.transform.rules.CustomerRules.title",
        }
        assert (
            class_rules_edges[
                (
                    "function:etl.transform.rules.CustomerRules.score",
                    "function:etl.transform.rules.CustomerRules._weighted",
                )
            ]["call_count"]
            == 2
        )
        for graph in (package_extract, package_data, module_app, module_data, class_rules):
            for node in graph["nodes"]:
                assert node["raw_event_orders"]
                assert node["first_seen"] is not None
                assert node["last_seen"] is not None
                assert "call_count" in node
                assert "representative_endpoint" in node
            for edge in graph["edges"]:
                assert edge["raw_event_orders"]
                assert edge["first_seen"] is not None
                assert edge["last_seen"] is not None
                assert edge["call_count"] > 0
                assert "representative_caller" in edge
                assert "representative_callee" in edge

    def test_workflow_explains_artifacts_and_architecture_views(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_large_graph").resolve()
        out_dir = tmp_path / ".skeleton" / "sample_large_graph"
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )
        snapshot = SnapshotBuilder(project_root).build(result.trace_path, out_dir / "snapshot.json")

        # When
        markdown = WorkflowNarrativeWriter().render(snapshot)

        # Then
        assert "## Artifact Guide" in markdown
        assert "`report.html`: interactive replay for humans." in markdown
        assert "`snapshot.json`: derived graph, architecture views, roles, quality inputs, and report data." in markdown
        assert "`trace.jsonl`: raw ordered call/return evidence; use it when you need audit-level detail." in markdown
        assert "`session.json`: stable manifest that lets IDEs and automation find the rest of the artifact set." in markdown
        assert "## Architecture Views" in markdown
        assert "- Default view: `actor`." in markdown
        assert "`actor` (Actor/Class): nodes=" in markdown
        assert "collapsed_internal_calls=" in markdown

    def test_html_report_exposes_architecture_view_controls_and_artifact_guide(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_large_graph").resolve()
        out_dir = tmp_path / ".skeleton" / "sample_large_graph"
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )
        snapshot = SnapshotBuilder(project_root).build(result.trace_path, out_dir / "snapshot.json")
        out_path = tmp_path / "report.html"

        # When
        HtmlReportWriter().write(snapshot, out_path)

        # Then
        html = out_path.read_text(encoding="utf-8")
        assert "architecture_views" in html
        assert 'id="architecture-view-mode"' in html
        assert "Architecture Views" in html
        assert "Actor/Class" in html
        assert "Artifact Guide" in html
        assert "function setArchitectureViewMode" in html
        assert "window.SkeletonReplay.setViewMode" in html
        assert "collapsed internal calls" in html

    def test_html_report_exposes_drilldown_interactions(self, tmp_path: Path) -> None:
        # Given
        project_root = Path("tests/fixtures/sample_large_graph").resolve()
        out_dir = tmp_path / ".skeleton" / "sample_large_graph"
        result = TargetScriptRunner().run(
            project_root / "app.py",
            [],
            TraceOptions(project_root=project_root, out_dir=out_dir),
        )
        snapshot = SnapshotBuilder(project_root).build(result.trace_path, out_dir / "snapshot.json")
        out_path = tmp_path / "report.html"

        # When
        HtmlReportWriter().write(snapshot, out_path)

        # Then
        html = out_path.read_text(encoding="utf-8")
        assert "drilldowns" in html
        assert 'id="drilldown-menu"' in html
        assert 'id="drilldown-menu-action"' in html
        assert 'cy.on("cxttap", "node"' in html
        assert "function expandDrilldownForNode" in html
        assert "function collapseExpandedDrilldown" in html
        assert "function drilldownVisibleElementIdsAt" in html
        assert 'eventOrdersTouchWindow(element.data("raw_event_orders"), startIndex, endIndex)' in html
        assert "expandedDrilldown = null" in html
        assert "collapseExpandedDrilldown();" in html
