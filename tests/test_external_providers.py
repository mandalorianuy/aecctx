from __future__ import annotations

import importlib.util
import aecctx.providers as providers
import pytest
import hashlib
import json
from pathlib import Path
import sys
import shutil
import subprocess


def test_external_provider_package_is_public() -> None:
    assert importlib.util.find_spec("aecctx.providers") is not None


def test_external_provider_contract_types_are_public() -> None:
    assert hasattr(providers, "ProviderDescriptor")
    assert hasattr(providers, "ProviderLimits")
    assert hasattr(providers, "ProviderRegistration")
    assert hasattr(providers, "ProviderRegistry")
    assert hasattr(providers, "ProviderRunner")
    assert hasattr(providers, "MacOSSeatbeltProfile")
    assert hasattr(providers, "OCIDockerProfile")
    assert hasattr(providers, "ProviderExecutionError")
    assert hasattr(providers, "build_provider_request")
    assert hasattr(providers, "validate_provider_response")
    assert hasattr(providers, "provider_descriptor_digest")
    assert hasattr(providers, "provider_response_payload_digest")
    assert hasattr(providers, "reference_provider_registry")
    assert hasattr(providers, "validate_provider_replay_corpus")


def test_reference_provider_replay_corpus_is_portable_and_valid() -> None:
    result = providers.validate_provider_replay_corpus("conformance/v0.2/provider-corpus.json")

    assert result == {
        "entries": [
            {
                "artifacts": 1,
                "id": "reference-provider-echo",
                "provider_id": "org.aecctx.reference-provider",
                "valid": True,
            }
        ],
        "ok": True,
        "version": "0.2.0",
    }


def test_provider_replay_entry_can_drive_offline_functional_mapping() -> None:
    replay = providers.load_provider_replay_entry("conformance/v0.2/provider-corpus.json", "reference-provider-echo")

    assert replay.descriptor.provider_id == "org.aecctx.reference-provider"
    assert replay.request["input"]["sha256"] == hashlib.sha256(replay.input_bytes).hexdigest()
    assert replay.result.ok is True
    assert replay.result.artifact_bytes["artifacts/echo.bin"] == replay.input_bytes


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


def descriptor_dict() -> dict[str, object]:
    return {
        "actions": ["describe", "extract", "finalize"],
        "deterministic": True,
        "distribution": "bundled-reference",
        "enforced_axes": {axis: True for axis in sorted(REQUIRED_AXES)},
        "enforcement_profile": "oci-docker-v1",
        "formats": ["application/x-aecctx-provider-fixture"],
        "license_spdx": "Apache-2.0",
        "network_mode": "disabled",
        "platforms": ["linux-container"],
        "protocol_version": "0.2",
        "provider_id": "org.aecctx.reference-provider",
        "provider_version": "0.2.0",
        "runtime_version": "python-3.12+",
        "runtime_digest": "sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df",
    }


def test_descriptor_requires_every_enforcement_axis() -> None:
    raw = descriptor_dict()
    raw["enforced_axes"] = {**raw["enforced_axes"], "filesystem": False}  # type: ignore[dict-item]

    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.ProviderDescriptor.from_dict(raw)

    assert captured.value.code == "AECCTX_PROVIDER_ENFORCEMENT_INCOMPLETE"


def test_descriptor_binds_digest_pinned_runtime() -> None:
    descriptor = providers.ProviderDescriptor.from_dict(descriptor_dict())

    assert descriptor.runtime_digest == "sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df"
    assert descriptor.to_dict()["runtime_digest"] == descriptor.runtime_digest


def test_registry_allows_only_reviewed_worker_modules_and_unique_ids() -> None:
    descriptor = providers.ProviderDescriptor.from_dict(descriptor_dict())
    registration = providers.ProviderRegistration(
        descriptor=descriptor,
        worker_module="aecctx.reference_provider_worker",
        runtime_roots=("/System", "/usr"),
    )
    registry = providers.ProviderRegistry(allowed_worker_modules={"aecctx.reference_provider_worker"})

    registry.register(registration)

    assert registry.resolve("org.aecctx.reference-provider") == registration
    with pytest.raises(providers.ProviderExecutionError) as duplicate:
        registry.register(registration)
    assert duplicate.value.code == "AECCTX_PROVIDER_DUPLICATE"

    unreviewed = providers.ProviderRegistration(descriptor=descriptor, worker_module="arbitrary.module")
    with pytest.raises(providers.ProviderExecutionError) as rejected:
        providers.ProviderRegistry(allowed_worker_modules=set()).register(unreviewed)
    assert rejected.value.code == "AECCTX_PROVIDER_LAUNCH_TARGET_UNREVIEWED"


