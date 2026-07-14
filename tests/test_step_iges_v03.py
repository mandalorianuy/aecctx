from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aecctx.adapters.step_iges import ingest_step_iges
from aecctx.package import PackageReader
from aecctx.providers import OCIDockerProfile, ProviderLimits, ProviderRunner
from aecctx.providers import load_provider_replay_entry
from aecctx.providers.protocol import ProviderResult
from aecctx.providers import step_iges as provider_profile
from aecctx.records import RecordStore
from aecctx.step_iges import StepIgesInputError, validate_step_iges_events
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
FIXED_TIME = "2026-07-14T00:00:00Z"


def _worker():
    path = ROOT / "providers/step-iges-ocp/worker.py"
    spec = importlib.util.spec_from_file_location("aecctx_test_step_iges_v03_worker", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capabilities(*, partial_recovery: bool = False) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for name in ("identity", "hierarchy", "properties", "relationships", "text", "2d_geometry", "3d_geometry", "materials_styles", "georeferencing", "validation"):
        level = "full" if name == "identity" else ("partial" if name in {"hierarchy", "properties", "relationships", "3d_geometry", "materials_styles", "validation"} else "unsupported")
        reasons = [] if level == "full" else (["AECCTX_STEP_IGES_TRANSFER_PARTIAL"] if partial_recovery else ["AECCTX_STEP_IGES_XDE_PARTIAL"])
        result[name] = {"affected": [] if level == "full" else ["root:1"], "fallback": "none" if level == "full" else "retain lexical and successful root evidence", "reason_codes": reasons, "support_level": level}
    return result


def _provider_result(*, partial: bool = False, healed: bool = True) -> ProviderResult:
    raw_brep = b"DBRep_DrawableShape\nraw-v03"
    healed_brep = b"DBRep_DrawableShape\nhealed-v03"
    mesh = json.dumps({"schema": "aecctx.triangle-mesh.v1", "triangles": [[0, 1, 2]], "vertices": [[0, 0, 0], [1, 0, 0], [0, 1, 0]]}, sort_keys=True, separators=(",", ":")).encode()
    source = {
        "entities": [
            {"id": 1, "original_class": "PRODUCT", "raw": "#1=PRODUCT('part','Part A','',());", "references": []},
            {"id": 2, "original_class": "MANIFOLD_SOLID_BREP", "raw": "#2=MANIFOLD_SOLID_BREP('Body',#1);", "references": [1]},
        ],
        "external_references": False,
        "format": "step",
        "headers": {"FILE_SCHEMA": ["AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }"]},
        "schema": "aecctx.step-iges.source.v1",
        "schemas": ["AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }"],
    }
    xde = {
        "format": "step",
        "labels": [
            {
                "colors": [{"kind": "surface", "rgba": [0.2, 0.4, 0.6, 1.0]}],
                "entry": "0:1:1:1",
                "kind": "simple-shape",
                "layers": ["A-WALL"],
                "materials": [{"kind": "physical", "name": "Steel"}],
                "name": {"state": "known", "value": "Part A"},
                "parent_entries": [],
                "placement": {"matrix_3x4": [1, 0, 0, 10, 0, 1, 0, 20, 0, 0, 1, 30], "state": "known"},
                "source_correlation": {"method": "exact-unique-name", "source_entity_ids": [1], "state": "known"},
                "unit": {"state": "known", "value": "millimetre"},
            }
        ],
        "schema": "aecctx.step-iges.xde.v1",
        "session_completeness": "partial" if partial else "complete",
    }
    root = {
        "artifact_path": "artifacts/root-1.translated.brep",
        "bounds": {"max": [1, 1, 0], "min": [0, 0, 0]},
        "format": "step",
        "healing": {
            "after_valid": True if healed else None,
            "applied": healed,
            "artifact_path": "artifacts/root-1.healed.brep" if healed else None,
            "maximum_tolerance": 0.001,
            "minimum_tolerance": 1e-7,
            "precision": 1e-7,
        },
        "mesh_artifact_path": "artifacts/root-1.mesh.json",
        "representation_fidelity": "brep-translator-derived",
        "root_id": "root:1",
        "schema": "aecctx.step-iges.root.v1",
        "status": "success",
        "tolerances": {"average": 1e-7, "maximum": 1e-7, "minimum": 1e-7},
        "topology": {"edges": 3, "faces": 1, "shells": 1, "solids": 1, "vertices": 3, "wires": 1},
        "valid": True,
        "xde_entry": "0:1:1:1",
    }
    events = [
        {"event_type": "primitive", "payload": source, "sequence": 0, "source_locator": "sha256:" + "a" * 64},
        {"event_type": "container", "payload": xde, "sequence": 1, "source_locator": "xde:document"},
        {"event_type": "primitive", "payload": root, "sequence": 2, "source_locator": "root:1"},
    ]
    if partial:
        events.append({"event_type": "diagnostic", "payload": {"format": "step", "root_id": "root:2", "schema": "aecctx.step-iges.root.v1", "status": "failed", "diagnostic": "AECCTX_STEP_IGES_ROOT_TRANSFER_FAILED", "xde_entry": "0:1:1:2"}, "sequence": 3, "source_locator": "root:2"})
    artifact_bytes = {"artifacts/root-1.translated.brep": raw_brep, "artifacts/root-1.mesh.json": mesh}
    if healed:
        artifact_bytes["artifacts/root-1.healed.brep"] = healed_brep
    artifacts = tuple({"bytes": len(value), "media_type": "application/vnd.aecctx.triangle-mesh+json" if path.endswith(".json") else "model/vnd.opencascade.brep", "path": path, "sha256": hashlib.sha256(value).hexdigest()} for path, value in artifact_bytes.items())
    return ProviderResult(ok=True, events=tuple(events), artifacts=artifacts, artifact_bytes=artifact_bytes, diagnostics=tuple({"code": "AECCTX_STEP_IGES_TRANSFER_PARTIAL", "severity": "warning"} for _ in [0] if partial), capability_report=_capabilities(partial_recovery=partial), resource_usage={"artifacts": len(artifacts), "events": len(events), "roots": 2 if partial else 1}, attestation={"provider_id": "org.aecctx.step-iges.ocp", "runtime_digest": "sha256:" + "b" * 64})


def test_v03_contract_is_governed_and_schema_is_packaged() -> None:
    schema_path = ROOT / "schemas/v0.2/step-iges-xde-event.schema.json"
    mirror = ROOT / "src/aecctx/schemas/v0_2/step-iges-xde-event.schema.json"
    assert schema_path.is_file()
    assert schema_path.read_bytes() == mirror.read_bytes()
    assert "ACXD-041" in (ROOT / "docs/specs/step-iges-v03-profile.md").read_text(encoding="utf-8")
    assert "ACX-32 | completed" in (ROOT / "docs/implementation-plan.md").read_text(encoding="utf-8")


def test_worker_v03_configuration_is_closed_and_healing_is_only_boolean_delta() -> None:
    worker = _worker()
    configuration = provider_profile.STEP_IGES_XDE_CONFIGURATION
    assert worker._configuration({"configuration": configuration}) == configuration
    enabled = json.loads(json.dumps(configuration))
    enabled["healing"]["enabled"] = True
    assert worker._configuration({"configuration": enabled}) == enabled
    for changed in ({**configuration, "path": "/tmp"}, {**configuration, "linear_deflection": 0.2}):
        with pytest.raises(ValueError, match="AECCTX_STEP_IGES_CONFIGURATION_INVALID"):
            worker._configuration({"configuration": changed})


def test_xde_and_root_events_validate_without_replacing_lexical_evidence() -> None:
    evidence = validate_step_iges_events(_provider_result())
    assert evidence.source["schema"] == "aecctx.step-iges.source.v1"
    assert evidence.xde["labels"][0]["source_correlation"] == {"method": "exact-unique-name", "source_entity_ids": [1], "state": "known"}
    assert evidence.roots[0]["artifact_path"].endswith(".translated.brep")
    assert evidence.roots[0]["healing"]["artifact_path"].endswith(".healed.brep")
    assert evidence.brep != evidence.healed_breps["root:1"]


def test_schema_rejects_source_exact_or_silent_healing() -> None:
    schema = json.loads((ROOT / "schemas/v0.2/step-iges-xde-event.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    root = dict(_provider_result().events[2]["payload"])
    root["representation_fidelity"] = "source-exact"
    assert list(validator.iter_errors(root))
    root = dict(_provider_result(healed=False).events[2]["payload"])
    root["healing"] = {**root["healing"], "applied": True, "artifact_path": None}
    assert list(validator.iter_errors(root))


def test_partial_root_recovery_retains_success_and_never_claims_full() -> None:
    result = _provider_result(partial=True, healed=False)
    evidence = validate_step_iges_events(result)
    assert evidence.xde["session_completeness"] == "partial"
    assert {root["status"] for root in evidence.roots} == {"success", "failed"}
    assert result.capability_report["3d_geometry"]["support_level"] == "partial"
    assert "AECCTX_STEP_IGES_TRANSFER_PARTIAL" in result.capability_report["3d_geometry"]["reason_codes"]


def test_adapter_packages_xde_raw_and_healed_evidence_separately(tmp_path: Path) -> None:
    source = ROOT / "fixtures/v0.2/step-iges/ap214-assembly.step"
    output = tmp_path / "xde.aecctx"
    ingest_step_iges(source, output, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0", provider_result=_provider_result())
    assert validate_package(output).valid
    reader = PackageReader(output)
    paths = {item["path"] for item in reader.manifest["artifacts"]}
    assert {"geometry/root-1.translated.brep", "geometry/root-1.healed.brep", "geometry/scene.glb"}.issubset(paths)
    records = [record.raw for record in RecordStore.open(output).records.values()]
    xde = next(item for item in records if item.get("original_class") == "XDE_LABEL")
    assert xde["evidence_class"] == "observed"
    assert xde["source_correlation"]["source_entity_ids"] == [1]
    healed = next(item for item in records if item.get("original_class") == "OCCT_HEALED_BREP")
    assert healed["evidence_class"] == "derived"
    assert healed["parent_evidence_ids"]


def test_committed_xde_replay_maps_all_roots_deterministically(tmp_path: Path) -> None:
    replay = load_provider_replay_entry(ROOT / "conformance/v0.3/step-iges-corpus.json", "ap214-metadata-healed")
    source = ROOT / "fixtures/v0.3/step-iges/ap214-xde.step"
    outputs = [tmp_path / "first.aecctx", tmp_path / "second.aecctx"]
    for output in outputs:
        ingest_step_iges(source, output, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0", provider_result=replay.result)
        assert validate_package(output).valid
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    paths = {item["path"] for item in PackageReader(outputs[0]).manifest["artifacts"]}
    assert {"geometry/root-1.translated.brep", "geometry/root-2.translated.brep", "geometry/root-1.healed.brep", "geometry/root-2.healed.brep", "geometry/scene.glb"}.issubset(paths)


@pytest.mark.skipif(os.environ.get("AECCTX_RUN_STEP_IGES_V03_PROVIDER") != "1", reason="exact live multiarch XDE matrix is opt-in")
def test_live_xde_provider_is_equal_on_arm64_and_amd64() -> None:
    fixtures = [
        ROOT / "fixtures/v0.2/step-iges/ap203-part.step",
        ROOT / "fixtures/v0.2/step-iges/ap214-assembly.step",
        ROOT / "fixtures/v0.2/step-iges/ap242-part.step",
        ROOT / "fixtures/v0.2/step-iges/iges53-part.igs",
        ROOT / "fixtures/v0.3/step-iges/ap214-xde.step",
    ]
    compared = {}
    for fixture in fixtures:
        results = []
        for target in provider_profile.STEP_IGES_OCI_TARGETS:
            runner = ProviderRunner(registry=provider_profile.step_iges_registry(repository_root=ROOT), profile=OCIDockerProfile(image=target.image, platform=target.platform, architecture=target.architecture), limits=ProviderLimits(max_input_bytes=2_000_000, max_output_bytes=20_000_000, max_records=2_000, wall_time_seconds=30))
            results.append(runner.run(provider_profile.STEP_IGES_PROVIDER_ID, "extract", fixture.read_bytes(), configuration=provider_profile.STEP_IGES_XDE_CONFIGURATION))
        assert all(result.ok for result in results), fixture.name
        assert results[0].events == results[1].events, fixture.name
        assert results[0].artifacts == results[1].artifacts, fixture.name
        assert results[0].artifact_bytes == results[1].artifact_bytes, fixture.name
        compared[fixture.name] = results[0]
    xde_result = compared["ap214-xde.step"]
    xde = next(event["payload"] for event in xde_result.events if event["payload"].get("schema") == "aecctx.step-iges.xde.v1")
    assert {label["name"].get("value") for label in xde["labels"]} >= {"Part A", "Part B"}
    assert any(label["colors"] for label in xde["labels"])
    assert any(label["layers"] == ["AECCTX-LAYER-1"] for label in xde["labels"])
    assert any({item["name"] for item in label["materials"]} == {"Steel"} for label in xde["labels"])
    assert all(label["unit"] == {"state": "known", "value": "millimetre"} for label in xde["labels"])
    assert any(label["placement"].get("matrix_3x4", [0] * 12)[3] == 40.0 for label in xde["labels"])
    assert len([event for event in xde_result.events if event["payload"].get("schema") == "aecctx.step-iges.root.v1"]) == 2


@pytest.mark.skipif(os.environ.get("AECCTX_RUN_STEP_IGES_V03_PROVIDER") != "1", reason="exact live healing pair is opt-in")
def test_live_healing_is_opt_in_and_preserves_raw_translator_artifacts() -> None:
    source = (ROOT / "fixtures/v0.3/step-iges/ap214-xde.step").read_bytes()
    enabled_configuration = json.loads(json.dumps(provider_profile.STEP_IGES_XDE_CONFIGURATION))
    enabled_configuration["healing"]["enabled"] = True
    disabled_results = []
    enabled_results = []
    for target in provider_profile.STEP_IGES_OCI_TARGETS:
        runner = ProviderRunner(registry=provider_profile.step_iges_registry(repository_root=ROOT), profile=OCIDockerProfile(image=target.image, platform=target.platform, architecture=target.architecture), limits=ProviderLimits(max_input_bytes=2_000_000, max_output_bytes=20_000_000, max_records=2_000, wall_time_seconds=30))
        disabled_results.append(runner.run(provider_profile.STEP_IGES_PROVIDER_ID, "extract", source, configuration=provider_profile.STEP_IGES_XDE_CONFIGURATION))
        enabled_results.append(runner.run(provider_profile.STEP_IGES_PROVIDER_ID, "extract", source, configuration=enabled_configuration))
    disabled, enabled = disabled_results[0], enabled_results[0]
    raw_paths = [path for path in disabled.artifact_bytes if path.endswith(".translated.brep")]
    assert raw_paths and {path: disabled.artifact_bytes[path] for path in raw_paths} == {path: enabled.artifact_bytes[path] for path in raw_paths}
    assert len([path for path in enabled.artifact_bytes if path.endswith(".healed.brep")]) == 2
    assert not [path for path in disabled.artifact_bytes if path.endswith(".healed.brep")]
    assert all(event["payload"]["healing"]["applied"] is True for event in enabled.events if event["payload"].get("schema") == "aecctx.step-iges.root.v1")
    assert enabled_results[0].events == enabled_results[1].events
    assert enabled_results[0].artifact_bytes == enabled_results[1].artifact_bytes
