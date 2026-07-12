from __future__ import annotations

from pathlib import Path

from aecctx.context import render_context
from aecctx.query import query_package
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "fixtures" / "v0.2" / "shared" / "minimal-v02"


def test_minimal_v02_shared_fixture_is_valid() -> None:
    result = validate_package(FIXTURE)

    assert result.valid is True
    assert result.manifest is not None
    assert result.manifest["aecctx_version"] == "0.2.0"


def test_v02_inference_fields_are_queryable_authoritative_records() -> None:
    result = query_package(FIXTURE, 'primitive.inference.reproducibility == "deterministic"')

    assert result.record_ids == ("prim_inference_1",)
    assert result.records[0]["evidence_class"] == "inferred"


def test_v02_context_projects_but_does_not_replace_inference_record() -> None:
    projection = render_context(FIXTURE, token_budget=8_000, chunk_token_budget=4_000)

    assert "prim_inference_1" in projection.included_record_ids
    assert any(b"Authority: `evidence/primitives.jsonl:1`" in content for content in projection.files.values())
