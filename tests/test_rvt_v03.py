from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).parents[1]
CHECKER = ROOT / "scripts" / "check_rvt_blocked_conformance.py"
DECISION = ROOT / "conformance" / "v0.3" / "rvt-provider-decision.json"
CLAIMS = ROOT / "conformance" / "v0.3" / "claims.json"


def _run(decision: Path = DECISION, claims: Path = CLAIMS) -> subprocess.CompletedProcess[str]:
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


def test_acx34_committed_renewal_is_machine_validated() -> None:
    result = _run()

    assert result.returncode == 0, result.stderr
    assert result.stdout == "aecctx RVT blocked conformance: ok\n"


def test_acx34_decision_binds_v02_and_every_reopening_axis() -> None:
    record = json.loads(DECISION.read_text(encoding="utf-8"))

    assert record["predecessor"] == {
        "path": "conformance/v0.2/rvt-provider-decision.json",
        "sha256": "d7bc7e0b8f14b9c41e4914675fddb967d1e14d934bd33dd0c8decc05e46f4fa8",
    }
    assert record["decision"] == "blocked"
    assert record["selected_route"] is None
    assert record["human_route_authorization"] == "missing"
    expected_axes = {
        "license_entitlement",
        "exact_runtime_rvt_versions",
        "automation_rights",
        "sandbox_or_network_profile",
        "ci_access",
        "fixture_rights",
        "privacy",
        "telemetry",
        "billing",
        "retention",
        "jurisdiction",
        "lifecycle",
    }
    for route in record["routes"]:
        assert set(route["axes"]) == expected_axes
        assert all(value in {"unavailable", "unapproved", "unknown", "not_applicable"} for value in route["axes"].values())


def test_acx34_checker_rejects_route_promotion_without_authorization(tmp_path: Path) -> None:
    record = json.loads(DECISION.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(record)
    mutated["selected_route"] = "aps-network-provider"
    decision = tmp_path / "decision.json"
    decision.write_text(json.dumps(mutated), encoding="utf-8")

    result = _run(decision=decision)

    assert result.returncode == 1
    assert "selected_route must be null while human_route_authorization is missing" in result.stderr


def test_acx34_registry_exposes_only_renewed_unsupported_boundary() -> None:
    registry = json.loads(CLAIMS.read_text(encoding="utf-8"))
    claims = [item for item in registry["claims"] if item["id"].startswith("rvt.")]

    assert claims == [
        {
            "evidence": "docs/evidence/ACX-34.md",
            "fixture_ids": ["v02-rvt-acx19-anti-claim"],
            "id": "rvt.external-provider",
            "platform_scope": ["any"],
            "profile": "rvt-no-provider-blocked-v03",
            "provider_scope": "none",
            "status": "public",
            "support_level": "unsupported",
            "test_ids": [
                "tests/test_rvt_v03.py::test_acx34_committed_renewal_is_machine_validated",
                "tests/test_rvt_blocked_profile.py::test_rvt_suffix_uses_deterministic_opaque_fallback",
                "tests/test_rvt_blocked_profile.py::test_cli_auto_does_not_promote_rvt_suffix",
            ],
        }
    ]
    fixtures = [item for item in registry["fixtures"] if item["id"] == "v02-rvt-acx19-anti-claim"]
    assert fixtures == [
        {"id": "v02-rvt-acx19-anti-claim", "path": "fixtures/v0.2/rvt/not-a-real-rvt.rvt"}
    ]
