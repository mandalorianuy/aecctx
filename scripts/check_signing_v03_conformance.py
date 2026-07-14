#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

from aecctx.trust import evaluate_advanced_trust


ROOT = Path(__file__).parents[1]
CORPUS = ROOT / "conformance/v0.3/signing-corpus.json"
PACKAGE = ROOT / "fixtures/v0.2/signing/packages/minimal-v01.aecctx"
FIXTURE = ROOT / "fixtures/v0.3/signing"


def load_corpus(path: Path = CORPUS) -> dict[str, object]:
    value = json.loads(path.read_bytes())
    if set(value) != {"corpus_version", "fixture_id", "profile", "files", "cases"}:
        raise ValueError("signing corpus has an open or incomplete top-level contract")
    if value["corpus_version"] != "1" or value["fixture_id"] != "v03-signing-acx35":
        raise ValueError("signing corpus identity is invalid")
    ids: set[str] = set()
    paths: set[str] = set()
    for item in value["files"]:
        if set(item) != {"path", "sha256"}:
            raise ValueError("signing corpus file contract is invalid")
        logical = PurePosixPath(item["path"])
        if logical.is_absolute() or ".." in logical.parts or logical.parts[:3] != ("fixtures", "v0.3", "signing"):
            raise ValueError("signing corpus file path is unsafe")
        if item["path"] in paths:
            raise ValueError("signing corpus file path is duplicated")
        paths.add(item["path"])
        physical = ROOT / logical
        if not physical.is_file() or physical.is_symlink():
            raise ValueError(f"signing fixture missing: {logical}")
        if hashlib.sha256(physical.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"signing fixture hash mismatch: {logical}")
    for case in value["cases"]:
        expected = {"id", "bundle", "policy", "policy_satisfied", "lifecycle", "archival"}
        if set(case) != expected or case["id"] in ids:
            raise ValueError("signing corpus case is invalid or duplicated")
        ids.add(case["id"])
        for key in ("bundle", "policy"):
            relative = PurePosixPath(case[key])
            if relative.is_absolute() or ".." in relative.parts or not (FIXTURE / relative).is_file():
                raise ValueError("signing corpus case path is unsafe or missing")
    return value


def run(path: Path = CORPUS) -> dict[str, object]:
    corpus = load_corpus(path)
    results = []
    for case in corpus["cases"]:
        result = evaluate_advanced_trust(
            PACKAGE, (FIXTURE / case["bundle"]).read_bytes(), (FIXTURE / case["policy"]).read_bytes()
        )
        signer = result["signatures"][0]
        actual = {
            "id": case["id"], "policy_satisfied": result["policy_satisfied"],
            "lifecycle": signer["lifecycle_status"], "archival": signer["archival_time_status"],
        }
        expected = {"id": case["id"], "policy_satisfied": case["policy_satisfied"], "lifecycle": case["lifecycle"], "archival": case["archival"]}
        if actual != expected:
            raise ValueError(f"signing case mismatch: {case['id']}: {actual!r}")
        results.append(actual)
    return {"ok": True, "cases": results, "case_count": len(results)}


def main() -> int:
    report = run()
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
