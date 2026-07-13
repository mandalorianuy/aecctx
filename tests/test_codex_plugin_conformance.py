from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
PLUGIN = ROOT / "plugins" / "aecctx-inspector"
CORPUS = ROOT / "conformance" / "v0.2" / "plugin-corpus.json"
CLAIMS = ROOT / "conformance" / "v0.2" / "claims.json"
CHECKER = ROOT / "scripts" / "check_codex_plugin_conformance.py"


def _run_checker(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_plugin_corpus_is_hash_bound_and_checker_is_green() -> None:
    assert CHECKER.is_file()
    payload = json.loads(CORPUS.read_text(encoding="utf-8"))
    assert payload["claim_id"] == "codex.aecctx-inspector"
    assert payload["claim_status"] == "target"
    assert payload["maximum_support"] == "partial"
    assert payload["profile"] == "aecctx-inspector-v1"
    assert len(payload["file_sha256"]) >= 10
    assert len(payload["operations"]) == 6
    assert len({entry["mcp_tool"] for entry in payload["operations"]}) == 6
    assert _run_checker().returncode == 0


def test_plugin_conformance_rejects_claim_state_drift(tmp_path: Path) -> None:
    claims_path = tmp_path / "claims.json"
    claims = json.loads(CLAIMS.read_text(encoding="utf-8"))
    claim = next(entry for entry in claims["claims"] if entry["id"] == "codex.aecctx-inspector")
    claim["status"] = "public"
    claim["support_level"] = "partial"
    claims_path.write_text(json.dumps(claims), encoding="utf-8")

    result = _run_checker("--claims", str(claims_path))
    assert result.returncode == 1
    assert "claim status does not match corpus" in result.stderr


def test_plugin_conformance_rejects_artifact_hash_drift(tmp_path: Path) -> None:
    plugin = tmp_path / "aecctx-inspector"
    shutil.copytree(PLUGIN, plugin)
    skill = plugin / "skills" / "inspect-package" / "SKILL.md"
    skill.write_text(skill.read_text(encoding="utf-8") + "\nmutation\n", encoding="utf-8")

    result = _run_checker("--plugin", str(plugin))
    assert result.returncode == 1
    assert "artifact hash mismatch" in result.stderr


def test_portable_verify_runs_plugin_contract_and_conformance_before_tests() -> None:
    script = (ROOT / "scripts" / "verify_portable.sh").read_text(encoding="utf-8")
    assert "scripts/check_codex_plugin.py" in script
    assert "scripts/check_codex_plugin_conformance.py" in script
    assert "conformance/v0.2/plugin-corpus.json" in script
    assert script.index("scripts/check_codex_plugin_conformance.py") < script.index('"$python_runtime" -m pytest')
