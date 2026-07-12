from __future__ import annotations

import hashlib
import json
import socket
import time
from pathlib import Path
from typing import Any

PROVIDER_ID = "org.aecctx.reference-provider"
REQUIRED_AXES = (
    "cpu", "decompression", "environment", "filesystem", "input_bytes", "memory", "network", "open_files",
    "output_bytes", "process", "process_tree", "records", "recursion", "temporary_storage", "user_permissions", "wall_time",
)


def _descriptor() -> dict[str, Any]:
    return {
        "actions": ["describe", "extract", "finalize"],
        "deterministic": True,
        "distribution": "bundled-reference",
        "enforced_axes": {axis: True for axis in REQUIRED_AXES},
        "enforcement_profile": "oci-docker-v1",
        "formats": ["application/x-aecctx-provider-fixture"],
        "license_spdx": "Apache-2.0",
        "network_mode": "disabled",
        "platforms": ["linux-container"],
        "protocol_version": "0.2",
        "provider_id": PROVIDER_ID,
        "provider_version": "0.2.0",
        "runtime_version": "python-3.12",
        "runtime_digest": "sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df",
    }


def _capability_report() -> dict[str, dict[str, Any]]:
    names = ("identity", "hierarchy", "properties", "relationships", "text", "2d_geometry", "3d_geometry", "materials_styles", "georeferencing", "validation")
    return {
        name: (
            {"affected": [], "fallback": "none", "reason_codes": [], "support_level": "full"}
            if name in {"identity", "validation"}
            else {
                "affected": ["reference-fixture"],
                "fallback": "retain opaque evidence",
                "reason_codes": ["AECCTX_REFERENCE_PROVIDER_CAPABILITY_UNSUPPORTED"],
                "support_level": "unsupported",
            }
        )
        for name in names
    }


def _request_digest(request: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _descriptor_digest(descriptor: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(descriptor, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _response_payload_digest(response: dict[str, Any]) -> str:
    payload = {key: value for key, value in response.items() if key != "attestation"}
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    workspace = Path.cwd()
    output_root = workspace / "output"
    response_path = output_root / "response.json"
    request = json.loads((workspace / "request.json").read_text(encoding="utf-8"))
    descriptor = _descriptor()
    configuration = request.get("configuration", {})
    ok = True
    error: dict[str, str] | None = None
    diagnostics: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    try:
        input_path = workspace / request["input"]["path"]
        data = input_path.read_bytes()
        if hashlib.sha256(data).hexdigest() != request["input"]["sha256"]:
            raise ValueError("AECCTX_REFERENCE_INPUT_HASH_MISMATCH")
        if configuration.get("sleep_seconds"):
            time.sleep(float(configuration["sleep_seconds"]))
        if configuration.get("network_attempt"):
            socket.create_connection(("127.0.0.1", 9), timeout=0.1)
        if configuration.get("outside_write"):
            Path("/aecctx-provider-escape").write_text("escape", encoding="utf-8")
        allocated = None
        if configuration.get("allocate_bytes"):
            allocated = bytearray(int(configuration["allocate_bytes"]))
        artifact_data = data
        artifact_path = output_root / "artifacts" / "echo.bin"
        artifact_path.write_bytes(artifact_data)
        artifact_hash = hashlib.sha256(artifact_data).hexdigest()
        artifacts.append(
            {
                "bytes": len(artifact_data),
                "media_type": "application/octet-stream",
                "path": "artifacts/echo.bin",
                "sha256": "f" * 64 if configuration.get("forge_hash") else artifact_hash,
            }
        )
        events.append(
            {
                "event_type": "diagnostic",
                "payload": {"message": "/Users/private/source" if configuration.get("host_path_leak") else "reference-provider"},
                "sequence": 0,
                "source_locator": f"sha256:{request['input']['sha256']}",
            }
        )
        if configuration.get("duplicate_sequence"):
            events.append(dict(events[0]))
    except (PermissionError, OSError) as caught:
        ok = False
        code = "AECCTX_PROVIDER_NETWORK_DENIED" if configuration.get("network_attempt") else "AECCTX_PROVIDER_FILESYSTEM_DENIED"
        error = {"code": code, "message": f"{type(caught).__name__}: operation denied by sandbox"}
        diagnostics.append({"code": code, "severity": "error"})
    except Exception as caught:
        ok = False
        error = {"code": "AECCTX_REFERENCE_PROVIDER_FAILED", "message": f"{type(caught).__name__}: {caught}"}
        diagnostics.append({"code": "AECCTX_REFERENCE_PROVIDER_FAILED", "severity": "error"})
    response: dict[str, Any] = {
        "artifacts": artifacts,
        "attestation": {
            "descriptor_digest": _descriptor_digest(descriptor),
            "deterministic": descriptor["deterministic"],
            "enforcement_profile": descriptor["enforcement_profile"],
            "network_mode": descriptor["network_mode"],
            "provider_id": descriptor["provider_id"],
            "provider_version": descriptor["provider_version"],
            "request_digest": _request_digest(request),
            "response_payload_digest": "0" * 64,
            "runtime_version": descriptor["runtime_version"],
            "runtime_digest": descriptor["runtime_digest"],
        },
        "capability_report": _capability_report(),
        "diagnostics": diagnostics,
        "events": events,
        "ok": ok,
        "protocol_version": "0.2",
        "provider_id": descriptor["provider_id"],
        "request_id": request["request_id"],
        "resource_usage": {"artifacts": len(artifacts), "events": len(events)},
    }
    if error is not None:
        response["error"] = error
    response["attestation"]["response_payload_digest"] = _response_payload_digest(response)
    response_path.write_text(json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
