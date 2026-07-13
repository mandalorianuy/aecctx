from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .adapters.dxf import ingest_dxf
from .adapters.geometry import ingest_geometry
from .adapters.ifc import ingest_ifc
from .adapters.image import ingest_image
from .adapters.pdf import ingest_pdf
from .ingest import ingest_opaque
from .package import PackageReader
from .validation import validate_package


INGESTERS: dict[str, Callable[..., Any]] = {
    "dxf": ingest_dxf,
    "geometry": ingest_geometry,
    "ifc": ingest_ifc,
    "image": ingest_image,
    "opaque": ingest_opaque,
    "pdf": ingest_pdf,
}


@dataclass(frozen=True, slots=True)
class ClaimRegistryResult:
    valid: bool
    errors: tuple[str, ...]


def validate_claim_registry(registry: dict[str, Any]) -> ClaimRegistryResult:
    errors: list[str] = []
    if registry.get("version") not in {"0.2.0", "0.3.0"}:
        errors.append("registry version must be 0.2.0 or 0.3.0")
    fixtures = registry.get("fixtures")
    fixture_ids: set[str] = set()
    if not isinstance(fixtures, list):
        errors.append("fixtures must be an array")
        fixtures = []
    for fixture in fixtures:
        if not isinstance(fixture, dict) or not isinstance(fixture.get("id"), str) or not fixture["id"]:
            errors.append("fixture requires a non-empty id")
            continue
        fixture_id = fixture["id"]
        if fixture_id in fixture_ids:
            errors.append(f"duplicate fixture id: {fixture_id}")
        fixture_ids.add(fixture_id)
        if not isinstance(fixture.get("path"), str) or not fixture["path"]:
            errors.append(f"{fixture_id}: fixture requires path")

    claims = registry.get("claims")
    claim_ids: set[str] = set()
    if not isinstance(claims, list):
        errors.append("claims must be an array")
        claims = []
    for claim in claims:
        if not isinstance(claim, dict) or not isinstance(claim.get("id"), str) or not claim["id"]:
            errors.append("claim requires a non-empty id")
            continue
        claim_id = claim["id"]
        if claim_id in claim_ids:
            errors.append(f"duplicate claim id: {claim_id}")
        claim_ids.add(claim_id)
        status = claim.get("status")
        if status not in {"target", "experimental", "public"}:
            errors.append(f"{claim_id}: invalid status")
        support_level = claim.get("support_level")
        if status == "target":
            if support_level is not None:
                errors.append(f"{claim_id}: target claim cannot declare support_level")
        elif support_level not in {"full", "partial", "opaque", "unsupported"}:
            errors.append(f"{claim_id}: implemented claim requires support_level")
        if not isinstance(claim.get("profile"), str) or not claim["profile"]:
            errors.append(f"{claim_id}: claim requires profile")
        if not isinstance(claim.get("provider_scope"), str) or not claim["provider_scope"]:
            errors.append(f"{claim_id}: claim requires provider_scope")
        platform_scope = claim.get("platform_scope")
        if status != "target" and (not isinstance(platform_scope, list) or not platform_scope):
            errors.append(f"{claim_id}: implemented claim requires platform_scope")
        configured_fixtures = claim.get("fixture_ids")
        configured_tests = claim.get("test_ids")
        if not isinstance(configured_fixtures, list):
            errors.append(f"{claim_id}: fixture_ids must be an array")
            configured_fixtures = []
        if not isinstance(configured_tests, list):
            errors.append(f"{claim_id}: test_ids must be an array")
            configured_tests = []
        if status == "public":
            if not configured_fixtures:
                errors.append(f"{claim_id}: public claim requires fixture_ids")
            if not configured_tests:
                errors.append(f"{claim_id}: public claim requires test_ids")
            if not isinstance(claim.get("evidence"), str) or not claim["evidence"]:
                errors.append(f"{claim_id}: public claim requires evidence")
        for fixture_id in configured_fixtures:
            if fixture_id not in fixture_ids:
                errors.append(f"{claim_id}: unknown fixture id {fixture_id}")
        for test_id in configured_tests:
            if not isinstance(test_id, str) or not test_id.startswith("tests/") or "::test_" not in test_id:
                errors.append(f"{claim_id}: invalid test id {test_id!r}")
    ordered = tuple(sorted(set(errors)))
    return ClaimRegistryResult(not ordered, ordered)


