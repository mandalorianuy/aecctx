from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .models import ProviderExecutionError, ProviderLimits, ProviderRegistration


@dataclass(frozen=True, slots=True)
class OCIDockerProfile:
    DEFAULT_IMAGE = "python@sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df"

    docker_executable: Path = Path("/usr/local/bin/docker")
    image: str = DEFAULT_IMAGE
    profile_id: str = "oci-docker-v1"

    def preflight(self, registration: ProviderRegistration) -> None:
        descriptor = registration.descriptor
        if not self.docker_executable.is_file() or not os.access(self.docker_executable, os.X_OK):
            raise ProviderExecutionError("AECCTX_PROVIDER_PROFILE_UNAVAILABLE", "Reviewed Docker runtime is unavailable")
        if descriptor.enforcement_profile != self.profile_id or "linux-container" not in descriptor.platforms:
            raise ProviderExecutionError("AECCTX_PROVIDER_PROFILE_MISMATCH", "Provider descriptor does not admit the OCI profile")
        if descriptor.network_mode != "disabled":
            raise ProviderExecutionError("AECCTX_PROVIDER_NETWORK_POLICY_UNSUPPORTED", "Reference OCI profile requires network_mode=disabled")
        if registration.container_image != self.image or "@sha256:" not in self.image:
            raise ProviderExecutionError("AECCTX_PROVIDER_IMAGE_UNPINNED", "Provider image must match the reviewed digest-pinned image")
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
                [str(self.docker_executable), "image", "inspect", self.image],
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

    def command(
        self,
        registration: ProviderRegistration,
        workspace: str | Path,
        limits: ProviderLimits,
        *,
        container_name: str,
    ) -> tuple[str, ...]:
        root = Path(workspace).resolve()
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
            "--pids-limit=1",
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
