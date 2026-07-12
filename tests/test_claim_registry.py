from __future__ import annotations

import aecctx.conformance as conformance
from pathlib import Path
import json


ROOT = Path(__file__).parents[1]


def test_claim_registry_validator_is_public() -> None:
    assert hasattr(conformance, "validate_claim_registry")
    assert hasattr(conformance, "validate_claim_registry_file")


def _registry(claim: dict[str, object]) -> dict[str, object]:
    return {
        "claims": [claim],
        "fixtures": [{"id": "v02-shared", "path": "fixtures/v0.2/shared/minimal-v02"}],
        "version": "0.2.0",
    }


def test_public_claim_requires_fixture_test_and_evidence_mapping() -> None:
    result = conformance.validate_claim_registry(
        _registry(
            {
                "evidence": "docs/evidence/ACX-11.md",
                "fixture_ids": [],
                "id": "core.v02.validation",
                "platform_scope": ["any"],
                "profile": "core-v0.2",
                "provider_scope": "none",
                "status": "public",
                "support_level": "full",
                "test_ids": [],
            }
        )
    )

    assert result.valid is False
    assert "core.v02.validation: public claim requires fixture_ids" in result.errors
    assert "core.v02.validation: public claim requires test_ids" in result.errors


def test_target_claim_may_remain_without_conformance_mapping() -> None:
    result = conformance.validate_claim_registry(
        _registry(
            {
                "evidence": None,
                "fixture_ids": [],
                "id": "ifc.2d.future-profile",
                "platform_scope": [],
                "profile": "unselected",
                "provider_scope": "none",
                "status": "target",
                "support_level": None,
                "test_ids": [],
            }
        )
    )

    assert result.valid is True
    assert result.errors == ()


def test_registry_rejects_duplicate_claim_ids_and_unknown_fixture_reference() -> None:
    claim = {
        "evidence": "docs/evidence/ACX-11.md",
        "fixture_ids": ["missing"],
        "id": "core.v02.validation",
        "platform_scope": ["any"],
        "profile": "core-v0.2",
        "provider_scope": "none",
        "status": "public",
        "support_level": "full",
        "test_ids": ["tests/test_v02_compatibility.py::test_v02_package_and_optional_extension_validate"],
    }
    registry = _registry(claim)
    registry["claims"] = [claim, dict(claim)]

    result = conformance.validate_claim_registry(registry)

    assert result.valid is False
    assert "duplicate claim id: core.v02.validation" in result.errors
    assert "core.v02.validation: unknown fixture id missing" in result.errors


def test_registry_file_requires_referenced_fixture_test_and_evidence_paths(tmp_path: Path) -> None:
    registry = _registry(
        {
            "evidence": "docs/evidence/ACX-11.md",
            "fixture_ids": ["v02-shared"],
            "id": "core.v02.validation",
            "platform_scope": ["any"],
            "profile": "core-v0.2",
            "provider_scope": "none",
            "status": "public",
            "support_level": "full",
            "test_ids": ["tests/test_missing.py::test_missing"],
        }
    )
    path = tmp_path / "claims.json"
    path.write_text(json.dumps(registry), encoding="utf-8")

    result = conformance.validate_claim_registry_file(path, repository_root=tmp_path)

    assert result.valid is False
    assert "v02-shared: fixture path does not exist: fixtures/v0.2/shared/minimal-v02" in result.errors
    assert "core.v02.validation: evidence path does not exist: docs/evidence/ACX-11.md" in result.errors
    assert "core.v02.validation: test file does not exist: tests/test_missing.py" in result.errors


def test_committed_v02_claim_registry_is_complete() -> None:
    result = conformance.validate_claim_registry_file(ROOT / "conformance" / "v0.2" / "claims.json")

    assert result.valid is True, result.errors
