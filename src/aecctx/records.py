from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .package import PackageReader
from .validation import validate_package


RECORD_PATHS = (
    "sources/sources.jsonl",
    "evidence/primitives.jsonl",
    "evidence/assertions.jsonl",
    "model/entities.jsonl",
    "model/relations.jsonl",
    "diagnostics/diagnostics.jsonl",
)
VALUE_STATES = {"known", "unknown", "not_applicable", "conflicted", "explicit_null", "unsupported"}


class RecordModelError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ValueState:
    state: str
    value: Any = None
    unit: str | None = None
    reason_code: str | None = None

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> ValueState:
        state = raw.get("state")
        if state not in VALUE_STATES:
            raise RecordModelError("AECCTX_VALUE_STATE_INVALID", f"Unsupported value state: {state!r}")
        if state == "known":
            if "value" not in raw:
                raise RecordModelError("AECCTX_VALUE_STATE_VALUE_REQUIRED", "known state requires value")
            return cls(state=state, value=raw["value"], unit=raw.get("unit"))
        reason = raw.get("reason_code")
        if not isinstance(reason, str) or not reason:
            raise RecordModelError("AECCTX_VALUE_STATE_REASON_REQUIRED", f"{state} state requires reason_code")
        if "value" in raw:
            raise RecordModelError("AECCTX_VALUE_STATE_VALUE_FORBIDDEN", f"{state} state cannot synthesize value")
        return cls(state=state, reason_code=reason, unit=raw.get("unit"))


@dataclass(frozen=True, slots=True)
class RecordLocation:
    path: str
    line: int


@dataclass(frozen=True, slots=True)
class NeutralRecord:
    record_id: str
    record_type: str
    raw: Mapping[str, Any]
    location: RecordLocation


class RecordStore:
    def __init__(self, reader: PackageReader, records: dict[str, NeutralRecord]) -> None:
        self.reader = reader
        self.records = records
        self.manifest = reader.manifest
        self.logical_digest = str(reader.manifest["logical_digest"])

    @classmethod
    def open(cls, package_path: str | Path) -> RecordStore:
        validation = validate_package(package_path)
        if not validation.valid:
            first = validation.diagnostics[0]
            raise RecordModelError("AECCTX_PACKAGE_INVALID", f"{first.code}: {first.message}")
        reader = PackageReader(package_path)
        records: dict[str, NeutralRecord] = {}
        for logical_path in RECORD_PATHS:
            text = reader.read_bytes(logical_path).decode("utf-8")
            for line_number, line in enumerate(text.splitlines(), 1):
                if not line.strip():
                    continue
                raw = json.loads(line)
                record_id = raw["record_id"]
                records[record_id] = NeutralRecord(
                    record_id=record_id,
                    record_type=raw["record_type"],
                    raw=raw,
                    location=RecordLocation(logical_path, line_number),
                )
        return cls(reader, {record_id: records[record_id] for record_id in sorted(records)})

