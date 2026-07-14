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


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aecctx.conformance import validate_claim_registry_file
from aecctx.dwg import validate_dwg_events
from aecctx.providers import load_provider_replay_entry, validate_provider_replay_corpus
from aecctx.providers.dwg import DWG_OCI_TARGETS


class ConformanceError(RuntimeError):
    pass


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ConformanceError(f"AECCTX_DWG_V03_JSON_INVALID: {path}")
    return value


def digest(reference: object) -> None:
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        raise ConformanceError("AECCTX_DWG_V03_REFERENCE_INVALID")
    path = ROOT / str(reference["path"])
    if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != reference["sha256"]:
        raise ConformanceError(f"AECCTX_DWG_V03_DIGEST_MISMATCH: {path}")


def members(path: Path) -> list[str]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()
    with tarfile.open(path) as archive:
        return [item.name for item in archive.getmembers() if item.isfile()]


def check(*, require_public: bool = False, require_live_images: bool = False, artifacts: tuple[Path, ...] = ()) -> dict[str, object]:
    corpus_path = ROOT / "conformance/v0.3/dwg-corpus.json"
    corpus = load(corpus_path)
    for key in ("generator", "profile", "schema", "worker"):
        digest(corpus.get(key))
    for fixture in corpus.get("fixtures", []):
        digest(fixture)
    replay = validate_provider_replay_corpus(corpus_path)
    expected = {"r13-profile", "r14-profile", "r2000-m-profile", "r2000-mm-xref"}
    if not replay["ok"] or {item["id"] for item in replay["entries"]} != expected:
        raise ConformanceError("AECCTX_DWG_V03_REPLAY_INVALID")
    events = {entry_id: validate_dwg_events(load_provider_replay_entry(corpus_path, entry_id).result).source_event for entry_id in expected}
    if {events[item]["dwg_version"] for item in ("r13-profile", "r14-profile", "r2000-m-profile")} != {"AC1012", "AC1014", "AC1015"}:
        raise ConformanceError("AECCTX_DWG_V03_VERSION_MATRIX_INVALID")
    if events["r2000-m-profile"]["units"].get("symbol") != "m" or events["r2000-mm-xref"]["units"].get("symbol") != "mm" or events["r13-profile"]["units"].get("state") != "unknown":
        raise ConformanceError("AECCTX_DWG_V03_UNIT_MATRIX_INVALID")
    if (ROOT / "schemas/v0.2/dwg-v03-event.schema.json").read_bytes() != (ROOT / "src/aecctx/schemas/v0_2/dwg-v03-event.schema.json").read_bytes():
        raise ConformanceError("AECCTX_DWG_V03_SCHEMA_MIRROR_MISMATCH")
    for document, markers in (("docs/licenses/libredwg-provider.md", ("GPL-3.0-or-later", "0.13.4", "R13", "R14")), ("docs/security/dwg-provider-review.md", ("#1037", "writer", "AC1012", "content-addressed"))):
        content = (ROOT / document).read_text(encoding="utf-8")
        if any(marker not in content for marker in markers):
            raise ConformanceError(f"AECCTX_DWG_V03_REVIEW_INVALID: {document}")
    claims_result = validate_claim_registry_file(ROOT / "conformance/v0.3/claims.json", repository_root=ROOT)
    if not claims_result.valid:
        raise ConformanceError("; ".join(claims_result.errors))
    claims = {item["id"]: item for item in load(ROOT / "conformance/v0.3/claims.json")["claims"]}  # type: ignore[index]
    claim = claims.get("dwg.external-provider.v03")
    if claim is None or claim.get("support_level") != "partial" or (require_public and claim.get("status") != "public"):
        raise ConformanceError("AECCTX_DWG_V03_CLAIM_INVALID")
    if require_live_images:
        for target in DWG_OCI_TARGETS:
            inspected = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}} {{.Os}}/{{.Architecture}}", target.image], capture_output=True, text=True, check=False)
            if inspected.returncode or inspected.stdout.strip() != f"{target.image_id} {target.platform}/{target.architecture}":
                raise ConformanceError(f"AECCTX_DWG_V03_LIVE_IMAGE_MISMATCH: {target.platform}/{target.architecture}")
        environment = dict(os.environ)
        environment["AECCTX_RUN_DWG_V03_PROVIDER"] = "1"
        live = subprocess.run([str(ROOT / ".venv/bin/python"), "-m", "pytest", "tests/test_dwg_v03.py", "-k", "live_v03", "-q"], cwd=ROOT, env=environment, check=False)
        if live.returncode:
            raise ConformanceError("AECCTX_DWG_V03_LIVE_MATRIX_FAILED")
    for artifact in artifacts:
        names = members(artifact)
        if not any(name.endswith("aecctx/schemas/v0_2/dwg-v03-event.schema.json") for name in names):
            raise ConformanceError("AECCTX_DWG_V03_SCHEMA_NOT_PACKAGED")
        normalized = tuple(name.replace("\\", "/").lower() for name in names)
        if any("/providers/libredwg/" in f"/{name}" for name in normalized):
            raise ConformanceError("AECCTX_DWG_V03_GPL_RUNTIME_BUNDLED")
    return {"claim": "dwg.external-provider.v03", "fixtures": len(expected), "ok": True, "versions": 3}


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
