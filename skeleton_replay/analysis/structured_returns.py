"""Derived grouping for repeated structured return records."""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from skeleton_replay.runtime.events import TraceEvent

JsonObject = dict[str, Any]

WEAK_STRUCTURED_RETURN_NAMES = frozenset({"payload", "to_dict", "as_dict", "serialize", "metadata", "schema", "snapshot", "trace_payload"})
DEFAULT_LABEL_FIELDS = ("name", "id", "key", "kind", "type", "lane", "owner", "role", "stage", "event_type", "active")
STRUCTURED_RETURN_NOTE = "These records were derived from repeated structured return values. Raw events remain available below."


@dataclass(frozen=True)
class StructuredReturnConfig:
    """Project-level tuning for structured return aggregation."""

    enabled: bool = True
    min_records: int = 3
    min_key_overlap: float = 0.75
    collapse_by_default: bool = True
    label_fields: tuple[str, ...] = DEFAULT_LABEL_FIELDS
    groups: dict[str, str] = field(default_factory=dict)
    display_labels: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_project(cls, project_root: Path) -> StructuredReturnConfig:
        """Load optional structured-return config from ``pyproject.toml``."""
        pyproject_path = project_root / "pyproject.toml"
        if not pyproject_path.exists():
            return cls()
        with pyproject_path.open("rb") as reader:
            data = tomllib.load(reader)
        tool_config = data.get("tool", {})
        if not isinstance(tool_config, dict):
            return cls()
        skeleton_config = tool_config.get("skeleton", {})
        if not isinstance(skeleton_config, dict):
            return cls()
        raw_config = skeleton_config.get("structured_returns", {})
        raw_display_labels = skeleton_config.get("display_labels", {})
        if not isinstance(raw_config, dict):
            return cls(display_labels=cls._string_map(raw_display_labels))
        return cls(
            enabled=bool(raw_config.get("enabled", True)),
            min_records=max(2, int(raw_config.get("min_records", 3))),
            min_key_overlap=max(0.0, min(1.0, float(raw_config.get("min_key_overlap", 0.75)))),
            collapse_by_default=bool(raw_config.get("collapse_by_default", True)),
            label_fields=cls._string_tuple(raw_config.get("label_fields", DEFAULT_LABEL_FIELDS)),
            groups=cls._string_map(raw_config.get("groups", {})),
            display_labels=cls._string_map(raw_display_labels),
        )

    @staticmethod
    def _string_tuple(value: object) -> tuple[str, ...]:
        if not isinstance(value, list | tuple):
            return DEFAULT_LABEL_FIELDS
        labels = tuple(str(item) for item in value if isinstance(item, str) and item)
        return labels or DEFAULT_LABEL_FIELDS

    @staticmethod
    def _string_map(value: object) -> dict[str, str]:
        if not isinstance(value, dict):
            return {}
        return {str(key): str(item) for key, item in value.items() if isinstance(key, str) and isinstance(item, str)}


@dataclass(frozen=True)
class StructuredReturnRecord:
    """One low-complexity call and compatible dictionary return."""

    call_event: TraceEvent
    return_event: TraceEvent
    keys: frozenset[str]
    values: JsonObject
    scalar_value_count: int
    total_value_count: int
    child_call_count: int
    resource_event_count: int


