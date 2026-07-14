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


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aecctx.conformance import validate_claim_registry_file
from aecctx.crs import load_crs_registry


class ConformanceError(RuntimeError):
    pass


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(path: Path, expected: str) -> None:
    if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ConformanceError(f"AECCTX_MESH_CRS_DIGEST_MISMATCH: {path}")


def _members(path: Path) -> list[str]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    with tarfile.open(path) as archive:
        return [item.name for item in archive.getmembers() if item.isfile()]


def check(*, require_public: bool = False, artifacts: tuple[Path, ...] = ()) -> dict[str, object]:
    corpus = _load(ROOT / "conformance/v0.3/mesh-crs-corpus.json")
    assert isinstance(corpus, dict)
    for item in [corpus["profile"], corpus["schema"], *corpus["fixtures"]]:
        _digest(ROOT / item["path"], item["sha256"])

    generated = subprocess.run(
        [sys.executable, str(ROOT / "fixtures/v0.3/mesh/generate_fixtures.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if generated.returncode:
        raise ConformanceError(generated.stderr or generated.stdout)

    schema = _load(ROOT / "schemas/v0.2/crs-registry.schema.json")
    if schema != _load(ROOT / "src/aecctx/schemas/v0_2/crs-registry.schema.json"):
        raise ConformanceError("AECCTX_MESH_CRS_SCHEMA_MIRROR_MISMATCH")
    registry = load_crs_registry(_load(ROOT / "fixtures/v0.3/mesh/crs-registry.json"))
    if registry.profile_id != corpus["registry"]["profile_id"] or registry.registry_digest != corpus["registry"]["logical_digest"]:
        raise ConformanceError("AECCTX_MESH_CRS_REGISTRY_MISMATCH")

    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    if 'crs = ["pyproj==3.7.2"]' not in pyproject or 'dependencies = ["jsonschema[format]>=4.23,<5"]' not in pyproject:
        raise ConformanceError("AECCTX_MESH_CRS_DEPENDENCY_BOUNDARY_INVALID")
    license_text = (ROOT / "docs/licenses/trimesh.md").read_text(encoding="utf-8")
    if "pyproj==3.7.2" not in license_text or "MIT" not in license_text or "EPSG" not in license_text:
        raise ConformanceError("AECCTX_MESH_CRS_LICENSE_RECORD_MISSING")

    result = validate_claim_registry_file(ROOT / "conformance/v0.3/claims.json", repository_root=ROOT)
    if not result.valid:
        raise ConformanceError("; ".join(result.errors))
    claims_document = _load(ROOT / "conformance/v0.3/claims.json")
    claims = {item["id"]: item for item in claims_document["claims"]}
    expected_claims = {"mesh.crs-registry", "mesh.datum-transform"}
    for claim_id in expected_claims:
        claim = claims.get(claim_id)
        if claim is None or claim["support_level"] != "partial" or (require_public and claim["status"] != "public"):
            raise ConformanceError(f"AECCTX_MESH_CRS_CLAIM_INVALID: {claim_id}")

    for artifact in artifacts:
        names = _members(artifact)
        if not any(name.endswith("aecctx/crs.py") for name in names):
            raise ConformanceError("AECCTX_MESH_CRS_MODULE_NOT_PACKAGED")
        if not any(name.endswith("aecctx/schemas/v0_2/crs-registry.schema.json") for name in names):
            raise ConformanceError("AECCTX_MESH_CRS_SCHEMA_NOT_PACKAGED")
        if any("site-packages/pyproj" in name or name.startswith("pyproj/") for name in names):
            raise ConformanceError("AECCTX_MESH_CRS_DEPENDENCY_BUNDLED")

    return {"claims": len(expected_claims), "fixtures": len(corpus["fixtures"]), "ok": True, "profile": registry.profile_id}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-public", action="store_true")
    parser.add_argument("--artifact", action="append", default=[])
    arguments = parser.parse_args()
    try:
        print(json.dumps(check(require_public=arguments.require_public, artifacts=tuple(Path(item) for item in arguments.artifact)), sort_keys=True, separators=(",", ":")))
    except Exception as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
