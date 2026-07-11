from __future__ import annotations

import json
from pathlib import Path

from aecctx.validation import validate_package


def test_minimal_directory_fixture_is_valid() -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "minimal-aecctx"

    result = validate_package(fixture)

    assert result.valid is True
    assert result.diagnostics == ()
    assert result.package_id == "pkg_minimal_fixture"


def test_missing_manifest_has_stable_code(tmp_path: Path) -> None:
    result = validate_package(tmp_path)

    assert result.valid is False
    assert result.diagnostics[0].code == "AECCTX_MANIFEST_MISSING"
    assert result.diagnostics[0].path == "manifest.json"


def test_invalid_manifest_json_has_stable_code(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text("{", encoding="utf-8")

    result = validate_package(tmp_path)

    assert result.valid is False
    assert result.diagnostics[0].code == "AECCTX_JSON_INVALID"


def test_manifest_schema_failure_has_stable_code(minimal_package: Path) -> None:
    manifest_path = minimal_package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["package_id"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = validate_package(minimal_package)

    assert result.valid is False
    assert any(item.code == "AECCTX_SCHEMA_INVALID" for item in result.diagnostics)


def test_artifact_hash_mismatch_is_rejected(minimal_package: Path) -> None:
    (minimal_package / "context" / "index.md").write_text("tampered\n", encoding="utf-8")

    result = validate_package(minimal_package)

    assert result.valid is False
    assert any(item.code == "AECCTX_ARTIFACT_HASH_MISMATCH" for item in result.diagnostics)


def test_duplicate_record_id_is_rejected(minimal_package: Path) -> None:
    primitive = (minimal_package / "evidence" / "primitives.jsonl").read_text(encoding="utf-8")
    (minimal_package / "model" / "relations.jsonl").write_text(primitive, encoding="utf-8")

    result = validate_package(minimal_package)

    assert result.valid is False
    assert any(item.code == "AECCTX_RECORD_ID_DUPLICATE" for item in result.diagnostics)

