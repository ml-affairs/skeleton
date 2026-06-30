from skeleton_replay.safety import ValueSummariser


class Example:
    """Simple object used to verify opaque object summaries."""

    pass


class TestValueSummariser:
    """Safe value summarisation behavior."""

    def test_redacts_sensitive_argument_names(self) -> None:
        # Given
        values = {"api_token": "secret", "name": "Ada"}

        # When
        summary = ValueSummariser().summarise_arguments(values)

        # Then
        assert summary["api_token"]["type"] == "redacted"
        assert summary["name"]["value"] == "Ada"

    def test_truncates_strings_and_previews_containers(self) -> None:
        # Given
        value = {"items": list(range(10)), "password": "hidden", "label": "x" * 140}

        # When
        summary = ValueSummariser().summarise_value(value)

        # Then
        assert summary["type"] == "dict"
        assert summary["len"] == 3
        preview = {item["key"]["value"]: item["value"] for item in summary["preview"]}
        assert preview["items"]["len"] == 10
        assert preview["password"]["type"] == "redacted"
        assert preview["label"]["truncated"] is True

    def test_objects_only_include_class_and_identity(self) -> None:
        # Given
        value = Example()

        # When
        summary = ValueSummariser().summarise_value(value)

        # Then
        assert summary["type"].endswith(".Example")
        assert summary["object_id"].startswith("0x")
        assert "repr" not in summary
