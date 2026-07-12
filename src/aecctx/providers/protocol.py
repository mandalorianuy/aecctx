from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from jsonschema import Draft202012Validator

from .models import ProviderDescriptor, ProviderExecutionError, ProviderLimits


PROVIDER_ACTIONS = {"describe", "probe", "extract", "finalize", "render"}
HOST_PATH_PATTERN = re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\\\)")
UNSAFE_CONFIGURATION_KEYS = {"argv", "callback", "command", "environment", "import_path", "output_path", "shell"}


@dataclass(frozen=True, slots=True)
class ProviderResult:
    ok: bool
    events: tuple[Mapping[str, Any], ...]
    artifacts: tuple[Mapping[str, Any], ...]
    artifact_bytes: Mapping[str, bytes]
    diagnostics: tuple[Mapping[str, Any], ...]
    capability_report: Mapping[str, Mapping[str, Any]]
    resource_usage: Mapping[str, Any]
    attestation: Mapping[str, Any]
    error: Mapping[str, Any] | None = None


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise ProviderExecutionError("AECCTX_PROVIDER_PROTOCOL_INVALID", f"Value is not canonical JSON: {error}") from error


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _load_schema(name: str) -> dict[str, Any]:
    resource = files("aecctx.schemas.v0_2").joinpath(name)
    return json.loads(resource.read_text(encoding="utf-8"))


def _validate_schema(value: Any, name: str) -> None:
    errors = sorted(Draft202012Validator(_load_schema(name)).iter_errors(value), key=lambda error: list(error.absolute_path))
    if errors:
        first = errors[0]
        location = "/".join(str(item) for item in first.absolute_path)
        raise ProviderExecutionError(
            "AECCTX_PROVIDER_PROTOCOL_INVALID",
            f"{name} invalid at {location or '<root>'}: {first.message}",
        )


