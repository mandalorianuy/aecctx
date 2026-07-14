#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
import zipfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aecctx.conformance import validate_claim_registry_file  # noqa: E402


PROFILE = "aecctx-gate-v1-ids-1.0-expanded-v1"
COMMIT = "1effec6f419798ce09617416d258a35bdc58320a"


class ConformanceError(RuntimeError):
    pass


def _json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as error:
        raise ConformanceError(f"AECCTX_GATE_V03_CORPUS_INVALID: {path}: {error}") from error
    if not isinstance(value, dict):
        raise ConformanceError(f"AECCTX_GATE_V03_CORPUS_INVALID: {path} must contain an object")
    return value


def _digest(relative: object, expected: object, code: str) -> None:
    if not isinstance(relative, str) or not isinstance(expected, str):
        raise ConformanceError(f"{code}: malformed path or digest")
    path = ROOT / relative
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ConformanceError(f"{code}: {relative}")


def _artifact_members(path: Path) -> tuple[str, ...]:
    if path.suffix == ".whl" or zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return tuple(sorted(archive.namelist()))
    if path.name.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(path) as archive:
            return tuple(sorted(member.name for member in archive.getmembers() if member.isfile()))
    raise ConformanceError(f"AECCTX_GATE_V03_ARTIFACT_INVALID: unsupported artifact {path}")


def _check_artifact(path: Path) -> None:
    members = _artifact_members(path)
    required_wheel = ("aecctx/gate/ids.py", "aecctx/gate/_ids_worker.py", "aecctx/schemas/v0_2/gate-check.schema.json")
    if path.suffix == ".whl" and not all(any(member.endswith(name) for member in members) for name in required_wheel):
        raise ConformanceError(f"AECCTX_GATE_V03_ARTIFACT_INVALID: runtime contract absent from {path.name}")
    if path.name.endswith((".tar.gz", ".tgz", ".tar")):
        required_source = (
            "conformance/v0.3/gate-corpus.json",
            "fixtures/v0.3/gate/official/ORIGIN.json",
            "fixtures/v0.3/gate/project/expanded-profile.ifc",
            "docs/specs/quality-gate-v03-profile.md",
            "scripts/check_gate_v03_conformance.py",
            "tests/test_gate_v03.py",
        )
        if not all(any(member.endswith(name) for member in members) for name in required_source):
            raise ConformanceError(f"AECCTX_GATE_V03_ARTIFACT_INVALID: conformance asset absent from {path.name}")
    forbidden = [
        member
        for member in members
        if any(name in member.lower() for name in ("ifctester", "ifcopenshell"))
        and member.lower().endswith((".dll", ".dylib", ".exe", ".pyd", ".so"))
    ]
    if forbidden:
        raise ConformanceError("AECCTX_GATE_V03_RESTRICTED_ARTIFACT: " + ", ".join(forbidden))


