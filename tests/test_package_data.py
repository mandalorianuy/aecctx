from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path


def test_bundled_manifest_schema_is_available_offline() -> None:
    schema_path = files("aecctx.schemas.v0_1").joinpath("manifest.schema.json")

    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    assert schema["$id"] == "https://aecctx.dev/schemas/v0.1/manifest.schema.json"


def test_bundled_schemas_match_normative_repository_copies() -> None:
    root = files("aecctx.schemas.v0_1")
    repository = Path(__file__).parents[1] / "schemas" / "v0.1"

    for name in ("manifest.schema.json", "record.schema.json", "neutral-vocabulary.json"):
        bundled = json.loads(root.joinpath(name).read_text(encoding="utf-8"))
        normative = json.loads((repository / name).read_text(encoding="utf-8"))
        assert bundled == normative


def test_bundled_v02_schemas_match_normative_repository_copies() -> None:
    root = files("aecctx.schemas.v0_2")
    repository = Path(__file__).parents[1] / "schemas" / "v0.2"

    for name in ("manifest.schema.json", "record.schema.json"):
        bundled = json.loads(root.joinpath(name).read_text(encoding="utf-8"))
        normative = json.loads((repository / name).read_text(encoding="utf-8"))
        assert bundled == normative


def test_signing_contract_schemas_are_public_and_bundled() -> None:
    bundled_root = files("aecctx.schemas.v0_2")
    repository = Path(__file__).parents[1] / "schemas" / "v0.2"

    for name in (
        "signature-bundle.schema.json",
        "signing-key-registry.schema.json",
        "signing-trust-policy.schema.json",
        "signature-verification-result.schema.json",
    ):
        assert bundled_root.joinpath(name).is_file()
        assert (repository / name).is_file()
        assert bundled_root.joinpath(name).read_bytes() == (repository / name).read_bytes()


def test_gate_contract_schemas_are_public_and_bundled() -> None:
    bundled_root = files("aecctx.schemas.v0_2")
    repository = Path(__file__).parents[1] / "schemas" / "v0.2"

    for name in (
        "gate-check.schema.json",
        "gate-waiver.schema.json",
        "gate-policy.schema.json",
        "gate-result.schema.json",
    ):
        assert bundled_root.joinpath(name).is_file()
        assert (repository / name).is_file()
        assert bundled_root.joinpath(name).read_bytes() == (repository / name).read_bytes()


def test_portable_verify_checks_v02_schemas_and_claim_registry() -> None:
    script = (Path(__file__).parents[1] / "scripts" / "verify_portable.sh").read_text(encoding="utf-8")

    assert "schemas/v0.2/manifest.schema.json" in script
    assert "schemas/v0.2/record.schema.json" in script
    assert "conformance/v0.2/claims.json" in script
    assert "conformance/v0.2/ifc-corpus.json" in script
    assert "validate_claim_registry_file" in script


def test_portable_verify_gates_rvt_boundary_before_tests_and_after_build() -> None:
    script = (Path(__file__).parents[1] / "scripts" / "verify_portable.sh").read_text(encoding="utf-8")

    assert "schemas/v0.2/rvt-provider-decision.schema.json" in script
    assert "conformance/v0.2/rvt-provider-decision.json" in script
    assert script.count("scripts/check_rvt_blocked_conformance.py") == 2
    assert script.index("scripts/check_rvt_blocked_conformance.py") < script.index('"$python_runtime" -m pytest')
    assert script.rindex("scripts/check_rvt_blocked_conformance.py") > script.index('"$python_runtime" -m build')
    assert "--artifact dist/aecctx-0.1.0-py3-none-any.whl" in script
    assert "--artifact dist/aecctx-0.1.0.tar.gz" in script


def test_spec_contract_requires_rvt_blocked_conformance_material() -> None:
    script = (Path(__file__).parents[1] / "scripts" / "check_spec_contract.py").read_text(encoding="utf-8")

    for path in (
        "schemas/v0.2/rvt-provider-decision.schema.json",
        "conformance/v0.2/rvt-provider-decision.json",
        "scripts/check_rvt_blocked_conformance.py",
        "fixtures/v0.2/rvt/not-a-real-rvt.rvt",
        "docs/specs/rvt-v02-blocked-profile.md",
    ):
        assert path in script


def test_sdist_includes_normative_v02_schemas_and_conformance_material() -> None:
    project = (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")

    assert '"/schemas/v0.2"' in project
    assert '"/conformance/v0.2"' in project
    assert '"/fixtures/v0.2"' in project
    assert '"/docs"' in project


def test_sdist_includes_inspector_plugin_while_wheel_remains_core_only() -> None:
    project = (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")

    assert '"/plugins/aecctx-inspector"' in project
    assert 'packages = ["src/aecctx"]' in project
    dependencies = project.split("dependencies = [", 1)[1].split("]", 1)[0]
    assert "mcp" not in dependencies
    assert "codex" not in dependencies.lower()


def test_external_provider_protocol_schemas_are_public_and_bundled() -> None:
    bundled_root = files("aecctx.schemas.v0_2")
    repository = Path(__file__).parents[1] / "schemas" / "v0.2"

    for name in (
        "provider-descriptor.schema.json",
        "provider-request.schema.json",
        "provider-response.schema.json",
    ):
        assert bundled_root.joinpath(name).is_file()
        assert (repository / name).is_file()
        bundled = json.loads(bundled_root.joinpath(name).read_text(encoding="utf-8"))
        normative = json.loads((repository / name).read_text(encoding="utf-8"))
        assert bundled == normative
