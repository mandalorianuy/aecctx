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
from aecctx.providers import load_provider_replay_entry, validate_provider_replay_corpus
from aecctx.providers.step_iges import STEP_IGES_OCI_TARGETS
from aecctx.step_iges import validate_step_iges_events


class ConformanceError(RuntimeError):
    pass


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ConformanceError(f"AECCTX_STEP_IGES_V03_JSON_INVALID: {path}")
    return value


def _digest(reference: object) -> None:
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        raise ConformanceError("AECCTX_STEP_IGES_V03_REFERENCE_INVALID")
    path = ROOT / str(reference["path"])
    if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != reference["sha256"]:
        raise ConformanceError(f"AECCTX_STEP_IGES_V03_DIGEST_MISMATCH: {path}")


def _members(path: Path) -> list[str]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    with tarfile.open(path) as archive:
        return [item.name for item in archive.getmembers() if item.isfile()]


def check(*, require_public: bool = False, require_live_images: bool = False, artifacts: tuple[Path, ...] = ()) -> dict[str, object]:
    corpus_path = ROOT / "conformance/v0.3/step-iges-corpus.json"
    corpus = _load(corpus_path)
    for key in ("fixture", "generator", "profile", "schema", "worker"):
        _digest(corpus.get(key))
    replay = validate_provider_replay_corpus(corpus_path)
    if not replay["ok"] or {entry["id"] for entry in replay["entries"]} != {"ap203-xde", "ap214-xde", "ap242-xde", "iges53-xde", "ap214-metadata", "ap214-metadata-healed"}:
        raise ConformanceError("AECCTX_STEP_IGES_V03_REPLAY_INVALID")
    metadata = validate_step_iges_events(load_provider_replay_entry(corpus_path, "ap214-metadata").result)
    healed = validate_step_iges_events(load_provider_replay_entry(corpus_path, "ap214-metadata-healed").result)
    if len(metadata.roots) != 2 or metadata.healed_breps or len(healed.healed_breps) != 2:
        raise ConformanceError("AECCTX_STEP_IGES_V03_ROOT_HEALING_INVALID")
    labels = metadata.xde.get("labels", [])
    if not labels or not any(item.get("colors") for item in labels) or not any(item.get("layers") for item in labels) or not any(item.get("materials") for item in labels):
        raise ConformanceError("AECCTX_STEP_IGES_V03_XDE_METADATA_MISSING")
    if not all(item.get("unit") == {"state": "known", "value": "millimetre"} for item in labels):
        raise ConformanceError("AECCTX_STEP_IGES_V03_UNIT_INVALID")
    if not any(item.get("placement", {}).get("matrix_3x4", [0] * 12)[3] == 40.0 for item in labels):
        raise ConformanceError("AECCTX_STEP_IGES_V03_PLACEMENT_INVALID")
    schema = _load(ROOT / "schemas/v0.2/step-iges-xde-event.schema.json")
    if schema != _load(ROOT / "src/aecctx/schemas/v0_2/step-iges-xde-event.schema.json"):
        raise ConformanceError("AECCTX_STEP_IGES_V03_SCHEMA_MIRROR_MISMATCH")
    license_record = (ROOT / "docs/licenses/step-iges-ocp-provider.md").read_text(encoding="utf-8")
    for marker in ("cadquery-ocp==7.9.3.1.1", "Apache-2.0", "LGPL-2.1", "not linked into or distributed"):
        if marker not in license_record:
            raise ConformanceError("AECCTX_STEP_IGES_V03_LICENSE_RECORD_INVALID")
    if require_live_images:
        for target in STEP_IGES_OCI_TARGETS:
            inspected = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}} {{.Os}}/{{.Architecture}}", target.image], capture_output=True, text=True, check=False)
            if inspected.returncode or inspected.stdout.strip() != f"{target.image_id} {target.platform}/{target.architecture}":
                raise ConformanceError(f"AECCTX_STEP_IGES_V03_LIVE_IMAGE_MISMATCH: {target.platform}/{target.architecture}")
    claims_result = validate_claim_registry_file(ROOT / "conformance/v0.3/claims.json", repository_root=ROOT)
    if not claims_result.valid:
        raise ConformanceError("; ".join(claims_result.errors))
    claims = {item["id"]: item for item in _load(ROOT / "conformance/v0.3/claims.json")["claims"]}  # type: ignore[index]
    expected = {"step-iges.xde-structure", "step-iges.partial-recovery"}
    for claim_id in expected:
        claim = claims.get(claim_id)
        if claim is None or claim.get("support_level") != "partial" or (require_public and claim.get("status") != "public"):
            raise ConformanceError(f"AECCTX_STEP_IGES_V03_CLAIM_INVALID: {claim_id}")
    for artifact in artifacts:
        names = _members(artifact)
        if not any(name.endswith("aecctx/schemas/v0_2/step-iges-xde-event.schema.json") for name in names):
            raise ConformanceError("AECCTX_STEP_IGES_V03_SCHEMA_NOT_PACKAGED")
        if any("cadquery" in name.lower() or "opencascade" in name.lower() or name.endswith("step-iges-ocp/worker.py") for name in names):
            raise ConformanceError("AECCTX_STEP_IGES_V03_NATIVE_RUNTIME_BUNDLED")
    return {"claims": len(expected), "fixtures": len(replay["entries"]), "healed_roots": len(healed.healed_breps), "ok": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-public", action="store_true")
    parser.add_argument("--require-live-images", action="store_true")
    parser.add_argument("--artifact", action="append", default=[])
    arguments = parser.parse_args()
    try:
        print(json.dumps(check(require_public=arguments.require_public, require_live_images=arguments.require_live_images, artifacts=tuple(Path(item) for item in arguments.artifact)), sort_keys=True, separators=(",", ":")))
    except Exception as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
