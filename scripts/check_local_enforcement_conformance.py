#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aecctx.conformance import validate_claim_registry_file  # noqa: E402
from aecctx.providers import (  # noqa: E402
    LocalProviderProfile,
    ProviderExecutionError,
    REQUIRED_ENFORCEMENT_AXES,
    local_enforcement_report,
    reference_provider_registry,
)


class ConformanceError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConformanceError(f"AECCTX_LOCAL_ENFORCEMENT_CORPUS_INVALID: {path}: {error}") from error
    if not isinstance(value, dict):
        raise ConformanceError(f"AECCTX_LOCAL_ENFORCEMENT_CORPUS_INVALID: {path} must contain an object")
    return value


def _artifact_members(path: Path) -> tuple[str, ...]:
    try:
        if path.suffix == ".whl" or zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                return tuple(sorted(archive.namelist()))
        if path.name.endswith((".tar.gz", ".tgz", ".tar")):
            with tarfile.open(path) as archive:
                return tuple(sorted(member.name for member in archive.getmembers() if member.isfile()))
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        raise ConformanceError(f"AECCTX_LOCAL_ENFORCEMENT_ARTIFACT_INVALID: {path}: {error}") from error
    raise ConformanceError(f"AECCTX_LOCAL_ENFORCEMENT_ARTIFACT_INVALID: unsupported artifact {path}")


def _check_artifact(path: Path) -> None:
    members = _artifact_members(path)
    forbidden_suffixes = (".dll", ".dylib", ".exe", ".so")
    forbidden = [member for member in members if member.lower().endswith(forbidden_suffixes)]
    if forbidden:
        raise ConformanceError(
            "AECCTX_LOCAL_ENFORCEMENT_RESTRICTED_ARTIFACT: " + ", ".join(forbidden)
        )
    if not any(member.endswith("aecctx/providers/local.py") for member in members):
        raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_MODULE_MISSING")


def _configured_profiles(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or len(value) != 3 or any(not isinstance(item, dict) for item in value):
        raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_CORPUS_INVALID: profiles must contain three objects")
    return value  # type: ignore[return-value]


def _attack_cases(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value or any(not isinstance(item, dict) for item in value):
        raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_CORPUS_INVALID: attack cases must be a non-empty array")
    cases = value  # type: ignore[assignment]
    ids = [case.get("id") for case in cases]
    if any(not isinstance(case_id, str) or not case_id for case_id in ids) or len(ids) != len(set(ids)):
        raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_CORPUS_INVALID: attack case IDs must be unique")
    for case in cases:
        if case.get("axis") not in REQUIRED_ENFORCEMENT_AXES:
            raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_CORPUS_INVALID: attack case axis is unknown")
    return cases


def check_conformance(*, artifacts: Iterable[Path] = ()) -> dict[str, object]:
    corpus = _read_json(ROOT / "conformance/v0.3/local-enforcement-corpus.json")
    if corpus.get("version") != "0.3.0" or corpus.get("claim_id") != "sandbox.local-enforcement":
        raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_CORPUS_INVALID: version or claim ID mismatch")

    fixture_config = corpus.get("fixture")
    if not isinstance(fixture_config, dict):
        raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_CORPUS_INVALID: fixture must be an object")
    relative = fixture_config.get("path")
    expected_hash = fixture_config.get("sha256")
    if not isinstance(relative, str) or not isinstance(expected_hash, str):
        raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_CORPUS_INVALID: fixture path/hash missing")
    fixture_path = ROOT / relative
    actual_hash = hashlib.sha256(fixture_path.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_FIXTURE_DIGEST_MISMATCH")
    fixture = _read_json(fixture_path)
    cases = _attack_cases(fixture.get("cases"))

    registration = reference_provider_registry().resolve("org.aecctx.reference-provider")
    seen_platforms: set[str] = set()
    for configured in _configured_profiles(corpus.get("profiles")):
        platform = configured.get("platform")
        if not isinstance(platform, str) or platform in seen_platforms:
            raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_CORPUS_INVALID: platform must be unique")
        seen_platforms.add(platform)
        first = local_enforcement_report(platform)
        second = local_enforcement_report(platform)
        if first.canonical_bytes() != second.canonical_bytes():
            raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_NONDETERMINISTIC")
        if first.profile_id != configured.get("profile_id") or list(first.diagnostics) != configured.get("diagnostics"):
            raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_REPORT_MISMATCH")
        if set(first.axes) != REQUIRED_ENFORCEMENT_AXES or first.executable:
            raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_REPORT_INCOMPLETE")
        profile = LocalProviderProfile(platform=platform)
        try:
            profile.preflight(registration)
        except ProviderExecutionError as error:
            if error.code != "AECCTX_PROVIDER_PROFILE_UNAVAILABLE" or error.details != {
                "local_enforcement": first.to_dict()
            }:
                raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_REJECTION_MISMATCH") from error
        else:
            raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_PROFILE_UNEXPECTEDLY_EXECUTABLE")

    if seen_platforms != {"linux", "macos", "windows"}:
        raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_CORPUS_INVALID: platform set mismatch")

    claims_result = validate_claim_registry_file(ROOT / "conformance/v0.3/claims.json", repository_root=ROOT)
    if not claims_result.valid:
        raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_CLAIM_INVALID: " + "; ".join(claims_result.errors))
    claims = _read_json(ROOT / "conformance/v0.3/claims.json").get("claims")
    claim = next(
        (item for item in claims if isinstance(item, dict) and item.get("id") == "sandbox.local-enforcement"),
        None,
    ) if isinstance(claims, list) else None
    if not isinstance(claim, dict):
        raise ConformanceError("AECCTX_LOCAL_ENFORCEMENT_CLAIM_MISSING")

    for artifact in artifacts:
        _check_artifact(artifact)

    return {
        "attack_cases": len(cases),
        "claim_status": claim.get("status"),
        "ok": True,
        "profiles": len(seen_platforms),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", action="append", default=[])
    arguments = parser.parse_args()
    try:
        result = check_conformance(artifacts=(Path(value) for value in arguments.artifact))
    except (ConformanceError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
