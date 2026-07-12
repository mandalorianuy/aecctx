from __future__ import annotations

import importlib.util
import hashlib
import json
import math
import os
from pathlib import Path

import pytest

from aecctx.providers.dwg import (
    DWG_CONFIGURATION,
    DWG_IMAGE,
    DWG_IMAGE_ID,
    DWG_PROVIDER_ID,
    dwg_descriptor,
    dwg_registry,
)
from aecctx.providers import OCIDockerProfile, ProviderLimits, ProviderRunner


ROOT = Path(__file__).parents[1]


def _worker():
    path = ROOT / "providers" / "libredwg" / "worker.py"
    spec = importlib.util.spec_from_file_location("aecctx_test_libredwg_worker", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dwg_profile_registration_pins_reviewed_runtime_and_worker() -> None:
    descriptor = dwg_descriptor()
    registration = dwg_registry(repository_root=ROOT).resolve(DWG_PROVIDER_ID)

    assert descriptor.provider_id == "org.aecctx.dwg.libredwg"
    assert descriptor.provider_version == "0.2.0"
    assert descriptor.runtime_version == "python-3.12+libredwg-0.13.4-api1"
    assert descriptor.runtime_digest == DWG_IMAGE_ID
    assert DWG_IMAGE_ID.startswith("sha256:") and len(DWG_IMAGE_ID) == 71
    assert DWG_IMAGE_ID != "sha256:" + "0" * 64
    assert descriptor.license_spdx == "GPL-3.0-or-later"
    assert descriptor.formats == ("image/vnd.dwg",)
    assert descriptor.platforms == ("linux-container",)
    assert descriptor.network_mode == "disabled"
    assert all(descriptor.enforced_axes.values())
    assert registration.container_image == DWG_IMAGE == "aecctx-dwg-libredwg:0.2.0"
    assert registration.container_image_id == DWG_IMAGE_ID
    assert registration.container_command == ("python3", "/provider/worker.py")
    assert registration.container_pids_limit == 2
    assert registration.worker_path == ROOT / "providers" / "libredwg" / "worker.py"
    assert DWG_CONFIGURATION == {
        "dwg_version": "AC1015",
        "dxf_version": "r2000",
        "json_format": "JSON",
        "profile": "acx18-r2000-v1",
        "resolve_external_references": False,
    }


def test_dwg_gpl_runtime_is_absent_from_core_distribution_dependencies() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()

    assert "libredwg" not in pyproject
    assert "real-dwg" not in pyproject
    assert "opendesign" not in pyproject
    assert "autodesk" not in pyproject


def test_dwg_worker_accepts_only_exact_configuration() -> None:
    worker = _worker()

    assert worker._configuration({"configuration": dict(DWG_CONFIGURATION)}) == DWG_CONFIGURATION
    for changed in (
        {**DWG_CONFIGURATION, "dwg_version": "AC1027"},
        {**DWG_CONFIGURATION, "resource_path": "/tmp/host"},
        {key: value for key, value in DWG_CONFIGURATION.items() if key != "profile"},
    ):
        with pytest.raises(ValueError, match="AECCTX_DWG_CONFIGURATION_INVALID"):
            worker._configuration({"configuration": changed})


def test_dwg_probe_accepts_only_exact_r2000_header() -> None:
    worker = _worker()

    assert worker._probe(b"AC1015\x00project fixture") == {"dwg_version": "AC1015"}
    with pytest.raises(ValueError, match="AECCTX_DWG_VERSION_UNCLAIMED"):
        worker._probe(b"AC1027\x00newer")
    with pytest.raises(ValueError, match="AECCTX_DWG_HEADER_TRUNCATED"):
        worker._probe(b"AC10")


def test_dwg_source_json_is_bounded_and_preserves_inert_values() -> None:
    worker = _worker()
    source = {
        "FILEHEADER": {"version": "AC1015"},
        "HEADER": {"version": "AC1015"},
        "CLASSES": [],
        "OBJECTS": [
            {"entity": "LINE", "handle": "a", "layer": "0"},
            {"entity": "XREF", "handle": "00B", "path": "../../etc/passwd"},
        ],
    }

    normalized = worker._validate_source_json(
        source,
        {"max_records": 10, "max_recursion_depth": 8, "max_string_bytes": 1024},
    )

    assert [item["aecctx_handle"] for item in normalized["OBJECTS"]] == ["A", "B"]
    assert [item["aecctx_locator"] for item in normalized["OBJECTS"]] == ["dwg:handle:A", "dwg:handle:B"]
    assert normalized["OBJECTS"][1]["path"] == "../../etc/passwd"
    assert worker._canonical(normalized) == worker._canonical(normalized)


def test_dwg_source_json_preserves_duplicate_handles_as_conflicted_occurrences() -> None:
    worker = _worker()
    base = {"FILEHEADER": {"version": "AC1015"}, "HEADER": {}, "CLASSES": [], "OBJECTS": [{"entity": "LINE", "handle": "A"}]}

    normalized = worker._validate_source_json(
        {**base, "OBJECTS": [base["OBJECTS"][0], {"entity": "CIRCLE", "handle": "0a"}]},
        {"max_records": 10, "max_recursion_depth": 8, "max_string_bytes": 1024},
    )

    assert normalized["aecctx_handle_conflicts"] == ["A"]
    assert [item["aecctx_locator"] for item in normalized["OBJECTS"]] == [
        "dwg:handle:A:occurrence:0",
        "dwg:handle:A:occurrence:1",
    ]


def test_dwg_source_json_rejects_malformed_handles_limits_and_non_finite_numbers() -> None:
    worker = _worker()
    base = {"FILEHEADER": {"version": "AC1015"}, "HEADER": {}, "CLASSES": [], "OBJECTS": [{"entity": "LINE", "handle": "A"}]}

    with pytest.raises(ValueError, match="AECCTX_DWG_HANDLE_INVALID"):
        worker._validate_source_json(
            {**base, "OBJECTS": [{"entity": "LINE", "handle": "not-hex"}]},
            {"max_records": 10, "max_recursion_depth": 8, "max_string_bytes": 1024},
        )
    with pytest.raises(ValueError, match="AECCTX_DWG_OBJECT_LIMIT_EXCEEDED"):
        worker._validate_source_json(base, {"max_records": 0, "max_recursion_depth": 8, "max_string_bytes": 1024})
    with pytest.raises(ValueError, match="AECCTX_DWG_RECURSION_LIMIT_EXCEEDED"):
        worker._validate_source_json(
            {**base, "HEADER": {"a": {"b": {"c": 1}}}},
            {"max_records": 10, "max_recursion_depth": 2, "max_string_bytes": 1024},
        )
    with pytest.raises(ValueError, match="AECCTX_DWG_NUMBER_INVALID"):
        worker._validate_source_json(
            {**base, "HEADER": {"value": math.inf}},
            {"max_records": 10, "max_recursion_depth": 8, "max_string_bytes": 1024},
        )
    with pytest.raises(ValueError, match="AECCTX_DWG_STRING_LIMIT_EXCEEDED"):
        worker._validate_source_json(
            {**base, "HEADER": {"value": "long"}},
            {"max_records": 10, "max_recursion_depth": 8, "max_string_bytes": 3},
        )


def test_project_authored_dwg_fixture_has_exact_r2000_envelope_and_negative_cases() -> None:
    fixture_root = ROOT / "fixtures" / "v0.2" / "dwg"
    source = (fixture_root / "r2000-profile.dwg").read_bytes()

    assert source.startswith(b"AC1015")
    assert hashlib.sha256(source).hexdigest() == "fe9e07cabc83eb99c3c2334d5503fbcc9ebe0f94d349581ee559d57d6a30c494"
    assert hashlib.sha256((fixture_root / "r2000-profile.dxf").read_bytes()).hexdigest() == "6dc440b5b49b63314487e74c9c77ba6602feb42797b0e3a96bb76620f0c2351e"
    assert (fixture_root / "r2000-profile.dxf").read_bytes().startswith(b"  0\nSECTION")
    assert (fixture_root / "wrong-version.dwg").read_bytes().startswith(b"AC1027")
    assert (fixture_root / "truncated.dwg").read_bytes() == b"AC10"


def _live_runner(*, max_output_bytes: int = 30_000_000) -> ProviderRunner:
    return ProviderRunner(
        registry=dwg_registry(repository_root=ROOT),
        profile=OCIDockerProfile(image=DWG_IMAGE),
        limits=ProviderLimits(
            max_input_bytes=2_000_000,
            max_output_bytes=max_output_bytes,
            max_records=2_000,
            wall_time_seconds=30,
        ),
    )


@pytest.mark.skipif(os.environ.get("AECCTX_RUN_DWG_PROVIDER") != "1", reason="exact reviewed OCI runtime is opt-in")
def test_dwg_live_provider_emits_direct_json_and_converted_dxf_evidence() -> None:
    source = (ROOT / "fixtures" / "v0.2" / "dwg" / "r2000-profile.dwg").read_bytes()
    result = _live_runner().run(DWG_PROVIDER_ID, "extract", source, configuration=DWG_CONFIGURATION)

    assert result.ok is True
    assert result.attestation["runtime_digest"] == DWG_IMAGE_ID
    assert [event["payload"]["schema"] for event in result.events] == ["aecctx.dwg.source.v1", "aecctx.dwg.conversion.v1"]
    assert result.events[0]["payload"]["object_count"] == 82
    assert result.events[0]["payload"]["handle_conflicts"] == ["1F", "B"]
    source_json = json.loads(result.artifact_bytes["artifacts/source.json"])
    assert source_json["FILEHEADER"]["version"] == "AC1015"
    assert "../../never-opened" in json.dumps(source_json)
    assert b"SECTION\r\n  2\r\nHEADER" in result.artifact_bytes["artifacts/converted-r2000.dxf"]
    assert b"AC1015" in result.artifact_bytes["artifacts/converted-r2000.dxf"]
    assert result.capability_report["2d_geometry"]["support_level"] == "partial"
    assert result.capability_report["3d_geometry"]["support_level"] == "unsupported"


@pytest.mark.skipif(os.environ.get("AECCTX_RUN_DWG_PROVIDER") != "1", reason="exact reviewed OCI runtime is opt-in")
def test_dwg_live_provider_is_deterministic_for_fixed_input_and_runtime() -> None:
    source = (ROOT / "fixtures" / "v0.2" / "dwg" / "r2000-profile.dwg").read_bytes()
    first = _live_runner().run(DWG_PROVIDER_ID, "extract", source, configuration=DWG_CONFIGURATION)
    second = _live_runner().run(DWG_PROVIDER_ID, "extract", source, configuration=DWG_CONFIGURATION)

    assert first.events == second.events
    assert first.artifacts == second.artifacts
    assert first.artifact_bytes == second.artifact_bytes
    assert first.attestation["response_payload_digest"] == second.attestation["response_payload_digest"]


@pytest.mark.skipif(os.environ.get("AECCTX_RUN_DWG_PROVIDER") != "1", reason="exact reviewed OCI runtime is opt-in")
@pytest.mark.parametrize(
    ("fixture", "code"),
    [("wrong-version.dwg", "AECCTX_DWG_VERSION_UNCLAIMED"), ("truncated.dwg", "AECCTX_DWG_HEADER_TRUNCATED")],
)
def test_dwg_live_provider_rejects_unclaimed_or_truncated_envelopes(fixture: str, code: str) -> None:
    source = (ROOT / "fixtures" / "v0.2" / "dwg" / fixture).read_bytes()
    result = _live_runner().run(DWG_PROVIDER_ID, "extract", source, configuration=DWG_CONFIGURATION)

    assert result.ok is False
    assert result.error == {"code": code, "message": "ValueError: DWG extraction failed"}