def validate_claim_registry_file(
    registry_path: str | Path,
    *,
    repository_root: str | Path | None = None,
) -> ClaimRegistryResult:
    path = Path(registry_path)
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return ClaimRegistryResult(False, (f"claim registry unreadable: {error}",))
    if not isinstance(registry, dict):
        return ClaimRegistryResult(False, ("claim registry must be an object",))
    semantic = validate_claim_registry(registry)
    errors = list(semantic.errors)
    root = Path(repository_root) if repository_root is not None else path.resolve().parents[2]
    fixtures = registry.get("fixtures", [])
    if isinstance(fixtures, list):
        for fixture in fixtures:
            if not isinstance(fixture, dict) or not isinstance(fixture.get("id"), str) or not isinstance(fixture.get("path"), str):
                continue
            fixture_path = root / fixture["path"]
            if not fixture_path.exists():
                errors.append(f"{fixture['id']}: fixture path does not exist: {fixture['path']}")
    claims = registry.get("claims", [])
    if isinstance(claims, list):
        for claim in claims:
            if not isinstance(claim, dict) or not isinstance(claim.get("id"), str):
                continue
            claim_id = claim["id"]
            evidence = claim.get("evidence")
            if isinstance(evidence, str) and not (root / evidence).is_file():
                errors.append(f"{claim_id}: evidence path does not exist: {evidence}")
            test_ids = claim.get("test_ids", [])
            if not isinstance(test_ids, list):
                continue
            for test_id in test_ids:
                if not isinstance(test_id, str) or "::" not in test_id:
                    continue
                test_file, test_name = test_id.split("::", 1)
                test_path = root / test_file
                if not test_path.is_file():
                    errors.append(f"{claim_id}: test file does not exist: {test_file}")
                elif f"def {test_name}(" not in test_path.read_text(encoding="utf-8"):
                    errors.append(f"{claim_id}: test function does not exist: {test_id}")
    ordered = tuple(sorted(set(errors)))
    return ClaimRegistryResult(not ordered, ordered)


def run_corpus(corpus_path: str | Path) -> dict[str, Any]:
    path = Path(corpus_path).resolve()
    root = path.parents[2]
    corpus = json.loads(path.read_text(encoding="utf-8"))
    entries = []
    with tempfile.TemporaryDirectory(prefix="aecctx-conformance-") as temporary:
        temporary_root = Path(temporary)
        for index, configured in enumerate(corpus["entries"]):
            source = root / configured["source"]
            source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            first = temporary_root / f"{index:02d}-a.aecctx"
            second = temporary_root / f"{index:02d}-b.aecctx"
            ingester = INGESTERS[configured["adapter"]]
            ingester(source, first, created_at=corpus["created_at"], package_form="zip")
            ingester(source, second, created_at=corpus["created_at"], package_form="zip")
            validation = validate_package(first)
            manifest = PackageReader(first).manifest
            entries.append(
                {
                    "adapter": configured["adapter"],
                    "claims_match": manifest["capabilities"] == configured["capabilities"] and source_hash == configured["sha256"],
                    "deterministic": first.read_bytes() == second.read_bytes(),
                    "id": configured["id"],
                    "logical_digest": manifest["logical_digest"],
                    "valid": validation.valid,
                }
            )
    return {
        "entries": entries,
        "ok": all(entry["valid"] and entry["deterministic"] and entry["claims_match"] for entry in entries),
        "version": corpus["version"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus")
    arguments = parser.parse_args()
    report = run_corpus(arguments.corpus)
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
