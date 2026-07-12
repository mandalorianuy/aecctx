from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).parents[1]
CHECKER = ROOT / "scripts" / "check_rvt_blocked_conformance.py"
CLAIMS = ROOT / "conformance" / "v0.2" / "claims.json"
DECISION = ROOT / "conformance" / "v0.2" / "rvt-provider-decision.json"
EXPECTED_RVT_CLAIM = {
    "id": "rvt.external-provider",
    "status": "public",
    "support_level": "unsupported",
    "profile": "rvt-no-provider-blocked-v1",
    "platform_scope": ["any"],
    "provider_scope": "none",
    "fixture_ids": ["v02-rvt-acx19-anti-claim"],
    "test_ids": [
        "tests/test_rvt_blocked_profile.py::test_rvt_suffix_uses_deterministic_opaque_fallback",
        "tests/test_rvt_blocked_profile.py::test_cli_auto_does_not_promote_rvt_suffix",
    ],
    "evidence": "docs/evidence/ACX-19.md",
}


def _base_record() -> dict[str, object]:
    record = json.loads(DECISION.read_text(encoding="utf-8"))
    assert isinstance(record, dict)
    return record


def _base_registry() -> dict[str, object]:
    registry = json.loads(CLAIMS.read_text(encoding="utf-8"))
    assert isinstance(registry, dict)
    fixtures = registry["fixtures"]
    claims = registry["claims"]
    assert isinstance(fixtures, list)
    assert isinstance(claims, list)
    if not any(item.get("id") == "v02-rvt-acx19-anti-claim" for item in fixtures):
        fixtures.append({"id": "v02-rvt-acx19-anti-claim", "path": "fixtures/v0.2/rvt/not-a-real-rvt.rvt"})
    registry["claims"] = [
        copy.deepcopy(EXPECTED_RVT_CLAIM) if item.get("id") == "rvt.external-provider" else item
        for item in claims
    ]
    return registry


def _run_checker(
    tmp_path: Path,
    record: dict[str, object],
    *,
    registry: dict[str, object] | None = None,
) -> subprocess.CompletedProcess[str]:
    decision = tmp_path / "decision.json"
    claims = tmp_path / "claims.json"
    decision.write_text(json.dumps(record), encoding="utf-8")
    claims.write_text(json.dumps(registry or json.loads(CLAIMS.read_text(encoding="utf-8"))), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--decision",
            str(decision),
            "--claims",
            str(claims),
            "--root",
            str(ROOT),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def test_committed_rvt_blocked_decision_is_valid() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--decision",
            str(DECISION),
            "--claims",
            str(CLAIMS),
            "--root",
            str(ROOT),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "aecctx RVT blocked conformance: ok\n"


def _select_provider(value: dict[str, object]) -> None:
    value["selected_provider"] = "autodesk-revit-desktop"


def _duplicate_candidate(value: dict[str, object]) -> None:
    candidates = value["candidates"]
    assert isinstance(candidates, list)
    candidates.append(copy.deepcopy(candidates[0]))


def _remove_ci_axis(value: dict[str, object]) -> None:
    candidates = value["candidates"]
    assert isinstance(candidates, list)
    axes = candidates[0]["axes"]
    assert isinstance(axes, dict)
    axes.pop("ci_access")


def _add_unknown_blocker(value: dict[str, object]) -> None:
    candidates = value["candidates"]
    assert isinstance(candidates, list)
    blockers = candidates[0]["blocker_codes"]
    assert isinstance(blockers, list)
    blockers.append("AECCTX_RVT_UNKNOWN")


def _add_non_official_source(value: dict[str, object]) -> None:
    candidates = value["candidates"]
    assert isinstance(candidates, list)
    sources = candidates[0]["official_sources"]
    assert isinstance(sources, list)
    sources.append("https://example.invalid/rvt")


def _swap_official_source(value: dict[str, object]) -> None:
    candidates = value["candidates"]
    assert isinstance(candidates, list)
    candidates[0]["official_sources"] = ["https://www.opendesign.com/faq/bimrv"]


def _duplicate_reopening(value: dict[str, object]) -> None:
    alternatives = value["reopening_alternatives"]
    assert isinstance(alternatives, list)
    alternatives.append(copy.deepcopy(alternatives[0]))


def _add_host_path(value: dict[str, object]) -> None:
    candidates = value["candidates"]
    assert isinstance(candidates, list)
    candidates[0]["notes"] = "/Users/operator/license.dat"


def _add_mutable_value(value: dict[str, object]) -> None:
    candidates = value["candidates"]
    assert isinstance(candidates, list)
    candidates[0]["impact"] = "TBD"


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (_select_provider, "selected_provider must be null"),
        (_duplicate_candidate, "duplicate candidate id"),
        (_remove_ci_axis, "ci_access"),
        (_add_unknown_blocker, "unknown blocker code"),
        (_add_non_official_source, "non-official decision source"),
        (_swap_official_source, "official sources do not match candidate"),
        (_duplicate_reopening, "duplicate reopening alternative id"),
        (_add_host_path, "host path or credential-like value"),
        (_add_mutable_value, "mutable decision value"),
    ],
)
def test_rvt_decision_rejects_incomplete_or_unsafe_values(
    tmp_path: Path,
    mutation: Callable[[dict[str, object]], None],
    expected: str,
) -> None:
    record = _base_record()
    mutation(record)

    result = _run_checker(tmp_path, record)

    assert result.returncode == 1
    assert expected in result.stderr


def _set_claim_field(registry: dict[str, object], field: str, value: object) -> None:
    claims = registry["claims"]
    assert isinstance(claims, list)
    claim = next(item for item in claims if item["id"] == "rvt.external-provider")
    claim[field] = value


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "experimental"),
        ("support_level", "partial"),
        ("profile", "rvt-2026-elements-v1"),
        ("provider_scope", "autodesk-revit-desktop"),
    ],
)
def test_rvt_claim_rejects_any_positive_or_provider_promotion(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    registry = _base_registry()
    _set_claim_field(registry, field, value)

    result = _run_checker(tmp_path, _base_record(), registry=registry)

    assert result.returncode == 1
    assert "RVT claim does not match blocked boundary" in result.stderr


def test_rvt_claim_rejects_a_second_rvt_claim(tmp_path: Path) -> None:
    registry = _base_registry()
    claims = registry["claims"]
    assert isinstance(claims, list)
    claims.append({**copy.deepcopy(EXPECTED_RVT_CLAIM), "id": "rvt.semantic-elements"})

    result = _run_checker(tmp_path, _base_record(), registry=registry)

    assert result.returncode == 1
    assert "unexpected RVT claim id: rvt.semantic-elements" in result.stderr
