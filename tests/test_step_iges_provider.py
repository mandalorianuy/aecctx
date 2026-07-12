from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

from aecctx.providers.step_iges import (
    STEP_IGES_IMAGE,
    STEP_IGES_IMAGE_ID,
    STEP_IGES_CONFIGURATION,
    STEP_IGES_PROVIDER_ID,
    step_iges_descriptor,
    step_iges_registry,
)
from aecctx.providers import OCIDockerProfile, ProviderLimits, ProviderRunner


ROOT = Path(__file__).parents[1]


def _worker():
    path = ROOT / "providers" / "step-iges-ocp" / "worker.py"
    spec = importlib.util.spec_from_file_location("aecctx_test_step_iges_worker", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _iges_line(payload: str, section: str, sequence: int) -> bytes:
    return f"{payload:<72}{section}{sequence:>7}".encode("ascii")


def test_step_iges_profile_registration_pins_reviewed_runtime_and_worker() -> None:
    descriptor = step_iges_descriptor()
    registration = step_iges_registry(repository_root=ROOT).resolve(STEP_IGES_PROVIDER_ID)

    assert descriptor.provider_id == "org.aecctx.step-iges.ocp"
    assert descriptor.provider_version == "0.2.0"
    assert descriptor.runtime_version == "python-3.12+cadquery-ocp-7.9.3.1.1+occt-7.9.3"
    assert descriptor.runtime_digest == STEP_IGES_IMAGE_ID
    assert descriptor.license_spdx == "Apache-2.0 AND LGPL-2.1-only WITH OCCT-exception"
    assert descriptor.formats == ("model/step", "model/iges")
    assert descriptor.platforms == ("linux-container",)
    assert descriptor.network_mode == "disabled"
    assert set(descriptor.enforced_axes) == {
        "cpu",
        "decompression",
        "environment",
        "filesystem",
        "input_bytes",
        "memory",
        "network",
        "open_files",
        "output_bytes",
        "process",
        "process_tree",
        "records",
        "recursion",
        "temporary_storage",
        "user_permissions",
        "wall_time",
    }
    assert registration.container_image == STEP_IGES_IMAGE
    assert registration.container_image_id == STEP_IGES_IMAGE_ID
    assert registration.container_command == ("python3", "/provider/worker.py")
    assert registration.worker_path == ROOT / "providers" / "step-iges-ocp" / "worker.py"


def test_step_iges_native_kernel_is_absent_from_core_distribution_dependencies() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()

    assert "cadquery-ocp" not in pyproject
    assert "pythonocc" not in pyproject
    assert "opencascade" not in pyproject


def test_step_iges_worker_accepts_only_exact_configuration() -> None:
    worker = _worker()
    request = {"configuration": dict(STEP_IGES_CONFIGURATION)}

    assert worker._configuration(request) == STEP_IGES_CONFIGURATION
    for changed in (
        {**STEP_IGES_CONFIGURATION, "linear_deflection": 0.2},
        {**STEP_IGES_CONFIGURATION, "resource_path": "/tmp/STEP"},
        {key: value for key, value in STEP_IGES_CONFIGURATION.items() if key != "schema_profile"},
    ):
        with pytest.raises(ValueError, match="AECCTX_STEP_IGES_CONFIGURATION_INVALID"):
            worker._configuration({"configuration": changed})


def test_step_scanner_preserves_header_entities_raw_records_and_references() -> None:
    worker = _worker()
    source = b"""ISO-10303-21;
HEADER;
FILE_DESCRIPTION(('AECCTX fixture'),'2;1');
FILE_NAME('fixture.step','2026-07-12T00:00:00',('AECCTX'),('AECCTX'),'','','');
FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));
ENDSEC;
DATA;
#1=PRODUCT('fixture','Part with ''quote''','',());
#2=SHAPE_DEFINITION_REPRESENTATION(/* bounded comment */#1,
#3);
#3=MANIFOLD_SOLID_BREP('Body',#4);
#4=CLOSED_SHELL('',());
ENDSEC;
END-ISO-10303-21;
"""

    assert worker._probe(source) == "step"
    scanned = worker._scan_step(source, max_records=10, max_recursion_depth=8)
    assert scanned["schemas"] == ["AUTOMOTIVE_DESIGN"]
    assert [item["id"] for item in scanned["entities"]] == [1, 2, 3, 4]
    assert scanned["entities"][1] == {
        "id": 2,
        "original_class": "SHAPE_DEFINITION_REPRESENTATION",
        "raw": "#2=SHAPE_DEFINITION_REPRESENTATION(/* bounded comment */#1,\n#3);",
        "references": [1, 3],
    }
    assert scanned["external_references"] is False


def test_step_scanner_rejects_duplicate_broken_or_excessive_entities() -> None:
    worker = _worker()
    duplicate = b"ISO-10303-21;HEADER;FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));ENDSEC;DATA;#1=PRODUCT('','','',());#1=PRODUCT('','','',());ENDSEC;END-ISO-10303-21;"
    broken = b"ISO-10303-21;HEADER;FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));ENDSEC;DATA;#1=PRODUCT('','','',(#99));ENDSEC;END-ISO-10303-21;"
    excessive = b"ISO-10303-21;HEADER;FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));ENDSEC;DATA;#1=PRODUCT('','','',());#2=PRODUCT('','','',());ENDSEC;END-ISO-10303-21;"

    with pytest.raises(ValueError, match="AECCTX_STEP_IGES_ENTITY_DUPLICATE"):
        worker._scan_step(duplicate, max_records=10, max_recursion_depth=8)
    with pytest.raises(ValueError, match="AECCTX_STEP_IGES_REFERENCE_INVALID"):
        worker._scan_step(broken, max_records=10, max_recursion_depth=8)
    with pytest.raises(ValueError, match="AECCTX_STEP_IGES_ENTITY_LIMIT_EXCEEDED"):
        worker._scan_step(excessive, max_records=1, max_recursion_depth=8)


def test_step_scanner_marks_external_references_without_opening_them() -> None:
    worker = _worker()
    source = b"ISO-10303-21;HEADER;FILE_SCHEMA(('AUTOMOTIVE_DESIGN'));ENDSEC;DATA;#1=EXTERNAL_FILE_ID_AND_LOCATION('part.step','file:///etc/passwd');ENDSEC;END-ISO-10303-21;"

    assert worker._scan_step(source, max_records=10, max_recursion_depth=8)["external_references"] is True


def test_iges_scanner_preserves_fixed_width_directory_evidence() -> None:
    worker = _worker()
    first_directory = f"{110:>8}{1:>8}{0:>8}{0:>8}{7:>8}{0:>8}{0:>8}{0:>8}{'00000000':>8}"
    second_directory = f"{110:>8}{0:>8}{3:>8}{1:>8}{0:>8}{0:>8}{0:>8}{'LINE':<8}{1:>8}"
    source = b"\n".join(
        [
            _iges_line("AECCTX IGES fixture", "S", 1),
            _iges_line("1H,,1H;,8Hfixture,8Hfixture,", "G", 1),
            _iges_line(first_directory, "D", 1),
            _iges_line(second_directory, "D", 2),
            _iges_line("110,0.,0.,0.,10.,0.,0.;", "P", 1),
            _iges_line("S0000001G0000001D0000002P0000001", "T", 1),
        ]
    ) + b"\n"

    assert worker._probe(source) == "iges"
    scanned = worker._scan_iges(source, max_records=10, max_recursion_depth=8)
    assert scanned["directory"] == [
        {
            "entity_type": 110,
            "form": 0,
            "label": "LINE",
            "level": 7,
            "parameter_pointer": 1,
            "sequence": 1,
            "subscript": 1,
            "transform_pointer": 0,
        }
    ]
    assert scanned["external_references"] is False


def test_probe_and_iges_scanner_reject_malformed_or_truncated_data() -> None:
    worker = _worker()
    with pytest.raises(ValueError, match="AECCTX_STEP_IGES_FORMAT_UNSUPPORTED"):
        worker._probe(b"not CAD")
    with pytest.raises(ValueError, match="AECCTX_STEP_IGES_PARSE_FAILED"):
        worker._scan_iges(_iges_line("only start", "S", 1), max_records=10, max_recursion_depth=8)


def test_generated_step_iges_fixtures_are_bound_to_exact_source_profiles() -> None:
    worker = _worker()
    expected = {
        "ap203-part.step": ("cc1c9e3cdb0799fd2e602edb533f30051a0ea47db45ed9c0fd84dcd892498c61", "CONFIG_CONTROL_DESIGN", 380),
        "ap214-assembly.step": ("ee5dabdca280453e5afcb57d89952e5cc04d904f2d6bc0683258641745c42375", "AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }", 382),
        "ap242-part.step": ("8153a85a2b6b9d2b2958d0dcec56562989cc0e407e65a348f0f3798dd5aa8815", "AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF {1 0 10303 442 1 1 4 }", 350),
    }
    fixture_root = ROOT / "fixtures" / "v0.2" / "step-iges"
    for filename, (digest, schema, count) in expected.items():
        data = (fixture_root / filename).read_bytes()
        scanned = worker._scan_step(data, max_records=1000, max_recursion_depth=64)
        assert hashlib.sha256(data).hexdigest() == digest
        assert scanned["schemas"] == [schema]
        assert len(scanned["entities"]) == count
        assert any(item.get("component_classes") for item in scanned["entities"])

    iges = (fixture_root / "iges53-part.igs").read_bytes()
    scanned_iges = worker._scan_iges(iges, max_records=1000, max_recursion_depth=64)
    assert hashlib.sha256(iges).hexdigest() == "b64f87ee6b4fea34d9d268154550a17593e587f8227670c1a78fc84b51c09321"
    assert scanned_iges["version"] == "5.3"
    assert len(scanned_iges["directory"]) == 52


@pytest.mark.skipif(os.environ.get("AECCTX_RUN_STEP_IGES_PROVIDER") != "1", reason="exact reviewed OCI runtime is opt-in")
@pytest.mark.parametrize("fixture", ["ap203-part.step", "ap214-assembly.step", "ap242-part.step", "iges53-part.igs"])
def test_step_iges_live_provider_emits_source_and_derived_brep_evidence(fixture: str) -> None:
    source = (ROOT / "fixtures" / "v0.2" / "step-iges" / fixture).read_bytes()
    runner = ProviderRunner(
        registry=step_iges_registry(repository_root=ROOT),
        profile=OCIDockerProfile(image=STEP_IGES_IMAGE),
        limits=ProviderLimits(max_input_bytes=2_000_000, max_output_bytes=20_000_000, max_records=2_000, wall_time_seconds=30),
    )

    result = runner.run(STEP_IGES_PROVIDER_ID, "extract", source, configuration=STEP_IGES_CONFIGURATION)

    assert result.ok is True
    assert result.attestation["runtime_digest"] == STEP_IGES_IMAGE_ID
    assert result.events[0]["payload"]["schema"] == "aecctx.step-iges.source.v1"
    assert result.events[0]["payload"]["format"] in {"step", "iges"}
    shape_events = [item for item in result.events if item["payload"].get("schema") == "aecctx.step-iges.shape.v1"]
    assert shape_events
    assert shape_events[0]["payload"]["representation_fidelity"] == "brep-translator-derived"
    assert shape_events[0]["payload"]["topology"]["solids"] >= 1
    brep_paths = [item["path"] for item in result.artifacts if item["media_type"] == "model/vnd.opencascade.brep"]
    assert brep_paths == ["artifacts/root-1.brep"]
    assert result.artifact_bytes[brep_paths[0]].startswith(b"DBRep_DrawableShape")
    mesh_paths = [item["path"] for item in result.artifacts if item["media_type"] == "application/vnd.aecctx.triangle-mesh+json"]
    assert mesh_paths == ["artifacts/scene-mesh.json"]
    mesh = json.loads(result.artifact_bytes[mesh_paths[0]])
    assert mesh["schema"] == "aecctx.triangle-mesh.v1"
    assert len(mesh["vertices"]) >= 8
    assert len(mesh["triangles"]) >= 12
    assert result.capability_report["3d_geometry"]["support_level"] == "partial"
    assert "AECCTX_STEP_IGES_TRANSLATOR_PROCESSING_APPLIED" in result.capability_report["3d_geometry"]["reason_codes"]


@pytest.mark.skipif(os.environ.get("AECCTX_RUN_STEP_IGES_PROVIDER") != "1", reason="exact reviewed OCI runtime is opt-in")
def test_step_iges_live_provider_is_deterministic_for_fixed_runtime_and_input() -> None:
    source = (ROOT / "fixtures" / "v0.2" / "step-iges" / "ap214-assembly.step").read_bytes()
    runner = ProviderRunner(
        registry=step_iges_registry(repository_root=ROOT),
        profile=OCIDockerProfile(image=STEP_IGES_IMAGE),
        limits=ProviderLimits(max_input_bytes=2_000_000, max_output_bytes=20_000_000, max_records=2_000, wall_time_seconds=30),
    )

    first = runner.run(STEP_IGES_PROVIDER_ID, "extract", source, configuration=STEP_IGES_CONFIGURATION)
    second = runner.run(STEP_IGES_PROVIDER_ID, "extract", source, configuration=STEP_IGES_CONFIGURATION)

    assert first.events == second.events
    assert first.artifacts == second.artifacts
    assert first.artifact_bytes == second.artifact_bytes
    assert first.attestation == second.attestation
