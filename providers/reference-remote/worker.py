#!/usr/bin/env python3
"""Apache-2.0 deterministic reference implementation for remote protocol fixtures."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from aecctx.providers import (
    ProviderDescriptor,
    ProviderLimits,
    REQUIRED_ENFORCEMENT_AXES,
    RemoteProviderPolicy,
    build_provider_request,
    build_remote_request_envelope,
    canonical_json_bytes,
    canonical_sha256,
    provider_descriptor_digest,
    provider_response_payload_digest,
)


DESCRIPTOR = {
    "actions": ["extract"],
    "deterministic": True,
    "distribution": "source-reference-only",
    "enforced_axes": {axis: True for axis in sorted(REQUIRED_ENFORCEMENT_AXES)},
    "enforcement_profile": "remote-https-spki-v1",
    "formats": ["application/x-aecctx-provider-fixture"],
    "license_spdx": "Apache-2.0",
    "network_mode": "allowlisted",
    "platforms": ["remote"],
    "protocol_version": "0.2",
    "provider_id": "org.aecctx.reference-remote",
    "provider_version": "0.3.0",
    "runtime_digest": "sha256:" + "3" * 64,
    "runtime_version": "python-3.12",
}


def build_response(request_body: bytes, *, region: str = "test-region") -> dict[str, Any]:
    envelope = json.loads(request_body)
    request = envelope["request"]
    source = base64.b64decode(envelope["input"]["data"], validate=True)
    descriptor = ProviderDescriptor.from_dict(DESCRIPTOR)
    artifact = source
    response: dict[str, Any] = {
        "artifacts": [{
            "bytes": len(artifact),
            "media_type": "application/octet-stream",
            "path": "artifacts/echo.bin",
            "sha256": hashlib.sha256(artifact).hexdigest(),
        }],
        "attestation": {
            "descriptor_digest": provider_descriptor_digest(descriptor),
            "deterministic": True,
            "enforcement_profile": "remote-https-spki-v1",
            "network_mode": "allowlisted",
            "provider_id": descriptor.provider_id,
            "provider_version": descriptor.provider_version,
            "request_digest": canonical_sha256(request),
            "response_payload_digest": "0" * 64,
            "runtime_version": descriptor.runtime_version,
            "runtime_digest": descriptor.runtime_digest,
        },
        "capability_report": {
            "identity": {"affected": [], "fallback": "none", "reason_codes": [], "support_level": "full"},
            "semantics": {
                "affected": ["reference-fixture"],
                "fallback": "retain opaque evidence",
                "reason_codes": ["AECCTX_REFERENCE_REMOTE_SEMANTICS_UNSUPPORTED"],
                "support_level": "unsupported",
            },
        },
        "diagnostics": [],
        "events": [{
            "event_type": "artifact",
            "payload": {"sha256": hashlib.sha256(artifact).hexdigest()},
            "sequence": 0,
            "source_locator": "sha256:" + hashlib.sha256(source).hexdigest(),
        }],
        "ok": True,
        "protocol_version": "0.2",
        "provider_id": descriptor.provider_id,
        "request_id": request["request_id"],
        "resource_usage": {"artifacts": 1, "output_bytes": len(artifact)},
    }
    response["attestation"]["response_payload_digest"] = provider_response_payload_digest(response)
    return {
        "artifacts": {"artifacts/echo.bin": base64.b64encode(artifact).decode("ascii")},
        "protocol_version": "0.3-remote",
        "provider_id": descriptor.provider_id,
        "provider_version": descriptor.provider_version,
        "region": region,
        "request_digest": hashlib.sha256(request_body).hexdigest(),
        "response": response,
        "retention_seconds": 0,
        "telemetry": False,
    }


def generate(root: Path) -> None:
    source = b"AECCTX remote reference fixture\n"
    policy = RemoteProviderPolicy.from_dict({
        "allowed_regions": ["test-region"],
        "billing_consent": True,
        "endpoint_origin": "https://127.0.0.1:4433",
        "endpoint_spki_sha256": "1" * 64,
        "expected_region": "test-region",
        "max_attempts": 2,
        "max_request_bytes": 16384,
        "max_response_bytes": 32768,
        "retention_max_seconds": 0,
        "retry_delay_seconds": 0,
        "telemetry_consent": False,
        "timeout_seconds": 2,
        "upload_consent": True,
    })
    descriptor = ProviderDescriptor.from_dict(DESCRIPTOR)
    request = build_provider_request(
        descriptor.provider_id,
        "extract",
        source,
        limits=ProviderLimits(max_input_bytes=1024, max_output_bytes=4096, max_records=10, max_files=4),
    )
    request_body = build_remote_request_envelope(request, policy, source)
    response = build_response(request_body)
    root.mkdir(parents=True, exist_ok=True)
    documents: Mapping[str, Any] = {
        "descriptor.json": DESCRIPTOR,
        "policy.json": policy.to_dict(),
        "request-envelope.json": json.loads(request_body),
        "response-envelope.json": response,
    }
    for name, value in documents.items():
        root.joinpath(name).write_bytes(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    root.joinpath("source.bin").write_bytes(source)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate-fixtures", type=Path)
    args = parser.parse_args()
    if args.generate_fixtures is None:
        raise SystemExit("--generate-fixtures is required")
    generate(args.generate_fixtures)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
