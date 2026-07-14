#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aecctx.adapters.dxf import DXFPlugin, load_source_bundle  # noqa: E402
from aecctx.conformance import validate_claim_registry_file  # noqa: E402


class ConformanceError(RuntimeError):
    pass


def _json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConformanceError(f"AECCTX_DXF_V03_CORPUS_INVALID: {path}: {error}") from error
    if not isinstance(value, dict):
        raise ConformanceError(f"AECCTX_DXF_V03_CORPUS_INVALID: {path} must contain an object")
    return value


def _digest(path: Path, expected: object, code: str) -> None:
    if not path.is_file() or not isinstance(expected, str) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ConformanceError(f"{code}: {path.relative_to(ROOT)}")


def _artifact_members(path: Path) -> tuple[str, ...]:
    if path.suffix == ".whl" or zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return tuple(sorted(archive.namelist()))
    if path.name.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(path) as archive:
            return tuple(sorted(member.name for member in archive.getmembers() if member.isfile()))
    raise ConformanceError(f"AECCTX_DXF_V03_ARTIFACT_INVALID: unsupported artifact {path}")


def _check_artifact(path: Path) -> None:
    members = _artifact_members(path)
    if not any(member.endswith("aecctx/adapters/dxf.py") for member in members):
        raise ConformanceError(f"AECCTX_DXF_V03_ARTIFACT_INVALID: DXF adapter absent from {path.name}")
    if not any(member.endswith("aecctx/schemas/v0_2/source-bundle.schema.json") for member in members):
        raise ConformanceError(f"AECCTX_DXF_V03_ARTIFACT_INVALID: source-bundle schema absent from {path.name}")
    forbidden = [member for member in members if "/ezdxf/" in member.lower() or member.lower().endswith(("ezdxf.so", "ezdxf.pyd"))]
    if forbidden:
        raise ConformanceError("AECCTX_DXF_V03_RESTRICTED_ARTIFACT: " + ", ".join(forbidden))


