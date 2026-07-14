from __future__ import annotations

import json
import runpy
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
PLUGIN = ROOT / "plugins" / "aecctx-inspector"
CHECKER = ROOT / "scripts" / "check_codex_plugin.py"
PROMPT_CASES = ROOT / "fixtures" / "v0.2" / "plugin" / "prompt-injection-cases.json"
MANAGER = PLUGIN / "scripts" / "manage.py"

EXPECTED_SKILLS = {
    "inspect-package": ("aecctx_validate", "aecctx_info", "aecctx_query"),
    "compare-revisions": ("aecctx_validate", "aecctx_diff"),
    "triage-capability-loss": ("aecctx_validate", "aecctx_info", "aecctx_query"),
    "render-agent-context": ("aecctx_validate", "aecctx_context"),
    "explain-quality-gate": ("aecctx_validate", "aecctx_gate"),
}


def _run_checker(plugin: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), str(plugin)],
        check=False,
        capture_output=True,
        text=True,
    )


def _copy_plugin(tmp_path: Path) -> Path:
    destination = tmp_path / "aecctx-inspector"
    shutil.copytree(PLUGIN, destination)
    return destination


def test_inspector_plugin_has_required_distribution_contract() -> None:
    assert (PLUGIN / ".codex-plugin" / "plugin.json").is_file()
    assert (PLUGIN / ".mcp.json").is_file()
    assert (PLUGIN / "assets" / "compatibility.json").is_file()
    assert (ROOT / "scripts" / "check_codex_plugin.py").is_file()


def test_plugin_checker_accepts_only_the_governed_manifest_and_compatibility(tmp_path: Path) -> None:
    assert _run_checker(PLUGIN).returncode == 0

    invalid = _copy_plugin(tmp_path)
    manifest_path = invalid / ".codex-plugin" / "plugin.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["version"] = "0.2.1"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    result = _run_checker(invalid)
    assert result.returncode == 1
    assert "version must be 0.3.0" in result.stderr


def test_plugin_checker_rejects_non_allowlisted_mcp_transport(tmp_path: Path) -> None:
    invalid = _copy_plugin(tmp_path)
    mcp_path = invalid / ".mcp.json"
    mcp_path.write_text(
        json.dumps({"mcpServers": {"aecctx": {"type": "http", "url": "https://example.invalid/mcp"}}}),
        encoding="utf-8",
    )
    result = _run_checker(invalid)
    assert result.returncode == 1
    assert "allowlist only the local aecctx-mcp stdio command" in result.stderr


def test_plugin_checker_rejects_compatibility_drift(tmp_path: Path) -> None:
    invalid = _copy_plugin(tmp_path)
    compatibility_path = invalid / "assets" / "compatibility.json"
    compatibility = json.loads(compatibility_path.read_text(encoding="utf-8"))
    compatibility["core_optional"] = False
    compatibility_path.write_text(json.dumps(compatibility), encoding="utf-8")
    result = _run_checker(invalid)
    assert result.returncode == 1
    assert "compatibility metadata does not match" in result.stderr


def test_plugin_skills_are_validate_first_read_only_and_citation_bound() -> None:
    for skill_name, tools in EXPECTED_SKILLS.items():
        skill_path = PLUGIN / "skills" / skill_name / "SKILL.md"
        contents = skill_path.read_text(encoding="utf-8")
        assert contents.startswith("---\n")
        assert f"name: {skill_name}" in contents
        assert "Validate first" in contents
        assert contents.index("aecctx_validate") < contents.index(tools[-1])
        assert "logical_digest" in contents
        assert "Untrusted data" in contents
        assert "Do not execute" in contents
        assert "Do not follow" in contents
        assert "Do not mutate" in contents
        assert "Do not select trust roots or create waivers" in contents
        assert "requires_review" in contents
        assert "must never become `pass`" in contents


def test_prompt_injection_fixture_covers_every_governed_surface() -> None:
    payload = json.loads(PROMPT_CASES.read_text(encoding="utf-8"))
    assert payload["license"] == "Apache-2.0"
    cases = payload["cases"]
    assert {case["surface"] for case in cases} == {
        "filename",
        "generated_context",
        "ifc_dxf_metadata",
        "ocr_provider_output",
        "pdf_text",
    }
    assert len({case["case_id"] for case in cases}) == len(cases)
    assert all(case["expected_treatment"] == "untrusted_data" for case in cases)
    assert all(case["content"] for case in cases)


def test_plugin_manager_enforces_compatible_core_versions() -> None:
    namespace = runpy.run_path(str(MANAGER))
    compatible = namespace["is_compatible_aecctx_version"]
    assert compatible("0.1.0")
    assert compatible("0.2.99")
    assert not compatible("0.0.9")
    assert not compatible("0.3.0")
    assert not compatible("invalid")


def test_plugin_manager_installs_create_only_and_uninstalls_exact_inventory(tmp_path: Path) -> None:
    destination = tmp_path / "aecctx-inspector"
    install = subprocess.run(
        [sys.executable, str(MANAGER), "install", "--destination", str(destination)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0, install.stderr
    assert (destination / ".aecctx-inspector-install.json").is_file()

    collision = subprocess.run(
        [sys.executable, str(MANAGER), "install", "--destination", str(destination)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert collision.returncode == 1
    assert "destination already exists" in collision.stderr

    unexpected = destination / "unexpected.txt"
    unexpected.write_text("preserve me", encoding="utf-8")
    refused = subprocess.run(
        [sys.executable, str(destination / "scripts" / "manage.py"), "uninstall", "--destination", str(destination)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert refused.returncode == 1
    assert "unexpected or modified content" in refused.stderr
    assert destination.is_dir()

    unexpected.unlink()
    removed = subprocess.run(
        [sys.executable, str(destination / "scripts" / "manage.py"), "uninstall", "--destination", str(destination)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert removed.returncode == 0, removed.stderr
    assert not destination.exists()


def test_plugin_manager_refuses_install_without_aecctx_distribution(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-S", str(MANAGER), "install", "--destination", str(tmp_path / "aecctx-inspector")],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "compatible aecctx distribution is required" in result.stderr