def build_provider_request(
    provider_id: str,
    action: str,
    input_bytes: bytes,
    *,
    limits: ProviderLimits | None = None,
    configuration: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    policy = limits or ProviderLimits()
    if len(input_bytes) > policy.max_input_bytes:
        raise ProviderExecutionError("AECCTX_PROVIDER_INPUT_LIMIT_EXCEEDED", "Provider input exceeds configured byte limit")
    if action not in PROVIDER_ACTIONS:
        raise ProviderExecutionError("AECCTX_PROVIDER_ACTION_UNSUPPORTED", f"Unsupported provider action: {action}")
    configured = dict(configuration or {})
    _validate_configuration(configured, policy.max_recursion_depth)
    if len(_canonical(configured)) > policy.max_input_bytes:
        raise ProviderExecutionError("AECCTX_PROVIDER_INPUT_LIMIT_EXCEEDED", "Provider configuration exceeds configured byte limit")
    input_digest = hashlib.sha256(input_bytes).hexdigest()
    request: dict[str, Any] = {
        "action": action,
        "configuration": configured,
        "configuration_digest": _sha256(configured),
        "input": {"bytes": len(input_bytes), "path": f"input/{input_digest}", "sha256": input_digest},
        "limits": policy.to_dict(),
        "protocol_version": "0.2",
        "provider_id": provider_id,
    }
    request["request_id"] = _sha256(request)
    _validate_schema(request, "provider-request.schema.json")
    return request


def _validate_configuration(value: Any, max_depth: int, *, depth: int = 1) -> None:
    if depth > max_depth:
        raise ProviderExecutionError("AECCTX_PROVIDER_RECURSION_LIMIT_EXCEEDED", "Provider configuration exceeds recursion limit")
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or key in UNSAFE_CONFIGURATION_KEYS:
                raise ProviderExecutionError("AECCTX_PROVIDER_CONFIGURATION_UNSAFE", f"Unsafe provider configuration key: {key!r}")
            _validate_configuration(item, max_depth, depth=depth + 1)
        return
    if isinstance(value, list):
        for item in value:
            _validate_configuration(item, max_depth, depth=depth + 1)
        return
    if isinstance(value, str) and (value.startswith(("/", "\\")) or HOST_PATH_PATTERN.search(value)):
        raise ProviderExecutionError("AECCTX_PROVIDER_CONFIGURATION_UNSAFE", "Provider configuration contains a host path")


def provider_descriptor_digest(descriptor: ProviderDescriptor) -> str:
    return _sha256(descriptor.to_dict())


def provider_response_payload_digest(response: Mapping[str, Any]) -> str:
    payload = {key: value for key, value in response.items() if key != "attestation"}
    return _sha256(payload)


def _safe_artifact_path(value: str) -> PurePosixPath:
    if "\\" in value or "\x00" in value:
        raise ProviderExecutionError("AECCTX_PROVIDER_ARTIFACT_PATH_UNSAFE", f"Unsafe provider artifact path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or path.parts[0] != "artifacts" or any(part in {"", ".", ".."} for part in path.parts):
        raise ProviderExecutionError("AECCTX_PROVIDER_ARTIFACT_PATH_UNSAFE", f"Unsafe provider artifact path: {value!r}")
    return path


def _contains_host_path(value: Any, workspace: Path) -> bool:
    if isinstance(value, str):
        return str(workspace) in value or HOST_PATH_PATTERN.search(value) is not None
    if isinstance(value, Mapping):
        return any(_contains_host_path(key, workspace) or _contains_host_path(item, workspace) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains_host_path(item, workspace) for item in value)
    return False


def validate_provider_response(
    response: Mapping[str, Any],
    request: Mapping[str, Any],
    descriptor: ProviderDescriptor,
    output_root: str | Path,
    *,
    limits: ProviderLimits | None = None,
) -> ProviderResult:
    policy = limits or ProviderLimits()
    response_copy = deepcopy(dict(response))
    _validate_schema(response_copy, "provider-response.schema.json")
    if response_copy.get("request_id") != request.get("request_id") or response_copy.get("provider_id") != descriptor.provider_id:
        raise ProviderExecutionError("AECCTX_PROVIDER_RESPONSE_MISMATCH", "Provider response does not match request or descriptor")
    workspace = Path(output_root).resolve()
    if _contains_host_path(response_copy, workspace):
        raise ProviderExecutionError("AECCTX_PROVIDER_HOST_PATH_LEAKED", "Provider response contains a host filesystem path")
    attestation = response_copy["attestation"]
    expected_attestation = {
        "descriptor_digest": provider_descriptor_digest(descriptor),
        "deterministic": descriptor.deterministic,
        "enforcement_profile": descriptor.enforcement_profile,
        "network_mode": descriptor.network_mode,
        "provider_id": descriptor.provider_id,
        "provider_version": descriptor.provider_version,
        "request_digest": _sha256(request),
        "runtime_version": descriptor.runtime_version,
        "runtime_digest": descriptor.runtime_digest,
    }
    for field, expected in expected_attestation.items():
        if attestation.get(field) != expected:
            raise ProviderExecutionError("AECCTX_PROVIDER_ATTESTATION_MISMATCH", f"Provider attestation mismatch: {field}")
    if attestation.get("response_payload_digest") != provider_response_payload_digest(response_copy):
        raise ProviderExecutionError("AECCTX_PROVIDER_RESPONSE_DIGEST_MISMATCH", "Provider response payload digest is invalid")

    events = response_copy["events"]
    if len(events) > policy.max_records:
        raise ProviderExecutionError("AECCTX_PROVIDER_RECORD_LIMIT_EXCEEDED", "Provider event count exceeds configured limit")
    if [event["sequence"] for event in events] != list(range(len(events))):
        raise ProviderExecutionError("AECCTX_PROVIDER_EVENT_SEQUENCE_INVALID", "Provider events must be bounded and strictly sequential")
    capability_report = response_copy["capability_report"]
    for capability, entry in capability_report.items():
        if entry["support_level"] != "full" and (not entry["reason_codes"] or not entry["fallback"]):
            raise ProviderExecutionError(
                "AECCTX_PROVIDER_CAPABILITY_REPORT_INVALID",
                f"Non-full capability requires reasons and fallback: {capability}",
            )

    artifacts = response_copy["artifacts"]
    if len(artifacts) > policy.max_files:
        raise ProviderExecutionError("AECCTX_PROVIDER_FILE_LIMIT_EXCEEDED", "Provider artifact count exceeds configured limit")
    total_bytes = 0
    seen_paths: set[str] = set()
    captured_artifacts: dict[str, bytes] = {}
    for artifact in artifacts:
        logical_path = _safe_artifact_path(artifact["path"]).as_posix()
        if logical_path in seen_paths:
            raise ProviderExecutionError("AECCTX_PROVIDER_ARTIFACT_PATH_DUPLICATE", f"Duplicate provider artifact: {logical_path}")
        seen_paths.add(logical_path)
        path = workspace.joinpath(*PurePosixPath(logical_path).parts)
        if path.is_symlink():
            raise ProviderExecutionError("AECCTX_PROVIDER_ARTIFACT_PATH_UNSAFE", f"Provider artifact symlink is forbidden: {logical_path}")
        if not path.is_file():
            raise ProviderExecutionError("AECCTX_PROVIDER_ARTIFACT_MISSING", f"Provider artifact is missing: {logical_path}")
        data = path.read_bytes()
        total_bytes += len(data)
        if total_bytes > policy.max_output_bytes:
            raise ProviderExecutionError("AECCTX_PROVIDER_OUTPUT_LIMIT_EXCEEDED", "Provider artifacts exceed configured byte limit")
        if artifact["bytes"] != len(data):
            raise ProviderExecutionError("AECCTX_PROVIDER_ARTIFACT_SIZE_MISMATCH", f"Provider artifact size mismatch: {logical_path}")
        if artifact["sha256"] != hashlib.sha256(data).hexdigest():
            raise ProviderExecutionError("AECCTX_PROVIDER_ARTIFACT_HASH_MISMATCH", f"Provider artifact hash mismatch: {logical_path}")
        captured_artifacts[logical_path] = data

    return ProviderResult(
        ok=bool(response_copy["ok"]),
        events=tuple(events),
        artifacts=tuple(artifacts),
        artifact_bytes=captured_artifacts,
        diagnostics=tuple(response_copy["diagnostics"]),
        capability_report=capability_report,
        resource_usage=response_copy["resource_usage"],
        attestation=attestation,
        error=response_copy.get("error"),
    )