@dataclass(frozen=True)
class StructuredReturnGroupAnalyzer:
    """Derive repeated structured-return groups from raw trace events."""

    config: StructuredReturnConfig = field(default_factory=StructuredReturnConfig)

    def analyze(self, events: list[TraceEvent]) -> list[JsonObject]:
        """Return snapshot-level structured-return groups."""
        if not self.config.enabled:
            return []
        records_by_callable: dict[str, list[StructuredReturnRecord]] = {}
        active_calls: dict[str, list[TraceEvent]] = {}
        for event in events:
            qualified_name = event.callee.qualified_name
            if event.event_type == "call":
                active_calls.setdefault(qualified_name, []).append(event)
                continue
            call_event = self._pop_active_call(active_calls, qualified_name)
            if call_event is None:
                continue
            record = self._record_from_pair(call_event=call_event, return_event=event, events=events)
            if record is not None:
                records_by_callable.setdefault(qualified_name, []).append(record)

        groups = []
        for records in records_by_callable.values():
            group = self._group_from_records(records)
            if group is not None:
                groups.append(group)
        groups.sort(key=lambda group: (int(group["first_event"]), str(group["qualified_name"])))
        return groups

    @staticmethod
    def _pop_active_call(active_calls: dict[str, list[TraceEvent]], qualified_name: str) -> TraceEvent | None:
        calls = active_calls.get(qualified_name)
        if not calls:
            return None
        return calls.pop()

    def _record_from_pair(self, *, call_event: TraceEvent, return_event: TraceEvent, events: list[TraceEvent]) -> StructuredReturnRecord | None:
        values = self._dict_values(return_event.return_value)
        if values is None:
            return None
        total_value_count = len(values)
        scalar_value_count = sum(1 for value in values.values() if isinstance(value, str | bool | int | float) or value is None)
        if total_value_count == 0 or scalar_value_count / total_value_count < 0.75:
            return None
        child_call_count, resource_event_count = self._complexity_between(call_event=call_event, return_event=return_event, events=events)
        if child_call_count > 0 or resource_event_count > 0:
            return None
        return StructuredReturnRecord(
            call_event=call_event,
            return_event=return_event,
            keys=frozenset(values),
            values=values,
            scalar_value_count=scalar_value_count,
            total_value_count=total_value_count,
            child_call_count=child_call_count,
            resource_event_count=resource_event_count,
        )

    def _dict_values(self, return_value: JsonObject | None) -> JsonObject | None:
        if not isinstance(return_value, dict) or return_value.get("type") != "dict":
            return None
        preview = return_value.get("preview")
        if not isinstance(preview, list) or not preview:
            return None
        values: JsonObject = {}
        for item in preview:
            if not isinstance(item, dict):
                return None
            key = self._preview_key(item.get("key"))
            if key is None:
                return None
            values[key] = self._preview_value(item.get("value"))
        return values

    @staticmethod
    def _preview_key(key_summary: object) -> str | None:
        if not isinstance(key_summary, dict) or key_summary.get("type") != "str":
            return None
        value = key_summary.get("value")
        return value if isinstance(value, str) and value else None

    def _preview_value(self, value_summary: object) -> object:
        if not isinstance(value_summary, dict):
            return None
        if "value" in value_summary and value_summary.get("type") in {"NoneType", "bool", "int", "float", "str"}:
            return value_summary["value"]
        return self._summary_text(value_summary)

    @staticmethod
    def _summary_text(value_summary: JsonObject) -> str:
        if value_summary.get("type") == "redacted":
            return "redacted"
        if "len" in value_summary:
            return f"{value_summary.get('type', 'value')} len={value_summary['len']}"
        if "object_id" in value_summary:
            return f"{value_summary.get('type', 'object')} {value_summary['object_id']}"
        if "summary" in value_summary:
            return f"{value_summary.get('type', 'value')}: {value_summary['summary']}"
        return str(value_summary.get("type", "value"))

    @staticmethod
    def _complexity_between(*, call_event: TraceEvent, return_event: TraceEvent, events: list[TraceEvent]) -> tuple[int, int]:
        child_call_count = 0
        resource_event_count = 0
        for event in events:
            if event.order <= call_event.order or event.order >= return_event.order:
                continue
            if event.depth <= call_event.depth:
                continue
            if event.callee.endpoint_type in {"resource", "external_service"}:
                resource_event_count += 1
            elif event.event_type == "call":
                child_call_count += 1
        return child_call_count, resource_event_count

    def _group_from_records(self, records: list[StructuredReturnRecord]) -> JsonObject | None:
        if len(records) < self.config.min_records:
            return None
        key_overlap = self._key_overlap(records)
        if key_overlap < self.config.min_key_overlap:
            return None
        semantic_keys = [field_name for field_name in self.config.label_fields if any(field_name in record.keys for record in records)]
        if not semantic_keys:
            return None
        first = records[0]
        columns = self._columns(records)
        label_field = self._label_field(columns)
        qualified_name = first.call_event.callee.qualified_name
        shape_hash = hashlib.sha256(json.dumps([qualified_name, columns], sort_keys=True).encode("utf-8")).hexdigest()[:12]
        raw_event_orders = sorted(order for record in records for order in (record.call_event.order, record.return_event.order))
        raw_events = sorted(
            [self._raw_event_detail(record.call_event) for record in records] + [self._raw_event_detail(record.return_event) for record in records],
            key=lambda event: int(event["order"]),
        )
        active_values = [record.values.get("active") for record in records if isinstance(record.values.get("active"), bool)]
        return {
            "id": f"structured_return:{qualified_name}:{shape_hash}",
            "label": self._group_label(first.call_event),
            "qualified_name": qualified_name,
            "class_name": first.call_event.callee.class_name,
            "function": first.call_event.callee.function,
            "record_count": len(records),
            "first_event": min(raw_event_orders),
            "last_event": max(raw_event_orders),
            "event_orders": [record.return_event.order for record in records],
            "raw_event_orders": raw_event_orders,
            "key_overlap": round(key_overlap, 3),
            "label_field": label_field,
            "columns": columns,
            "collapse_by_default": self.config.collapse_by_default,
            "note": STRUCTURED_RETURN_NOTE,
            "active_count": sum(1 for value in active_values if value),
            "inactive_count": sum(1 for value in active_values if not value),
            "records": [self._record_json(record, label_field) for record in records],
            "raw_events": raw_events,
        }

    @staticmethod
    def _key_overlap(records: list[StructuredReturnRecord]) -> float:
        all_keys = set().union(*(record.keys for record in records))
        if not all_keys:
            return 0.0
        common_keys = set(records[0].keys)
        for record in records[1:]:
            common_keys.intersection_update(record.keys)
        return len(common_keys) / len(all_keys)

    def _columns(self, records: list[StructuredReturnRecord]) -> list[str]:
        threshold = max(1, int(len(records) * self.config.min_key_overlap))
        counts: dict[str, int] = {}
        for record in records:
            for key in record.keys:
                counts[key] = counts.get(key, 0) + 1
        eligible = {key for key, count in counts.items() if count >= threshold}
        ordered = [field_name for field_name in self.config.label_fields if field_name in eligible]
        ordered.extend(sorted(key for key in eligible if key not in set(ordered)))
        return ordered

    def _label_field(self, columns: list[str]) -> str | None:
        for field_name in self.config.label_fields:
            if field_name in columns and field_name != "active":
                return field_name
        return columns[0] if columns else None

    def _group_label(self, call_event: TraceEvent) -> str:
        qualified_name = call_event.callee.qualified_name
        for pattern, label in self.config.groups.items():
            if fnmatch(qualified_name, pattern):
                return label
        class_name = call_event.callee.class_name
        if class_name:
            return f"{class_name} {call_event.callee.function} records"
        return f"{qualified_name} records"

    def _record_json(self, record: StructuredReturnRecord, label_field: str | None) -> JsonObject:
        label_template = self._display_label_template(record.call_event)
        label = self._render_label(label_template, record.values) if label_template else None
        if not label and label_field:
            label = str(record.values.get(label_field, ""))
        return {
            "event_order": record.return_event.order,
            "call_event_order": record.call_event.order,
            "return_event_order": record.return_event.order,
            "label": label or str(record.return_event.order),
            "values": record.values,
            "raw_event_orders": [record.call_event.order, record.return_event.order],
        }

    def _display_label_template(self, call_event: TraceEvent) -> str | None:
        candidates = [call_event.callee.qualified_name]
        if call_event.callee.class_name:
            candidates.append(f"{call_event.callee.module}.{call_event.callee.class_name}")
            candidates.append(call_event.callee.class_name)
        for pattern, template in self.config.display_labels.items():
            if any(fnmatch(candidate, pattern) for candidate in candidates):
                return template
        return None

    @staticmethod
    def _render_label(template: str, values: JsonObject) -> str:
        label = template
        for key, value in values.items():
            label = label.replace("{" + key + "}", str(value))
        return label

    @staticmethod
    def _raw_event_detail(event: TraceEvent) -> JsonObject:
        caller = event.caller
        return {
            "order": event.order,
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "caller": caller.qualified_name if caller else "entrypoint",
            "callee": event.callee.qualified_name,
            "caller_object_id": caller.instance_id if caller else None,
            "callee_object_id": event.callee.instance_id,
            "args": event.args,
            "return_value": event.return_value,
        }
