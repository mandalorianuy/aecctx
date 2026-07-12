from __future__ import annotations

import socket
import time
from dataclasses import replace
from importlib import import_module

import pytest


def _signing():
    return import_module("aecctx.signing")


def _key(**changes: object):
    value = _signing().SigningKey(
        kid="test-a",
        public_key_x="A" * 43,
        subject="urn:aecctx:test:a",
        valid_from="2026-01-01T00:00:00Z",
        valid_until="2027-01-01T00:00:00Z",
        revocation_status="good",
        revoked_at=None,
        scopes=("aecctx.package.sign",),
    )
    return replace(value, **changes)


def _policy(verification_time: str = "2026-07-12T00:00:00Z", **changes: object):
    value = _signing().TrustPolicy(
        verification_time=verification_time,
        allowed_algorithms=("Ed25519",),
        trusted_kids=("test-a",),
        trusted_subjects=(),
        required_scopes=("aecctx.package.sign",),
        minimum_authorized_signatures=1,
    )
    return replace(value, **changes)


@pytest.mark.parametrize(
    ("instant", "expected"),
    (
        ("2025-12-31T23:59:59Z", "not_yet_valid"),
        ("2026-01-01T00:00:00Z", "valid"),
        ("2026-12-31T23:59:59Z", "valid"),
        ("2027-01-01T00:00:00Z", "expired"),
    ),
)
def test_key_lifecycle_uses_inclusive_start_and_exclusive_end(instant: str, expected: str) -> None:
    evaluation = _signing().evaluate_key(_key(), _policy(instant))

    assert evaluation.key_status == expected
    assert evaluation.trust_status == ("trusted" if expected == "valid" else "untrusted")
    assert evaluation.authorization_status == ("authorized" if expected == "valid" else "unauthorized")


def test_revocation_boundary_is_valid_before_and_revoked_at_instant() -> None:
    key = _key(revocation_status="revoked", revoked_at="2026-06-01T00:00:00Z")

    before = _signing().evaluate_key(key, _policy("2026-05-31T23:59:59Z"))
    at = _signing().evaluate_key(key, _policy("2026-06-01T00:00:00Z"))

    assert (before.key_status, before.trust_status, before.authorization_status) == (
        "valid",
        "trusted",
        "authorized",
    )
    assert (at.key_status, at.trust_status, at.authorization_status) == (
        "revoked",
        "untrusted",
        "unauthorized",
    )
    assert at.diagnostic_codes == (
        "AECCTX_SIGNING_KEY_REVOKED",
        "AECCTX_SIGNING_KEY_UNTRUSTED",
        "AECCTX_SIGNING_SIGNER_UNAUTHORIZED",
    )


def test_unknown_revocation_status_is_explicit_and_not_not_evaluated() -> None:
    evaluation = _signing().evaluate_key(_key(revocation_status="unknown"), _policy())

    assert evaluation.key_status == "unknown_status"
    assert evaluation.trust_status == "untrusted"
    assert evaluation.authorization_status == "unauthorized"
    assert evaluation.diagnostic_codes[0] == "AECCTX_SIGNING_KEY_STATUS_UNKNOWN"


def test_lifecycle_trust_and_authorization_failures_remain_separate() -> None:
    expired_untrusted = _signing().evaluate_key(
        _key(),
        _policy("2030-01-01T00:00:00Z", trusted_kids=(), trusted_subjects=()),
    )
    trusted_missing_scope = _signing().evaluate_key(
        _key(scopes=()),
        _policy(),
    )

    assert (expired_untrusted.key_status, expired_untrusted.trust_status) == ("expired", "untrusted")
    assert trusted_missing_scope.key_status == "valid"
    assert trusted_missing_scope.trust_status == "trusted"
    assert trusted_missing_scope.authorization_status == "unauthorized"


def test_subject_allowlist_is_resolved_only_from_registry_key() -> None:
    evaluation = _signing().evaluate_key(
        _key(kid="rotation-b"),
        _policy(trusted_kids=(), trusted_subjects=("urn:aecctx:test:a",)),
    )

    assert evaluation.trust_status == "trusted"
    assert evaluation.authorization_status == "authorized"


@pytest.mark.parametrize(
    ("key", "policy"),
    (
        (None, _policy()),
        (_key(), None),
        (None, None),
    ),
)
def test_missing_key_or_policy_is_not_evaluated(key: object, policy: object) -> None:
    evaluation = _signing().evaluate_key(key, policy)

    assert evaluation.key_status == "not_evaluated"
    assert evaluation.trust_status == "not_evaluated"
    assert evaluation.authorization_status == "not_evaluated"
    assert evaluation.diagnostic_codes == ()


def test_policy_evaluation_is_deterministic_without_host_clock_or_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("host clock or network access is forbidden")

    monkeypatch.setattr(time, "time", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)

    first = _signing().evaluate_key(_key(), _policy())
    second = _signing().evaluate_key(_key(), _policy())

    assert first == second
