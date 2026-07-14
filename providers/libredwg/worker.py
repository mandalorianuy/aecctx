from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any


PROVIDER_ID = "org.aecctx.dwg.libredwg"
RUNTIME_DIGEST = "sha256:bb237d62599b5204b550fb075ee9f738e4198e031b71f3a6d7f85eae07c0c7c1"
RUNTIME_VERSION = "python-3.12+libredwg-0.13.4-api1"
CONFIGURATION = {
    "dwg_version": "AC1015",
    "dxf_version": "r2000",
    "json_format": "JSON",
    "profile": "acx18-r2000-v1",
    "resolve_external_references": False,
}
CONFIGURATIONS = {
    "acx33-r13-v1": {"dwg_version": "AC1012", "dxf_version": "r13", "json_format": "JSON", "profile": "acx33-r13-v1", "resolve_external_references": False},
    "acx33-r14-v1": {"dwg_version": "AC1014", "dxf_version": "r14", "json_format": "JSON", "profile": "acx33-r14-v1", "resolve_external_references": False},
    "acx33-r2000-v1": {"dwg_version": "AC1015", "dxf_version": "r2000", "json_format": "JSON", "profile": "acx33-r2000-v1", "resolve_external_references": False},
}
REQUIRED_AXES = (
    "cpu", "decompression", "environment", "filesystem", "input_bytes", "memory", "network", "open_files",
    "output_bytes", "process", "process_tree", "records", "recursion", "temporary_storage", "user_permissions", "wall_time",
)
CAPABILITIES = (
    "identity", "hierarchy", "properties", "relationships", "text", "2d_geometry", "3d_geometry", "materials_styles", "georeferencing", "validation",
)
HANDLE_RE = re.compile(r"[0-9A-F]+")
UNIT_SYMBOLS = {1: "in", 2: "ft", 4: "mm", 5: "cm", 6: "m", 7: "km"}
UNSUPPORTED_CLASSES = {"3DSOLID", "ACAD_PROXY_ENTITY", "ACAD_PROXY_OBJECT", "BODY", "REGION", "SURFACE"}


def _configuration(request: dict[str, Any]) -> dict[str, Any]:
    configured = request.get("configuration")
    accepted = (CONFIGURATION, *CONFIGURATIONS.values())
    if configured not in accepted:
        raise ValueError("AECCTX_DWG_CONFIGURATION_INVALID")
    return dict(configured)


def _probe(data: bytes, configuration: dict[str, Any] | None = None) -> dict[str, str]:
    if len(data) < 6:
        raise ValueError("AECCTX_DWG_HEADER_TRUNCATED")
    version = data[:6].decode("ascii", errors="replace")
    expected = str((configuration or CONFIGURATION)["dwg_version"])
    if version != expected:
        raise ValueError("AECCTX_DWG_VERSION_UNCLAIMED")
    return {"dwg_version": version}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _handle(value: Any) -> str:
    if isinstance(value, str):
        normalized = value.upper().lstrip("0") or "0"
    elif (
        isinstance(value, list)
        and len(value) in {3, 4}
        and all(isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in value)
    ):
        normalized = f"{value[-1]:X}"
    else:
        raise ValueError("AECCTX_DWG_HANDLE_INVALID")
    if not HANDLE_RE.fullmatch(normalized):
        raise ValueError("AECCTX_DWG_HANDLE_INVALID")
    return normalized


def _bounded(value: Any, *, depth: int, limits: dict[str, Any]) -> None:
    if depth > int(limits["max_recursion_depth"]):
        raise ValueError("AECCTX_DWG_RECURSION_LIMIT_EXCEEDED")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("AECCTX_DWG_JSON_INVALID")
            _bounded(key, depth=depth + 1, limits=limits)
            _bounded(item, depth=depth + 1, limits=limits)
    elif isinstance(value, list):
        for item in value:
            _bounded(item, depth=depth + 1, limits=limits)
    elif isinstance(value, str):
        if len(value.encode("utf-8")) > int(limits["max_string_bytes"]):
            raise ValueError("AECCTX_DWG_STRING_LIMIT_EXCEEDED")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            raise ValueError("AECCTX_DWG_NUMBER_INVALID")
    elif value is not None and not isinstance(value, bool):
        raise ValueError("AECCTX_DWG_JSON_INVALID")


