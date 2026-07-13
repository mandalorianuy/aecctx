from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pytest

from aecctx.gate import (
    GateError,
    GateLimits,
    canonical_gate_json,
    load_gate_policy,
    read_gate_document,
    validate_gate_document,
)


SHA256 = "0" * 64


def _capability_check(check_id: str = "capabilities") -> dict[str, Any]:
    return {
        "check_id": check_id,
        "kind": "capability.minimum",
        "severity": "error",
        "failure_mode": "fail",
        "configuration": {"capabilities": {"ifc.read": "partial"}},
    }


def _diagnostic_check(check_id: str = "diagnostics") -> dict[str, Any]:
    return {
        "check_id": check_id,
        "kind": "diagnostic.maximum",
        "severity": "warning",
        "failure_mode": "requires_review",
        "configuration": {"threshold": "error", "max_count": 0},
    }


def _waiver(check_id: str = "aecctx.policy.capabilities", waiver_id: str = "exception") -> dict[str, Any]:
    return {
        "waiver_id": waiver_id,
        "check_id": check_id,
        "finding_fingerprint": SHA256,
        "reason": "reviewed exception",
        "approved_by": "delivery-authority",
        "issued_at": "2026-07-01T00:00:00Z",
        "expires_at": "2026-08-01T00:00:00Z",
    }


def _policy(*, checks: list[dict[str, Any]] | None = None, waivers: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "profile": "https://aecctx.dev/gate/v1",
        "policy_id": "delivery",
        "policy_version": "1.0.0",
        "evaluation_time": "2026-07-13T00:00:00Z",
        "checks": checks or [],
        "waivers": waivers or [],
    }


def _bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _assert_code(code: str, data: bytes, *, limits: GateLimits | None = None) -> None:
    with pytest.raises(GateError) as caught:
        load_gate_policy(data, **({} if limits is None else {"limits": limits}))
    assert caught.value.code == code


def test_policy_digest_is_independent_of_whitespace_and_object_key_order() -> None:
    left = load_gate_policy(_bytes(_policy()))
    right = load_gate_policy(
        b'{ "waivers": [], "checks": [], "evaluation_time": "2026-07-13T00:00:00Z", '
        b'"policy_version": "1.0.0", "policy_id": "delivery", '
        b'"profile": "https://aecctx.dev/gate/v1" }'
    )

    expected = (
        b'{"checks":[],"evaluation_time":"2026-07-13T00:00:00Z",'
        b'"policy_id":"delivery","policy_version":"1.0.0",'
        b'"profile":"https://aecctx.dev/gate/v1","waivers":[]}\n'
    )
    assert left.canonical_bytes == expected
    assert right.canonical_bytes == expected
    assert left.digest == right.digest == hashlib.sha256(expected).hexdigest()


def test_policy_normalizes_all_strings_to_nfc_but_preserves_array_order() -> None:
    decomposed_waiver = _waiver()
    decomposed_waiver["reason"] = "cafe\u0301"
    composed_waiver = _waiver()
    composed_waiver["reason"] = "caf\u00e9"
    decomposed = _policy(checks=[_capability_check()], waivers=[decomposed_waiver])
    composed = _policy(checks=[_capability_check()], waivers=[composed_waiver])
    reversed_policy = _policy(checks=[_diagnostic_check(), _capability_check()], waivers=[composed_waiver])
    ordered_policy = _policy(checks=[_capability_check(), _diagnostic_check()], waivers=[composed_waiver])

    left = load_gate_policy(_bytes(decomposed))
    right = load_gate_policy(_bytes(composed))

    assert left.digest == right.digest
    assert left.waivers[0].reason == "caf\u00e9"
    assert load_gate_policy(_bytes(reversed_policy)).digest != load_gate_policy(_bytes(ordered_policy)).digest


