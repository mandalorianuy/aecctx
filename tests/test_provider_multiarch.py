from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import aecctx.providers as providers


ARM64_ID = "sha256:" + "a" * 64
AMD64_ID = "sha256:" + "b" * 64
REQUIRED_AXES = {
    "cpu",
    "decompression",
    "environment",
    "filesystem",
    "input_bytes",
    "memory",
    "network",
    "open_files",
    "output_bytes",
    "process",
    "process_tree",
    "records",
    "recursion",
    "temporary_storage",
    "user_permissions",
    "wall_time",
}


def _descriptor() -> providers.ProviderDescriptor:
    return providers.ProviderDescriptor.from_dict(
        {
            "actions": ["extract"],
            "deterministic": True,
            "distribution": "operator-built-oci-image",
            "enforced_axes": {axis: True for axis in sorted(REQUIRED_AXES)},
            "enforcement_profile": "oci-docker-v1",
            "formats": ["application/x-test"],
            "license_spdx": "Apache-2.0",
            "network_mode": "disabled",
            "platforms": ["linux-container"],
            "protocol_version": "0.2",
            "provider_id": "org.aecctx.test.multiarch",
            "provider_version": "0.2.0",
            "runtime_digest": ARM64_ID,
            "runtime_version": "test-1",
        }
    )


def _registration(tmp_path: Path) -> providers.ProviderRegistration:
    worker = tmp_path / "worker.py"
    worker.write_text("pass\n", encoding="utf-8")
    return providers.ProviderRegistration(
        descriptor=_descriptor(),
        worker_module="aecctx.external.test",
        container_command=("python3", "/provider/worker.py"),
        worker_path=worker,
        oci_targets=(
            providers.OCIRuntimeTarget("linux", "arm64", "aecctx-test:arm64", ARM64_ID),
            providers.OCIRuntimeTarget("linux", "amd64", "aecctx-test:amd64", AMD64_ID),
        ),
    )


def test_runtime_target_selection_is_exact_and_order_independent(tmp_path: Path) -> None:
    registration = _registration(tmp_path)

    selected = providers.resolve_oci_target(registration, "linux", "amd64")

    assert selected == providers.OCIRuntimeTarget("linux", "amd64", "aecctx-test:amd64", AMD64_ID)


@pytest.mark.parametrize(
    ("platform", "architecture"),
    [("linux", "s390x"), ("darwin", "arm64"), ("windows", "amd64")],
)
def test_runtime_target_selection_rejects_unknown_platform_or_architecture(
    tmp_path: Path, platform: str, architecture: str
) -> None:
    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.resolve_oci_target(_registration(tmp_path), platform, architecture)

    assert captured.value.code == "AECCTX_PROVIDER_ARCHITECTURE_UNSUPPORTED"


def test_runtime_target_rejects_invalid_digest_and_duplicate_key(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        providers.OCIRuntimeTarget("linux", "arm64", "aecctx-test:arm64", "sha256:not-a-digest")

    registration = _registration(tmp_path)
    duplicate = providers.ProviderRegistration(
        descriptor=registration.descriptor,
        worker_module=registration.worker_module,
        container_command=registration.container_command,
        worker_path=registration.worker_path,
        oci_targets=(registration.oci_targets[0], registration.oci_targets[0]),
    )
    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.resolve_oci_target(duplicate, "linux", "arm64")

    assert captured.value.code == "AECCTX_PROVIDER_REGISTRATION_INVALID"


def test_oci_preflight_binds_local_image_id_os_and_architecture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docker = tmp_path / "docker"
    docker.write_text("#!/bin/sh\n", encoding="utf-8")
    docker.chmod(0o755)
    calls: list[tuple[str, ...]] = []

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(tuple(command))
        if command[1] == "version":
            return subprocess.CompletedProcess(command, 0, stdout="linux\n", stderr="")
        return subprocess.CompletedProcess(command, 0, stdout=f"{AMD64_ID} linux amd64\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    profile = providers.OCIDockerProfile(
        docker_executable=docker,
        image="aecctx-test:amd64",
        platform="linux",
        architecture="amd64",
    )

    profile.preflight(_registration(tmp_path))

    assert calls == [
        (str(docker), "version", "--format", "{{.Server.Os}}"),
        (
            str(docker),
            "image",
            "inspect",
            "--format",
            "{{.Id}} {{.Os}} {{.Architecture}}",
            "aecctx-test:amd64",
        ),
    ]
    assert not any("pull" in call or "build" in call for call in calls)


@pytest.mark.parametrize(
    ("inspect_output", "error_code"),
    [
        (f"{ARM64_ID} linux amd64\n", "AECCTX_PROVIDER_IMAGE_DIGEST_MISMATCH"),
        (f"{AMD64_ID} linux arm64\n", "AECCTX_PROVIDER_ARCHITECTURE_UNSUPPORTED"),
        (f"{AMD64_ID} windows amd64\n", "AECCTX_PROVIDER_ARCHITECTURE_UNSUPPORTED"),
    ],
)
def test_oci_preflight_rejects_digest_or_platform_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    inspect_output: str,
    error_code: str,
) -> None:
    docker = tmp_path / "docker"
    docker.write_text("#!/bin/sh\n", encoding="utf-8")
    docker.chmod(0o755)

    def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        stdout = "linux\n" if command[1] == "version" else inspect_output
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    profile = providers.OCIDockerProfile(
        docker_executable=docker,
        image="aecctx-test:amd64",
        platform="linux",
        architecture="amd64",
    )

    with pytest.raises(providers.ProviderExecutionError) as captured:
        profile.preflight(_registration(tmp_path))

    assert captured.value.code == error_code


def test_multiarch_registration_requires_explicit_profile_target(tmp_path: Path) -> None:
    profile = providers.OCIDockerProfile(image="aecctx-test:amd64")

    with pytest.raises(providers.ProviderExecutionError) as captured:
        profile.preflight(_registration(tmp_path))

    assert captured.value.code == "AECCTX_PROVIDER_ARCHITECTURE_UNSUPPORTED"


@pytest.mark.parametrize(
    ("registry_factory", "provider_id"),
    [
        (providers.tesseract_ocr_registry, providers.TESSERACT_OCR_PROVIDER_ID),
        (providers.step_iges_registry, providers.STEP_IGES_PROVIDER_ID),
        (providers.dwg_registry, providers.DWG_PROVIDER_ID),
    ],
)
def test_reviewed_provider_registrations_publish_both_linux_targets(
    registry_factory: object,
    provider_id: str,
) -> None:
    registry = registry_factory(repository_root=Path.cwd())  # type: ignore[operator]
    registration = registry.resolve(provider_id)

    assert [(target.platform, target.architecture) for target in registration.oci_targets] == [
        ("linux", "arm64"),
        ("linux", "amd64"),
    ]
    assert all(target.image_id.startswith("sha256:") and len(target.image_id) == 71 for target in registration.oci_targets)
