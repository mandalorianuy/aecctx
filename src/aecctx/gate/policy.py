from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import unicodedata
from datetime import datetime, timezone
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from .models import (
    GATE_PROFILE,
    GateCheckPolicy,
    GateError,
    GateLimits,
    GatePolicy,
    GateWaiver,
)


GATE_SCHEMA_NAMES = frozenset(
    {
        "gate-check.schema.json",
        "gate-waiver.schema.json",
        "gate-policy.schema.json",
        "gate-result.schema.json",
    }
)
_MAX_JSON_DEPTH = 32
_SEMVER = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
_UTC_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z")


class _DuplicateJSONName(ValueError):
    pass


class _NormalizedJSONNameCollision(ValueError):
    pass


class _NonFiniteJSONNumber(ValueError):
    pass


def _normalize_nfc(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize_nfc(item) for item in value]
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            normalized_key = unicodedata.normalize("NFC", key)
            if normalized_key in normalized:
                raise _NormalizedJSONNameCollision(normalized_key)
            normalized[normalized_key] = _normalize_nfc(item)
        return normalized
    if isinstance(value, float) and not math.isfinite(value):
        raise _NonFiniteJSONNumber
    if value is None or isinstance(value, (bool, int, float)):
        return value
    raise TypeError("value is not representable as JSON")


def _object_from_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    raw_names: set[str] = set()
    normalized: dict[str, Any] = {}
    for raw_key, value in pairs:
        if raw_key in raw_names:
            raise _DuplicateJSONName(raw_key)
        raw_names.add(raw_key)
        key = unicodedata.normalize("NFC", raw_key)
        if key in normalized:
            raise _NormalizedJSONNameCollision(key)
        normalized[key] = _normalize_nfc(value)
    return normalized


def _reject_constant(_value: str) -> None:
    raise _NonFiniteJSONNumber


def _parse_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise _NonFiniteJSONNumber
    return parsed


def _json_depth(value: Any) -> int:
    if isinstance(value, dict):
        return 1 + max((_json_depth(item) for item in value.values()), default=0)
    if isinstance(value, list):
        return 1 + max((_json_depth(item) for item in value), default=0)
    return 0


def _strict_json(data: bytes) -> Any:
    if not isinstance(data, bytes):
        raise GateError("AECCTX_GATE_INPUT_TYPE_INVALID", "policy input must be bytes")
    try:
        text = data.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_object_from_pairs,
            parse_constant=_reject_constant,
            parse_float=_parse_float,
        )
        value = _normalize_nfc(value)
    except _DuplicateJSONName as error:
        raise GateError("AECCTX_GATE_JSON_DUPLICATE_KEY", "policy contains a duplicate JSON name") from error
    except _NormalizedJSONNameCollision as error:
        raise GateError(
            "AECCTX_GATE_JSON_NORMALIZATION_COLLISION",
            "policy contains JSON names that collide after NFC normalization",
        ) from error
    except _NonFiniteJSONNumber as error:
        raise GateError("AECCTX_GATE_JSON_NONFINITE", "policy contains a non-finite JSON number") from error
    except RecursionError as error:
        raise GateError("AECCTX_GATE_JSON_DEPTH_EXCEEDED", "policy exceeds the JSON depth limit") from error
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise GateError("AECCTX_GATE_JSON_INVALID", "policy is not valid strict UTF-8 JSON") from error
    try:
        depth = _json_depth(value)
    except RecursionError as error:
        raise GateError("AECCTX_GATE_JSON_DEPTH_EXCEEDED", "policy exceeds the JSON depth limit") from error
    if depth > _MAX_JSON_DEPTH:
        raise GateError("AECCTX_GATE_JSON_DEPTH_EXCEEDED", "policy exceeds the JSON depth limit")
    return value