def test_registry_rejects_unknown_provider_id() -> None:
    registry = providers.ProviderRegistry(allowed_worker_modules=set())

    with pytest.raises(providers.ProviderExecutionError) as captured:
        registry.resolve("caller.supplied.command")

    assert captured.value.code == "AECCTX_PROVIDER_NOT_REGISTERED"


def test_provider_limits_publish_complete_policy() -> None:
    policy = providers.ProviderLimits().to_dict()

    assert set(policy) == {
        "cpu_seconds",
        "max_decompression_ratio",
        "max_files",
        "max_input_bytes",
        "max_memory_bytes",
        "max_open_files",
        "max_output_bytes",
        "max_records",
        "max_recursion_depth",
        "wall_time_seconds",
    }


def test_request_is_content_addressed_and_deterministic() -> None:
    limits = providers.ProviderLimits(max_input_bytes=1024)

    first = providers.build_provider_request(
        "org.aecctx.reference-provider",
        "extract",
        b"fixture-input",
        limits=limits,
        configuration={"profile": "fixture"},
    )
    second = providers.build_provider_request(
        "org.aecctx.reference-provider",
        "extract",
        b"fixture-input",
        limits=limits,
        configuration={"profile": "fixture"},
    )

    digest = hashlib.sha256(b"fixture-input").hexdigest()
    assert first == second
    assert first["input"] == {"bytes": 13, "path": f"input/{digest}", "sha256": digest}
    assert first["request_id"] == hashlib.sha256(
        json.dumps({key: value for key, value in first.items() if key != "request_id"}, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def test_request_rejects_input_over_limit() -> None:
    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.build_provider_request(
            "org.aecctx.reference-provider",
            "extract",
            b"too-large",
            limits=providers.ProviderLimits(max_input_bytes=2),
        )

    assert captured.value.code == "AECCTX_PROVIDER_INPUT_LIMIT_EXCEEDED"


def test_request_rejects_commands_environment_and_host_paths() -> None:
    for configuration in (
        {"command": ["/bin/sh", "-c", "id"]},
        {"environment": {"TOKEN": "secret"}},
        {"output_path": "/Users/example/output"},
    ):
        with pytest.raises(providers.ProviderExecutionError) as captured:
            providers.build_provider_request(
                "org.aecctx.reference-provider",
                "extract",
                b"fixture",
                configuration=configuration,
            )
        assert captured.value.code == "AECCTX_PROVIDER_CONFIGURATION_UNSAFE"


def test_request_rejects_configuration_beyond_recursion_limit() -> None:
    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.build_provider_request(
            "org.aecctx.reference-provider",
            "extract",
            b"fixture",
            limits=providers.ProviderLimits(max_recursion_depth=2),
            configuration={"one": {"two": {"three": True}}},
        )

    assert captured.value.code == "AECCTX_PROVIDER_RECURSION_LIMIT_EXCEEDED"


def _valid_response(
    request: dict[str, object],
    descriptor: providers.ProviderDescriptor,
    output_root: Path,
) -> dict[str, object]:
    artifact = output_root / "artifacts" / "echo.txt"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"provider-output")
    response: dict[str, object] = {
        "artifacts": [
            {
                "bytes": len(b"provider-output"),
                "media_type": "text/plain",
                "path": "artifacts/echo.txt",
                "sha256": hashlib.sha256(b"provider-output").hexdigest(),
            }
        ],
        "attestation": {
            "descriptor_digest": providers.provider_descriptor_digest(descriptor),
            "deterministic": True,
            "enforcement_profile": "oci-docker-v1",
            "network_mode": "disabled",
            "provider_id": descriptor.provider_id,
            "provider_version": descriptor.provider_version,
            "request_digest": hashlib.sha256(json.dumps(request, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "response_payload_digest": "0" * 64,
            "runtime_version": descriptor.runtime_version,
            "runtime_digest": descriptor.runtime_digest,
        },
        "capability_report": {
            "identity": {"affected": [], "fallback": "none", "reason_codes": [], "support_level": "full"},
            "properties": {
                "affected": ["fixture"],
                "fallback": "retain opaque evidence",
                "reason_codes": ["AECCTX_REFERENCE_PROVIDER_NO_PROPERTIES"],
                "support_level": "unsupported",
            },
        },
        "diagnostics": [],
        "events": [
            {"event_type": "diagnostic", "payload": {"message": "reference"}, "sequence": 0, "source_locator": "input:fixture"}
        ],
        "ok": True,
        "protocol_version": "0.2",
        "provider_id": descriptor.provider_id,
        "request_id": request["request_id"],
        "resource_usage": {"output_bytes": len(b"provider-output")},
    }
    response["attestation"]["response_payload_digest"] = providers.provider_response_payload_digest(response)  # type: ignore[index]
    return response


def test_response_validates_events_artifacts_capabilities_and_attestation(tmp_path: Path) -> None:
    descriptor = providers.ProviderDescriptor.from_dict(descriptor_dict())
    limits = providers.ProviderLimits(max_output_bytes=1024, max_records=10)
    request = providers.build_provider_request(descriptor.provider_id, "extract", b"fixture", limits=limits)
    response = _valid_response(request, descriptor, tmp_path)

    result = providers.validate_provider_response(response, request, descriptor, tmp_path, limits=limits)

    assert result.ok is True
    assert result.events[0]["sequence"] == 0
    assert result.artifacts[0]["path"] == "artifacts/echo.txt"
    assert result.artifact_bytes["artifacts/echo.txt"] == b"provider-output"
    assert result.capability_report["properties"]["support_level"] == "unsupported"


def test_response_rejects_duplicate_sequence_and_forged_artifact(tmp_path: Path) -> None:
    descriptor = providers.ProviderDescriptor.from_dict(descriptor_dict())
    limits = providers.ProviderLimits(max_output_bytes=1024, max_records=10)
    request = providers.build_provider_request(descriptor.provider_id, "extract", b"fixture", limits=limits)
    response = _valid_response(request, descriptor, tmp_path)
    response["events"] = [response["events"][0], response["events"][0]]  # type: ignore[index]
    response["artifacts"][0]["sha256"] = "f" * 64  # type: ignore[index]
    response["attestation"]["response_payload_digest"] = providers.provider_response_payload_digest(response)  # type: ignore[index]

    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.validate_provider_response(response, request, descriptor, tmp_path, limits=limits)

    assert captured.value.code in {"AECCTX_PROVIDER_EVENT_SEQUENCE_INVALID", "AECCTX_PROVIDER_ARTIFACT_HASH_MISMATCH"}


def test_response_enforces_record_file_and_output_limits(tmp_path: Path) -> None:
    descriptor = providers.ProviderDescriptor.from_dict(descriptor_dict())
    request = providers.build_provider_request(descriptor.provider_id, "extract", b"fixture")

    records = _valid_response(request, descriptor, tmp_path / "records")
    records["events"] = [
        records["events"][0],  # type: ignore[index]
        {"event_type": "diagnostic", "payload": {}, "sequence": 1, "source_locator": "input:second"},
    ]
    records["attestation"]["response_payload_digest"] = providers.provider_response_payload_digest(records)  # type: ignore[index]
    with pytest.raises(providers.ProviderExecutionError) as record_error:
        providers.validate_provider_response(
            records,
            request,
            descriptor,
            tmp_path / "records",
            limits=providers.ProviderLimits(max_records=1),
        )
    assert record_error.value.code == "AECCTX_PROVIDER_RECORD_LIMIT_EXCEEDED"

    files_root = tmp_path / "files"
    files = _valid_response(request, descriptor, files_root)
    second = files_root / "artifacts" / "second.txt"
    second.write_bytes(b"second")
    files["artifacts"].append(  # type: ignore[union-attr]
        {"bytes": 6, "media_type": "text/plain", "path": "artifacts/second.txt", "sha256": hashlib.sha256(b"second").hexdigest()}
    )
    files["attestation"]["response_payload_digest"] = providers.provider_response_payload_digest(files)  # type: ignore[index]
    with pytest.raises(providers.ProviderExecutionError) as file_error:
        providers.validate_provider_response(
            files,
            request,
            descriptor,
            files_root,
            limits=providers.ProviderLimits(max_files=1),
        )
    assert file_error.value.code == "AECCTX_PROVIDER_FILE_LIMIT_EXCEEDED"

    output = _valid_response(request, descriptor, tmp_path / "output")
    with pytest.raises(providers.ProviderExecutionError) as output_error:
        providers.validate_provider_response(
            output,
            request,
            descriptor,
            tmp_path / "output",
            limits=providers.ProviderLimits(max_output_bytes=2),
        )
    assert output_error.value.code == "AECCTX_PROVIDER_OUTPUT_LIMIT_EXCEEDED"


def test_response_rejects_host_path_leakage(tmp_path: Path) -> None:
    descriptor = providers.ProviderDescriptor.from_dict(descriptor_dict())
    limits = providers.ProviderLimits(max_output_bytes=1024, max_records=10)
    request = providers.build_provider_request(descriptor.provider_id, "extract", b"fixture", limits=limits)
    response = _valid_response(request, descriptor, tmp_path)
    response["diagnostics"] = [{"message": "/Users/example/private/source.dwg"}]
    response["attestation"]["response_payload_digest"] = providers.provider_response_payload_digest(response)  # type: ignore[index]

    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.validate_provider_response(response, request, descriptor, tmp_path, limits=limits)

    assert captured.value.code == "AECCTX_PROVIDER_HOST_PATH_LEAKED"


def test_response_rejects_artifact_traversal_with_stable_code(tmp_path: Path) -> None:
    descriptor = providers.ProviderDescriptor.from_dict(descriptor_dict())
    request = providers.build_provider_request(descriptor.provider_id, "extract", b"fixture")
    response = _valid_response(request, descriptor, tmp_path)
    response["artifacts"][0]["path"] = "artifacts/../escape"  # type: ignore[index]
    response["attestation"]["response_payload_digest"] = providers.provider_response_payload_digest(response)  # type: ignore[index]

    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.validate_provider_response(response, request, descriptor, tmp_path)

    assert captured.value.code == "AECCTX_PROVIDER_ARTIFACT_PATH_UNSAFE"


def test_response_rejects_artifact_symlink_with_stable_code(tmp_path: Path) -> None:
    descriptor = providers.ProviderDescriptor.from_dict(descriptor_dict())
    request = providers.build_provider_request(descriptor.provider_id, "extract", b"fixture")
    response = _valid_response(request, descriptor, tmp_path)
    target = tmp_path / "outside.txt"
    target.write_bytes(b"provider-output")
    link = tmp_path / "artifacts" / "link.txt"
    link.symlink_to(target)
    response["artifacts"][0]["path"] = "artifacts/link.txt"  # type: ignore[index]
    response["attestation"]["response_payload_digest"] = providers.provider_response_payload_digest(response)  # type: ignore[index]

    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.validate_provider_response(response, request, descriptor, tmp_path)

    assert captured.value.code == "AECCTX_PROVIDER_ARTIFACT_PATH_UNSAFE"


def test_macos_profile_is_explicitly_unavailable_for_restricted_providers() -> None:
    registration = providers.reference_provider_registry().resolve("org.aecctx.reference-provider")
    profile = providers.MacOSSeatbeltProfile()

    with pytest.raises(providers.ProviderExecutionError) as captured:
        profile.preflight(registration)

    assert captured.value.code == "AECCTX_PROVIDER_PROFILE_UNAVAILABLE"


def test_oci_profile_rejects_missing_runtime(tmp_path: Path) -> None:
    registration = providers.reference_provider_registry().resolve("org.aecctx.reference-provider")
    profile = providers.OCIDockerProfile(docker_executable=tmp_path / "missing-docker")

    with pytest.raises(providers.ProviderExecutionError) as captured:
        profile.preflight(registration)

    assert captured.value.code == "AECCTX_PROVIDER_PROFILE_UNAVAILABLE"


def test_oci_profile_verifies_allowlisted_local_image_id(tmp_path: Path) -> None:
    docker = tmp_path / "docker"
    docker.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = version ]; then echo linux; exit 0; fi\n"
        "if [ \"$1\" = image ]; then echo sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa; exit 0; fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    base = providers.reference_provider_registry().resolve("org.aecctx.reference-provider")
    registration = providers.ProviderRegistration(
        descriptor=base.descriptor,
        worker_module=base.worker_module,
        container_image="aecctx-local-provider:0.2.0",
        container_image_id="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        container_command=base.container_command,
        worker_path=base.worker_path,
    )

    providers.OCIDockerProfile(docker_executable=docker, image="aecctx-local-provider:0.2.0").preflight(registration)


def test_oci_profile_rejects_local_image_id_mismatch(tmp_path: Path) -> None:
    docker = tmp_path / "docker"
    docker.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = version ]; then echo linux; exit 0; fi\n"
        "if [ \"$1\" = image ]; then echo sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb; exit 0; fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    docker.chmod(0o755)
    base = providers.reference_provider_registry().resolve("org.aecctx.reference-provider")
    registration = providers.ProviderRegistration(
        descriptor=base.descriptor,
        worker_module=base.worker_module,
        container_image="aecctx-local-provider:0.2.0",
        container_image_id="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        container_command=base.container_command,
        worker_path=base.worker_path,
    )

    with pytest.raises(providers.ProviderExecutionError) as captured:
        providers.OCIDockerProfile(docker_executable=docker, image="aecctx-local-provider:0.2.0").preflight(registration)

    assert captured.value.code == "AECCTX_PROVIDER_IMAGE_DIGEST_MISMATCH"


def test_oci_profile_command_enforces_network_filesystem_user_and_resources(tmp_path: Path) -> None:
    registration = providers.reference_provider_registry().resolve("org.aecctx.reference-provider")
    profile = providers.OCIDockerProfile()
    limits = providers.ProviderLimits(
        cpu_seconds=2,
        max_memory_bytes=128 * 1024 * 1024,
        max_open_files=32,
        wall_time_seconds=4,
    )

    command = profile.command(registration, tmp_path, limits, container_name="aecctx-test")
    rendered = " ".join(command)

    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert "--user=65532:65532" in command
    assert "--pids-limit=1" in command
    assert "--memory=134217728" in command
    assert "--cpus=0.5" in command
    assert "--ulimit=nofile=32:32" in command
    assert f"src={tmp_path.resolve() / 'input'},dst=/workspace/input,readonly" in rendered
    assert f"src={tmp_path.resolve() / 'request.json'},dst=/workspace/request.json,readonly" in rendered
    assert f"src={tmp_path.resolve() / 'output'},dst=/workspace/output" in rendered
    assert "dst=/provider/worker.py,readonly" in rendered
    assert "dst=/provider/reference_provider_worker.py" not in rendered


def _oci_reference_available() -> bool:
    profile_type = getattr(providers, "OCIDockerProfile", None)
    if profile_type is None:
        return False
    docker = shutil.which("docker")
    if docker is None:
        return False
    return subprocess.run(
        [docker, "image", "inspect", profile_type.DEFAULT_IMAGE],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0


@pytest.mark.skipif(not _oci_reference_available(), reason="digest-pinned OCI reference image is not installed")
def test_reference_provider_round_trip_is_content_addressed_and_cleans_workspace(tmp_path: Path) -> None:
    limits = providers.ProviderLimits(max_input_bytes=1024, max_output_bytes=4096, max_records=10, wall_time_seconds=5)
    runner = providers.ProviderRunner(
        registry=providers.reference_provider_registry(),
        profile=providers.OCIDockerProfile(),
        limits=limits,
        workspace_parent=tmp_path,
    )

    first = runner.run("org.aecctx.reference-provider", "extract", b"reference fixture")
    second = runner.run("org.aecctx.reference-provider", "extract", b"reference fixture")

    assert first.ok is True
    assert first.events == second.events
    assert first.artifact_bytes == second.artifact_bytes
    assert first.attestation["network_mode"] == "disabled"
    assert list(tmp_path.iterdir()) == []


def test_runner_rejects_action_not_declared_by_provider(tmp_path: Path) -> None:
    runner = providers.ProviderRunner(
        registry=providers.reference_provider_registry(),
        profile=providers.OCIDockerProfile(docker_executable=tmp_path / "unused"),
        workspace_parent=tmp_path,
    )

    with pytest.raises(providers.ProviderExecutionError) as captured:
        runner.run("org.aecctx.reference-provider", "render", b"fixture")

    assert captured.value.code == "AECCTX_PROVIDER_ACTION_UNSUPPORTED"


def _reference_runner(tmp_path: Path, **limit_overrides: object) -> providers.ProviderRunner:
    limits = providers.ProviderLimits(**limit_overrides)
    return providers.ProviderRunner(
        registry=providers.reference_provider_registry(),
        profile=providers.OCIDockerProfile(),
        limits=limits,
        workspace_parent=tmp_path,
    )


@pytest.mark.skipif(not _oci_reference_available(), reason="digest-pinned OCI reference image is not installed")
def test_oci_profile_denies_network_and_outside_filesystem_write(tmp_path: Path) -> None:
    runner = _reference_runner(tmp_path, max_output_bytes=8192, max_records=10, wall_time_seconds=5)

    network = runner.run(
        "org.aecctx.reference-provider",
        "extract",
        b"fixture",
        configuration={"network_attempt": True},
    )
    filesystem = runner.run(
        "org.aecctx.reference-provider",
        "extract",
        b"fixture",
        configuration={"outside_write": True},
    )

    assert network.ok is False
    assert network.error["code"] == "AECCTX_PROVIDER_NETWORK_DENIED"  # type: ignore[index]
    assert filesystem.ok is False
    assert filesystem.error["code"] == "AECCTX_PROVIDER_FILESYSTEM_DENIED"  # type: ignore[index]
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(not _oci_reference_available(), reason="digest-pinned OCI reference image is not installed")
def test_oci_profile_timeout_terminates_container_and_cleans_workspace(tmp_path: Path) -> None:
    runner = _reference_runner(tmp_path, max_output_bytes=8192, max_records=10, wall_time_seconds=0.1)

    with pytest.raises(providers.ProviderExecutionError) as captured:
        runner.run(
            "org.aecctx.reference-provider",
            "extract",
            b"fixture",
            configuration={"sleep_seconds": 2},
        )

    assert captured.value.code == "AECCTX_PROVIDER_TIMEOUT"
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(not _oci_reference_available(), reason="digest-pinned OCI reference image is not installed")
@pytest.mark.parametrize(
    ("configuration", "expected_code"),
    [
        ({"forge_hash": True}, "AECCTX_PROVIDER_ARTIFACT_HASH_MISMATCH"),
        ({"duplicate_sequence": True}, "AECCTX_PROVIDER_EVENT_SEQUENCE_INVALID"),
        ({"host_path_leak": True}, "AECCTX_PROVIDER_HOST_PATH_LEAKED"),
    ],
)
def test_runner_rejects_hostile_provider_output(
    tmp_path: Path,
    configuration: dict[str, bool],
    expected_code: str,
) -> None:
    runner = _reference_runner(tmp_path, max_output_bytes=8192, max_records=10, wall_time_seconds=5)

    with pytest.raises(providers.ProviderExecutionError) as captured:
        runner.run("org.aecctx.reference-provider", "extract", b"fixture", configuration=configuration)

    assert captured.value.code == expected_code
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(not _oci_reference_available(), reason="digest-pinned OCI reference image is not installed")
def test_oci_profile_enforces_memory_limit(tmp_path: Path) -> None:
    runner = _reference_runner(
        tmp_path,
        max_memory_bytes=32 * 1024 * 1024,
        max_output_bytes=8192,
        max_records=10,
        wall_time_seconds=5,
    )

    with pytest.raises(providers.ProviderExecutionError) as captured:
        runner.run(
            "org.aecctx.reference-provider",
            "extract",
            b"fixture",
            configuration={"allocate_bytes": 128 * 1024 * 1024},
        )

    assert captured.value.code == "AECCTX_PROVIDER_MEMORY_LIMIT_EXCEEDED"
