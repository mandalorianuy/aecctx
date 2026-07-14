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

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from aecctx.conformance import validate_claim_registry_file  # noqa: E402


class ConformanceError(RuntimeError): pass


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ConformanceError(f"AECCTX_OCR_CORPUS_INVALID: {path}")
    return value


def digest(path: Path, expected: object) -> None:
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ConformanceError(f"AECCTX_OCR_DIGEST_MISMATCH: {path.relative_to(ROOT)}")


def _artifact_members(path: Path) -> tuple[str, ...]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive: return tuple(sorted(archive.namelist()))
    with tarfile.open(path) as archive: return tuple(sorted(item.name for item in archive.getmembers() if item.isfile()))


def check(*, require_public: bool = False, require_live_images: bool = False, artifacts: tuple[Path, ...] = ()) -> dict[str, object]:
    corpus = load(ROOT / "conformance/v0.3/ocr-corpus.json")
    if corpus.get("version") != "0.3.0": raise ConformanceError("AECCTX_OCR_CORPUS_INVALID: version")
    for key in ("profile", "generator", "runtime", "replay", "worker", "live_runner"):
        item = corpus[key]; digest(ROOT / str(item["path"] if key != "runtime" else item["dockerfile"]), item["sha256"])
    fixtures = corpus.get("fixtures")
    if not isinstance(fixtures, list) or len(fixtures) != 11: raise ConformanceError("AECCTX_OCR_CORPUS_INVALID: fixtures")
    for item in fixtures: digest(ROOT / str(item["path"]), item["sha256"])
    regenerated = subprocess.run([sys.executable, str(ROOT / corpus["generator"]["path"]), "--check"], cwd=ROOT, capture_output=True, text=True)
    if regenerated.returncode: raise ConformanceError("AECCTX_OCR_FIXTURE_DRIFT: " + regenerated.stderr)
    schema = load(ROOT / "schemas/v0.2/ocr-layout.schema.json")
    if schema != load(ROOT / "src/aecctx/schemas/v0_2/ocr-layout.schema.json"): raise ConformanceError("AECCTX_OCR_SCHEMA_MIRROR_MISMATCH")
    validator = Draft202012Validator(schema)
    live = corpus["live"]; digest(ROOT / live["path"] / "summary.json", live["summary_sha256"])
    profiles = ("eng-auto-v1", "eng-block-v1", "eng-column-v1", "eng-table-v1", "por-block-v1", "spa-block-v1")
    for profile in profiles:
        values = []
        for architecture in ("arm64", "amd64"):
            response_path = ROOT / live["path"] / f"{architecture}-{profile}.json"
            digest(response_path, live["responses"][profile])
            result = load(response_path)
            payload = result["events"][0]["payload"]; errors = list(validator.iter_errors(payload))
            if errors: raise ConformanceError(f"AECCTX_OCR_SCHEMA_INVALID: {architecture}/{profile}: {errors[0].message}")
            values.append(result)
        if values[0] != values[1]: raise ConformanceError(f"AECCTX_OCR_REPLAY_EQUIVALENCE_FAILED: {profile}")
    if require_live_images:
        for platform, image_id in live["architectures"].items():
            architecture = platform.split("/")[1]; tag = f"aecctx-tesseract-ocr-layout:0.3.0-linux-{architecture}"
            probe = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}} {{.Os}}/{{.Architecture}}", tag], capture_output=True, text=True)
            if probe.returncode or probe.stdout.strip() != f"{image_id} {platform}": raise ConformanceError(f"AECCTX_OCR_LIVE_IMAGE_MISMATCH: {platform}")
    result = validate_claim_registry_file(ROOT / "conformance/v0.3/claims.json", repository_root=ROOT)
    if not result.valid: raise ConformanceError("AECCTX_OCR_CLAIM_INVALID: " + "; ".join(result.errors))
    claims = load(ROOT / "conformance/v0.3/claims.json")["claims"]
    claim = next((item for item in claims if item.get("id") == "pdf-image.ocr-layout"), None)
    allowed = {"public"} if require_public else {"target", "public"}
    if not claim or claim.get("status") not in allowed or (claim.get("status") == "public" and (claim.get("support_level") != "partial" or claim.get("evidence") != "docs/evidence/ACX-29.md")): raise ConformanceError("AECCTX_OCR_CLAIM_INVALID: lifecycle")
    from aecctx.providers import validate_provider_replay_corpus
    if not validate_provider_replay_corpus(ROOT / corpus["replay"]["path"])["ok"]: raise ConformanceError("AECCTX_OCR_REPLAY_INVALID")
    for artifact in artifacts:
        members = _artifact_members(artifact)
        if not any(name.endswith("aecctx/schemas/v0_2/ocr-layout.schema.json") for name in members): raise ConformanceError(f"AECCTX_OCR_SCHEMA_NOT_PACKAGED: {artifact.name}")
        forbidden = [name for name in members if name.lower().endswith(".traineddata") or "/libtesseract" in name.lower() or name.lower().endswith("/tesseract")]
        if forbidden: raise ConformanceError("AECCTX_OCR_RESTRICTED_ARTIFACT: " + ", ".join(forbidden))
    return {"entries": len(fixtures), "live_executions": 12, "profiles": len(profiles), "claim_status": claim["status"], "ok": True}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--require-public", action="store_true"); parser.add_argument("--require-live-images", action="store_true"); parser.add_argument("--artifact", action="append", default=[]); args = parser.parse_args()
    try: value = check(require_public=args.require_public, require_live_images=args.require_live_images, artifacts=tuple(Path(item) for item in args.artifact))
    except (ConformanceError, OSError, KeyError, ValueError, json.JSONDecodeError) as error: print(error, file=sys.stderr); return 1
    print(json.dumps(value, sort_keys=True, separators=(",", ":"))); return 0


if __name__ == "__main__": raise SystemExit(main())