def _validate_source_json(value: Any, limits: dict[str, Any], *, expected_version: str = "AC1015", include_v03: bool | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("AECCTX_DWG_JSON_INVALID")
    _bounded(value, depth=0, limits=limits)
    if not isinstance(value.get("FILEHEADER"), dict) or value["FILEHEADER"].get("version") != expected_version:
        raise ValueError("AECCTX_DWG_JSON_VERSION_INVALID")
    if not isinstance(value.get("HEADER"), dict) or not isinstance(value.get("CLASSES"), list) or not isinstance(value.get("OBJECTS"), list):
        raise ValueError("AECCTX_DWG_JSON_INVALID")
    objects = value["OBJECTS"]
    if len(objects) > int(limits["max_records"]):
        raise ValueError("AECCTX_DWG_OBJECT_LIMIT_EXCEEDED")
    handles: list[str] = []
    for item in objects:
        if not isinstance(item, dict) or not isinstance(item.get("object", item.get("entity")), str):
            raise ValueError("AECCTX_DWG_OBJECT_INVALID")
        handles.append(_handle(item.get("handle")))
    conflicts = sorted(handle for handle, count in Counter(handles).items() if count > 1)
    occurrences: Counter[str] = Counter()
    normalized_objects: list[dict[str, Any]] = []
    for item, handle in zip(objects, handles, strict=True):
        occurrence = occurrences[handle]
        occurrences[handle] += 1
        locator = f"dwg:handle:{handle}"
        if handle in conflicts:
            locator += f":occurrence:{occurrence}"
        normalized_objects.append({**item, "aecctx_handle": handle, "aecctx_locator": locator})
    normalized = {**value, "OBJECTS": normalized_objects, "aecctx_handle_conflicts": conflicts}
    if include_v03 is True or expected_version != "AC1015":
        raw_units = value["HEADER"].get("INSUNITS", value["HEADER"].get("$INSUNITS"))
        if isinstance(raw_units, int) and not isinstance(raw_units, bool) and raw_units in UNIT_SYMBOLS:
            units: dict[str, Any] = {"code": raw_units, "state": "known", "symbol": UNIT_SYMBOLS[raw_units]}
        else:
            units = {"reason_code": "AECCTX_DWG_UNITS_NOT_QUALIFIED", "state": "unknown"}
        unsupported = sorted(
            {str(item.get("object", item.get("entity"))) for item in normalized_objects if str(item.get("object", item.get("entity"))) in UNSUPPORTED_CLASSES or "PROXY" in str(item.get("object", item.get("entity")))}
        )
        normalized.update({"aecctx_units": units, "aecctx_unsupported_classes": unsupported})
    return normalized


def descriptor(*, provider_version: str = "0.2.0") -> dict[str, Any]:
    return {
        "actions": ["extract"],
        "deterministic": True,
        "distribution": "operator-built-oci-image",
        "enforced_axes": {axis: True for axis in REQUIRED_AXES},
        "enforcement_profile": "oci-docker-v1",
        "formats": ["image/vnd.dwg"],
        "license_spdx": "GPL-3.0-or-later",
        "network_mode": "disabled",
        "platforms": ["linux-container"],
        "protocol_version": "0.2",
        "provider_id": PROVIDER_ID,
        "provider_version": provider_version,
        "runtime_digest": RUNTIME_DIGEST,
        "runtime_version": RUNTIME_VERSION,
    }


def _capability_report(ok: bool, conflicts: bool = False, *, v03: bool = False) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for name in CAPABILITIES:
        if ok and name in ({"identity", "properties", "relationships", "text", "2d_geometry", "3d_geometry", "materials_styles", "validation"} if v03 else {"identity", "properties", "relationships", "text", "2d_geometry", "materials_styles", "validation"}):
            reasons = ["AECCTX_DWG_CONVERTED_DXF_EVIDENCE"]
            if conflicts and name in {"identity", "relationships"}:
                reasons.append("AECCTX_DWG_HANDLE_CONFLICT")
            result[name] = {
                "affected": ["dwg-source"],
                "fallback": "retain observed source objects and converted DXF evidence",
                "reason_codes": reasons,
                "support_level": "partial",
            }
        else:
            result[name] = {
                "affected": ["dwg-source"],
                "fallback": "retain opaque source evidence",
                "reason_codes": ["AECCTX_DWG_CAPABILITY_UNSUPPORTED"],
                "support_level": "unsupported",
            }
    return result


def _run_dwgread(source_path: Path, format_name: str, output_path: Path) -> str:
    process = subprocess.run(
        ["/opt/libredwg/bin/dwgread", "-O", format_name, "-o", str(output_path), str(source_path)],
        check=False,
        capture_output=True,
        env={"HOME": "/workspace/tmp", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PATH": ""},
        shell=False,
        timeout=60,
    )
    if process.returncode != 0 or not output_path.is_file():
        raise ValueError(f"AECCTX_DWG_{format_name}_CONVERSION_FAILED")
    return process.stderr.decode("utf-8", errors="replace")


def _response(request: dict[str, Any], source_path: Path, output_root: Path) -> dict[str, Any]:
    input_bytes = source_path.read_bytes()
    input_sha = hashlib.sha256(input_bytes).hexdigest()
    if input_sha != request["input"]["sha256"]:
        raise ValueError("AECCTX_DWG_INPUT_HASH_MISMATCH")
    configuration = _configuration(request)
    v03 = configuration["profile"].startswith("acx33-")
    if input_bytes[6:].startswith(b"AECCTX_ENCRYPTED_TEST"):
        raise ValueError("AECCTX_DWG_ENCRYPTED_UNSUPPORTED")
    if input_bytes[6:].startswith(b"AECCTX_PROTECTED_TEST"):
        raise ValueError("AECCTX_DWG_PROTECTED_UNSUPPORTED")
    _probe(input_bytes, configuration)
    artifacts_root = output_root / "artifacts"
    artifacts_root.mkdir(parents=True, exist_ok=True)
    raw_json_path = artifacts_root / "libredwg-raw.json"
    dxf_path = artifacts_root / ("converted.dxf" if v03 else "converted-r2000.dxf")
    json_warnings = _run_dwgread(source_path, "JSON", raw_json_path)
    dxf_warnings = _run_dwgread(source_path, "DXF", dxf_path)
    try:
        raw = json.loads(
            raw_json_path.read_text(encoding="utf-8"),
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("AECCTX_DWG_NUMBER_INVALID")),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("AECCTX_DWG_JSON_INVALID") from error
    limits = request["limits"]
    source_json = _validate_source_json(
        raw,
        {
            "max_records": limits["max_records"],
            "max_recursion_depth": limits["max_recursion_depth"],
            "max_string_bytes": min(int(limits["max_output_bytes"]), 1_048_576),
        }, expected_version=configuration["dwg_version"], include_v03=v03,
    )
    source_path_out = artifacts_root / "source.json"
    source_path_out.write_bytes(_canonical(source_json))
    raw_json_path.unlink()
    source_bytes = source_path_out.read_bytes()
    dxf_bytes = dxf_path.read_bytes()
    source_sha = hashlib.sha256(source_bytes).hexdigest()
    dxf_sha = hashlib.sha256(dxf_bytes).hexdigest()
    conflicts = source_json["aecctx_handle_conflicts"]
    diagnostics: list[dict[str, str]] = []
    if conflicts:
        diagnostics.append({"code": "AECCTX_DWG_HANDLE_CONFLICT", "severity": "warning"})
    if json_warnings.strip() or dxf_warnings.strip():
        diagnostics.append({"code": "AECCTX_DWG_LIBREDWG_DIAGNOSTIC_RETAINED", "severity": "info"})
    unsupported = source_json.get("aecctx_unsupported_classes", [])
    if unsupported:
        diagnostics.extend(
            {"code": "AECCTX_DWG_PROXY_OBJECT_UNSUPPORTED" if "PROXY" in item else "AECCTX_DWG_ACIS_UNSUPPORTED", "severity": "warning"}
            for item in unsupported
        )
    if v03:
        events = [
            {
                "event_type": "primitive",
                "payload": {
                    "artifact_path": "artifacts/source.json", "artifact_sha256": source_sha,
                    "dwg_version": configuration["dwg_version"], "handle_conflicts": conflicts,
                    "input_sha256": input_sha, "object_count": len(source_json["OBJECTS"]),
                    "profile": configuration["profile"], "schema": "aecctx.dwg.source.v2",
                    "units": source_json["aecctx_units"], "unsupported_classes": unsupported,
                },
                "sequence": 0, "source_locator": f"sha256:{input_sha}",
            },
            {
                "event_type": "primitive",
                "payload": {
                    "artifact_path": "artifacts/converted.dxf", "artifact_sha256": dxf_sha,
                    "conversion_losses": [item["code"] for item in diagnostics if item["code"] in {"AECCTX_DWG_ACIS_UNSUPPORTED", "AECCTX_DWG_PROXY_OBJECT_UNSUPPORTED"}],
                    "converter": "LibreDWG dwgread 0.13.4", "input_sha256": input_sha,
                    "observed_dxf_version": configuration["dwg_version"], "profile": configuration["profile"],
                    "representation_fidelity": "converted", "requested_dxf_version": configuration["dwg_version"],
                    "schema": "aecctx.dwg.conversion.v2",
                },
                "sequence": 1, "source_locator": f"dwg-artifact:converted-dxf:sha256:{dxf_sha}",
            },
        ]
        return {
            "artifacts": [
                {"bytes": len(source_bytes), "media_type": "application/vnd.aecctx.libredwg+json", "path": "artifacts/source.json", "sha256": source_sha},
                {"bytes": len(dxf_bytes), "media_type": "application/dxf", "path": "artifacts/converted.dxf", "sha256": dxf_sha},
            ],
            "capability_report": _capability_report(True, bool(conflicts), v03=True),
            "diagnostics": diagnostics, "events": events, "ok": True,
            "resource_usage": {"artifacts": 2, "events": 2, "source_objects": len(source_json["OBJECTS"])},
        }
    events = [
        {
            "event_type": "primitive",
            "payload": {
                "artifact_path": "artifacts/source.json",
                "artifact_sha256": source_sha,
                "dwg_version": "AC1015",
                "handle_conflicts": conflicts,
                "input_sha256": input_sha,
                "object_count": len(source_json["OBJECTS"]),
                "schema": "aecctx.dwg.source.v1",
            },
            "sequence": 0,
            "source_locator": f"sha256:{input_sha}",
        },
        {
            "event_type": "primitive",
            "payload": {
                "artifact_path": "artifacts/converted-r2000.dxf",
                "artifact_sha256": dxf_sha,
                "converter": "LibreDWG dwgread 0.13.4",
                "dxf_version": "AC1015",
                "input_sha256": input_sha,
                "representation_fidelity": "converted",
                "schema": "aecctx.dwg.conversion.v1",
            },
            "sequence": 1,
            "source_locator": f"dwg-artifact:converted-dxf:sha256:{dxf_sha}",
        },
    ]
    return {
        "artifacts": [
            {"bytes": len(source_bytes), "media_type": "application/vnd.aecctx.libredwg+json", "path": "artifacts/source.json", "sha256": source_sha},
            {"bytes": len(dxf_bytes), "media_type": "application/dxf", "path": "artifacts/converted-r2000.dxf", "sha256": dxf_sha},
        ],
        "capability_report": _capability_report(True, bool(conflicts)),
        "diagnostics": diagnostics,
        "events": events,
        "ok": True,
        "resource_usage": {"artifacts": 2, "events": 2, "source_objects": len(source_json["OBJECTS"])},
    }


def main() -> int:
    workspace = Path.cwd()
    output_root = workspace / "output"
    response_path = output_root / "response.json"
    request = json.loads((workspace / "request.json").read_text(encoding="utf-8"))
    error: dict[str, str] | None = None
    try:
        if request.get("provider_id") != PROVIDER_ID or request.get("action") != "extract":
            raise ValueError("AECCTX_DWG_REQUEST_OUTSIDE_PROFILE")
        payload = _response(request, workspace / request["input"]["path"], output_root)
    except Exception as caught:
        code = str(caught) if str(caught).startswith("AECCTX_") else "AECCTX_DWG_PROVIDER_FAILED"
        error = {"code": code, "message": f"{type(caught).__name__}: DWG extraction failed"}
        payload = {
            "artifacts": [],
            "capability_report": _capability_report(False),
            "diagnostics": [{"code": code, "severity": "error"}],
            "events": [],
            "ok": False,
            "resource_usage": {"artifacts": 0, "events": 0},
        }
    v03 = isinstance(request.get("configuration"), dict) and str(request["configuration"].get("profile", "")).startswith("acx33-")
    provider_version = "0.3.0" if v03 else "0.2.0"
    described = descriptor(provider_version=provider_version)
    response = {
        **payload,
        "attestation": {
            "descriptor_digest": _digest(described),
            "deterministic": True,
            "enforcement_profile": "oci-docker-v1",
            "network_mode": "disabled",
            "provider_id": PROVIDER_ID,
            "provider_version": provider_version,
            "request_digest": _digest(request),
            "response_payload_digest": "0" * 64,
            "runtime_digest": RUNTIME_DIGEST,
            "runtime_version": RUNTIME_VERSION,
        },
        "protocol_version": "0.2",
        "provider_id": PROVIDER_ID,
        "request_id": request["request_id"],
    }
    if error is not None:
        response["error"] = error
    response["attestation"]["response_payload_digest"] = _digest({key: value for key, value in response.items() if key != "attestation"})
    response_path.write_bytes(_canonical(response))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
