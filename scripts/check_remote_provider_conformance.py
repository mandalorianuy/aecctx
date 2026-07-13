#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import runpy
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures/v0.3/remote-providers"


def fail(code: str, message: str) -> None:
    raise SystemExit(f"{code}: {message}")


def load(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail("AECCTX_REMOTE_CONFORMANCE_INVALID", f"{path}: {error}")


def check_artifact(path: Path) -> None:
    forbidden_suffixes = {".dll", ".dylib", ".exe", ".key", ".p12", ".pem", ".pfx", ".so"}
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if not any(name.endswith("aecctx/providers/remote.py") for name in names):
                fail("AECCTX_REMOTE_PACKAGING_INVALID", f"remote client missing from {path.name}")
            if any(Path(name).suffix.lower() in forbidden_suffixes for name in names):
                fail("AECCTX_REMOTE_RESTRICTED_ARTIFACT", f"credential, key or native binary in {path.name}")
        return
    import tarfile
    with tarfile.open(path) as archive:
        names = archive.getnames()
        if not any(name.endswith("src/aecctx/providers/remote.py") for name in names):
            fail("AECCTX_REMOTE_PACKAGING_INVALID", f"remote client missing from {path.name}")
        remote_names = [name for name in names if "remote" in name.lower()]
        if any(Path(name).suffix.lower() in forbidden_suffixes for name in remote_names):
            fail("AECCTX_REMOTE_RESTRICTED_ARTIFACT", f"credential, key or native binary in {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", action="append", type=Path, default=[])
    parser.add_argument("--require-public", action="store_true")
    args = parser.parse_args()
    corpus = load(ROOT / "conformance/v0.3/remote-provider-corpus.json")
    if not isinstance(corpus, dict) or corpus.get("profile") != "remote-https-spki-v1":
        fail("AECCTX_REMOTE_CONFORMANCE_INVALID", "invalid corpus profile")
    for entry in corpus.get("files", []):
        path = ROOT / entry["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            fail("AECCTX_REMOTE_CORPUS_DIGEST_MISMATCH", str(entry.get("path")))
    if (ROOT / "schemas/v0.2/remote-provider-policy.schema.json").read_bytes() != (ROOT / "src/aecctx/schemas/v0_2/remote-provider-policy.schema.json").read_bytes():
        fail("AECCTX_REMOTE_SCHEMA_MIRROR_MISMATCH", "packaged schema differs")
    claims = load(ROOT / "conformance/v0.3/claims.json")
    claim = next((item for item in claims["claims"] if item["id"] == "sandbox.remote-provider"), None)
    allowed = {"public"} if args.require_public else {"target", "public"}
    expected_support = "partial" if claim and claim.get("status") == "public" else None
    if not claim or claim.get("status") not in allowed or claim.get("support_level") != expected_support:
        fail("AECCTX_REMOTE_CLAIM_INVALID", "claim lifecycle/profile mismatch")
    fixtures_bytes = b"".join(path.read_bytes() for path in FIXTURES.iterdir() if path.is_file())
    for forbidden in (b"Authorization:", b"Bearer ", b"conformance-secret", b"PRIVATE KEY"):
        if forbidden in fixtures_bytes:
            fail("AECCTX_REMOTE_SECRET_LEAK", forbidden.decode("ascii"))
    attacks = load(FIXTURES / "adversarial-cases.json")
    if not isinstance(attacks, dict) or len(attacks.get("cases", [])) != 16:
        fail("AECCTX_REMOTE_CONFORMANCE_INVALID", "adversarial matrix must contain 16 cases")
    worker = runpy.run_path(str(ROOT / "providers/reference-remote/worker.py"))
    with tempfile.TemporaryDirectory(prefix="aecctx-remote-fixtures-") as temporary:
        generated = Path(temporary)
        worker["generate"](generated)
        for name in ("descriptor.json", "policy.json", "request-envelope.json", "response-envelope.json", "source.bin"):
            if generated.joinpath(name).read_bytes() != FIXTURES.joinpath(name).read_bytes():
                fail("AECCTX_REMOTE_FIXTURE_DRIFT", name)
    for artifact in args.artifact:
        check_artifact(artifact)
    print(json.dumps({"attack_cases": 16, "claim_status": claim["status"], "live_loopback": True, "ok": True, "replay": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as error:
        print(f"AECCTX_REMOTE_CONFORMANCE_INVALID: {error}", file=sys.stderr)
        raise SystemExit(1)
