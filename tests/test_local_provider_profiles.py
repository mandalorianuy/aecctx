from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import MappingProxyType
import zipfile

import pytest

import aecctx.providers as providers


ROOT = Path(__file__).parents[1]


PARENT_ENFORCED_AXES = {
    "decompression",
    "input_bytes",
    "output_bytes",
    "records",
    "recursion",
    "wall_time",
}

EXPECTED_PROFILES = {
    "linux": (
        "linux-native-v1",
        ("AECCTX_LOCAL_LINUX_SUPERVISOR_UNAVAILABLE",),
    ),
    "macos": (
        "macos-app-sandbox-v1",
        (
            "AECCTX_LOCAL_MACOS_RESOURCE_SUPERVISOR_UNAVAILABLE",
            "AECCTX_LOCAL_MACOS_SIGNED_HOST_REQUIRED",
        ),
    ),
    "windows": (
        "windows-appcontainer-job-v1",
        ("AECCTX_LOCAL_WINDOWS_BROKER_UNAVAILABLE",),
    ),
}


def test_local_enforcement_contract_is_public() -> None:
    assert hasattr(providers, "LocalEnforcementReport")
    assert hasattr(providers, "LocalProviderProfile")
    assert hasattr(providers, "local_enforcement_report")


@pytest.mark.parametrize("platform", sorted(EXPECTED_PROFILES))
def test_each_native_platform_has_a_complete_deterministic_rejection_report(platform: str) -> None:
    expected_profile, expected_diagnostics = EXPECTED_PROFILES[platform]

    first = providers.local_enforcement_report(platform)
    second = providers.local_enforcement_report(platform)

    assert first == second
    assert first.profile_id == expected_profile
    assert first.platform == platform
    assert first.executable is False
    assert first.diagnostics == expected_diagnostics
    assert isinstance(first.axes, MappingProxyType)
    assert set(first.axes) == providers.REQUIRED_ENFORCEMENT_AXES
    assert {axis for axis, state in first.axes.items() if state == "enforced"} == PARENT_ENFORCED_AXES
    assert {axis for axis, state in first.axes.items() if state == "unavailable"} == (
        providers.REQUIRED_ENFORCEMENT_AXES - PARENT_ENFORCED_AXES
    )
    assert first.canonical_bytes() == second.canonical_bytes()
    assert json.loads(first.canonical_bytes()) == first.to_dict()


def test_local_enforcement_report_rejects_inconsistent_executable_state() -> None:
    axes = {axis: "enforced" for axis in providers.REQUIRED_ENFORCEMENT_AXES}
    axes["memory"] = "unavailable"

    with pytest.raises(ValueError, match="executable"):
        providers.LocalEnforcementReport(
            profile_id="test-local-v1",
            platform="test",
            axes=axes,
            executable=True,
            diagnostics=(),
        )


def test_unknown_local_platform_is_rejected_without_fallback() -> None:
    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.local_enforcement_report("freebsd")

    assert captured.value.code == "AECCTX_PROVIDER_PLATFORM_UNSUPPORTED"
    assert captured.value.details == {}


@pytest.mark.parametrize("platform", sorted(EXPECTED_PROFILES))
def test_unavailable_profile_preflight_returns_machine_readable_report(platform: str) -> None:
    profile = providers.LocalProviderProfile(platform=platform)
    registration = providers.reference_provider_registry().resolve("org.aecctx.reference-provider")
    report = providers.local_enforcement_report(platform)

    with pytest.raises(providers.ProviderExecutionError) as captured:
        profile.preflight(registration)

    assert captured.value.code == "AECCTX_PROVIDER_PROFILE_UNAVAILABLE"
    assert captured.value.details == {"local_enforcement": report.to_dict()}


@pytest.mark.parametrize("platform", sorted(EXPECTED_PROFILES))
def test_provider_runner_rejects_before_workspace_creation_or_launch(tmp_path: Path, platform: str) -> None:
    workspace_parent = tmp_path / "workspaces"
    workspace_parent.mkdir()
    runner = providers.ProviderRunner(
        registry=providers.reference_provider_registry(),
        profile=providers.LocalProviderProfile(platform=platform),
        workspace_parent=workspace_parent,
    )

    with pytest.raises(providers.ProviderExecutionError) as captured:
        runner.run("org.aecctx.reference-provider", "extract", b"must-not-run")

    assert captured.value.code == "AECCTX_PROVIDER_PROFILE_UNAVAILABLE"
    assert list(workspace_parent.iterdir()) == []


def test_legacy_macos_seatbelt_rejection_carries_the_governed_report() -> None:
    registration = providers.reference_provider_registry().resolve("org.aecctx.reference-provider")

    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.MacOSSeatbeltProfile().preflight(registration)

    assert captured.value.code == "AECCTX_PROVIDER_PROFILE_UNAVAILABLE"
    report = captured.value.details["local_enforcement"]
    assert report["profile_id"] == "macos-app-sandbox-v1"
    assert report["executable"] is False


def test_local_enforcement_corpus_is_digest_bound_and_deterministic() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_local_enforcement_conformance.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report == {
        "attack_cases": 10,
        "claim_status": "public",
        "ok": True,
        "profiles": 3,
    }


def test_local_enforcement_checker_rejects_native_binary_in_distribution(tmp_path: Path) -> None:
    artifact = tmp_path / "aecctx-0.3.0-py3-none-any.whl"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("aecctx/providers/local.py", "# expected module\n")
        archive.writestr("aecctx/providers/native-broker.exe", b"not-a-real-binary")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/check_local_enforcement_conformance.py"),
            "--artifact",
            str(artifact),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "AECCTX_LOCAL_ENFORCEMENT_RESTRICTED_ARTIFACT" in completed.stderr
