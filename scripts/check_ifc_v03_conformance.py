#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aecctx.adapters.ifc import IFCPlugin  # noqa: E402
from aecctx.conformance import validate_claim_registry_file  # noqa: E402


class ConformanceError(RuntimeError):
    pass


def _json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConformanceError(f"AECCTX_IFC_V03_CORPUS_INVALID: {path}: {error}") from error
    if not isinstance(value, dict):
        raise ConformanceError(f"AECCTX_IFC_V03_CORPUS_INVALID: {path} must contain an object")
    return value


def _digest(path: Path, expected: object, code: str) -> None:
    if not path.is_file() or not isinstance(expected, str):
        raise ConformanceError(f"{code}: {path.relative_to(ROOT)}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ConformanceError(f"{code}: {path.relative_to(ROOT)}")


def _artifact_members(path: Path) -> tuple[str, ...]:
    if path.suffix == ".whl" or zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return tuple(sorted(archive.namelist()))
    if path.name.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(path) as archive:
            return tuple(sorted(member.name for member in archive.getmembers() if member.isfile()))
    raise ConformanceError(f"AECCTX_IFC_V03_ARTIFACT_INVALID: unsupported artifact {path}")


def _check_artifact(path: Path) -> None:
    members = _artifact_members(path)
    if not any(member.endswith("aecctx/adapters/ifc.py") for member in members):
        raise ConformanceError(f"AECCTX_IFC_V03_ARTIFACT_INVALID: IFC adapter absent from {path.name}")
    forbidden = [
        member
        for member in members
        if "ifcopenshell" in member.lower()
        and member.lower().endswith((".dll", ".dylib", ".exe", ".pyd", ".so"))
    ]
    if forbidden:
        raise ConformanceError("AECCTX_IFC_V03_RESTRICTED_ARTIFACT: " + ", ".join(forbidden))


def check_conformance(*, artifacts: Iterable[Path] = (), require_public: bool = False) -> dict[str, object]:
    corpus = _json(ROOT / "conformance/v0.3/ifc-corpus.json")
    entries = corpus.get("entries")
    if corpus.get("version") != "0.3.0" or not isinstance(entries, list) or len(entries) != 3:
        raise ConformanceError("AECCTX_IFC_V03_CORPUS_INVALID: version or entry count")
    expected_ids = {
        "ifc4x3-curves-annotations-scaled",
        "ifc4x3-degraded",
        "ifc4x3-conflicted-georef",
    }
    seen: set[str] = set()
    try:
        import ifcopenshell
    except ImportError as error:
        raise ConformanceError("AECCTX_IFC_V03_DEPENDENCY_MISSING: install aecctx[ifc]") from error
    if str(ifcopenshell.version) != "0.8.5":
        raise ConformanceError(f"AECCTX_IFC_V03_RUNTIME_MISMATCH: {ifcopenshell.version}")
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ConformanceError("AECCTX_IFC_V03_CORPUS_INVALID: malformed entry")
        path = ROOT / entry["path"]
        _digest(path, entry.get("sha256"), "AECCTX_IFC_V03_CORPUS_DIGEST_MISMATCH")
        model = ifcopenshell.open(path)
        if (
            model.schema != entry.get("schema")
            or entry.get("schema") != "IFC4X3"
            or model.schema_identifier != entry.get("schema_identifier")
            or entry.get("schema_identifier") != "IFC4X3_ADD2"
        ):
            raise ConformanceError(f"AECCTX_IFC_V03_SCHEMA_MISMATCH: {entry['path']}")
        seen.add(str(entry.get("id")))
    if seen != expected_ids:
        raise ConformanceError("AECCTX_IFC_V03_CORPUS_INVALID: fixture IDs")

    generator = corpus.get("generator")
    profile = corpus.get("profile")
    if not isinstance(generator, dict) or generator.get("runtime") != "ifcopenshell==0.8.5":
        raise ConformanceError("AECCTX_IFC_V03_CORPUS_INVALID: generator contract")
    if not isinstance(profile, dict):
        raise ConformanceError("AECCTX_IFC_V03_CORPUS_INVALID: profile contract")
    _digest(ROOT / str(generator.get("path")), generator.get("sha256"), "AECCTX_IFC_V03_GENERATOR_DIGEST_MISMATCH")
    _digest(ROOT / str(profile.get("path")), profile.get("sha256"), "AECCTX_IFC_V03_PROFILE_DIGEST_MISMATCH")
    regeneration = subprocess.run(
        [sys.executable, str(ROOT / str(generator["path"])), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if regeneration.returncode != 0:
        raise ConformanceError("AECCTX_IFC_V03_FIXTURE_DRIFT: " + regeneration.stderr.strip())

    descriptor = IFCPlugin().describe()
    if descriptor.get("implementation_runtime") != "ifcopenshell/0.8.5":
        raise ConformanceError("AECCTX_IFC_V03_RUNTIME_MISMATCH: plugin descriptor")
    if descriptor.get("distribution_posture") != "optional-not-bundled":
        raise ConformanceError("AECCTX_IFC_V03_LICENSE_BOUNDARY_INVALID")

    registry_path = ROOT / "conformance/v0.3/claims.json"
    registry_result = validate_claim_registry_file(registry_path, repository_root=ROOT)
    if not registry_result.valid:
        raise ConformanceError("AECCTX_IFC_V03_CLAIM_INVALID: " + "; ".join(registry_result.errors))
    registry = _json(registry_path)
    claims = registry.get("claims")
    if not isinstance(claims, list):
        raise ConformanceError("AECCTX_IFC_V03_CLAIM_INVALID: claims array")
    selected = {
        item.get("id"): item
        for item in claims
        if isinstance(item, dict) and item.get("id") in {"ifc.native-2d.v03", "ifc.georeferencing.v03"}
    }
    if set(selected) != {"ifc.native-2d.v03", "ifc.georeferencing.v03"}:
        raise ConformanceError("AECCTX_IFC_V03_CLAIM_INVALID: missing claims")
    allowed = {"public"} if require_public else {"target", "public"}
    for claim in selected.values():
        status = claim.get("status")
        expected_support = "partial" if status == "public" else None
        expected_evidence = "docs/evidence/ACX-27.md" if status == "public" else None
        if status not in allowed or claim.get("support_level") != expected_support or claim.get("evidence") != expected_evidence:
            raise ConformanceError("AECCTX_IFC_V03_CLAIM_INVALID: lifecycle/profile mismatch")
    for artifact in artifacts:
        _check_artifact(artifact)
    return {
        "claim_status": sorted({str(claim.get("status")) for claim in selected.values()}),
        "entries": len(entries),
        "fixture_regeneration": True,
        "ok": True,
        "runtime": str(ifcopenshell.version),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--require-public", action="store_true")
    arguments = parser.parse_args()
    try:
        result = check_conformance(
            artifacts=(Path(value) for value in arguments.artifact),
            require_public=arguments.require_public,
        )
    except (ConformanceError, OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
