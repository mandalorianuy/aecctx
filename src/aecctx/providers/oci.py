from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .models import ProviderExecutionError, ProviderLimits, ProviderRegistration, resolve_oci_target


@dataclass(frozen=True, slots=True)
class OCIDockerProfile:
    DEFAULT_IMAGE = "python@sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df"

    docker_executable: Path = Path("/usr/local/bin/docker")
    image: str = DEFAULT_IMAGE
    profile_id: str = "oci-docker-v1"
    platform: str | None = None
    architecture: str | None = None

    @staticmethod
    def _pids_limit(registration: ProviderRegistration) -> int:
        value = registration.container_pids_limit
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 4:
            raise ProviderExecutionError(
                "AECCTX_PROVIDER_PROCESS_LIMIT_INVALID",
                "OCI provider PID ceiling must be an integer from 1 through 4",
            )
        return value

    def preflight(self, registration: ProviderRegistration) -> None:
        self._pids_limit(registration)
        multiarch_selected = self.platform is not None and self.architecture is not None
        descriptor = registration.descriptor
        if not self.docker_executable.is_file() or not os.access(self.docker_executable, os.X_OK):
            raise ProviderExecutionError("AECCTX_PROVIDER_PROFILE_UNAVAILABLE", "Reviewed Docker runtime is unavailable")
        if descriptor.enforcement_profile != self.profile_id or "linux-container" not in descriptor.platforms:
            raise ProviderExecutionError("AECCTX_PROVIDER_PROFILE_MISMATCH", "Provider descriptor does not admit the OCI profile")
        if descriptor.network_mode != "disabled":
            raise ProviderExecutionError("AECCTX_PROVIDER_NETWORK_POLICY_UNSUPPORTED", "Reference OCI profile requires network_mode=disabled")
        if registration.oci_targets and multiarch_selected:
            target = resolve_oci_target(registration, self.platform, self.architecture)
            if target.image != self.image:
                raise ProviderExecutionError("AECCTX_PROVIDER_IMAGE_UNPINNED", "Provider image must match the reviewed architecture target")
            local_image_id = target.image_id
        elif registration.container_image == self.image and self.platform is None and self.architecture is None:
            if registration.container_image != self.image:
                raise ProviderExecutionError("AECCTX_PROVIDER_IMAGE_UNPINNED", "Provider image must match the reviewed image registration")
            local_image_id = registration.container_image_id
        elif registration.oci_targets:
            raise ProviderExecutionError(
                "AECCTX_PROVIDER_ARCHITECTURE_UNSUPPORTED",
                "Multi-architecture OCI providers require an explicit reviewed platform and architecture target",
            )
        else:
            raise ProviderExecutionError("AECCTX_PROVIDER_IMAGE_UNPINNED", "Provider image must match the reviewed image registration")
        if "@sha256:" not in self.image and local_image_id is None:
            raise ProviderExecutionError("AECCTX_PROVIDER_IMAGE_UNPINNED", "Mutable image tags require an allowlisted immutable local image ID")
        if local_image_id is not None:
            digest = local_image_id.removeprefix("sha256:")
            if not local_image_id.startswith("sha256:") or len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
                raise ProviderExecutionError("AECCTX_PROVIDER_IMAGE_UNPINNED", "Local image ID must be a sha256 digest")
        if registration.worker_path is None or not registration.worker_path.is_file() or not registration.container_command:
            raise ProviderExecutionError("AECCTX_PROVIDER_LAUNCH_TARGET_UNREVIEWED", "Provider container launch target is incomplete")
        try:
            version = subprocess.run(
                [str(self.docker_executable), "version", "--format", "{{.Server.Os}}"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            image = subprocess.run(
                [
                    str(self.docker_executable),
                    "image",
                    "inspect",
                    "--format",
                    "{{.Id}} {{.Os}} {{.Architecture}}",
                    self.image,
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ProviderExecutionError("AECCTX_PROVIDER_PROFILE_UNAVAILABLE", f"Docker preflight failed: {error}") from error
        if version.returncode != 0 or version.stdout.strip() != "linux" or image.returncode != 0:
            raise ProviderExecutionError(
                "AECCTX_PROVIDER_PROFILE_UNAVAILABLE",
                "Reviewed Linux-container runtime or digest-pinned image is unavailable; images are never pulled implicitly",
            )
        image_fields = image.stdout.strip().split()
        if not image_fields or (multiarch_selected and len(image_fields) != 3):
            raise ProviderExecutionError(
                "AECCTX_PROVIDER_PROFILE_UNAVAILABLE",
                "Reviewed provider image identity, OS and architecture are unavailable",
            )
        image_id = image_fields[0]
        if local_image_id is not None and image_id != local_image_id:
            raise ProviderExecutionError("AECCTX_PROVIDER_IMAGE_DIGEST_MISMATCH", "Installed provider image ID does not match the reviewed registration")
        if self.platform is not None and self.architecture is not None and (
            len(image_fields) != 3 or image_fields[1] != self.platform or image_fields[2] != self.architecture
        ):
            raise ProviderExecutionError(
                "AECCTX_PROVIDER_ARCHITECTURE_UNSUPPORTED",
                "Installed provider image does not match the reviewed OS and architecture target",
            )

    def command(
        self,
        registration: ProviderRegistration,
        workspace: str | Path,
        limits: ProviderLimits,
        *,
        container_name: str,
    ) -> tuple[str, ...]:
        root = Path(workspace).resolve()
        pids_limit = self._pids_limit(registration)
        worker_path = registration.worker_path.resolve() if registration.worker_path is not None else Path("/missing")
        cpu_quota = min(1.0, limits.cpu_seconds / limits.wall_time_seconds)
        return (
            str(self.docker_executable),
            "run",
            "--rm",
            f"--name={container_name}",
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--user=65532:65532",
            f"--pids-limit={pids_limit}",
            f"--memory={limits.max_memory_bytes}",
            f"--cpus={cpu_quota:g}",
            f"--ulimit=nofile={limits.max_open_files}:{limits.max_open_files}",
            f"--ulimit=fsize={limits.max_output_bytes}:{limits.max_output_bytes}",
            "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16777216",
            f"--mount=type=bind,src={root / 'input'},dst=/workspace/input,readonly",
            f"--mount=type=bind,src={root / 'request.json'},dst=/workspace/request.json,readonly",
            f"--mount=type=bind,src={root / 'output'},dst=/workspace/output",
            f"--mount=type=bind,src={worker_path},dst=/provider/worker.py,readonly",
            "--workdir=/workspace",
            self.image,
            *registration.container_command,
        )

    def launch(
        self,
        registration: ProviderRegistration,
        workspace: Path,
        limits: ProviderLimits,
        environment: Mapping[str, str],
        stdout: object,
        stderr: object,
    ) -> subprocess.Popen[bytes]:
        self.preflight(registration)
        container_name = f"aecctx-{workspace.name.lower().replace('_', '-')[:40]}"
        command = self.command(registration, workspace, limits, container_name=container_name)
        try:
            return subprocess.Popen(
                command,
                env={"HOME": environment.get("HOME", "/tmp"), "PATH": os.environ.get("PATH", "")},
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
        except OSError as error:
            raise ProviderExecutionError("AECCTX_PROVIDER_LAUNCH_FAILED", f"Provider container launch failed: {error}") from error

    def terminate(self, process: subprocess.Popen[bytes]) -> None:
        container_name = None
        args = process.args if isinstance(process.args, (list, tuple)) else []
        for argument in args:
            if isinstance(argument, str) and argument.startswith("--name="):
                container_name = argument.split("=", 1)[1]
                break
        if container_name:
            subprocess.run(
                [str(self.docker_executable), "rm", "-f", container_name],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        process.kill()
        process.wait()

    @staticmethod
    def memory_bytes(pid: int) -> int:
        return 0