def canonical_gate_json(value: Any) -> bytes:
    try:
        normalized = _normalize_nfc(value)
        if _json_depth(normalized) > _MAX_JSON_DEPTH:
            raise GateError("AECCTX_GATE_JSON_DEPTH_EXCEEDED", "value exceeds the JSON depth limit")
        encoded = json.dumps(
            normalized,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except GateError:
        raise
    except _NormalizedJSONNameCollision as error:
        raise GateError(
            "AECCTX_GATE_JSON_NORMALIZATION_COLLISION",
            "value contains JSON names that collide after NFC normalization",
        ) from error
    except _NonFiniteJSONNumber as error:
        raise GateError("AECCTX_GATE_JSON_NONFINITE", "value contains a non-finite number") from error
    except RecursionError as error:
        raise GateError("AECCTX_GATE_JSON_DEPTH_EXCEEDED", "value exceeds the JSON depth limit") from error
    except (TypeError, ValueError) as error:
        if isinstance(error, ValueError) and "Out of range float" in str(error):
            raise GateError("AECCTX_GATE_JSON_NONFINITE", "value contains a non-finite number") from error
        raise GateError("AECCTX_GATE_JSON_INVALID", "value cannot be represented as canonical JSON") from error
    return encoded + b"\n"


@lru_cache(maxsize=1)
def _schema_registry() -> tuple[dict[str, Any], Registry[Any]]:
    schemas: dict[str, Any] = {}
    resources: list[tuple[str, Resource[Any]]] = []
    packaged = files("aecctx.schemas.v0_2")
    for schema_name in sorted(GATE_SCHEMA_NAMES):
        schema = json.loads(packaged.joinpath(schema_name).read_text(encoding="utf-8"))
        schemas[schema_name] = schema
        resources.append((schema["$id"], Resource.from_contents(schema)))
    return schemas, Registry().with_resources(resources)


def validate_gate_document(value: Any, schema_name: str) -> None:
    if schema_name not in GATE_SCHEMA_NAMES:
        raise GateError("AECCTX_GATE_SCHEMA_UNSUPPORTED", "gate schema name is not allowlisted")
    schemas, registry = _schema_registry()
    validator = Draft202012Validator(
        schemas[schema_name],
        registry=registry,
        format_checker=FormatChecker(),
    )
    errors = sorted(validator.iter_errors(value), key=lambda item: [str(part) for part in item.absolute_path])
    if errors:
        location = "/".join(str(part) for part in errors[0].absolute_path) or "$"
        raise GateError("AECCTX_GATE_SCHEMA_INVALID", f"{schema_name} failed validation at {location}")


def _validate_maximum(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise GateError("AECCTX_GATE_LIMIT_INVALID", f"{name} must be a positive integer")
    return value


def read_gate_document(path: str | Path, *, maximum_bytes: int, label: str) -> bytes:
    maximum = _validate_maximum(maximum_bytes, name="maximum_bytes")
    if not isinstance(label, str) or not label:
        raise GateError("AECCTX_GATE_INPUT_TYPE_INVALID", "input label must be a non-empty string")
    try:
        candidate = Path(path)
        initial = candidate.lstat()
    except (OSError, TypeError, ValueError) as error:
        raise GateError("AECCTX_GATE_INPUT_UNREADABLE", f"{label} cannot be read safely") from error
    if not stat.S_ISREG(initial.st_mode):
        raise GateError("AECCTX_GATE_INPUT_TYPE_INVALID", f"{label} must be a regular non-symlink file")
    if initial.st_size > maximum:
        raise GateError("AECCTX_GATE_INPUT_LIMIT_EXCEEDED", f"{label} exceeds its byte limit")

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(candidate, flags)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_dev != initial.st_dev
            or opened.st_ino != initial.st_ino
        ):
            raise GateError("AECCTX_GATE_INPUT_TYPE_INVALID", f"{label} changed or is not a regular file")
        chunks: list[bytes] = []
        remaining = maximum + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
    except GateError:
        raise
    except OSError as error:
        raise GateError("AECCTX_GATE_INPUT_UNREADABLE", f"{label} cannot be read safely") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if len(data) > maximum:
        raise GateError("AECCTX_GATE_INPUT_LIMIT_EXCEEDED", f"{label} exceeds its byte limit")
    return data


def _validate_limits(limits: GateLimits) -> GateLimits:
    if not isinstance(limits, GateLimits):
        raise GateError("AECCTX_GATE_LIMIT_INVALID", "limits must be GateLimits")
    hard = GateLimits()
    for field in hard.__dataclass_fields__:
        if getattr(limits, field) > getattr(hard, field):
            raise GateError("AECCTX_GATE_LIMIT_INVALID", f"{field} exceeds the v1 hard maximum")
    return limits


def _parse_utc(value: str, *, code: str, label: str) -> datetime:
    if _UTC_INSTANT.fullmatch(value) is None:
        raise GateError(code, f"{label} must be an RFC3339 UTC Z instant")
    try:
        instant = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise GateError(code, f"{label} must be an RFC3339 UTC Z instant") from error
    if instant.tzinfo != timezone.utc:
        raise GateError(code, f"{label} must be an RFC3339 UTC Z instant")
    return instant


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze_json(item)) for key, item in value.items()))
    if isinstance(value, list):
        return tuple(_freeze_json(item) for item in value)
    return value


