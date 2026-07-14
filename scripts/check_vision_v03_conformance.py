#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, tarfile, zipfile
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from aecctx.conformance import validate_claim_registry_file
from aecctx.providers import validate_provider_replay_corpus

class Error(RuntimeError): pass
def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def digest(path, expected):
    path = Path(path)
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected: raise Error(f"AECCTX_VISION_DIGEST_MISMATCH: {path}")
def members(path):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive: return archive.namelist()
    with tarfile.open(path) as archive: return [item.name for item in archive.getmembers() if item.isfile()]
def check(require_public=False, require_live_images=False, artifacts=()):
    corpus = load(ROOT / "conformance/v0.3/vision-corpus.json")
    for key in ("profile", "worker", "generator", "live_runner", "replay"): digest(ROOT / corpus[key]["path"], corpus[key]["sha256"])
    digest(ROOT / corpus["runtime"]["dockerfile"], corpus["runtime"]["sha256"])
    for item in corpus["fixtures"]: digest(ROOT / item["path"], item["sha256"])
    generated = subprocess.run([sys.executable, str(ROOT / corpus["generator"]["path"]), "--check"], capture_output=True, text=True)
    if generated.returncode: raise Error(generated.stderr)
    schema = load(ROOT / "schemas/v0.2/vision-candidate.schema.json")
    if schema != load(ROOT / "src/aecctx/schemas/v0_2/vision-candidate.schema.json"): raise Error("AECCTX_VISION_SCHEMA_MIRROR_MISMATCH")
    validator = Draft202012Validator(schema); live = corpus["live"]
    values = []
    for arch in ("arm64", "amd64"):
        path = ROOT / live["path"] / f"{arch}.json"; digest(path, live["response_sha256"]); value = load(path); values.append(value)
        errors = list(validator.iter_errors(value["events"][0]["payload"]))
        if errors: raise Error("AECCTX_VISION_SCHEMA_INVALID: " + errors[0].message)
    if values[0] != values[1]: raise Error("AECCTX_VISION_ARCH_EQUIVALENCE_FAILED")
    digest(ROOT / live["path"] / "summary.json", live["summary_sha256"])
    if require_live_images:
        for platform, image_id in live["architectures"].items():
            arch = platform.split("/")[1]; tag = f"aecctx-vision-raster-rules:0.3.0-linux-{arch}"; probe = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}} {{.Os}}/{{.Architecture}}", tag], capture_output=True, text=True)
            if probe.returncode or probe.stdout.strip() != f"{image_id} {platform}": raise Error(f"AECCTX_VISION_LIVE_IMAGE_MISMATCH: {platform}")
    if not validate_provider_replay_corpus(ROOT / corpus["replay"]["path"])["ok"]: raise Error("AECCTX_VISION_REPLAY_INVALID")
    result = validate_claim_registry_file(ROOT / "conformance/v0.3/claims.json", repository_root=ROOT)
    if not result.valid: raise Error("; ".join(result.errors))
    claims = {item["id"]: item for item in load(ROOT / "conformance/v0.3/claims.json")["claims"]}; expected = {"pdf-image.vision-inference", "pdf-image.reconstruction-hypothesis"}
    for claim in expected:
        if claim not in claims or (require_public and claims[claim]["status"] != "public") or claims[claim]["support_level"] != "partial": raise Error("AECCTX_VISION_CLAIM_INVALID: " + claim)
    for artifact in artifacts:
        names = members(artifact)
        if not any(name.endswith("aecctx/schemas/v0_2/vision-candidate.schema.json") for name in names): raise Error("AECCTX_VISION_SCHEMA_NOT_PACKAGED")
        if any("vision-raster-rules/worker.py" in name for name in names): raise Error("AECCTX_VISION_PROVIDER_BUNDLED")
    return {"claims": 2, "fixtures": len(corpus["fixtures"]), "live_executions": 2, "ok": True}
def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--require-public",action="store_true"); parser.add_argument("--require-live-images",action="store_true"); parser.add_argument("--artifact",action="append",default=[]); args=parser.parse_args()
    try: print(json.dumps(check(args.require_public,args.require_live_images,tuple(Path(v) for v in args.artifact)),sort_keys=True,separators=(",",":")))
    except Exception as error: print(error,file=sys.stderr); return 1
    return 0
if __name__ == "__main__": raise SystemExit(main())
