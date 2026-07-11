from __future__ import annotations

import base64
import json
import os
import signal
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from typing import Any


BUILTIN_PLUGIN_IDS = {"dxf", "geometry", "ifc", "image", "pdf"}
CONFORMANCE_PLUGIN_IDS = {"_conformance_flood", "_conformance_network", "_conformance_sleep"}


@dataclass(frozen=True, slots=True)
class PluginLimits:
    max_input_bytes: int = 512 * 1024 * 1024
    max_output_bytes: int = 64 * 1024 * 1024
    max_records: int = 1_000_000
    wall_time_seconds: float = 120.0
    cpu_seconds: int = 120
    max_memory_bytes: int = 2 * 1024 * 1024 * 1024
    max_open_files: int = 64

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


class PluginExecutionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _resource_limiter(limits: PluginLimits) -> Any:
    def configure() -> None:
        try:
            import resource

            resource.setrlimit(resource.RLIMIT_CPU, (limits.cpu_seconds, limits.cpu_seconds))
            if hasattr(resource, "RLIMIT_AS"):
                resource.setrlimit(resource.RLIMIT_AS, (limits.max_memory_bytes, limits.max_memory_bytes))
            resource.setrlimit(resource.RLIMIT_NOFILE, (limits.max_open_files, limits.max_open_files))
            resource.setrlimit(resource.RLIMIT_FSIZE, (limits.max_output_bytes, limits.max_output_bytes))
        except (ImportError, OSError, ValueError):
            pass

    return configure


class IsolatedPluginRunner:
    def __init__(self, *, limits: PluginLimits | None = None, allow_conformance_plugins: bool = False) -> None:
        self.limits = limits or PluginLimits()
        self.allow_conformance_plugins = allow_conformance_plugins

    def _check_plugin(self, plugin_id: str) -> None:
        allowed = set(BUILTIN_PLUGIN_IDS)
        if self.allow_conformance_plugins:
            allowed.update(CONFORMANCE_PLUGIN_IDS)
        if plugin_id not in allowed:
            raise PluginExecutionError("AECCTX_PLUGIN_NOT_REGISTERED", f"Plugin is not registered: {plugin_id}")

    def probe(self, plugin_id: str, prefix: bytes) -> dict[str, Any]:
        if len(prefix) > self.limits.max_input_bytes:
            raise PluginExecutionError("AECCTX_PLUGIN_INPUT_LIMIT_EXCEEDED", "Probe input exceeds configured byte limit")
        return self.run(plugin_id, "probe", {"prefix_base64": base64.b64encode(prefix).decode("ascii")})

    def run(self, plugin_id: str, action: str, payload: dict[str, Any] | None = None) -> Any:
        self._check_plugin(plugin_id)
        request = {"action": action, "limits": self.limits.to_dict(), "payload": payload or {}, "plugin_id": plugin_id}
        request_bytes = json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(request_bytes) > self.limits.max_input_bytes * 2 + 16_384:
            raise PluginExecutionError("AECCTX_PLUGIN_INPUT_LIMIT_EXCEEDED", "Plugin request exceeds configured byte limit")
        with tempfile.TemporaryDirectory(prefix="aecctx-plugin-") as temporary, tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            environment = {
                "AECCTX_NETWORK": "disabled",
                "HOME": temporary,
                "LANG": "C.UTF-8",
                "LC_ALL": "C.UTF-8",
                "PATH": os.environ.get("PATH", ""),
                "PYTHONHASHSEED": "0",
                "TMPDIR": temporary,
            }
            if self.allow_conformance_plugins:
                environment["AECCTX_CONFORMANCE"] = "1"
            process = subprocess.Popen(
                [sys.executable, "-I", "-m", "aecctx.plugin_worker"],
                cwd=temporary,
                env=environment,
                stdin=subprocess.PIPE,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                preexec_fn=_resource_limiter(self.limits) if os.name == "posix" else None,
            )
            try:
                process.communicate(request_bytes, timeout=self.limits.wall_time_seconds)
            except subprocess.TimeoutExpired as error:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait()
                raise PluginExecutionError("AECCTX_PLUGIN_TIMEOUT", "Plugin exceeded wall-time limit") from error
            stdout_size = stdout.seek(0, os.SEEK_END)
            stderr_size = stderr.seek(0, os.SEEK_END)
            if stdout_size > self.limits.max_output_bytes or stderr_size > self.limits.max_output_bytes:
                raise PluginExecutionError("AECCTX_PLUGIN_OUTPUT_LIMIT_EXCEEDED", "Plugin output exceeds configured byte limit")
            stdout.seek(0)
            stderr.seek(0)
            output = stdout.read()
            error_output = stderr.read().decode("utf-8", errors="replace")
        try:
            response = json.loads(output)
        except json.JSONDecodeError as error:
            raise PluginExecutionError("AECCTX_PLUGIN_PROTOCOL_INVALID", f"Worker returned invalid JSON: {error_output[:500]}") from error
        if not response.get("ok"):
            failure = response.get("error", {})
            raise PluginExecutionError(failure.get("code", "AECCTX_PLUGIN_FAILED"), failure.get("message", "Plugin failed"))
        return response["result"]