def check_conformance(*, artifacts: Iterable[Path] = (), require_public: bool = False) -> dict[str, object]:
    corpus = _json(ROOT / "conformance/v0.3/gate-corpus.json")
    entries = corpus.get("entries")
    if (
        corpus.get("corpus_version") != "1"
        or corpus.get("fixture_id") != "v03-gate-acx36"
        or corpus.get("profile") != PROFILE
        or not isinstance(entries, list)
        or len(entries) != 45
    ):
        raise ConformanceError("AECCTX_GATE_V03_CORPUS_INVALID: profile, fixture or entry count")
    expected_runtime = {"ifcopenshell": "0.8.5", "ifctester": "0.8.5"}
    if corpus.get("runtime") != expected_runtime:
        raise ConformanceError("AECCTX_GATE_V03_RUNTIME_MISMATCH: corpus contract")
    runtime: dict[str, str] = {}
    for name, expected in expected_runtime.items():
        try:
            actual = version(name)
        except PackageNotFoundError as error:
            raise ConformanceError(f"AECCTX_GATE_V03_DEPENDENCY_MISSING: install aecctx[gate-ids] ({name})") from error
        if actual != expected:
            raise ConformanceError(f"AECCTX_GATE_V03_RUNTIME_MISMATCH: {name}=={actual}")
        runtime[name] = actual

    project_count = 0
    official_count = 0
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("case_id"), str):
            raise ConformanceError("AECCTX_GATE_V03_CORPUS_INVALID: malformed entry")
        case_id = entry["case_id"]
        if case_id in seen or entry.get("expected") not in {"pass", "fail"}:
            raise ConformanceError(f"AECCTX_GATE_V03_CORPUS_INVALID: duplicate/outcome {case_id}")
        seen.add(case_id)
        _digest(entry.get("ids"), entry.get("ids_sha256"), "AECCTX_GATE_V03_CORPUS_DIGEST_MISMATCH")
        _digest(entry.get("ifc"), entry.get("ifc_sha256"), "AECCTX_GATE_V03_CORPUS_DIGEST_MISMATCH")
        if entry.get("origin") == "AECCTX project-authored" and entry.get("license") == "Apache-2.0":
            project_count += 1
        elif entry.get("origin") == "buildingSMART IDS v1.0.0 unchanged" and entry.get("license") == "CC-BY-ND-4.0":
            official_count += 1
        else:
            raise ConformanceError(f"AECCTX_GATE_V03_LICENSE_INVALID: {case_id}")
    if project_count != 22 or official_count != 23:
        raise ConformanceError("AECCTX_GATE_V03_CORPUS_INVALID: project/official partition")

    origin = _json(ROOT / "fixtures/v0.3/gate/official/ORIGIN.json")
    origin_files = origin.get("files")
    if (
        origin.get("commit") != COMMIT
        or origin.get("release") != "v1.0.0"
        or origin.get("license") != "CC-BY-ND-4.0"
        or not isinstance(origin_files, list)
        or len(origin_files) != 46
    ):
        raise ConformanceError("AECCTX_GATE_V03_PROVENANCE_INVALID")
    for item in origin_files:
        if not isinstance(item, dict) or not str(item.get("upstream_path", "")).startswith(
            "Documentation/ImplementersDocumentation/TestCases/"
        ):
            raise ConformanceError("AECCTX_GATE_V03_PROVENANCE_INVALID: upstream path")
        _digest(item.get("path"), item.get("sha256"), "AECCTX_GATE_V03_OFFICIAL_DIGEST_MISMATCH")
    if (ROOT / "fixtures/v0.3/gate/official/LICENSE.txt").read_text(encoding="utf-8").find("Attribution-NoDerivatives") < 0:
        raise ConformanceError("AECCTX_GATE_V03_LICENSE_INVALID: official license text")

    regeneration = subprocess.run(
        [sys.executable, str(ROOT / "fixtures/v0.3/gate/generate_fixtures.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if regeneration.returncode != 0:
        raise ConformanceError("AECCTX_GATE_V03_FIXTURE_DRIFT: " + regeneration.stderr.strip())

    registry_path = ROOT / "conformance/v0.3/claims.json"
    registry_result = validate_claim_registry_file(registry_path, repository_root=ROOT)
    if not registry_result.valid:
        raise ConformanceError("AECCTX_GATE_V03_CLAIM_INVALID: " + "; ".join(registry_result.errors))
    claims = _json(registry_path).get("claims")
    claim = next((item for item in claims if isinstance(item, dict) and item.get("id") == "quality-gate.ids-expanded"), None)
    allowed = {"public"} if require_public else {"target", "public"}
    if (
        not isinstance(claim, dict)
        or claim.get("status") not in allowed
        or (claim.get("status") == "public" and claim.get("support_level") != "partial")
        or claim.get("profile") != PROFILE
        or claim.get("fixture_ids") != ["v03-gate-acx36"]
        or (claim.get("status") == "public" and claim.get("evidence") != "docs/evidence/ACX-36.md")
    ):
        raise ConformanceError("AECCTX_GATE_V03_CLAIM_INVALID: lifecycle/profile mismatch")
    for artifact in artifacts:
        _check_artifact(artifact)
    return {
        "claim_status": claim["status"],
        "entries": len(entries),
        "fixture_regeneration": True,
        "official_commit": COMMIT,
        "ok": True,
        "runtime": runtime,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--require-public", action="store_true")
    args = parser.parse_args()
    try:
        result = check_conformance(
            artifacts=(Path(value) for value in args.artifact),
            require_public=args.require_public,
        )
    except (ConformanceError, OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
