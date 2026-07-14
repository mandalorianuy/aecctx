from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import zipfile
from dataclasses import replace
from importlib.resources import files
from pathlib import Path

import ezdxf
import pytest

from aecctx.adapters.dwg import ingest_dwg
from aecctx.dwg import DWGInputError, probe_dwg, validate_dwg_events
from aecctx.package import PackageReader
from aecctx.providers.dwg import DWG_CONFIGURATIONS, DWG_OCI_TARGETS, DWG_PROVIDER_ID, dwg_v03_descriptor, dwg_v03_registry
from aecctx.providers.protocol import ProviderResult
from aecctx.providers import OCIDockerProfile, ProviderLimits, ProviderRunner, load_provider_replay_entry, validate_provider_replay_corpus
from aecctx.records import RecordStore
from aecctx.source_bundle import SourceBundleError, load_source_bundle
from scripts.check_dwg_v03_conformance import ConformanceError, check as check_dwg_v03_conformance


ROOT = Path(__file__).parents[1]
FIXED_TIME = "2026-07-14T00:00:00Z"


def _worker():
    path = ROOT / "providers/libredwg/worker.py"
    spec = importlib.util.spec_from_file_location("aecctx_test_libredwg_v03_worker", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _capabilities() -> dict[str, dict[str, object]]:
    names = (
        "identity", "hierarchy", "properties", "relationships", "text", "2d_geometry",
        "3d_geometry", "materials_styles", "georeferencing", "validation",
    )
    return {
        name: {
            "affected": ["dwg-source"],
            "fallback": "retain observed source objects and converted DXF evidence",
            "reason_codes": ["AECCTX_DWG_CONVERTED_DXF_EVIDENCE"],
            "support_level": "partial" if name not in {"georeferencing"} else "unsupported",
        }
        for name in names
    }


def _v03_result(source: bytes, dxf: bytes, *, version: str = "AC1015", profile: str = "acx33-r2000-v1", units: dict[str, object] | None = None) -> ProviderResult:
    document = ezdxf.read(io.StringIO(dxf.decode("utf-8")))
    objects = []
    for entity in sorted(document.entitydb.values(), key=lambda item: item.dxf.get("handle", "")):
        handle = entity.dxf.get("handle")
        if handle:
            normalized = str(handle).upper().lstrip("0") or "0"
            objects.append({"aecctx_handle": normalized, "aecctx_locator": f"dwg:handle:{normalized}", "handle": handle, "object": entity.dxftype()})
    direct = {
        "CLASSES": [],
        "FILEHEADER": {"version": version},
        "HEADER": {"INSUNITS": 6},
        "OBJECTS": objects,
        "aecctx_handle_conflicts": [],
        "aecctx_unsupported_classes": [],
    }
    direct_bytes = json.dumps(direct, sort_keys=True, separators=(",", ":")).encode()
    input_sha = hashlib.sha256(source).hexdigest()
    direct_sha = hashlib.sha256(direct_bytes).hexdigest()
    dxf_sha = hashlib.sha256(dxf).hexdigest()
    unit_state = units or {"code": 6, "state": "known", "symbol": "m"}
    events = (
        {
            "event_type": "primitive",
            "payload": {
                "artifact_path": "artifacts/source.json", "artifact_sha256": direct_sha,
                "dwg_version": version, "handle_conflicts": [], "input_sha256": input_sha,
                "object_count": len(objects), "profile": profile, "schema": "aecctx.dwg.source.v2",
                "units": unit_state, "unsupported_classes": [],
            },
            "sequence": 0,
            "source_locator": f"sha256:{input_sha}",
        },
        {
            "event_type": "primitive",
            "payload": {
                "artifact_path": "artifacts/converted.dxf", "artifact_sha256": dxf_sha,
                "conversion_losses": [], "converter": "LibreDWG dwgread 0.13.4",
                "input_sha256": input_sha, "observed_dxf_version": version, "profile": profile,
                "representation_fidelity": "converted", "requested_dxf_version": version,
                "schema": "aecctx.dwg.conversion.v2",
            },
            "sequence": 1,
            "source_locator": f"dwg-artifact:converted-dxf:sha256:{dxf_sha}",
        },
    )
    return ProviderResult(
        ok=True,
        events=events,
        artifacts=(
            {"bytes": len(direct_bytes), "media_type": "application/vnd.aecctx.libredwg+json", "path": "artifacts/source.json", "sha256": direct_sha},
            {"bytes": len(dxf), "media_type": "application/dxf", "path": "artifacts/converted.dxf", "sha256": dxf_sha},
        ),
        artifact_bytes={"artifacts/source.json": direct_bytes, "artifacts/converted.dxf": dxf},
        diagnostics=(), capability_report=_capabilities(),
        resource_usage={"artifacts": 2, "events": 2, "source_objects": len(objects)},
        attestation={"provider_id": DWG_PROVIDER_ID, "runtime_digest": "sha256:" + "b" * 64},
    )


def test_v03_registration_is_closed_to_three_exact_profiles_and_extract_only() -> None:
    descriptor = dwg_v03_descriptor()
    assert descriptor.provider_version == "0.3.0"
    assert descriptor.actions == ("extract",)
    assert set(DWG_CONFIGURATIONS) == {"acx33-r13-v1", "acx33-r14-v1", "acx33-r2000-v1"}
    assert {item["dwg_version"] for item in DWG_CONFIGURATIONS.values()} == {"AC1012", "AC1014", "AC1015"}
    assert all(item["resolve_external_references"] is False for item in DWG_CONFIGURATIONS.values())


def test_worker_accepts_selected_headers_and_denies_writers_or_caller_commands() -> None:
    worker = _worker()
    for profile, configuration in DWG_CONFIGURATIONS.items():
        assert worker._configuration({"configuration": dict(configuration)})["profile"] == profile
        assert worker._probe(configuration["dwg_version"].encode() + b"fixture", configuration) == {"dwg_version": configuration["dwg_version"]}
    for changed in (
        {**DWG_CONFIGURATIONS["acx33-r14-v1"], "action": "dwgwrite"},
        {**DWG_CONFIGURATIONS["acx33-r14-v1"], "command_name": "dxf2dwg"},
        {**DWG_CONFIGURATIONS["acx33-r14-v1"], "resolve_external_references": True},
    ):
        with pytest.raises(ValueError, match="AECCTX_DWG_CONFIGURATION_INVALID"):
            worker._configuration({"configuration": changed})
    with pytest.raises(ValueError, match="AECCTX_DWG_VERSION_UNCLAIMED"):
        worker._probe(b"AC1032future", DWG_CONFIGURATIONS["acx33-r2000-v1"])


def test_worker_qualifies_only_explicit_units_and_reports_unsupported_classes() -> None:
    worker = _worker()
    limits = {"max_records": 10, "max_recursion_depth": 16, "max_string_bytes": 1024}
    base = {"FILEHEADER": {"version": "AC1014"}, "HEADER": {"INSUNITS": 4}, "CLASSES": [], "OBJECTS": [{"entity": "3DFACE", "handle": "A"}]}
    normalized = worker._validate_source_json(base, limits, expected_version="AC1014")
    assert normalized["aecctx_units"] == {"code": 4, "state": "known", "symbol": "mm"}
    unsupported = worker._validate_source_json(
        {**base, "HEADER": {}, "OBJECTS": [{"entity": "3DSOLID", "handle": "A"}, {"entity": "ACAD_PROXY_ENTITY", "handle": "B"}]},
        limits, expected_version="AC1014",
    )
    assert unsupported["aecctx_units"] == {"reason_code": "AECCTX_DWG_UNITS_NOT_QUALIFIED", "state": "unknown"}
    assert unsupported["aecctx_unsupported_classes"] == ["3DSOLID", "ACAD_PROXY_ENTITY"]


def test_dwg_v03_event_schema_is_public_packaged_and_version_bounded() -> None:
    public = ROOT / "schemas/v0.2/dwg-v03-event.schema.json"
    packaged = files("aecctx.schemas.v0_2").joinpath("dwg-v03-event.schema.json")
    assert public.read_bytes() == packaged.read_bytes()
    schema = json.loads(public.read_text())
    assert set(schema["$defs"]["dwg_version"]["enum"]) == {"AC1012", "AC1014", "AC1015"}


def test_package_gate_allows_license_review_but_rejects_external_runtime(tmp_path: Path) -> None:
    safe = tmp_path / "safe.zip"
    with zipfile.ZipFile(safe, "w") as archive:
        archive.writestr("aecctx/schemas/v0_2/dwg-v03-event.schema.json", "{}")
        archive.writestr("aecctx-0.2.0/docs/licenses/libredwg-provider.md", "review only")
    assert check_dwg_v03_conformance(artifacts=(safe,))["ok"] is True

    unsafe = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(unsafe, "w") as archive:
        archive.writestr("aecctx/schemas/v0_2/dwg-v03-event.schema.json", "{}")
        archive.writestr("aecctx-0.2.0/providers/libredwg/worker.py", "runtime")
    with pytest.raises(ConformanceError, match="AECCTX_DWG_V03_GPL_RUNTIME_BUNDLED"):
        check_dwg_v03_conformance(artifacts=(unsafe,))


def test_repository_preserves_generated_dwg_dxf_evidence_as_binary() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "fixtures/v0.3/dwg/**/*.dxf binary" in attributes


def test_shared_source_bundle_accepts_only_hash_bound_dwg_members(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    (root / "refs").mkdir(parents=True)
    members = {"root.dwg": b"AC1015root", "refs/child.dwg": b"AC1014child"}
    for logical, data in members.items():
        path = root / logical
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    manifest = {
        "version": "0.2", "root": "root.dwg",
        "entries": [
            {"path": logical, "role": "root" if logical == "root.dwg" else "xref", "media_type": "image/vnd.dwg", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for logical, data in sorted(members.items())
        ],
    }
    (root / "source-bundle.json").write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")))
    bundle = load_source_bundle(root, allowed_media_types={"image/vnd.dwg"})
    assert bundle.root.logical_path == "root.dwg"
    assert [item.logical_path for item in bundle.entries] == ["refs/child.dwg", "root.dwg"]
    manifest["entries"][0]["sha256"] = "0" * 64
    (root / "source-bundle.json").write_text(json.dumps(manifest))
    with pytest.raises(SourceBundleError, match="digest mismatch"):
        load_source_bundle(root, allowed_media_types={"image/vnd.dwg"})


def test_v03_events_map_explicit_units_and_converted_3d_without_fidelity_escalation(tmp_path: Path) -> None:
    fixture = ROOT / "fixtures/v0.2/dwg/r2000-profile.dwg"
    dxf = (ROOT / "fixtures/v0.2/dwg/r2000-profile.dxf").read_bytes()
    result = _v03_result(fixture.read_bytes(), dxf)
    evidence = validate_dwg_events(result)
    assert evidence.source_event["units"] == {"code": 6, "state": "known", "symbol": "m"}
    output = tmp_path / "package.aecctx"
    ingest_dwg(fixture, output, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0", provider_result=result)
    records = [record.raw for record in RecordStore.open(output).records.values()]
    source_record = next(item for item in records if item["record_type"] == "source")
    faces = [item for item in records if item.get("original_class") == "3DFACE" and item.get("evidence_class") == "derived"]
    assert source_record["detected_units"] == {"state": "known", "value": "m"}
    assert source_record["detected_format"] == {"state": "known", "value": "DWG AC1015"}
    assert faces and all(item["representation_fidelity"]["class"] == "converted" for item in faces)
    reader = PackageReader(output)
    assert reader.read_bytes("evidence/converted.dxf") == dxf

    events = [dict(item) for item in result.events]
    events[1]["payload"] = {**events[1]["payload"], "representation_fidelity": "source-exact"}
    with pytest.raises(DWGInputError) as caught:
        validate_dwg_events(replace(result, events=tuple(events)))
    assert caught.value.code == "AECCTX_DWG_EVENT_INVALID"


@pytest.mark.parametrize("prefix", [b"AC1012fixture", b"AC1014fixture", b"AC1015fixture"])
def test_probe_dwg_accepts_only_selected_v03_headers(prefix: bytes) -> None:
    assert probe_dwg(prefix) == {"confidence": 1.0, "format": "dwg", "version": prefix[:6].decode()}
    assert probe_dwg(b"AC1009fixture")["confidence"] == 0.0


def test_committed_v03_corpus_binds_all_selected_versions_units_and_generator() -> None:
    corpus_path = ROOT / "conformance/v0.3/dwg-corpus.json"
    result = validate_provider_replay_corpus(corpus_path)
    assert result["ok"] is True
    assert {item["id"] for item in result["entries"]} == {"r13-profile", "r14-profile", "r2000-m-profile", "r2000-mm-xref"}
    corpus = json.loads(corpus_path.read_text())
    for key in ("generator", "profile", "schema", "worker"):
        reference = corpus[key]
        assert hashlib.sha256((ROOT / reference["path"]).read_bytes()).hexdigest() == reference["sha256"]
    observed = {entry_id: validate_dwg_events(load_provider_replay_entry(corpus_path, entry_id).result).source_event for entry_id in ("r13-profile", "r14-profile", "r2000-m-profile", "r2000-mm-xref")}
    assert [observed[name]["dwg_version"] for name in ("r13-profile", "r14-profile", "r2000-m-profile")] == ["AC1012", "AC1014", "AC1015"]
    assert observed["r2000-m-profile"]["units"]["symbol"] == "m"
    assert observed["r2000-mm-xref"]["units"]["symbol"] == "mm"
    assert observed["r13-profile"]["units"]["state"] == "unknown"


def test_dwg_content_addressed_bundle_maps_separate_sources_and_xref(tmp_path: Path) -> None:
    corpus = ROOT / "conformance/v0.3/dwg-corpus.json"
    results = {
        "root.dwg": load_provider_replay_entry(corpus, "r2000-m-profile").result,
        "refs/child.dwg": load_provider_replay_entry(corpus, "r2000-mm-xref").result,
    }
    output = tmp_path / "bundle.aecctx"
    ingest_dwg(ROOT / "fixtures/v0.3/dwg/xref-bundle", output, created_at=FIXED_TIME, package_form="zip", aecctx_version="0.2.0", provider_results=results)
    records = [record.raw for record in RecordStore.open(output).records.values()]
    sources = [item for item in records if item["record_type"] == "source"]
    xrefs = [item for item in records if item["record_type"] == "relation" and item["relation_type"] == "aecctx:external-reference"]
    assert {item["bundle_logical_path"] for item in sources} == {"root.dwg", "refs/child.dwg"}
    assert {item["detected_units"].get("value") for item in sources} == {"m", "mm"}
    assert len(xrefs) == 1 and xrefs[0]["declared_path"] == "refs/child.dwg"
    assert xrefs[0]["resolution"] == "content-addressed-source-bundle"


def test_worker_rejects_project_authored_encrypted_and_protected_envelopes_before_decoder(tmp_path: Path) -> None:
    worker = _worker()
    configuration = DWG_CONFIGURATIONS["acx33-r2000-v1"]
    request = {"configuration": configuration, "input": {"sha256": ""}, "limits": {"max_records": 10, "max_recursion_depth": 8, "max_output_bytes": 1024}}
    for marker, code in ((b"AECCTX_ENCRYPTED_TEST", "AECCTX_DWG_ENCRYPTED_UNSUPPORTED"), (b"AECCTX_PROTECTED_TEST", "AECCTX_DWG_PROTECTED_UNSUPPORTED")):
        source = tmp_path / f"{code}.dwg"
        source.write_bytes(b"AC1015" + marker)
        request["input"]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
        with pytest.raises(ValueError, match=code):
            worker._response(request, source, tmp_path / code)


def test_cli_replay_ingests_closed_dwg_bundle_without_launching_runtime(tmp_path: Path) -> None:
    from aecctx.cli import main

    output = tmp_path / "cli-bundle.aecctx"
    assert main([
        "ingest", str(ROOT / "fixtures/v0.3/dwg/xref-bundle"), "--adapter", "dwg", "--aecctx-version", "0.2.0",
        "--provider-replay", str(ROOT / "conformance/v0.3/dwg-corpus.json"),
        "--provider-entry", "r2000-m-profile", "--provider-entry", "r2000-mm-xref",
        "--output", str(output), "--form", "zip", "--created-at", FIXED_TIME, "--json",
    ]) == 0
    assert PackageReader(output).manifest["source_ids"] == sorted(PackageReader(output).manifest["source_ids"])


@pytest.mark.skipif(os.environ.get("AECCTX_RUN_DWG_V03_PROVIDER") != "1", reason="exact reviewed OCI multiarch runtime is opt-in")
def test_live_v03_profiles_are_equal_on_arm64_and_amd64() -> None:
    corpus = ROOT / "conformance/v0.3/dwg-corpus.json"
    for entry_id, profile in (("r13-profile", "acx33-r13-v1"), ("r14-profile", "acx33-r14-v1"), ("r2000-m-profile", "acx33-r2000-v1"), ("r2000-mm-xref", "acx33-r2000-v1")):
        source = load_provider_replay_entry(corpus, entry_id).input_bytes
        results = []
        for target in DWG_OCI_TARGETS:
            runner = ProviderRunner(
                registry=dwg_v03_registry(repository_root=ROOT),
                profile=OCIDockerProfile(image=target.image, platform=target.platform, architecture=target.architecture),
                limits=ProviderLimits(max_input_bytes=2_000_000, max_output_bytes=30_000_000, max_records=2_000, wall_time_seconds=30),
            )
            result = runner.run(DWG_PROVIDER_ID, "extract", source, configuration=DWG_CONFIGURATIONS[profile])
            assert result.ok is True
            results.append(result)
        assert results[0].events == results[1].events
        assert results[0].artifacts == results[1].artifacts
        assert results[0].artifact_bytes == results[1].artifact_bytes
