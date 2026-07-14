from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from aecctx.context import render_context
from aecctx.diff import diff_packages
from aecctx.gate import GateLimits, evaluate_gate, load_gate_policy, read_gate_document
from aecctx.mcp_server import mcp_context, mcp_diff, mcp_gate, mcp_info, mcp_query, mcp_validate
from aecctx.query import query_package
from aecctx.validation import validate_package


ROOT = Path(__file__).parents[1]
PLUGIN = ROOT / "plugins" / "aecctx-inspector"
BUILDER = ROOT / "scripts" / "build_inspector_distribution.py"
CHECKER = ROOT / "scripts" / "check_inspector_v03_conformance.py"
MANAGER = PLUGIN / "scripts" / "manage.py"
HOSTS = json.loads((ROOT / "fixtures/v0.3/plugin/host-matrix.json").read_text(encoding="utf-8"))["hosts"]
PACKAGE = ROOT / "fixtures/minimal-aecctx"
GATE_PACKAGE = ROOT / "fixtures/v0.2/gate/packages/core.aecctx"
GATE_POLICY = ROOT / "fixtures/v0.2/gate/policies/pass.json"


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_v03_distribution_contract_starts_with_governed_files() -> None:
    assert BUILDER.is_file()
    assert CHECKER.is_file()
    assert (PLUGIN / "assets/distribution.json").is_file()
    assert json.loads((PLUGIN / ".codex-plugin/plugin.json").read_text())["version"] == "0.3.0"


def test_distribution_build_is_byte_reproducible_and_inventory_bound(tmp_path: Path) -> None:
    builder = _load_script(BUILDER, "aecctx_inspector_builder")
    first = builder.build_distribution(PLUGIN, tmp_path / "first.zip")
    second = builder.build_distribution(PLUGIN, tmp_path / "second.zip")
    assert first.archive_sha256 == second.archive_sha256
    assert (tmp_path / "first.zip").read_bytes() == (tmp_path / "second.zip").read_bytes()
    assert first.inventory_sha256 == second.inventory_sha256
    with zipfile.ZipFile(tmp_path / "first.zip") as archive:
        assert archive.namelist() == sorted(archive.namelist())
        assert all(name.startswith("aecctx-inspector/") for name in archive.namelist())
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())


def test_distribution_checksum_inventory_and_optional_signature_fail_closed(tmp_path: Path) -> None:
    cryptography = pytest.importorskip("cryptography")
    del cryptography
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    builder = _load_script(BUILDER, "aecctx_inspector_signing_builder")
    archive = tmp_path / "plugin.zip"
    result = builder.build_distribution(PLUGIN, archive)
    private_key = Ed25519PrivateKey.generate()
    signature = builder.sign_distribution(result, private_key)
    public_key = private_key.public_key()
    assert builder.verify_distribution_signature(result, signature, public_key)
    mutated = bytearray(archive.read_bytes())
    mutated[-1] ^= 1
    archive.write_bytes(mutated)
    with pytest.raises(builder.DistributionError, match="checksum"):
        builder.verify_archive(archive, result.archive_sha256)
    bad_signature = dict(signature)
    replacement = "A" if bad_signature["signature"][0] != "A" else "B"
    bad_signature["signature"] = replacement + bad_signature["signature"][1:]
    assert not builder.verify_distribution_signature(result, bad_signature, public_key)


def test_verified_archive_install_is_create_only_and_rejects_unsafe_paths(tmp_path: Path) -> None:
    builder = _load_script(BUILDER, "aecctx_inspector_archive_installer")
    archive = tmp_path / "plugin.zip"
    result = builder.build_distribution(PLUGIN, archive)
    destination = tmp_path / "installed" / "aecctx-inspector"
    builder.install_distribution(
        archive,
        result.archive_sha256,
        destination,
        host_profile="codex-local-v1-macos",
        mcp_version="1.28.1",
    )
    assert (destination / ".aecctx-inspector-install.json").is_file()
    with pytest.raises(builder.DistributionError, match="already exists"):
        builder.install_distribution(archive, result.archive_sha256, destination, host_profile="codex-local-v1-macos", mcp_version="1.28.1")

    unsafe = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(unsafe, "w") as value:
        value.writestr("aecctx-inspector/../escape", b"bad")
    unsafe_sha = hashlib.sha256(unsafe.read_bytes()).hexdigest()
    with pytest.raises(builder.DistributionError, match="unsafe"):
        builder.verify_archive(unsafe, unsafe_sha)