@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b'{"profile":"https://aecctx.dev/gate/v1","profile":"x"}', "AECCTX_GATE_JSON_DUPLICATE_KEY"),
        (b'{"caf\\u00e9":1,"cafe\\u0301":2}', "AECCTX_GATE_JSON_NORMALIZATION_COLLISION"),
        (b'\xff', "AECCTX_GATE_JSON_INVALID"),
        (b'{"value":NaN}', "AECCTX_GATE_JSON_NONFINITE"),
        (b'{"value":Infinity}', "AECCTX_GATE_JSON_NONFINITE"),
        (b'{', "AECCTX_GATE_JSON_INVALID"),
    ],
)
def test_strict_json_rejections_have_stable_codes(data: bytes, code: str) -> None:
    _assert_code(code, data)


def test_policy_rejects_values_deeper_than_governed_limit() -> None:
    nested: Any = "leaf"
    for _ in range(32):
        nested = [nested]
    document = _policy()
    document["extra"] = nested
    _assert_code("AECCTX_GATE_JSON_DEPTH_EXCEEDED", _bytes(document))


def test_policy_maps_parser_recursion_exhaustion_to_depth_error() -> None:
    data = b'{"value":' + (b"[" * 2_000) + b"0" + (b"]" * 2_000) + b"}"
    _assert_code("AECCTX_GATE_JSON_DEPTH_EXCEEDED", data)


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda value: value.update({"unknown": True}), "AECCTX_GATE_SCHEMA_INVALID"),
        (
            lambda value: value.update({"checks": [{**_diagnostic_check(), "configuration": {"threshold": "error", "max_count": True}}]}),
            "AECCTX_GATE_SCHEMA_INVALID",
        ),
        (lambda value: value.update({"profile": "https://example.test/gate/v1"}), "AECCTX_GATE_PROFILE_UNSUPPORTED"),
        (lambda value: value.update({"policy_version": "01.0"}), "AECCTX_GATE_POLICY_VERSION_INVALID"),
        (lambda value: value.update({"policy_version": "1.0.0-01"}), "AECCTX_GATE_POLICY_VERSION_INVALID"),
        (lambda value: value.update({"policy_version": "1.0.0-"}), "AECCTX_GATE_POLICY_VERSION_INVALID"),
        (lambda value: value.update({"policy_version": "1.0.0+"}), "AECCTX_GATE_POLICY_VERSION_INVALID"),
        (lambda value: value.update({"evaluation_time": "2026-07-13T00:00:00+00:00"}), "AECCTX_GATE_EVALUATION_TIME_INVALID"),
        (lambda value: value.update({"evaluation_time": "2026-02-30T00:00:00Z"}), "AECCTX_GATE_EVALUATION_TIME_INVALID"),
    ],
)
def test_policy_schema_and_identity_rejections_are_stable(mutate: Any, code: str) -> None:
    document = _policy()
    mutate(document)
    _assert_code(code, _bytes(document))


def test_policy_rejects_duplicate_and_reserved_check_ids() -> None:
    _assert_code(
        "AECCTX_GATE_CHECK_ID_DUPLICATE",
        _bytes(_policy(checks=[_capability_check("same"), _diagnostic_check("same")])),
    )
    _assert_code(
        "AECCTX_GATE_CHECK_ID_RESERVED",
        _bytes(_policy(checks=[_capability_check("aecctx.system.validation")])),
    )


def test_policy_rejects_duplicate_waiver_ids() -> None:
    _assert_code(
        "AECCTX_GATE_WAIVER_ID_DUPLICATE",
        _bytes(
            _policy(
                checks=[_capability_check()],
                waivers=[_waiver(waiver_id="same"), _waiver(waiver_id="same")],
            )
        ),
    )


@pytest.mark.parametrize("target", ["capabilities", "aecctx.system.validation", "aecctx.policy.unknown", "*"])
def test_policy_rejects_non_exact_or_undeclared_waiver_targets(target: str) -> None:
    _assert_code(
        "AECCTX_GATE_WAIVER_TARGET_INVALID",
        _bytes(_policy(checks=[_capability_check()], waivers=[_waiver(check_id=target)])),
    )


@pytest.mark.parametrize(
    ("issued_at", "expires_at"),
    [
        ("2026-08-01T00:00:00Z", "2026-08-01T00:00:00Z"),
        ("2026-08-02T00:00:00Z", "2026-08-01T00:00:00Z"),
        ("2026-07-01T00:00:00+00:00", "2026-08-01T00:00:00Z"),
    ],
)
def test_policy_rejects_invalid_waiver_intervals(issued_at: str, expires_at: str) -> None:
    waiver = _waiver()
    waiver.update(issued_at=issued_at, expires_at=expires_at)
    _assert_code(
        "AECCTX_GATE_WAIVER_INTERVAL_INVALID",
        _bytes(_policy(checks=[_capability_check()], waivers=[waiver])),
    )


def test_caller_limits_can_reduce_but_not_expand_v1_hard_maxima() -> None:
    assert len(load_gate_policy(_bytes(_policy(checks=[_capability_check()])), limits=GateLimits(max_checks=1)).checks) == 1
    _assert_code(
        "AECCTX_GATE_CHECK_LIMIT_EXCEEDED",
        _bytes(_policy(checks=[_capability_check(), _diagnostic_check()])),
        limits=GateLimits(max_checks=1),
    )
    _assert_code(
        "AECCTX_GATE_LIMIT_INVALID",
        _bytes(_policy()),
        limits=GateLimits(max_checks=257),
    )


def test_policy_rejects_waiver_and_byte_overflow() -> None:
    document = _policy(
        checks=[_capability_check()],
        waivers=[_waiver(waiver_id="one"), _waiver(waiver_id="two")],
    )
    _assert_code(
        "AECCTX_GATE_WAIVER_LIMIT_EXCEEDED",
        _bytes(document),
        limits=GateLimits(max_waivers=1),
    )
    _assert_code(
        "AECCTX_GATE_INPUT_LIMIT_EXCEEDED",
        _bytes(_policy()),
        limits=GateLimits(max_policy_bytes=10),
    )


def test_canonical_gate_json_rejects_nonfinite_and_invalid_types() -> None:
    with pytest.raises(GateError, match="finite") as nonfinite:
        canonical_gate_json({"value": math.inf})
    assert nonfinite.value.code == "AECCTX_GATE_JSON_NONFINITE"

    with pytest.raises(GateError) as invalid:
        canonical_gate_json({1: "not a JSON object key"})
    assert invalid.value.code == "AECCTX_GATE_JSON_INVALID"


def test_validate_gate_document_uses_only_allowlisted_packaged_schemas() -> None:
    validate_gate_document(_policy(), "gate-policy.schema.json")
    with pytest.raises(GateError) as caught:
        validate_gate_document(_policy(), "https://example.test/remote.schema.json")
    assert caught.value.code == "AECCTX_GATE_SCHEMA_UNSUPPORTED"


def test_read_gate_document_rejects_symlinks_nonregular_and_overflow(tmp_path: Path) -> None:
    regular = tmp_path / "policy.json"
    regular.write_bytes(b"{}")
    assert read_gate_document(regular, maximum_bytes=2, label="policy") == b"{}"

    link = tmp_path / "link.json"
    link.symlink_to(regular)
    directory = tmp_path / "directory"
    directory.mkdir()

    for path in (link, directory):
        with pytest.raises(GateError) as caught:
            read_gate_document(path, maximum_bytes=10, label="policy")
        assert caught.value.code == "AECCTX_GATE_INPUT_TYPE_INVALID"
        assert str(tmp_path) not in str(caught.value)

    with pytest.raises(GateError) as caught:
        read_gate_document(regular, maximum_bytes=1, label="policy")
    assert caught.value.code == "AECCTX_GATE_INPUT_LIMIT_EXCEEDED"


def test_load_policy_rejects_non_bytes_without_leaking_value() -> None:
    with pytest.raises(GateError) as caught:
        load_gate_policy("secret policy")  # type: ignore[arg-type]
    assert caught.value.code == "AECCTX_GATE_INPUT_TYPE_INVALID"
    assert "secret" not in str(caught.value)
