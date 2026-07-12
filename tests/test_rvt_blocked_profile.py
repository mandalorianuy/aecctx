from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aecctx import cli
from aecctx.ingest import ingest_opaque
from aecctx.package import PackageReader


ROOT = Path(__file__).parents[1]
SENTINEL = ROOT / "fixtures" / "v0.2" / "rvt" / "not-a-real-rvt.rvt"
CLAIMS = ROOT / "conformance" / "v0.2" / "claims.json"
SENTINEL_BYTES = b"AECCTX anti-claim sentinel. This is not an Autodesk Revit RVT file.\n"
FIXED_TIME = "2026-07-12T00:00:00Z"


def test_rvt_sentinel_is_explicitly_invalid_and_stable() -> None:
    assert SENTINEL.read_bytes() == SENTINEL_BYTES
    assert hashlib.sha256(SENTINEL_BYTES).hexdigest() == "a0e93c6e20f3ee4356fc8f6ecca029d95da723154f7b2f25e49ed7268d2e1a49"


def test_rvt_suffix_uses_deterministic_opaque_fallback(tmp_path: Path) -> None:
    first = tmp_path / "first.aecctx"
    second = tmp_path / "second.aecctx"

    ingest_opaque(SENTINEL, first, created_at=FIXED_TIME, package_form="zip")
    ingest_opaque(SENTINEL, second, created_at=FIXED_TIME, package_form="zip")

    assert first.read_bytes() == second.read_bytes()
    package = PackageReader(first)
    assert package.manifest["capabilities"]["identity"] == "full"
    assert package.manifest["capabilities"]["validation"] == "full"
    assert all(
        value == "opaque"
        for key, value in package.manifest["capabilities"].items()
        if key not in {"identity", "validation"}
    )
    source = json.loads(package.read_bytes("sources/sources.jsonl").decode("utf-8"))
    assert source["detected_format"] == {"reason_code": "AECCTX_NO_FORMAT_ADAPTER", "state": "unknown"}
    assert source["extractor"]["plugin_id"] == "aecctx.core.opaque"


def test_cli_auto_does_not_promote_rvt_suffix(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "auto.aecctx"

    result = cli.main(
        [
            "ingest",
            str(SENTINEL),
            "--output",
            str(output),
            "--form",
            "zip",
            "--adapter",
            "auto",
            "--created-at",
            FIXED_TIME,
            "--json",
        ]
    )

    assert result == 0
    assert json.loads(capsys.readouterr().out)["data"]["support"] == "opaque"
    package = PackageReader(output)
    source = json.loads(package.read_bytes("sources/sources.jsonl").decode("utf-8"))
    assert source["detected_format"]["state"] == "unknown"


def test_opaque_sentinel_output_contains_no_consumer_mapping(tmp_path: Path) -> None:
    output = tmp_path / "opaque.aecctx"
    ingest_opaque(SENTINEL, output, created_at=FIXED_TIME, package_form="zip")
    package = PackageReader(output)

    authoritative = b"".join(
        package.read_bytes(path)
        for path in (
            "sources/sources.jsonl",
            "evidence/primitives.jsonl",
            "model/entities.jsonl",
            "model/relations.jsonl",
            "diagnostics/diagnostics.jsonl",
        )
    ).lower()
    assert b"woodframing" not in authoritative
    assert b"wfdomain" not in authoritative
    assert b"wfimport" not in authoritative
    assert package.read_bytes("model/entities.jsonl") == b""
    assert package.read_bytes("model/relations.jsonl") == b""


def test_claim_registry_exposes_only_unsupported_rvt_boundary() -> None:
    registry = json.loads(CLAIMS.read_text(encoding="utf-8"))
    claim = next(item for item in registry["claims"] if item["id"] == "rvt.external-provider")

    assert claim == {
        "id": "rvt.external-provider",
        "status": "public",
        "support_level": "unsupported",
        "profile": "rvt-no-provider-blocked-v1",
        "platform_scope": ["any"],
        "provider_scope": "none",
        "fixture_ids": ["v02-rvt-acx19-anti-claim"],
        "test_ids": [
            "tests/test_rvt_blocked_profile.py::test_rvt_suffix_uses_deterministic_opaque_fallback",
            "tests/test_rvt_blocked_profile.py::test_cli_auto_does_not_promote_rvt_suffix",
        ],
        "evidence": "docs/evidence/ACX-19.md",
    }