def test_manager_install_upgrade_rollback_downgrade_and_exact_uninstall(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = _load_script(MANAGER, "aecctx_inspector_manager_v03")
    monkeypatch.setattr(manager, "_installed_aecctx_version", lambda: "0.2.0")
    destination = tmp_path / "aecctx-inspector"
    manager.install(PLUGIN, destination, host_profile="codex-local-v1-macos", mcp_version="1.28.1")
    original = manager._inventory(destination)
    with pytest.raises(manager.PluginManagementError, match="already exists"):
        manager.install(PLUGIN, destination, host_profile="codex-local-v1-macos", mcp_version="1.28.1")

    upgrade_destination = tmp_path / "upgrade" / "aecctx-inspector"
    manager.install(PLUGIN, upgrade_destination, host_profile="codex-local-v1-macos", mcp_version="1.28.1")
    legacy_marker_path = upgrade_destination / ".aecctx-inspector-install.json"
    legacy_marker = json.loads(legacy_marker_path.read_text())
    legacy_marker["plugin_version"] = "0.2.0"
    legacy_marker["profile"] = "aecctx-inspector-v1"
    legacy_marker_path.write_text(json.dumps(legacy_marker, sort_keys=True, separators=(",", ":")) + "\n")
    manager.upgrade(PLUGIN, upgrade_destination, host_profile="codex-local-v1-macos", mcp_version="1.28.1")
    upgraded_marker = json.loads((upgrade_destination / ".aecctx-inspector-install.json").read_text())
    assert upgraded_marker["plugin_version"] == "0.3.0"
    manager.uninstall(upgrade_destination)

    older = tmp_path / "older" / "aecctx-inspector"
    shutil.copytree(PLUGIN, older)
    manifest_path = older / ".codex-plugin/plugin.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["version"] = "0.2.0"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(manager.PluginManagementError, match="downgrade"):
        manager.upgrade(older, destination, host_profile="codex-local-v1-macos", mcp_version="1.28.1")
    assert manager._inventory(destination) == original

    legacy_marker_path = destination / ".aecctx-inspector-install.json"
    legacy_marker = json.loads(legacy_marker_path.read_text())
    legacy_marker["plugin_version"] = "0.2.0"
    legacy_marker["profile"] = "aecctx-inspector-v1"
    legacy_marker_path.write_text(json.dumps(legacy_marker, sort_keys=True, separators=(",", ":")) + "\n")
    original_copy = manager._copy_install
    monkeypatch.setattr(manager, "_copy_install", lambda *args, **kwargs: (_ for _ in ()).throw(OSError("injected staging failure")))
    with pytest.raises(OSError, match="injected staging failure"):
        manager.upgrade(PLUGIN, destination, host_profile="codex-local-v1-macos", mcp_version="1.28.1")
    monkeypatch.setattr(manager, "_copy_install", original_copy)
    assert destination.is_dir()
    assert manager._inventory(destination) == original

    broken = tmp_path / "broken" / "aecctx-inspector"
    shutil.copytree(PLUGIN, broken)
    (broken / "assets/distribution.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(manager.PluginManagementError):
        manager.upgrade(broken, destination, host_profile="codex-local-v1-macos", mcp_version="1.28.1")
    assert manager._inventory(destination) == original

    unexpected = destination / "unknown.txt"
    unexpected.write_text("preserve", encoding="utf-8")
    with pytest.raises(manager.PluginManagementError, match="unexpected or modified"):
        manager.uninstall(destination)
    unexpected.unlink()
    manager.uninstall(destination)
    assert not destination.exists()


def test_core_mcp_and_host_compatibility_fail_closed() -> None:
    manager = _load_script(MANAGER, "aecctx_inspector_compatibility_v03")
    assert manager.is_compatible_v03_core_version("0.2.0")
    assert manager.is_compatible_v03_core_version("0.3.99")
    assert not manager.is_compatible_v03_core_version("0.1.99")
    assert not manager.is_compatible_v03_core_version("0.4.0")
    assert manager.is_compatible_mcp_version("1.20.0")
    assert manager.is_compatible_mcp_version("1.28.1")
    assert not manager.is_compatible_mcp_version("1.19.99")
    assert not manager.is_compatible_mcp_version("2.0.0")
    assert manager.HOST_PROFILES == {"codex-local-v1-linux", "codex-local-v1-macos", "codex-local-v1-windows"}


@pytest.mark.parametrize("host", HOSTS, ids=lambda host: host["host_profile"])
def test_every_claimed_host_has_exact_six_operation_parity(host: dict[str, str]) -> None:
    assert host["python"] == "3.12"
    assert host["mcp"] == "1.28.1"
    assert mcp_validate(str(PACKAGE)) == validate_package(PACKAGE).to_dict()
    validated = validate_package(PACKAGE)
    assert validated.manifest is not None
    assert mcp_info(str(PACKAGE))["logical_digest"] == validated.manifest["logical_digest"]
    expression = 'entity.original_class == "LINE"'
    assert mcp_query(str(PACKAGE), expression) == query_package(PACKAGE, expression).to_dict()
    assert mcp_diff(str(PACKAGE), str(PACKAGE)) == diff_packages(PACKAGE, PACKAGE).to_dict()
    assert mcp_context(str(PACKAGE), token_budget=2000, chunk_token_budget=500) == render_context(PACKAGE, token_budget=2000, chunk_token_budget=500).to_dict()
    limits = GateLimits()
    policy = load_gate_policy(read_gate_document(GATE_POLICY, maximum_bytes=limits.max_policy_bytes, label="gate policy"), limits=limits)
    assert mcp_gate(str(GATE_PACKAGE), str(GATE_POLICY)) == evaluate_gate(GATE_PACKAGE, policy, limits=limits).to_dict()


def test_v03_checker_binds_claim_hosts_lifecycle_security_and_core_independence() -> None:
    result = subprocess.run([sys.executable, str(CHECKER), "--require-public"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout
