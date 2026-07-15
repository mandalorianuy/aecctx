from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path
from typing import Any, Iterable


_TASKS = tuple(f"ACX-{number}" for number in range(24, 38))
_CLAIM_STATUSES = {"public"}
_SUPPORT_LEVELS = {"full", "partial", "opaque", "unsupported"}
_NATIVE_SUFFIXES = {".dll", ".dylib", ".exe", ".pyd", ".so"}
_CONSUMER_TOKENS = ("wood" + "framing", "wf" + "domain", "wf" + "import")
_EXECUTABLE_SUFFIXES = {".py", ".pyi", ".sh"}


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid release document: {path}") from error
    if not isinstance(value, dict):
        raise ValueError(f"release document must be an object: {path}")
    return value


def _resolve(value: object, *, corpus_path: Path, repository_root: Path) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError("release path must be a non-empty string")
    path = Path(value)
    if path.is_absolute():
        return path
    candidate = repository_root / path
    return candidate if candidate.exists() else corpus_path.parent / path


def _validate_claim(claim: object, *, root: Path, fixture_ids: set[str]) -> tuple[str, str]:
    if not isinstance(claim, dict):
        raise ValueError("claim must be an object")
    claim_id = claim.get("id")
    if not isinstance(claim_id, str) or not claim_id:
        raise ValueError("claim id must be a non-empty string")
    if claim.get("status") not in _CLAIM_STATUSES:
        raise ValueError(f"target or blocked claim cannot enter release: {claim_id}")
    support = claim.get("support_level")
    if support not in _SUPPORT_LEVELS:
        raise ValueError(f"invalid support level for {claim_id}")
    for key in ("profile", "provider_scope", "platform_scope", "fixture_ids", "test_ids", "evidence"):
        if not claim.get(key):
            raise ValueError(f"claim {claim_id} lacks {key} evidence")
    if any(item not in fixture_ids for item in claim["fixture_ids"]):
        raise ValueError(f"claim {claim_id} references an unknown fixture")
    evidence = root / claim["evidence"]
    if not evidence.is_file():
        raise ValueError(f"claim {claim_id} evidence does not exist")
    for nodeid in claim["test_ids"]:
        test_path = root / str(nodeid).split("::", 1)[0]
        if not test_path.is_file():
            raise ValueError(f"claim {claim_id} test does not exist: {nodeid}")
    scope = claim["platform_scope"]
    if support != "unsupported" and (not isinstance(scope, list) or not any(item != "portable-replay" for item in scope)):
        raise ValueError(f"replay-only claim cannot enter release: {claim_id}")
    return claim_id, support


