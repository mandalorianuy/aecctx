from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from aecctx.context import render_context
from aecctx.diff import diff_packages
from aecctx.query import QuerySyntaxError, query_package
from aecctx.records import RecordStore


FIXTURE = Path(__file__).parents[1] / "fixtures" / "minimal-aecctx"


def _rehash(package: Path) -> None:
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    lines = []
    for artifact in manifest["artifacts"]:
        data = (package / artifact["path"]).read_bytes()
        artifact["bytes"] = len(data)
        artifact["sha256"] = hashlib.sha256(data).hexdigest()
        lines.append(f"{artifact['path']}\0{artifact['sha256']}\0{artifact['bytes']}\n".encode())
    manifest["logical_digest"] = hashlib.sha256(b"".join(sorted(lines))).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")


def test_record_store_loads_authoritative_records_with_locations() -> None:
    store = RecordStore.open(FIXTURE)

    assert list(store.records) == sorted(store.records)
    entity = store.records["entity_line_1"]
    assert entity.record_type == "entity"
    assert entity.location.path == "model/entities.jsonl"
    assert entity.location.line == 1
    assert store.logical_digest == "7ca4067f732dc1aed30c1be1257437ed009742e8d85f318a1ee1d0b6b6026b1b"


def test_query_selects_records_deterministically() -> None:
    result = query_package(FIXTURE, 'entity.original_class == "LINE"')

    assert result.record_ids == ("entity_line_1",)
    assert result.logical_digest == "7ca4067f732dc1aed30c1be1257437ed009742e8d85f318a1ee1d0b6b6026b1b"
    assert result.records[0]["record_id"] == "entity_line_1"


def test_query_rejects_executable_or_unsupported_syntax() -> None:
    with pytest.raises(QuerySyntaxError) as captured:
        query_package(FIXTURE, '__import__("os").system("id")')

    assert captured.value.code == "AECCTX_QUERY_SYNTAX_INVALID"


def test_diff_ignores_manifest_creation_time(tmp_path: Path) -> None:
    changed = tmp_path / "changed-time"
    shutil.copytree(FIXTURE, changed)
    manifest_path = changed / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["created_at"] = "2030-01-01T00:00:00Z"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = diff_packages(FIXTURE, changed)

    assert result.semantic_change is False
    assert result.changed_records == ()


def test_diff_reports_record_and_capability_changes(tmp_path: Path) -> None:
    changed = tmp_path / "changed-record"
    shutil.copytree(FIXTURE, changed)
    entity_path = changed / "model" / "entities.jsonl"
    entity = json.loads(entity_path.read_text(encoding="utf-8"))
    entity["label"] = {"state": "known", "value": "Changed"}
    entity_path.write_text(json.dumps(entity, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    manifest_path = changed / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["capabilities"]["properties"] = "full"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    _rehash(changed)

    result = diff_packages(FIXTURE, changed)

    assert result.semantic_change is True
    assert result.changed_records == ("entity_line_1",)
    assert result.capability_changes == {"properties": {"before": "partial", "after": "full"}}


def test_context_projection_has_citations_chunks_and_budget_report() -> None:
    projection = render_context(FIXTURE, profile="agent", token_budget=600, chunk_token_budget=220)

    assert "context/index.md" in projection.files
    assert any(path.startswith("context/chunk-") for path in projection.files)
    index = projection.files["context/index.md"].decode("utf-8")
    chunks = b"\n".join(value for path, value in projection.files.items() if path != "context/index.md").decode("utf-8")
    assert "Token estimate:" in index
    assert "model/entities.jsonl:1" in chunks
    assert "entity_line_1" in chunks
    assert projection.token_estimate <= 600


def test_context_budget_omits_projection_records_not_authoritative_data() -> None:
    before = (FIXTURE / "evidence" / "primitives.jsonl").read_bytes()

    projection = render_context(FIXTURE, profile="agent", token_budget=180, chunk_token_budget=100)

    assert projection.omitted_record_ids
    assert (FIXTURE / "evidence" / "primitives.jsonl").read_bytes() == before

