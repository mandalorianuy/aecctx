#!/usr/bin/env python3
"""Validate the governed ACX-19 no-provider decision without claiming RVT support."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlparse

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


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--claims", type=Path, required=True)
    parser.add_argument("--root", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    arguments = _parse_arguments()
    decision, errors = _load_json(arguments.decision, "provider decision")
    claims, claim_errors = _load_json(arguments.claims, "claim registry")
    collected = [*errors, *claim_errors]
    if not arguments.root.is_dir():
        collected.append(f"repository root does not exist: {arguments.root}")
    if decision is not None:
        collected.extend(validate_decision(decision))
    if claims is not None:
        collected.extend(validate_claim(claims))
    ordered = tuple(sorted(set(collected)))
    if ordered:
        for error in ordered:
            print(f"aecctx RVT blocked conformance: {error}", file=sys.stderr)
        return 1
    print("aecctx RVT blocked conformance: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
