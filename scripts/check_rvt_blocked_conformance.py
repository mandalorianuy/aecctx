#!/usr/bin/env python3
"""Validate the governed ACX-19 no-provider decision without claiming RVT support."""

from __future__ import annotations

import argparse
from email import policy
from email.parser import BytesParser
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile
import tomllib
from urllib.parse import urlparse
import zipfile

from jsonschema import Draft202012Validator, FormatChecker


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA = REPOSITORY_ROOT / "schemas" / "v0.2" / "rvt-provider-decision.schema.json"
ALLOWED_BLOCKERS = frozenset(
    {
        "AECCTX_RVT_ENTITLEMENT_UNAVAILABLE",
        "AECCTX_RVT_RUNTIME_UNAVAILABLE",
        "AECCTX_RVT_SANDBOX_PROFILE_UNAVAILABLE",
        "AECCTX_RVT_CI_UNAVAILABLE",
        "AECCTX_RVT_FIXTURE_RIGHTS_UNAVAILABLE",
        "AECCTX_RVT_NETWORK_POLICY_UNAPPROVED",
        "AECCTX_RVT_BILLING_POLICY_UNAPPROVED",
        "AECCTX_RVT_RETENTION_POLICY_UNAPPROVED",
    }
)
OFFICIAL_HOSTS = frozenset({"help.autodesk.com", "aps.autodesk.com", "www.opendesign.com", "github.com"})
EXPECTED_SOURCES = {
    "autodesk-revit-desktop": (
        "https://help.autodesk.com/cloudhelp/2018/ENU/Revit-API/Revit_API_Developers_Guide/Introduction/Getting_Started/Welcome_to_the_Revit_Platform_API/Installation.html",
    ),
    "autodesk-aps-automation": (
        "https://aps.autodesk.com/en/docs/design-automation/v3/developers_guide/overview/",
        "https://aps.autodesk.com/blog/aps-business-model-evolution",
    ),
    "oda-bimrv": (
        "https://www.opendesign.com/faq/bimrv",
        "https://www.opendesign.com/products/bimrv",
    ),
    "autodesk-revit-ifc-exporter": ("https://github.com/Autodesk/revit-ifc",),
}
EXPECTED_RVT_FIXTURE = {"id": "v02-rvt-acx19-anti-claim", "path": "fixtures/v0.2/rvt/not-a-real-rvt.rvt"}
EXPECTED_RVT_CLAIM = {
    "id": "rvt.external-provider",
    "status": "public",
    "support_level": "unsupported",
    "profile": "rvt-no-provider-blocked-v1",
    "platform_scope": ["any"],
    "provider_scope": "none",
    "fixture_ids": ["v02-rvt-acx19-anti-claim"],
    "test_ids": [
        "tests/test_rvt_blocked_profile.py::test_rvt_suffix_uses_deterministic_opaque_fallback",
        "tests/test_rvt_blocked_profile.py::test_cli_auto_does_not_promote_rvt_suffix",
    ],
    "evidence": "docs/evidence/ACX-19.md",
}
PROHIBITED_RUNTIME_SUFFIXES = (".dll", ".dylib", ".exe", ".pyd", ".so")
PROHIBITED_DEPENDENCY_NAMES = ("autodesk", "aps", "bimrv", "oda", "revit", "woodframing", "wfdomain", "wfimport")
ALLOWED_RVT_MEMBER_SUFFIX = "fixtures/v0.2/rvt/not-a-real-rvt.rvt"
PROHIBITED_CODE_SUFFIXES = (
    "src/aecctx/adapters/rvt.py",
    "src/aecctx/providers/rvt.py",
    "src/aecctx/schemas/v0_2/rvt-provider-event.schema.json",
)


def _load_json(path: Path, label: str) -> tuple[object | None, tuple[str, ...]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), ()
    except (OSError, json.JSONDecodeError) as error:
        return None, (f"{label} unreadable: {error}",)


