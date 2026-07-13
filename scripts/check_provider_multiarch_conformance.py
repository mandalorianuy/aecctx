#!/usr/bin/env python3
"""Validate the ACX-24 portable corpus and optional live runtime binding."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "conformance/v0.3/provider-multiarch-corpus.json"
EXPECTED = {
    (provider, architecture)
    for provider in (
        "org.aecctx.ocr.tesseract-tsv",
        "org.aecctx.step-iges.ocp",
        "org.aecctx.dwg.libredwg",
    )
    for architecture in ("arm64", "amd64")
}
ADVERSARIAL = {
    "filesystem": "AECCTX_PROVIDER_FILESYSTEM_DENIED",
    "malformed": "AECCTX_PROVIDER_PROTOCOL_INVALID",
    "memory": "AECCTX_PROVIDER_MEMORY_LIMIT_EXCEEDED",
    "network": "AECCTX_PROVIDER_NETWORK_DENIED",
    "output": "AECCTX_PROVIDER_OUTPUT_LIMIT_EXCEEDED",
    "process_tree": "AECCTX_PROVIDER_PROCESS_DENIED",
    "timeout": "AECCTX_PROVIDER_TIMEOUT",
}


def fail(message: str) -> None:
    raise SystemExit(f"aecctx provider multiarch conformance: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"invalid JSON at {path.relative_to(ROOT)}: {error}")


def checked_reference(reference: Any, label: str) -> Path:
    if not isinstance(reference, dict) or set(reference) != {"path", "sha256"}:
        fail(f"{label} must contain exact path and sha256")
    relative = reference["path"]
    expected = reference["sha256"]
    if not isinstance(relative, str) or not isinstance(expected, str):
        fail(f"{label} path and sha256 must be strings")
    path = ROOT / relative
    if not path.is_file() or sha256(path) != expected:
        fail(f"{label} missing or digest mismatch: {relative}")
    return path


def validate(*, require_live: bool) -> dict[str, Any]:
    corpus = load_json(CORPUS)
    if not isinstance(corpus, dict) or corpus.get("version") != "0.3.0":
        fail("corpus version must be 0.3.0")
    entries = corpus.get("entries")
    if not isinstance(entries, list) or len(entries) != 6:
        fail("corpus must contain exactly six provider/architecture entries")
    observed: set[tuple[str, str]] = set()
    equivalence: dict[str, tuple[str, dict[str, str]]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            fail("entry must be an object")
        provider = entry.get("provider_id")
        architecture = entry.get("architecture")
        if not isinstance(provider, str) or not isinstance(architecture, str):
            fail("entry requires provider_id and architecture")
        key = (provider, architecture)
        if key in observed:
            fail(f"duplicate entry: {provider}/{architecture}")
        observed.add(key)
        if entry.get("platform") != "linux":
            fail(f"{provider}/{architecture}: platform must be linux")
        for field in ("source", "descriptor", "request", "response", "receipt", "execution"):
            checked_reference(entry.get(field), f"{provider}/{architecture} {field}")
        artifacts = entry.get("artifacts")
        if not isinstance(artifacts, list):
            fail(f"{provider}/{architecture}: artifacts must be an array")
        for index, artifact in enumerate(artifacts):
            checked_reference(artifact, f"{provider}/{architecture} artifact {index}")
        receipt_path = ROOT / entry["receipt"]["path"]
        receipt = load_json(receipt_path)
        if (
            receipt.get("provider_id") != provider
            or receipt.get("platform") != "linux"
            or receipt.get("architecture") != architecture
            or receipt.get("image") != entry.get("image")
            or receipt.get("image_id") != entry.get("image_id")
            or receipt.get("no_push") is not True
        ):
            fail(f"{provider}/{architecture}: receipt identity mismatch")
        package_lock = receipt.get("package_lock")
        if not isinstance(package_lock, list) or not package_lock:
            fail(f"{provider}/{architecture}: receipt package lock is empty")
        lock_digest = hashlib.sha256("\n".join(package_lock).encode("utf-8")).hexdigest()
        if receipt.get("package_lock_sha256") != lock_digest:
            fail(f"{provider}/{architecture}: package lock digest mismatch")
        execution = load_json(ROOT / entry["execution"]["path"])
        if (
            execution.get("provider_id") != provider
            or execution.get("platform") != "linux"
            or execution.get("architecture") != architecture
            or execution.get("image_id") != entry.get("image_id")
            or execution.get("source_sha256") != entry["source"]["sha256"]
        ):
            fail(f"{provider}/{architecture}: execution identity mismatch")
        semantic = execution.get("response_semantic_sha256")
        artifact_digests = execution.get("artifact_digests")
        if not isinstance(semantic, str) or not isinstance(artifact_digests, dict):
            fail(f"{provider}/{architecture}: execution digests missing")
        previous = equivalence.setdefault(provider, (semantic, artifact_digests))
        if previous != (semantic, artifact_digests):
            fail(f"{provider}: arm64/amd64 semantic equivalence mismatch")
        if require_live:
            docker = shutil.which("docker")
            if docker is None:
                fail("Docker unavailable for --require-live")
            inspected = subprocess.run(
                [docker, "image", "inspect", "--format", "{{.Id}} {{.Os}} {{.Architecture}}", entry["image"]],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            expected_inspect = f"{entry['image_id']} linux {architecture}"
            if inspected.returncode != 0 or inspected.stdout.strip() != expected_inspect:
                fail(f"{provider}/{architecture}: live image binding mismatch")
    if observed != EXPECTED:
        fail("provider/architecture coverage mismatch")
    summary_path = checked_reference(corpus.get("security_summary"), "security summary")
    summary = load_json(summary_path)
    if summary.get("ok") is not True or summary.get("adversarial") != {"amd64": ADVERSARIAL, "arm64": ADVERSARIAL}:
        fail("security summary does not cover every governed adversarial outcome")
    return {"entries": len(entries), "live": require_live, "ok": True}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-live", action="store_true")
    args = parser.parse_args()
    print(json.dumps(validate(require_live=args.require_live), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
