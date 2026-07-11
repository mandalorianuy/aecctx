from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .records import RecordStore


QUERY_PATTERN = re.compile(
    r"^(?P<record_type>source|primitive|assertion|entity|relation|diagnostic|unsupported|record)\."
    r"(?P<field>[A-Za-z_][A-Za-z0-9_.]*)\s*(?P<operator>==|!=)\s*(?P<literal>.+)$"
)


class QuerySyntaxError(ValueError):
    code = "AECCTX_QUERY_SYNTAX_INVALID"


@dataclass(frozen=True, slots=True)
class QueryResult:
    expression: str
    logical_digest: str
    record_ids: tuple[str, ...]
    records: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "expression": self.expression,
            "logical_digest": self.logical_digest,
            "record_ids": list(self.record_ids),
            "records": list(self.records),
        }


def _field_value(record: dict[str, Any], path: str) -> Any:
    value: Any = record
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return _MISSING
        value = value[part]
    return value


_MISSING = object()


def query_package(package_path: str | Path, expression: str) -> QueryResult:
    match = QUERY_PATTERN.fullmatch(expression.strip())
    if match is None:
        raise QuerySyntaxError("Expected '<record-type>.<field> == <JSON literal>'")
    try:
        expected = json.loads(match.group("literal"))
    except json.JSONDecodeError as error:
        raise QuerySyntaxError(f"Query literal must be valid JSON: {error.msg}") from error
    store = RecordStore.open(package_path)
    selected: list[dict[str, Any]] = []
    requested_type = match.group("record_type")
    operator = match.group("operator")
    field = match.group("field")
    for record in store.records.values():
        if requested_type != "record" and record.record_type != requested_type:
            continue
        actual = _field_value(dict(record.raw), field)
        matches = actual is not _MISSING and actual == expected
        if (operator == "==" and matches) or (operator == "!=" and not matches):
            selected.append(dict(record.raw))
    record_ids = tuple(record["record_id"] for record in selected)
    return QueryResult(expression, store.logical_digest, record_ids, tuple(selected))