def validate_decision(record: object) -> tuple[str, ...]:
    errors: list[str] = []
    schema, schema_errors = _load_json(SCHEMA, "decision schema")
    if schema_errors:
        return schema_errors
    assert isinstance(schema, dict)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors.extend(error.message for error in validator.iter_errors(record))
    if not isinstance(record, dict):
        return tuple(sorted(set(errors)))

    if record.get("selected_provider") is not None:
        errors.append("selected_provider must be null")

    candidates = record.get("candidates", [])
    candidate_ids = [item.get("id") for item in candidates if isinstance(item, dict)] if isinstance(candidates, list) else []
    if len(candidate_ids) != len(set(candidate_ids)):
        errors.append("duplicate candidate id")
    for item in candidates if isinstance(candidates, list) else []:
        if not isinstance(item, dict):
            continue
        candidate_id = item.get("id")
        blocker_codes = item.get("blocker_codes", [])
        for code in blocker_codes if isinstance(blocker_codes, list) else []:
            if code not in ALLOWED_BLOCKERS:
                errors.append(f"unknown blocker code: {code}")
        official_sources = item.get("official_sources", [])
        for source in official_sources if isinstance(official_sources, list) else []:
            if not isinstance(source, str) or urlparse(source).hostname not in OFFICIAL_HOSTS:
                errors.append(f"non-official decision source: {source}")
        if isinstance(candidate_id, str) and isinstance(official_sources, list):
            if tuple(official_sources) != EXPECTED_SOURCES.get(candidate_id):
                errors.append(f"official sources do not match candidate: {candidate_id}")

    alternatives = record.get("reopening_alternatives", [])
    alternative_ids = [item.get("id") for item in alternatives if isinstance(item, dict)] if isinstance(alternatives, list) else []
    if len(alternative_ids) != len(set(alternative_ids)):
        errors.append("duplicate reopening alternative id")

    serialized = json.dumps(record, sort_keys=True)
    if re.search(
        r"(?:/Users/|[A-Za-z]:\\\\|AKIA|BEGIN (?:RSA |EC )?PRIVATE KEY|client_secret)",
        serialized,
        re.IGNORECASE,
    ):
        errors.append("host path or credential-like value")
    if re.search(r'"(?:pending|to_be_decided|tbd)"', serialized, re.IGNORECASE):
        errors.append("mutable decision value")
    return tuple(sorted(set(errors)))


def validate_claim(registry: object) -> tuple[str, ...]:
    if not isinstance(registry, dict):
        return ("claim registry must be an object",)
    errors: list[str] = []
    fixtures = registry.get("fixtures")
    if not isinstance(fixtures, list) or EXPECTED_RVT_FIXTURE not in fixtures:
        errors.append("RVT anti-claim fixture mapping is missing or changed")
    claims = registry.get("claims")
    if not isinstance(claims, list):
        return tuple(sorted({*errors, "claim registry claims must be an array"}))
    rvt_claims = [
        item
        for item in claims
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].startswith("rvt.")
    ]
    for claim in rvt_claims:
        if claim.get("id") != "rvt.external-provider":
            errors.append(f"unexpected RVT claim id: {claim['id']}")
    blocked_claims = [item for item in rvt_claims if item.get("id") == "rvt.external-provider"]
    if len(blocked_claims) != 1 or blocked_claims[0] != EXPECTED_RVT_CLAIM:
        errors.append("RVT claim does not match blocked boundary")
    return tuple(sorted(set(errors)))


def validate_source_boundary(root: Path) -> tuple[str, ...]:
    errors: list[str] = []
    source_root = root / "src" / "aecctx"
    if not source_root.is_dir():
        return ()
    for path in sorted(source_root.rglob("*.py")):
        relative = path.relative_to(root).as_posix()
        lower_relative = relative.lower()
        if lower_relative.endswith(("src/aecctx/adapters/rvt.py", "src/aecctx/providers/rvt.py")):
            errors.append(f"RVT adapter/provider scaffolding: {relative}")
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            errors.append(f"executable source unreadable: {relative}: {error}")
            continue
        lower_content = content.lower()
        if "ingest_rvt" in lower_content:
            errors.append(f"RVT adapter/provider scaffolding: {relative}")
        if any(token in lower_content for token in ("woodframing", "wfdomain", "wfimport")):
            errors.append(f"consumer symbol in executable source: {relative}")
    return tuple(sorted(set(errors)))


def _safe_member(name: str) -> bool:
    if not name or "\\" in name:
        return False
    logical = PurePosixPath(name)
    return not logical.is_absolute() and ".." not in logical.parts


def _validate_member_name(name: str) -> tuple[str, ...]:
    lower = name.lower()
    errors: list[str] = []
    if not _safe_member(name):
        errors.append(f"unsafe artifact member: {name}")
    if lower.endswith(PROHIBITED_RUNTIME_SUFFIXES):
        errors.append(f"proprietary/native runtime member: {name}")
    if lower.endswith(PROHIBITED_CODE_SUFFIXES):
        errors.append(f"RVT adapter/provider scaffolding: {name}")
    if lower.endswith(".rvt") and not lower.endswith(ALLOWED_RVT_MEMBER_SUFFIX):
        errors.append(f"unexpected RVT artifact member: {name}")
    return tuple(errors)