def _validate_policy_semantics(value: Any, limits: GateLimits) -> None:
    if not isinstance(value, dict):
        raise GateError("AECCTX_GATE_POLICY_INVALID", "policy root must be an object")

    profile = value.get("profile")
    if isinstance(profile, str) and profile != GATE_PROFILE:
        raise GateError("AECCTX_GATE_PROFILE_UNSUPPORTED", "policy profile is unsupported")
    version = value.get("policy_version")
    if isinstance(version, str) and _SEMVER.fullmatch(version) is None:
        raise GateError("AECCTX_GATE_POLICY_VERSION_INVALID", "policy_version must be semantic versioning")
    evaluation_time = value.get("evaluation_time")
    if isinstance(evaluation_time, str):
        _parse_utc(
            evaluation_time,
            code="AECCTX_GATE_EVALUATION_TIME_INVALID",
            label="evaluation_time",
        )

    checks = value.get("checks")
    if isinstance(checks, list):
        if len(checks) > limits.max_checks:
            raise GateError("AECCTX_GATE_CHECK_LIMIT_EXCEEDED", "policy exceeds its check limit")
        check_ids = [item.get("check_id") for item in checks if isinstance(item, dict)]
        string_check_ids = [item for item in check_ids if isinstance(item, str)]
        if len(string_check_ids) != len(set(string_check_ids)):
            raise GateError("AECCTX_GATE_CHECK_ID_DUPLICATE", "policy contains a duplicate check_id")
        if any(item.startswith("aecctx.system.") for item in string_check_ids):
            raise GateError("AECCTX_GATE_CHECK_ID_RESERVED", "policy check_id uses the reserved system namespace")
    else:
        string_check_ids = []

    waivers = value.get("waivers")
    if isinstance(waivers, list):
        if len(waivers) > limits.max_waivers:
            raise GateError("AECCTX_GATE_WAIVER_LIMIT_EXCEEDED", "policy exceeds its waiver limit")
        waiver_ids = [item.get("waiver_id") for item in waivers if isinstance(item, dict)]
        string_waiver_ids = [item for item in waiver_ids if isinstance(item, str)]
        if len(string_waiver_ids) != len(set(string_waiver_ids)):
            raise GateError("AECCTX_GATE_WAIVER_ID_DUPLICATE", "policy contains a duplicate waiver_id")
        declared_targets = {f"aecctx.policy.{item}" for item in string_check_ids}
        for waiver in waivers:
            if not isinstance(waiver, dict):
                continue
            target = waiver.get("check_id")
            if isinstance(target, str) and target not in declared_targets:
                raise GateError("AECCTX_GATE_WAIVER_TARGET_INVALID", "waiver target is not a declared policy check")
            issued_at = waiver.get("issued_at")
            expires_at = waiver.get("expires_at")
            if isinstance(issued_at, str) and isinstance(expires_at, str):
                issued = _parse_utc(
                    issued_at,
                    code="AECCTX_GATE_WAIVER_INTERVAL_INVALID",
                    label="waiver issued_at",
                )
                expires = _parse_utc(
                    expires_at,
                    code="AECCTX_GATE_WAIVER_INTERVAL_INVALID",
                    label="waiver expires_at",
                )
                if issued >= expires:
                    raise GateError("AECCTX_GATE_WAIVER_INTERVAL_INVALID", "waiver interval must be increasing")


def load_gate_policy(data: bytes, *, limits: GateLimits = GateLimits()) -> GatePolicy:
    active_limits = _validate_limits(limits)
    if not isinstance(data, bytes):
        raise GateError("AECCTX_GATE_INPUT_TYPE_INVALID", "policy input must be bytes")
    if len(data) > active_limits.max_policy_bytes:
        raise GateError("AECCTX_GATE_INPUT_LIMIT_EXCEEDED", "policy exceeds its byte limit")

    value = _strict_json(data)
    _validate_policy_semantics(value, active_limits)
    validate_gate_document(value, "gate-policy.schema.json")
    canonical_bytes = canonical_gate_json(value)

    try:
        checks = tuple(
            GateCheckPolicy(
                check_id=item["check_id"],
                kind=item["kind"],
                severity=item["severity"],
                failure_mode=item["failure_mode"],
                configuration=_freeze_json(item["configuration"]),
            )
            for item in value["checks"]
        )
        waivers = tuple(
            GateWaiver(
                waiver_id=item["waiver_id"],
                check_id=item["check_id"],
                finding_fingerprint=item["finding_fingerprint"],
                reason=item["reason"],
                approved_by=item["approved_by"],
                issued_at=item["issued_at"],
                expires_at=item["expires_at"],
            )
            for item in value["waivers"]
        )
        return GatePolicy(
            profile=value["profile"],
            policy_id=value["policy_id"],
            policy_version=value["policy_version"],
            evaluation_time=value["evaluation_time"],
            checks=checks,
            waivers=waivers,
            digest=hashlib.sha256(canonical_bytes).hexdigest(),
            canonical_bytes=canonical_bytes,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise GateError("AECCTX_GATE_POLICY_INVALID", "validated policy could not be materialized") from error
