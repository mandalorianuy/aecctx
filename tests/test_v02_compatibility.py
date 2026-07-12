from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from aecctx.diff import diff_packages
from aecctx.validation import validate_package


RECORD_PATHS = (
    "sources/sources.jsonl",
    "evidence/primitives.jsonl",
    "evidence/assertions.jsonl",
    "model/entities.jsonl",
    "model/relations.jsonl",
    "diagnostics/diagnostics.jsonl",
)


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"


def _rehash_package(package: Path) -> None:
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest_lines: list[bytes] = []
    for artifact in manifest["artifacts"]:
        data = (package / artifact["path"]).read_bytes()
        artifact["bytes"] = len(data)
        artifact["sha256"] = hashlib.sha256(data).hexdigest()
        digest_lines.append(f"{artifact['path']}\0{artifact['sha256']}\0{len(data)}\n".encode())
    manifest["logical_digest"] = hashlib.sha256(b"".join(sorted(digest_lines))).hexdigest()
    manifest_path.write_text(_canonical_json(manifest), encoding="utf-8")


def make_v02_package(tmp_path: Path) -> Path:
    source = Path(__file__).parents[1] / "fixtures" / "minimal-aecctx"
    package = tmp_path / "v02-package"
    shutil.copytree(source, package)
    for relative in RECORD_PATHS:
        path = package / relative
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        path.write_text(
            "".join(_canonical_json({**record, "evidence_class": "observed", "record_version": "0.2"}) for record in records),
            encoding="utf-8",
        )
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["aecctx_version"] = "0.2.0"
    manifest["required_extensions"] = []
    manifest["extensions"] = {"org.example.optional": {"retained": True}}
    manifest_path.write_text(_canonical_json(manifest), encoding="utf-8")
    _rehash_package(package)
    return package


def test_v02_package_and_optional_extension_validate(tmp_path: Path) -> None:
    package = make_v02_package(tmp_path)

    result = validate_package(package)

    assert result.valid is True
    assert result.manifest is not None
    assert result.manifest["aecctx_version"] == "0.2.0"


def test_unknown_required_extension_is_rejected(tmp_path: Path) -> None:
    package = make_v02_package(tmp_path)
    manifest_path = package / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["required_extensions"] = ["org.example.unsupported@1"]
    manifest_path.write_text(_canonical_json(manifest), encoding="utf-8")

    result = validate_package(package)

    assert result.valid is False
    assert any(item.code == "AECCTX_REQUIRED_EXTENSION_UNSUPPORTED" for item in result.diagnostics)


def test_record_version_must_match_manifest_version(tmp_path: Path) -> None:
    package = make_v02_package(tmp_path)
    path = package / "evidence" / "primitives.jsonl"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["record_version"] = "0.1"
    path.write_text(_canonical_json(record), encoding="utf-8")
    _rehash_package(package)

    result = validate_package(package)

    assert result.valid is False
    assert any(item.code == "AECCTX_SCHEMA_INVALID" for item in result.diagnostics)


def test_cross_version_diff_reports_version_change(tmp_path: Path) -> None:
    v01 = Path(__file__).parents[1] / "fixtures" / "minimal-aecctx"
    v02 = make_v02_package(tmp_path)

    result = diff_packages(v01, v02)

    assert result.version_changed is True
    assert result.before_version == "0.1.0"
    assert result.after_version == "0.2.0"


def test_inferred_record_requires_provider_inference_metadata(tmp_path: Path) -> None:
    package = make_v02_package(tmp_path)
    path = package / "evidence" / "primitives.jsonl"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["evidence_class"] = "inferred"
    path.write_text(_canonical_json(record), encoding="utf-8")
    _rehash_package(package)

    result = validate_package(package)

    assert result.valid is False
    assert any(item.code == "AECCTX_SCHEMA_INVALID" and item.path == "evidence/primitives.jsonl:1" for item in result.diagnostics)


def test_manual_calibration_cannot_occupy_declared_units_slot(tmp_path: Path) -> None:
    package = make_v02_package(tmp_path)
    path = package / "evidence" / "primitives.jsonl"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["coordinate_qualification"] = {
        "declared_units": {"authority": "manual", "state": "known", "value": "m"},
        "global_location": {"reason_code": "AECCTX_CRS_NOT_DECLARED", "state": "unknown"},
        "transform_chain": [],
    }
    path.write_text(_canonical_json(record), encoding="utf-8")
    _rehash_package(package)

    result = validate_package(package)

    assert result.valid is False
    assert any(item.code == "AECCTX_SCHEMA_INVALID" for item in result.diagnostics)


def test_incomplete_transform_chain_cannot_claim_known_global_location(tmp_path: Path) -> None:
    package = make_v02_package(tmp_path)
    path = package / "evidence" / "primitives.jsonl"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["coordinate_qualification"] = {
        "global_location": {"state": "known", "value": "EPSG:32721"},
        "transform_chain": [
            {
                "from_frame": "source-local",
                "reason_code": "AECCTX_TRANSFORM_NOT_OBSERVED",
                "state": "unknown",
                "to_frame": "project",
            }
        ],
    }
    path.write_text(_canonical_json(record), encoding="utf-8")
    _rehash_package(package)

    result = validate_package(package)

    assert result.valid is False
    assert any(item.code == "AECCTX_COORDINATE_GLOBAL_STATE_INVALID" for item in result.diagnostics)


def test_preview_record_cannot_claim_source_fidelity(tmp_path: Path) -> None:
    package = make_v02_package(tmp_path)
    path = package / "evidence" / "primitives.jsonl"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["representation_fidelity"] = {
        "class": "preview",
        "derived": False,
        "source_representation_ids": [record["record_id"]],
    }
    path.write_text(_canonical_json(record), encoding="utf-8")
    _rehash_package(package)

    result = validate_package(package)

    assert result.valid is False
    assert any(item.code == "AECCTX_FIDELITY_DERIVATION_INVALID" for item in result.diagnostics)


def test_network_attestation_requires_explicit_allowlisted_mode(tmp_path: Path) -> None:
    package = make_v02_package(tmp_path)
    path = package / "evidence" / "primitives.jsonl"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["provider_attestation"] = {
        "deterministic": False,
        "execution_mode": "network",
        "network_mode": "disabled",
        "provider_id": "org.example.remote",
        "provider_version": "1",
        "request_digest": "a" * 64,
        "response_digest": "b" * 64,
        "runtime_version": "remote-1",
    }
    path.write_text(_canonical_json(record), encoding="utf-8")
    _rehash_package(package)

    result = validate_package(package)

    assert result.valid is False
    assert any(item.code == "AECCTX_PROVIDER_ATTESTATION_NETWORK_INVALID" for item in result.diagnostics)
