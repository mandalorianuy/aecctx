from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from aecctx.conformance import validate_claim_registry_file


ROOT = Path(__file__).parents[1]


def test_v03_claim_registry_is_complete() -> None:
    result = validate_claim_registry_file(ROOT / "conformance/v0.3/claims.json")

    assert result.valid is True, result.errors


def test_remote_provider_claim_is_public_partial() -> None:
    registry = json.loads((ROOT / "conformance/v0.3/claims.json").read_text(encoding="utf-8"))
    claim = next(item for item in registry["claims"] if item["id"] == "sandbox.remote-provider")

    assert claim["status"] == "public"
    assert claim["support_level"] == "partial"
    assert claim["evidence"] == "docs/evidence/ACX-26.md"


def test_ifc_v03_claims_are_public_partial() -> None:
    registry = json.loads((ROOT / "conformance/v0.3/claims.json").read_text(encoding="utf-8"))
    claims = {
        item["id"]: item
        for item in registry["claims"]
        if item["id"] in {"ifc.native-2d.v03", "ifc.georeferencing.v03"}
    }

    assert set(claims) == {"ifc.native-2d.v03", "ifc.georeferencing.v03"}
    assert {claim["status"] for claim in claims.values()} == {"public"}
    assert {claim["support_level"] for claim in claims.values()} == {"partial"}
    assert {claim["evidence"] for claim in claims.values()} == {"docs/evidence/ACX-27.md"}


def test_provider_multiarch_portable_corpus_is_digest_bound() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_provider_multiarch_conformance.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