def validate_v03_release_corpus(corpus: str | Path, *, repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    corpus_path = Path(corpus).resolve()
    document = _load(corpus_path)
    if document.get("version") != "0.3.0":
        raise ValueError("release corpus version must be 0.3.0")
    if document.get("compatibility") != ["conformance/v0.1/corpus.json", "conformance/v0.2/corpus.json"]:
        raise ValueError("release corpus must bind exact v0.1/v0.2 compatibility corpora")

    claims_path = _resolve(document.get("claims"), corpus_path=corpus_path, repository_root=root)
    claim_registry = _load(claims_path)
    if claim_registry.get("version") != "0.3.0":
        raise ValueError("claim registry version must be 0.3.0")
    fixtures = claim_registry.get("fixtures")
    claims = claim_registry.get("claims")
    if not isinstance(fixtures, list) or not isinstance(claims, list):
        raise ValueError("claim registry must contain fixtures and claims")
    fixture_ids = {item.get("id") for item in fixtures if isinstance(item, dict) and isinstance(item.get("id"), str)}
    if len(fixture_ids) != len(fixtures):
        raise ValueError("duplicate or invalid fixture id")

    claim_support: dict[str, str] = {}
    for claim in claims:
        claim_id, support = _validate_claim(claim, root=root, fixture_ids=fixture_ids)
        if claim_id in claim_support:
            raise ValueError(f"duplicate claim id: {claim_id}")
        claim_support[claim_id] = support

    tasks = document.get("tasks")
    if not isinstance(tasks, list) or [task.get("id") for task in tasks if isinstance(task, dict)] != list(_TASKS):
        raise ValueError("release corpus must enumerate ACX-24 through ACX-37 in order")
    mapped: list[str] = []
    blocked: list[str] = []
    completed = 0
    for task in tasks:
        status = task.get("status")
        task_id = task["id"]
        if status == "completed":
            completed += 1
        elif status == "blocked":
            blocked.append(task_id)
        else:
            raise ValueError(f"task {task_id} is not completed or documented blocked")
        evidence = root / str(task.get("evidence", ""))
        if not evidence.is_file():
            raise ValueError(f"task {task_id} lacks evidence")
        claim_ids = task.get("claim_ids")
        if not isinstance(claim_ids, list) or not claim_ids:
            raise ValueError(f"task {task_id} lacks claim mapping")
        for claim_id in claim_ids:
            if claim_id not in claim_support:
                raise ValueError(f"unmapped claim: {claim_id}")
            if status == "blocked" and claim_support[claim_id] != "unsupported":
                raise ValueError(f"blocked task claim must remain unsupported: {claim_id}")
            mapped.append(claim_id)
    if len(mapped) != len(set(mapped)) or set(mapped) != set(claim_support):
        raise ValueError("claims must map exactly once to task outcomes")
    if blocked != ["ACX-34"]:
        raise ValueError("ACX-34 must remain the exact documented blocked task")

    suites = document.get("suites")
    if not isinstance(suites, list) or not suites:
        raise ValueError("release corpus must enumerate component suites")
    suite_ids: set[str] = set()
    for suite in suites:
        suite_id = suite.get("id") if isinstance(suite, dict) else None
        if not isinstance(suite_id, str) or suite_id in suite_ids:
            raise ValueError(f"duplicate or invalid suite id: {suite_id}")
        suite_ids.add(suite_id)
        suite_path = _resolve(suite.get("path"), corpus_path=corpus_path, repository_root=root)
        if not suite_path.is_file():
            raise ValueError(f"missing suite: {suite_path}")
        if hashlib.sha256(suite_path.read_bytes()).hexdigest() != suite.get("sha256"):
            raise ValueError(f"suite digest mismatch: {suite_id}")

    unsupported = sum(level == "unsupported" for level in claim_support.values())
    return {
        "blocked_tasks": blocked,
        "claim_count": len(claim_support),
        "completed_tasks": completed,
        "mapped_claim_count": len(mapped),
        "ok": True,
        "positive_claim_count": len(claim_support) - unsupported,
        "suite_count": len(suites),
        "unsupported_claim_count": unsupported,
        "version": "0.3.0",
    }


def _archive_members(path: Path) -> Iterable[tuple[str, bytes]]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                if not info.is_dir():
                    yield info.filename, archive.read(info)
        return
    if tarfile.is_tarfile(path):
        with tarfile.open(path) as archive:
            for info in archive.getmembers():
                if info.isfile():
                    stream = archive.extractfile(info)
                    if stream is not None:
                        yield info.name, stream.read()
        return
    yield path.name, path.read_bytes()


def scan_release_artifacts(artifacts: Iterable[str | Path]) -> dict[str, Any]:
    paths = [Path(path) for path in artifacts]
    if not paths:
        raise ValueError("release artifact scan requires artifacts")
    for path in paths:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"release artifact is missing or unsafe: {path}")
        for name, payload in _archive_members(path):
            lowered = name.casefold()
            suffix = Path(name).suffix.casefold()
            executable_contract = suffix in _EXECUTABLE_SUFFIXES or lowered.endswith(("/.mcp.json", "/plugin.json"))
            if executable_contract and any(token in lowered for token in _CONSUMER_TOKENS):
                raise ValueError(f"consumer leakage in release artifact: {name}")
            if "/fixtures/v0.3/rvt/" in f"/{lowered}" or lowered.endswith("/aecctx/adapters/rvt.py") or lowered.endswith("/aecctx/providers/rvt.py"):
                raise ValueError(f"restricted RVT leakage in release artifact: {name}")
            if suffix in _NATIVE_SUFFIXES or payload.startswith((b"\x7fELF", b"MZ", b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf")):
                raise ValueError(f"restricted binary in release artifact: {name}")
    return {"artifact_count": len(paths), "ok": True}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", nargs="?", default="conformance/v0.3/corpus.json")
    parser.add_argument("--repository-root", default=".")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(validate_v03_release_corpus(args.corpus, repository_root=args.repository_root), sort_keys=True))
    except ValueError as error:
        print(f"aecctx v0.3 release conformance: {error}", file=__import__("sys").stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
