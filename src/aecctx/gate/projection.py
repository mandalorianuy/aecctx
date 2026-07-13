from __future__ import annotations

import html
from typing import Any

from .models import GateResult
from .policy import canonical_gate_json


ANNOTATION_VERSION = "aecctx-ci-annotations-v1"


def _safe_text(value: str) -> str:
    return html.escape(value, quote=True).replace("[", "\\[").replace("]", "\\]")


def _safe_tree(value: Any) -> Any:
    if isinstance(value, str):
        return _safe_text(value)
    if isinstance(value, list):
        return [_safe_tree(item) for item in value]
    if isinstance(value, dict):
        return {key: _safe_tree(item) for key, item in value.items()}
    return value


def _markdown_records(data: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    records: list[dict[str, Any]] = [
        {
            "kind": "summary",
            "outcome": data["outcome"],
            "exit_code": data["exit_code"],
            "candidate": data["candidate"],
            "policy": data["policy"],
        }
    ]
    records.extend({"kind": "check", **check} for check in data["checks"])
    records.extend({"kind": "finding", **finding} for finding in data["findings"])
    records.extend({"kind": "diagnostic", **diagnostic} for diagnostic in data["diagnostics"])
    return tuple(_safe_tree(record) for record in records)


def render_gate_markdown(result: GateResult) -> bytes:
    if not isinstance(result, GateResult):
        raise TypeError("result must be GateResult")
    data = result.to_dict()
    lines = [
        "# AECCTX delivery gate projection",
        "",
        "> Generated from the canonical GateResult. This does not mean engineering approval.",
        "",
        f"Outcome: `{data['outcome']}` (exit `{data['exit_code']}`)",
        "",
        "## Inert canonical records",
        "",
    ]
    lines.extend(f"    {canonical_gate_json(record).decode('utf-8').rstrip()}" for record in _markdown_records(data))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _level(severity: str) -> str:
    return "error" if severity in {"error", "blocking"} else "warning" if severity == "warning" else "notice"


def render_ci_annotations(result: GateResult) -> bytes:
    if not isinstance(result, GateResult):
        raise TypeError("result must be GateResult")
    data = result.to_dict()
    records: list[dict[str, Any]] = [
        {
            "annotation_version": ANNOTATION_VERSION,
            "kind": "summary",
            "level": "error" if data["exit_code"] == 2 else "warning" if data["exit_code"] == 1 else "notice",
            "outcome": data["outcome"],
            "exit_code": data["exit_code"],
            "candidate": data["candidate"],
            "policy": data["policy"],
        }
    ]
    records.extend(
        {**check, "annotation_version": ANNOTATION_VERSION, "kind": "check", "level": _level(check["severity"])}
        for check in data["checks"]
    )
    records.extend(
        {**finding, "annotation_version": ANNOTATION_VERSION, "kind": "finding", "level": _level(finding["severity"])}
        for finding in data["findings"]
    )
    records.extend(
        {**diagnostic, "annotation_version": ANNOTATION_VERSION, "kind": "diagnostic", "level": _level(diagnostic["severity"])}
        for diagnostic in data["diagnostics"]
    )
    return b"".join(canonical_gate_json(record) for record in records)