def check_conformance(*, artifacts: Iterable[Path] = (), require_public: bool = False) -> dict[str, object]:
    corpus = _json(ROOT / "conformance/v0.3/dxf-corpus.json")
    entries = corpus.get("entries")
    if corpus.get("version") != "0.3.0" or not isinstance(entries, list) or len(entries) != 6:
        raise ConformanceError("AECCTX_DXF_V03_CORPUS_INVALID: version or entry count")
    try:
        import ezdxf
    except ImportError as error:
        raise ConformanceError("AECCTX_DXF_V03_DEPENDENCY_MISSING: install aecctx[dxf]") from error
    if str(ezdxf.__version__) != "1.4.4":
        raise ConformanceError(f"AECCTX_DXF_V03_RUNTIME_MISMATCH: {ezdxf.__version__}")
    generator = corpus.get("generator")
    profile = corpus.get("profile")
    if not isinstance(generator, dict) or generator.get("runtime") != "ezdxf==1.4.4" or not isinstance(profile, dict):
        raise ConformanceError("AECCTX_DXF_V03_CORPUS_INVALID: generator/profile contract")
    _digest(ROOT / str(generator.get("path")), generator.get("sha256"), "AECCTX_DXF_V03_GENERATOR_DIGEST_MISMATCH")
    _digest(ROOT / str(profile.get("path")), profile.get("sha256"), "AECCTX_DXF_V03_PROFILE_DIGEST_MISMATCH")
    environment = dict(os.environ)
    environment["PYTHONHASHSEED"] = "0"
    regenerated = subprocess.run(
        [sys.executable, str(ROOT / str(generator["path"])), "--check"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if regenerated.returncode != 0:
        detail = "\n".join(part.strip() for part in (regenerated.stdout, regenerated.stderr) if part.strip())
        raise ConformanceError("AECCTX_DXF_V03_FIXTURE_DRIFT: " + detail)
    expected = {
        "r12-curves-ascii": ("AC1009", "ascii"),
        "r2004-curves-binary": ("AC1018", "binary"),
        "r2007-curves-ascii": ("AC1021", "ascii"),
        "xref-root": ("AC1032", "ascii"),
        "xref-child": ("AC1021", "ascii"),
        "xref-nested": ("AC1018", "ascii"),
    }
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ConformanceError("AECCTX_DXF_V03_CORPUS_INVALID: malformed entry")
        fixture_id = str(entry.get("id"))
        path = ROOT / entry["path"]
        _digest(path, entry.get("sha256"), "AECCTX_DXF_V03_CORPUS_DIGEST_MISMATCH")
        document = ezdxf.readfile(path)
        expected_profile = expected.get(fixture_id)
        container = "binary" if path.read_bytes()[:22].startswith(b"AutoCAD Binary DXF") else "ascii"
        if expected_profile is None or (document.dxfversion, container) != expected_profile or (entry.get("release"), entry.get("container")) != expected_profile:
            raise ConformanceError(f"AECCTX_DXF_V03_PROFILE_MISMATCH: {entry['path']}")
        seen.add(fixture_id)
    if seen != set(expected):
        raise ConformanceError("AECCTX_DXF_V03_CORPUS_INVALID: fixture IDs")

    bundle = load_source_bundle(ROOT / "fixtures/v0.3/dxf/xref-bundle")
    if len(bundle.entries) != 3 or bundle.root.logical_path != "root.dxf":
        raise ConformanceError("AECCTX_DXF_V03_BUNDLE_INVALID")
    if _json(ROOT / "schemas/v0.2/source-bundle.schema.json") != _json(ROOT / "src/aecctx/schemas/v0_2/source-bundle.schema.json"):
        raise ConformanceError("AECCTX_DXF_V03_SCHEMA_MIRROR_MISMATCH")
    descriptor = DXFPlugin().describe()
    if descriptor.get("implementation_runtime") != "ezdxf/1.4.4" or descriptor.get("distribution_posture") != "optional-not-bundled":
        raise ConformanceError("AECCTX_DXF_V03_RUNTIME_OR_LICENSE_BOUNDARY_INVALID")

    registry_path = ROOT / "conformance/v0.3/claims.json"
    registry_result = validate_claim_registry_file(registry_path, repository_root=ROOT)
    if not registry_result.valid:
        raise ConformanceError("AECCTX_DXF_V03_CLAIM_INVALID: " + "; ".join(registry_result.errors))
    claims = _json(registry_path).get("claims")
    if not isinstance(claims, list):
        raise ConformanceError("AECCTX_DXF_V03_CLAIM_INVALID: claims array")
    selected = {item.get("id"): item for item in claims if isinstance(item, dict) and item.get("id") in {"dxf.source-semantics.v03", "dxf.geometry.v03"}}
    if set(selected) != {"dxf.source-semantics.v03", "dxf.geometry.v03"}:
        raise ConformanceError("AECCTX_DXF_V03_CLAIM_INVALID: missing claims")
    allowed = {"public"} if require_public else {"target", "public"}
    for claim in selected.values():
        status = claim.get("status")
        if status not in allowed:
            raise ConformanceError("AECCTX_DXF_V03_CLAIM_INVALID: lifecycle")
        if status == "public" and (claim.get("support_level") != "partial" or claim.get("evidence") != "docs/evidence/ACX-28.md"):
            raise ConformanceError("AECCTX_DXF_V03_CLAIM_INVALID: public mapping")
    for artifact in artifacts:
        _check_artifact(artifact)
    return {"claim_status": sorted({str(claim.get("status")) for claim in selected.values()}), "entries": len(entries), "fixture_regeneration": True, "ok": True, "runtime": str(ezdxf.__version__)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--require-public", action="store_true")
    arguments = parser.parse_args()
    try:
        result = check_conformance(artifacts=(Path(value) for value in arguments.artifact), require_public=arguments.require_public)
    except (ConformanceError, OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
