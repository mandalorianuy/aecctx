from __future__ import annotations

import copy
import importlib.metadata
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

import pytest


ROOT = Path(__file__).parents[1]
CHECKER = ROOT / "scripts" / "check_gate_conformance.py"
CORPUS = ROOT / "conformance" / "v0.2" / "gate-corpus.json"
CLAIMS = ROOT / "conformance" / "v0.2" / "claims.json"
GENERATOR = ROOT / "fixtures" / "v0.2" / "gate" / "generate_fixtures.py"
REQUIRED_CASES = {
    "pass-core",
    "directory-zip-equivalence",
    "fail-capability",
    "review-capability",
    "error-invalid-candidate",
    "malicious-policy-duplicate-key",
    "baseline-regression",
    "loss-maximum",
    "value-state-all",
    "diagnostic-maximum",
    "waiver-active",
    "waiver-expired",
    "waiver-invalid",
    "ids-project-pass",
    "ids-project-fail",
    "ids-active-xml-error",
    "ids-missing-extra",
    *{
        f"ids-official-{facet}-{outcome}"
        for facet in ("entity", "attribute", "classification", "property", "material")
        for outcome in ("pass", "fail")
    },
}


def checker_module():
    if not CHECKER.is_file():
        pytest.fail("missing gate conformance checker")
    spec = importlib.util.spec_from_file_location("aecctx_gate_conformance", CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corpus_value() -> dict[str, object]:
    if not CORPUS.is_file():
        pytest.fail("missing gate conformance corpus")
    value = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_gate_corpus_contract_is_complete_hash_bound_and_valid() -> None:
    assert checker_module().validate_gate_corpus(CORPUS) == ()
    corpus = corpus_value()
    entries = corpus["entries"]
    assert isinstance(entries, list)
    assert {entry["case_id"] for entry in entries} == REQUIRED_CASES
    assert corpus["claim_id"] == "quality-gate.policy-ids"
    assert corpus["claim_status"] == "target"
    assert corpus["maximum_support"] == "partial"
    assert corpus["profile"] == "aecctx-gate-v1-ids-1.0-simple-v1"
    for entry in entries:
        assert entry["claim_id"] == corpus["claim_id"]
        assert entry["origin"] in {"AECCTX project-authored", "buildingSMART IDS v1.0.0 unchanged inputs"}
        assert entry["license"] in {
            "Apache-2.0",
            "CC-BY-ND-4.0 inputs; Apache-2.0 generated harness",
        }
        hashes = entry["file_sha256"]
        assert isinstance(hashes, dict) and hashes
        for configured in hashes:
            logical = PurePosixPath(configured)
            assert not logical.is_absolute()
            assert ".." not in logical.parts
            assert (ROOT / configured).is_file()


def test_gate_corpus_rejects_duplicate_missing_unmapped_stale_and_claim_drift(tmp_path: Path) -> None:
    base = corpus_value()
    mutations: list[tuple[dict[str, object], str]] = []

    duplicate = copy.deepcopy(base)
    duplicate["entries"].append(copy.deepcopy(duplicate["entries"][0]))
    mutations.append((duplicate, "duplicate case_id"))

    missing = copy.deepcopy(base)
    missing["entries"] = [entry for entry in missing["entries"] if entry["case_id"] != "pass-core"]
    mutations.append((missing, "missing required case"))

    unmapped = copy.deepcopy(base)
    unmapped["entries"].append({**copy.deepcopy(unmapped["entries"][0]), "case_id": "surprise"})
    mutations.append((unmapped, "unmapped case_id"))

    stale = copy.deepcopy(base)
    first_hash = next(iter(stale["entries"][0]["file_sha256"]))
    stale["entries"][0]["file_sha256"][first_hash] = "0" * 64
    mutations.append((stale, "file hash mismatch"))

    unknown_claim = copy.deepcopy(base)
    unknown_claim["entries"][0]["claim_id"] = "quality-gate.unknown"
    mutations.append((unknown_claim, "claim_id mismatch"))

    public_drift = copy.deepcopy(base)
    public_drift["claim_status"] = "public"
    mutations.append((public_drift, "claim status mismatch"))

    unsafe = copy.deepcopy(base)
    unsafe["entries"][0]["candidate"] = "../outside"
    mutations.append((unsafe, "unsafe path"))

    for index, (value, expected) in enumerate(mutations):
        path = tmp_path / f"mutation-{index}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        errors = checker_module().validate_gate_corpus(path)
        assert any(expected in error for error in errors), errors


def test_gate_corpus_executes_offline_twice_and_matches_exact_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("network access is forbidden")

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    report = checker_module().run_gate_corpus(CORPUS)

    assert report["ok"] is True
    assert len(report["entries"]) == len(REQUIRED_CASES)
    assert all(entry["matches"] and entry["deterministic"] for entry in report["entries"])


def test_gate_fixture_regeneration_is_byte_stable() -> None:
    completed = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout == "aecctx gate fixtures: deterministic\n"


def test_official_gate_cases_are_unchanged_attributed_and_separate() -> None:
    origin_path = ROOT / "fixtures" / "third_party" / "buildingsmart-ids-1.0" / "ORIGIN.json"
    origin = json.loads(origin_path.read_text(encoding="utf-8"))
    corpus = corpus_value()
    official = [entry for entry in corpus["entries"] if entry["origin"].startswith("buildingSMART")]

    assert origin["commit"] == "1effec6f419798ce09617416d258a35bdc58320a"
    assert origin["license"] == "CC-BY-ND-4.0"
    assert len(official) == 10
    selected_paths = {path for entry in official for path in entry["file_sha256"] if "/cases/" in path}
    origin_paths = {
        f"fixtures/third_party/buildingsmart-ids-1.0/{entry['path']}"
        for entry in origin["files"]
    }
    assert selected_paths == origin_paths
    assert all(
        entry["license"] == "CC-BY-ND-4.0 inputs; Apache-2.0 generated harness"
        for entry in official
    )
    assert all("fixtures/v0.2/gate" not in path for path in selected_paths)


def test_gate_claim_is_selected_but_remains_target_until_task_9() -> None:
    registry = json.loads(CLAIMS.read_text(encoding="utf-8"))
    fixtures = {entry["id"]: entry for entry in registry["fixtures"]}
    claims = {entry["id"]: entry for entry in registry["claims"]}

    assert fixtures["v02-gate-acx21"] == {"id": "v02-gate-acx21", "path": "fixtures/v0.2/gate"}
    claim = claims["quality-gate.policy-ids"]
    assert claim["status"] == "target"
    assert claim["support_level"] is None
    assert claim["profile"] == "aecctx-gate-v1-ids-1.0-simple-v1"
    assert claim["platform_scope"] == ["python-3.12-linux-macos-windows-candidate"]
    assert claim["fixture_ids"] == ["v02-gate-acx21"]
    assert claim["test_ids"] == [
        "tests/test_gate_conformance.py::test_gate_corpus_executes_offline_twice_and_matches_exact_results",
        "tests/test_gate_conformance.py::test_clean_core_install_and_gate_ids_packaging_boundaries",
    ]
    assert claim["evidence"] == "docs/evidence/ACX-21.md"


def _venv_python(root: Path) -> Path:
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def test_clean_core_install_and_gate_ids_packaging_boundaries(tmp_path: Path) -> None:
    distribution = tmp_path / "dist"
    built = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--sdist", "--outdir", str(distribution)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert built.returncode == 0, built.stdout + built.stderr
    wheel = next(distribution.glob("aecctx-*.whl"))
    sdist = next(distribution.glob("aecctx-*.tar.gz"))

    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        metadata = archive.read(metadata_name).decode("utf-8")
        unconditional = "\n".join(line for line in metadata.splitlines() if "extra ==" not in line)
        for dependency in ("ifctester", "ifcopenshell", "flask", "bcf-client"):
            assert f"Requires-Dist: {dependency}" not in unconditional.lower()
        for schema in ("gate-check.schema.json", "gate-waiver.schema.json", "gate-policy.schema.json", "gate-result.schema.json"):
            assert any(name.endswith(f"aecctx/schemas/v0_2/{schema}") for name in archive.namelist())

    with tarfile.open(sdist, "r:gz") as archive:
        members = {member.name for member in archive.getmembers()}
        assert any(name.endswith("/scripts/check_gate_conformance.py") for name in members)
        assert any(name.endswith("/fixtures/v0.2/gate/generate_fixtures.py") for name in members)
        assert any(name.endswith("/conformance/v0.2/gate-corpus.json") for name in members)
        assert any(name.endswith("/fixtures/third_party/buildingsmart-ids-1.0/ORIGIN.json") for name in members)
        assert any(name.endswith("/fixtures/third_party/buildingsmart-ids-1.0/LICENSE-CC-BY-ND-4.0.txt") for name in members)
        referenced_packages = {
            path
            for entry in corpus_value()["entries"]
            for path in entry["file_sha256"]
            if path.startswith("fixtures/v0.2/gate/packages/")
        }
        for package in referenced_packages:
            assert any(name.endswith(f"/{package}") for name in members), package

    core = tmp_path / "core-venv"
    created = subprocess.run([sys.executable, "-m", "venv", str(core)], text=True, capture_output=True)
    assert created.returncode == 0, created.stderr
    installed = subprocess.run(
        [str(_venv_python(core)), "-m", "pip", "install", str(wheel)],
        text=True,
        capture_output=True,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    probe = subprocess.run(
        [
            str(_venv_python(core)),
            "-c",
            "import importlib.util; from aecctx.gate import evaluate_gate; "
            "assert all(importlib.util.find_spec(n) is None for n in ('ifctester','ifcopenshell','flask','bcf'))",
        ],
        text=True,
        capture_output=True,
    )
    assert probe.returncode == 0, probe.stdout + probe.stderr
    assert importlib.metadata.version("ifctester") == "0.8.5"
    assert importlib.metadata.version("ifcopenshell") == "0.8.5"


def test_portable_verification_runs_gate_contract_and_corpus() -> None:
    script = (ROOT / "scripts" / "verify_portable.sh").read_text(encoding="utf-8")

    assert "conformance/v0.2/gate-corpus.json" in script
    assert "scripts/check_gate_conformance.py" in script
    assert "tests/test_gate_" in script
    assert script.index("scripts/check_gate_conformance.py") < script.index('"$python_runtime" -m pytest')
