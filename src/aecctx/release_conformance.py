from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


POSITIVE_STATUSES = {"public", "experimental"}


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"release document must be an object: {path}")
    return value


def _resolve(value: str, *, corpus_path: Path, repository_root: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidate = repository_root / path
    return candidate if candidate.exists() else corpus_path.parent / path


def validate_release_corpus(corpus: str | Path, *, repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    corpus_path = Path(corpus).resolve()
    document = _load(corpus_path)
    if document.get("version") != "0.2.0":
        raise ValueError("release corpus version must be 0.2.0")

    claims_path = _resolve(str(document.get("claims", "")), corpus_path=corpus_path, repository_root=root)
    claims = _load(claims_path).get("claims")
    if not isinstance(claims, list):
        raise ValueError("claim registry must contain claims")
    claim_registry = _load(claims_path)
    fixture_ids = {item["id"] for item in claim_registry.get("fixtures", [])}

    seen: set[str] = set()
    mapped = 0
    for claim in claims:
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or claim_id in seen:
            raise ValueError(f"duplicate or invalid claim id: {claim_id}")
        seen.add(claim_id)
        if claim.get("status") not in POSITIVE_STATUSES and claim.get("status") != "target":
            raise ValueError(f"unknown claim status for {claim_id}")
        if claim.get("status") == "target":
            continue
        for key in ("support_level", "profile", "fixture_ids", "test_ids", "evidence"):
            if not claim.get(key):
                raise ValueError(f"claim {claim_id} lacks {key} evidence")
        if any(item not in fixture_ids for item in claim["fixture_ids"]):
            raise ValueError(f"claim {claim_id} references an unknown fixture")
        evidence = root / claim["evidence"]
        if not evidence.is_file():
            raise ValueError(f"claim {claim_id} evidence does not exist")
        for nodeid in claim["test_ids"]:
            test_path = root / nodeid.split("::", 1)[0]
            if not test_path.is_file():
                raise ValueError(f"claim {claim_id} test does not exist: {nodeid}")
        mapped += 1

    suites = document.get("suites")
    if not isinstance(suites, list) or not suites:
        raise ValueError("release corpus must enumerate component suites")
    suite_ids: set[str] = set()
    for suite in suites:
        suite_id = suite.get("id")
        if not isinstance(suite_id, str) or suite_id in suite_ids:
            raise ValueError(f"duplicate or invalid suite id: {suite_id}")
        suite_ids.add(suite_id)
        suite_path = root / suite["path"]
        if not suite_path.is_file():
            raise ValueError(f"missing suite: {suite_path}")
        digest = hashlib.sha256(suite_path.read_bytes()).hexdigest()
        if digest != suite.get("sha256"):
            raise ValueError(f"suite digest mismatch: {suite_id}")

    blocked = document.get("blocked_tasks")
    if blocked != ["ACX-19"]:
        raise ValueError("ACX-19 must remain the exact documented blocked task")
    return {
        "ok": True,
        "version": "0.2.0",
        "claim_count": mapped,
        "mapped_claim_count": mapped,
        "target_count": len(claims) - mapped,
        "suite_count": len(suites),
        "blocked_tasks": blocked,
    }
