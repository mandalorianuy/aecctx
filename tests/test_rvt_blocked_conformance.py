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


def _base_record() -> dict[str, object]:
    record = json.loads(DECISION.read_text(encoding="utf-8"))
    assert isinstance(record, dict)
    return record


def _run_checker(tmp_path: Path, record: dict[str, object]) -> subprocess.CompletedProcess[str]:
    decision = tmp_path / "decision.json"
    decision.write_text(json.dumps(record), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--decision",
            str(decision),
            "--claims",
            str(CLAIMS),
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
