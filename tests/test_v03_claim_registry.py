from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from aecctx.conformance import validate_claim_registry_file


ROOT = Path(__file__).parents[1]


def test_v03_claim_registry_is_complete() -> None:
    result = validate_claim_registry_file(ROOT / "conformance/v0.3/claims.json")

    assert result.valid is True, result.errors


def test_provider_multiarch_portable_corpus_is_digest_bound() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_provider_multiarch_conformance.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
