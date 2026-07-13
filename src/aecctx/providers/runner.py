from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping

from .models import ProviderExecutionError, ProviderLimits
from .protocol import ProviderResult, build_provider_request, validate_provider_response
from .registry import ProviderRegistry


class ProviderRunner:
    def __init__(
        self,
        *,
        registry: ProviderRegistry,
        profile: Any,
        limits: ProviderLimits | None = None,
        workspace_parent: str | Path | None = None,
    ) -> None:
        self.registry = registry
        self.profile = profile
        self.limits = limits or ProviderLimits()
        self.workspace_parent = Path(workspace_parent) if workspace_parent is not None else None

    def run(
        self,
        provider_id: str,
        action: str,
        input_bytes: bytes,
        *,
        configuration: Mapping[str, Any] | None = None,
    ) -> ProviderResult:
        registration = self.registry.resolve(provider_id)
        descriptor = registration.descriptor
        if action not in descriptor.actions:
            raise ProviderExecutionError("AECCTX_PROVIDER_ACTION_UNSUPPORTED", f"Provider does not declare action: {action}")
        self.profile.preflight(registration)
        request = build_provider_request(provider_id, action, input_bytes, limits=self.limits, configuration=configuration)
        remote_run = getattr(self.profile, "run_remote", None)
        if callable(remote_run):
            return remote_run(registration, request, input_bytes, self.limits)
        parent = str(self.workspace_parent) if self.workspace_parent is not None else None
        with tempfile.TemporaryDirectory(prefix="aecctx-provider-", dir=parent) as temporary:
            workspace = Path(temporary).resolve()
            input_path = workspace / str(request["input"]["path"])
            output_root = workspace / "output"
            (output_root / "artifacts").mkdir(parents=True)
            output_root.chmod(0o777)
            (output_root / "artifacts").chmod(0o777)
            (workspace / "tmp").mkdir()
            input_path.parent.mkdir()
            input_path.write_bytes(input_bytes)
            input_path.chmod(0o444)
            request_path = workspace / "request.json"
            request_path.write_text(json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            request_path.chmod(0o444)
            environment = {
                "AECCTX_NETWORK": "disabled",
                "HOME": str(workspace / "tmp"),
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "PATH": "",
                "PYTHONHASHSEED": "0",
                "TMPDIR": str(workspace / "tmp"),
            }
            stdout_path = output_root / "stdout.log"
            stderr_path = output_root / "stderr.log"
            with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
                process = self.profile.launch(registration, workspace, self.limits, environment, stdout, stderr)
                started = time.monotonic()
                while process.poll() is None:
                    if time.monotonic() - started > self.limits.wall_time_seconds:
                        self.profile.terminate(process)
                        raise ProviderExecutionError("AECCTX_PROVIDER_TIMEOUT", "Provider exceeded wall-time limit")
                    memory_bytes = self.profile.memory_bytes(process.pid)
                    if memory_bytes > self.limits.max_memory_bytes:
                        self.profile.terminate(process)
                        raise ProviderExecutionError("AECCTX_PROVIDER_MEMORY_LIMIT_EXCEEDED", "Provider exceeded memory limit")
                    time.sleep(0.01)
            self._check_workspace_output(output_root)
            response_path = output_root / "response.json"
            if not response_path.is_file():
                stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")[:500]
                if process.returncode == 137:
                    raise ProviderExecutionError(
                        "AECCTX_PROVIDER_MEMORY_LIMIT_EXCEEDED",
                        "Provider container was terminated by its memory limit",
                    )
                raise ProviderExecutionError(
                    "AECCTX_PROVIDER_RESPONSE_MISSING",
                    f"Provider did not produce response.json (exit={process.returncode}): {stderr_text}",
                )
            if response_path.stat().st_size > self.limits.max_output_bytes:
                raise ProviderExecutionError("AECCTX_PROVIDER_OUTPUT_LIMIT_EXCEEDED", "Provider response exceeds configured byte limit")
            try:
                response = json.loads(response_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ProviderExecutionError("AECCTX_PROVIDER_PROTOCOL_INVALID", f"Provider response is invalid JSON: {error}") from error
            if not isinstance(response, dict):
                raise ProviderExecutionError("AECCTX_PROVIDER_PROTOCOL_INVALID", "Provider response must be an object")
            return validate_provider_response(response, request, descriptor, output_root, limits=self.limits)

    def _check_workspace_output(self, output_root: Path) -> None:
        files = [path for path in output_root.rglob("*") if path.is_file() or path.is_symlink()]
        if len(files) > self.limits.max_files:
            raise ProviderExecutionError("AECCTX_PROVIDER_FILE_LIMIT_EXCEEDED", "Provider output file count exceeds limit")
        total = 0
        for path in files:
            if path.is_symlink():
                raise ProviderExecutionError("AECCTX_PROVIDER_ARTIFACT_PATH_UNSAFE", "Provider output symlink is forbidden")
            total += path.stat().st_size
            if total > self.limits.max_output_bytes:
                raise ProviderExecutionError("AECCTX_PROVIDER_OUTPUT_LIMIT_EXCEEDED", "Provider output exceeds configured byte limit")