def _requirement_name(requirement: str) -> str:
    match = re.match(r"[A-Za-z0-9_.-]+", requirement)
    return "" if match is None else match.group(0).lower().replace("_", "-")


def _validate_requirements(requirements: list[object]) -> tuple[str, ...]:
    errors: list[str] = []
    for requirement in requirements:
        if not isinstance(requirement, str):
            errors.append("dependency metadata contains a non-string requirement")
            continue
        name = _requirement_name(requirement)
        if not name or any(token in name for token in PROHIBITED_DEPENDENCY_NAMES):
            errors.append(f"prohibited core dependency: {requirement}")
    return tuple(errors)


def _validate_wheel(path: Path) -> tuple[str, ...]:
    errors: list[str] = []
    metadata: list[bytes] = []
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                errors.extend(_validate_member_name(info.filename))
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    errors.append(f"unsafe artifact member: {info.filename}")
                if info.filename.endswith(".dist-info/METADATA"):
                    if info.file_size > 1024 * 1024:
                        errors.append(f"wheel metadata exceeds 1 MiB: {info.filename}")
                    else:
                        metadata.append(archive.read(info))
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        return (f"artifact unreadable: {path}: {error}",)
    if len(metadata) != 1:
        errors.append("wheel must contain exactly one dist-info/METADATA")
    else:
        message = BytesParser(policy=policy.default).parsebytes(metadata[0])
        errors.extend(_validate_requirements(list(message.get_all("Requires-Dist", []))))
    return tuple(sorted(set(errors)))


def _validate_sdist(path: Path) -> tuple[str, ...]:
    errors: list[str] = []
    pyprojects: list[bytes] = []
    try:
        with tarfile.open(path, "r:*") as archive:
            for member in archive.getmembers():
                errors.extend(_validate_member_name(member.name))
                if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                    errors.append(f"unsafe artifact member: {member.name}")
                if member.isfile() and member.name.endswith("/pyproject.toml"):
                    if member.size > 1024 * 1024:
                        errors.append(f"sdist pyproject exceeds 1 MiB: {member.name}")
                        continue
                    handle = archive.extractfile(member)
                    if handle is None:
                        errors.append(f"sdist pyproject unreadable: {member.name}")
                    else:
                        pyprojects.append(handle.read())
    except (OSError, tarfile.TarError) as error:
        return (f"artifact unreadable: {path}: {error}",)
    if len(pyprojects) != 1:
        errors.append("sdist must contain exactly one root pyproject.toml")
    else:
        try:
            project = tomllib.loads(pyprojects[0].decode("utf-8")).get("project", {})
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            errors.append(f"sdist pyproject invalid: {error}")
        else:
            requirements = list(project.get("dependencies", [])) if isinstance(project, dict) else []
            optional = project.get("optional-dependencies", {}) if isinstance(project, dict) else {}
            if isinstance(optional, dict):
                for configured in optional.values():
                    if isinstance(configured, list):
                        requirements.extend(configured)
            errors.extend(_validate_requirements(requirements))
    return tuple(sorted(set(errors)))


def validate_artifact(path: Path) -> tuple[str, ...]:
    if not path.is_file() or path.is_symlink():
        return (f"artifact must be a regular file: {path}",)
    if path.suffix == ".whl":
        return _validate_wheel(path)
    if path.name.endswith(".tar.gz"):
        return _validate_sdist(path)
    return (f"unsupported artifact type: {path}",)


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--decision",
        type=Path,
        default=REPOSITORY_ROOT / "conformance" / "v0.2" / "rvt-provider-decision.json",
    )
    parser.add_argument("--claims", type=Path, default=REPOSITORY_ROOT / "conformance" / "v0.2" / "claims.json")
    parser.add_argument("--root", type=Path, default=REPOSITORY_ROOT)
    parser.add_argument("--artifact", type=Path, action="append", default=[])
    return parser.parse_args()


def main() -> int:
    arguments = _parse_arguments()
    decision, errors = _load_json(arguments.decision, "provider decision")
    claims, claim_errors = _load_json(arguments.claims, "claim registry")
    collected = [*errors, *claim_errors]
    if not arguments.root.is_dir():
        collected.append(f"repository root does not exist: {arguments.root}")
    else:
        collected.extend(validate_source_boundary(arguments.root))
    if decision is not None:
        collected.extend(validate_decision(decision))
    if claims is not None:
        collected.extend(validate_claim(claims))
    for artifact in arguments.artifact:
        collected.extend(validate_artifact(artifact))
    ordered = tuple(sorted(set(collected)))
    if ordered:
        for error in ordered:
            print(f"aecctx RVT blocked conformance: {error}", file=sys.stderr)
        return 1
    print("aecctx RVT blocked conformance: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
