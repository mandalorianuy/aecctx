from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

import pytest


ROOT = Path(__file__).parents[1]
CHECKER = ROOT / "scripts" / "check_signing_conformance.py"
CORPUS = ROOT / "conformance" / "v0.2" / "signing-corpus.json"
GENERATOR = ROOT / "fixtures" / "v0.2" / "signing" / "generate_fixtures.py"
CLAIMS = ROOT / "conformance" / "v0.2" / "claims.json"
REQUIRED_CASES = {
    "unsigned-v01",
    "unsigned-v02",
    "directory-zip-equivalence",
    "valid-authorized",
    "invalid-signature",
    "foreign-statement",
    "unknown-key",
    "unsupported-algorithm",
    "valid-untrusted",
    "trusted-unauthorized",
    "not-yet-valid",
    "expired",
    "revoked",
    "unknown-status",
    "rotation",
    "threshold-1-of-n",
    "threshold-n-of-n",
    "artifact-mutation",
    "manifest-mutation",
    "header-mutation",
    "signature-mutation",
    "duplicate-json",
    "oversize-input",
    "missing-extra",
}


def checker_module():
    if not CHECKER.is_file():
        pytest.fail("missing signing conformance checker")
    spec = importlib.util.spec_from_file_location("aecctx_signing_conformance", CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def corpus_value() -> dict[str, object]:
    if not CORPUS.is_file():
        pytest.fail("missing signing conformance corpus")
    value = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_committed_signing_corpus_contract_is_complete_and_valid() -> None:
    assert checker_module().validate_signing_corpus(CORPUS) == ()
    entries = corpus_value()["entries"]
    assert isinstance(entries, list)
    assert {entry["case_id"] for entry in entries} == REQUIRED_CASES


def test_signing_corpus_paths_are_safe_and_every_configured_file_is_hashed() -> None:
    entries = corpus_value()["entries"]
    assert isinstance(entries, list)
    for entry in entries:
        assert isinstance(entry, dict)
        hashes = entry["file_sha256"]
        assert isinstance(hashes, dict) and hashes
        for configured_path in hashes:
            logical = PurePosixPath(configured_path)
            assert not logical.is_absolute()
            assert ".." not in logical.parts
            assert (ROOT / configured_path).is_file()
        for field in ("bundle", "registry", "policy"):
            configured = entry.get(field)
            if configured is not None:
                assert configured in hashes
        package = entry.get("package")
        if isinstance(package, str):
            package_path = ROOT / package
            hashed_package = package if package_path.is_file() else f"{package}/manifest.json"
            assert hashed_package in hashes


def test_every_publishable_signing_corpus_file_is_tracked() -> None:
    entries = corpus_value()["entries"]
    tracked_paths = sorted(
        {
            configured_path
            for entry in entries
            for configured_path in entry["file_sha256"]
        }
    )
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", *tracked_paths],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_signing_corpus_rejects_duplicate_missing_unmapped_and_unsafe_cases(tmp_path: Path) -> None:
    base = corpus_value()
    mutations: list[tuple[dict[str, object], str]] = []

    duplicate = copy.deepcopy(base)
    duplicate["entries"].append(copy.deepcopy(duplicate["entries"][0]))
    mutations.append((duplicate, "duplicate case_id"))

    missing = copy.deepcopy(base)
    missing["entries"] = [item for item in missing["entries"] if item["case_id"] != "unsigned-v01"]
    mutations.append((missing, "missing required case"))

    unmapped = copy.deepcopy(base)
    unmapped["entries"].append({**copy.deepcopy(unmapped["entries"][0]), "case_id": "surprise-case"})
    mutations.append((unmapped, "unmapped case_id"))

    unsafe = copy.deepcopy(base)
    unsafe["entries"][0]["package"] = "../outside"
    mutations.append((unsafe, "unsafe path"))

    unhashed = copy.deepcopy(base)
    unhashed["entries"][0]["file_sha256"] = {}
    mutations.append((unhashed, "missing file hash"))

    unknown_status = copy.deepcopy(base)
    unknown_status["entries"][0]["expected"]["signature_presence"] = "maybe"
    mutations.append((unknown_status, "invalid expected signature_presence"))

    for index, (value, expected) in enumerate(mutations):
        path = tmp_path / f"mutation-{index}.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        errors = checker_module().validate_signing_corpus(path)
        assert any(expected in error for error in errors), errors


def test_signing_corpus_executes_offline_and_matches_governed_results(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("network access is forbidden")

    import socket

    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    report = checker_module().run_signing_corpus(CORPUS)

    assert report["ok"] is True
    assert len(report["entries"]) == len(REQUIRED_CASES)
    assert all(entry["matches"] for entry in report["entries"])


def test_signing_fixture_regeneration_is_byte_stable() -> None:
    completed = subprocess.run(
        [sys.executable, str(GENERATOR), "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout == "aecctx signing fixtures: deterministic\n"


def test_signing_claim_is_public_partial_and_maps_exact_corpus() -> None:
    registry = json.loads(CLAIMS.read_text(encoding="utf-8"))
    fixtures = {item["id"]: item for item in registry["fixtures"]}
    claims = {item["id"]: item for item in registry["claims"]}

    assert fixtures["v02-signing-acx20"] == {
        "id": "v02-signing-acx20",
        "path": "fixtures/v0.2/signing",
    }
    claim = claims["package.authenticity-signing"]
    assert claim["status"] == "public"
    assert claim["support_level"] == "partial"
    assert claim["profile"] == "detached-jws-ed25519-offline-v1"
    assert claim["platform_scope"] == ["python-3.12-linux-macos-windows"]
    assert claim["provider_scope"] == "cryptography>=45,<50 optional; caller-owned registry and policy"
    assert claim["fixture_ids"] == ["v02-signing-acx20"]
    assert claim["test_ids"] == [
        "tests/test_signing_conformance.py::test_signing_corpus_executes_offline_and_matches_governed_results",
        "tests/test_signing_conformance.py::test_clean_install_base_and_signing_extra_boundaries",
    ]
    assert claim["evidence"] == "docs/evidence/ACX-20.md"


def _venv_python(root: Path) -> Path:
    return root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def test_clean_install_base_and_signing_extra_boundaries(tmp_path: Path) -> None:
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
        names = set(archive.namelist())
        assert "Requires-Dist: cryptography" not in "\n".join(
            line for line in metadata.splitlines() if "extra ==" not in line
        )
        for schema in (
            "signature-bundle.schema.json",
            "signing-key-registry.schema.json",
            "signing-trust-policy.schema.json",
            "signature-verification-result.schema.json",
        ):
            assert any(name.endswith(f"aecctx/schemas/v0_2/{schema}") for name in names)
        private_members = [name for name in names if "PRIVATE" in name.upper() or name.lower().endswith(".pem")]
        assert all(name.startswith("aecctx/fixtures/v0.2/signing/") for name in private_members)
    with tarfile.open(sdist, "r:gz") as archive:
        members = {member.name for member in archive.getmembers()}
        assert any(name.endswith("/scripts/check_signing_conformance.py") for name in members)
        assert any(name.endswith("/fixtures/v0.2/signing/generate_fixtures.py") for name in members)
        assert any(name.endswith("/conformance/v0.2/signing-corpus.json") for name in members)
        private_members = [name for name in members if name.lower().endswith(".pem")]
        assert private_members
        assert all("/fixtures/v0.2/signing/keys/test-" in name for name in private_members)
        readme_name = next(name for name in members if name.endswith("/fixtures/v0.2/signing/README.md"))
        readme = archive.extractfile(readme_name)
        assert readme is not None
        assert b"TEST ONLY" in readme.read()

    base = tmp_path / "base-venv"
    signing = tmp_path / "signing-venv"
    for environment in (base, signing):
        created = subprocess.run([sys.executable, "-m", "venv", str(environment)], capture_output=True, text=True)
        assert created.returncode == 0, created.stderr
    installed_base = subprocess.run(
        [str(_venv_python(base)), "-m", "pip", "install", str(wheel)],
        text=True,
        capture_output=True,
    )
    assert installed_base.returncode == 0, installed_base.stdout + installed_base.stderr
    installed_signing = subprocess.run(
        [str(_venv_python(signing)), "-m", "pip", "install", f"aecctx[signing] @ {wheel.as_uri()}"],
        text=True,
        capture_output=True,
    )
    assert installed_signing.returncode == 0, installed_signing.stdout + installed_signing.stderr

    fixture_root = ROOT / "fixtures" / "v0.2" / "signing"
    base_validate = subprocess.run(
        [str(_venv_python(base)), "-m", "aecctx", "validate", str(PACKAGE := ROOT / "fixtures/minimal-aecctx"), "--json"],
        text=True,
        capture_output=True,
    )
    base_sign = subprocess.run(
        [
            str(_venv_python(base)),
            "-m",
            "aecctx",
            "sign",
            str(PACKAGE),
            "--private-key",
            str(fixture_root / "keys/test-a.pem"),
            "--kid",
            "test-a",
            "--output",
            str(tmp_path / "base-bundle.json"),
            "--json",
        ],
        text=True,
        capture_output=True,
    )
    signed_verify = subprocess.run(
        [
            str(_venv_python(signing)),
            "-m",
            "aecctx",
            "verify-signatures",
            str(PACKAGE),
            "--signature-bundle",
            str(fixture_root / "bundles/valid-a.json"),
            "--key-registry",
            str(fixture_root / "registries/valid.json"),
            "--trust-policy",
            str(fixture_root / "policies/trust-a.json"),
            "--json",
        ],
        text=True,
        capture_output=True,
    )

    assert base_validate.returncode == 0, base_validate.stdout + base_validate.stderr
    assert base_sign.returncode == 2
    assert json.loads(base_sign.stdout)["diagnostics"][0]["code"] == "AECCTX_SIGNING_CRYPTO_UNAVAILABLE"
    assert signed_verify.returncode == 0, signed_verify.stdout + signed_verify.stderr
    assert json.loads(signed_verify.stdout)["data"]["policy_evaluation"]["policy_satisfied"] is True
