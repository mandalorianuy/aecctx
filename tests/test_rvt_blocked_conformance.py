from __future__ import annotations

import copy
from io import BytesIO
import json
from collections.abc import Callable
from pathlib import Path
import subprocess
import sys
import tarfile
import zipfile

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
    root: Path = ROOT,
    artifacts: tuple[Path, ...] = (),
) -> subprocess.CompletedProcess[str]:
    decision = tmp_path / "decision.json"
    claims = tmp_path / "claims.json"
    decision.write_text(json.dumps(record), encoding="utf-8")
    claims.write_text(json.dumps(registry or json.loads(CLAIMS.read_text(encoding="utf-8"))), encoding="utf-8")
    command = [
        sys.executable,
        str(CHECKER),
        "--decision",
        str(decision),
        "--claims",
        str(claims),
        "--root",
        str(root),
    ]
    for artifact in artifacts:
        command.extend(("--artifact", str(artifact)))
    return subprocess.run(
        command,
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


@pytest.mark.parametrize(
    ("relative", "content", "expected"),
    [
        ("src/aecctx/adapters/rvt.py", "def ingest_rvt(): pass\n", "RVT adapter/provider scaffolding"),
        ("src/aecctx/providers/rvt.py", "PROVIDER = 'autodesk'\n", "RVT adapter/provider scaffolding"),
        ("src/aecctx/consumer.py", "import WFDomain\n", "consumer symbol in executable source"),
        ("src/aecctx/other.py", "consumer = 'woodframing'\n", "consumer symbol in executable source"),
    ],
)
def test_source_boundary_rejects_rvt_scaffolding_and_consumer_symbols(
    tmp_path: Path,
    relative: str,
    content: str,
    expected: str,
) -> None:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    result = _run_checker(tmp_path, _base_record(), registry=_base_registry(), root=tmp_path)

    assert result.returncode == 1
    assert expected in result.stderr


def _write_wheel(path: Path, members: dict[str, bytes]) -> None:
    defaults = {
        "aecctx/__init__.py": b"",
        "aecctx-0.1.0.dist-info/METADATA": b"Metadata-Version: 2.4\nName: aecctx\nVersion: 0.1.0\nRequires-Dist: jsonschema\n",
    }
    defaults.update(members)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in defaults.items():
            archive.writestr(name, content)


def _write_sdist(path: Path, members: dict[str, bytes]) -> None:
    defaults = {
        "aecctx-0.1.0/pyproject.toml": (
            b'[project]\nname = "aecctx"\nversion = "0.1.0"\ndependencies = ["jsonschema"]\n'
            b'[project.optional-dependencies]\ntest = ["pytest"]\n'
        ),
        "aecctx-0.1.0/src/aecctx/__init__.py": b"",
        "aecctx-0.1.0/fixtures/v0.2/rvt/not-a-real-rvt.rvt": (
            b"AECCTX anti-claim sentinel. This is not an Autodesk Revit RVT file.\n"
        ),
    }
    defaults.update(members)
    with tarfile.open(path, "w:gz") as archive:
        for name, content in defaults.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, BytesIO(content))


def test_artifact_boundary_accepts_minimal_core_wheel_and_sdist(tmp_path: Path) -> None:
    wheel = tmp_path / "aecctx-0.1.0-py3-none-any.whl"
    sdist = tmp_path / "aecctx-0.1.0.tar.gz"
    _write_wheel(wheel, {})
    _write_sdist(sdist, {})

    result = _run_checker(
        tmp_path,
        _base_record(),
        registry=_base_registry(),
        artifacts=(wheel, sdist),
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("artifact_kind", "members", "expected"),
    [
        (
            "wheel",
            {"aecctx-0.1.0.dist-info/METADATA": b"Metadata-Version: 2.4\nName: aecctx\nVersion: 0.1.0\nRequires-Dist: Autodesk-Revit\n"},
            "prohibited core dependency",
        ),
        ("wheel", {"aecctx/revit-runtime.dll": b"native"}, "proprietary/native runtime member"),
        ("sdist", {"aecctx-0.1.0/tools/revit.exe": b"native"}, "proprietary/native runtime member"),
        ("sdist", {"aecctx-0.1.0/src/aecctx/adapters/rvt.py": b""}, "RVT adapter/provider scaffolding"),
        ("sdist", {"aecctx-0.1.0/fixtures/v0.2/rvt/sample.rvt": b"sample"}, "unexpected RVT artifact member"),
        ("wheel", {"../escape.py": b""}, "unsafe artifact member"),
    ],
)
def test_artifact_boundary_rejects_dependencies_binaries_scaffolding_and_samples(
    tmp_path: Path,
    artifact_kind: str,
    members: dict[str, bytes],
    expected: str,
) -> None:
    artifact = tmp_path / ("aecctx-0.1.0-py3-none-any.whl" if artifact_kind == "wheel" else "aecctx-0.1.0.tar.gz")
    if artifact_kind == "wheel":
        _write_wheel(artifact, members)
    else:
        _write_sdist(artifact, members)

    result = _run_checker(tmp_path, _base_record(), registry=_base_registry(), artifacts=(artifact,))

    assert result.returncode == 1
    assert expected in result.stderr
