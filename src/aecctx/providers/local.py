from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Mapping

from .models import (
    REQUIRED_ENFORCEMENT_AXES,
    ProviderExecutionError,
    ProviderLimits,
    ProviderRegistration,
)


AxisState = Literal["enforced", "unavailable"]

_PARENT_ENFORCED_AXES = frozenset(
    {
        "decompression",
        "input_bytes",
        "output_bytes",
        "records",
        "recursion",
        "wall_time",
    }
)

_PROFILE_DECISIONS: dict[str, tuple[str, tuple[str, ...]]] = {
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


@dataclass(frozen=True, slots=True)
class LocalEnforcementReport:
    profile_id: str
    platform: str
    axes: Mapping[str, AxisState]
    executable: bool
    diagnostics: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.profile_id or not self.platform:
            raise ValueError("local enforcement profile_id and platform must be non-empty")
        normalized_axes = dict(sorted(self.axes.items()))
        if set(normalized_axes) != REQUIRED_ENFORCEMENT_AXES:
            raise ValueError("local enforcement report must contain every required axis")
        if any(state not in {"enforced", "unavailable"} for state in normalized_axes.values()):
            raise ValueError("local enforcement axis state must be enforced or unavailable")
        expected_executable = all(state == "enforced" for state in normalized_axes.values())
        if self.executable is not expected_executable:
            raise ValueError("local enforcement executable state must match all axes")
        normalized_diagnostics = tuple(sorted(set(self.diagnostics)))
        if not expected_executable and not normalized_diagnostics:
            raise ValueError("unavailable local enforcement report requires diagnostics")
        if expected_executable and normalized_diagnostics:
            raise ValueError("executable local enforcement report cannot carry diagnostics")
        object.__setattr__(self, "axes", MappingProxyType(normalized_axes))
        object.__setattr__(self, "diagnostics", normalized_diagnostics)

    def to_dict(self) -> dict[str, object]:
        return {
            "axes": dict(self.axes),
            "diagnostics": list(self.diagnostics),
            "executable": self.executable,
            "platform": self.platform,
            "profile_id": self.profile_id,
        }

    def canonical_bytes(self) -> bytes:
        return (
            json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")


def local_enforcement_report(platform: str) -> LocalEnforcementReport:
    try:
        profile_id, diagnostics = _PROFILE_DECISIONS[platform]
    except KeyError as error:
        raise ProviderExecutionError(
            "AECCTX_PROVIDER_PLATFORM_UNSUPPORTED",
            f"No reviewed local enforcement decision exists for platform: {platform}",
        ) from error
    axes: dict[str, AxisState] = {
        axis: "enforced" if axis in _PARENT_ENFORCED_AXES else "unavailable"
        for axis in sorted(REQUIRED_ENFORCEMENT_AXES)
    }
    return LocalEnforcementReport(
        profile_id=profile_id,
        platform=platform,
        axes=axes,
        executable=False,
        diagnostics=diagnostics,
    )


@dataclass(frozen=True, slots=True)
class LocalProviderProfile:
    platform: str

    @property
    def profile_id(self) -> str:
        return local_enforcement_report(self.platform).profile_id

    def report(self) -> LocalEnforcementReport:
        return local_enforcement_report(self.platform)

    def _unavailable(self) -> ProviderExecutionError:
        report = self.report()
        return ProviderExecutionError(
            "AECCTX_PROVIDER_PROFILE_UNAVAILABLE",
            f"{report.profile_id} has unavailable required enforcement axes",
            details={"local_enforcement": report.to_dict()},
        )

    def preflight(self, registration: ProviderRegistration) -> None:
        del registration
        raise self._unavailable()

    def launch(
        self,
        registration: ProviderRegistration,
        workspace: Path,
        limits: ProviderLimits,
        environment: Mapping[str, str],
        stdout: object,
        stderr: object,
    ) -> subprocess.Popen[bytes]:
        del registration, workspace, limits, environment, stdout, stderr
        raise self._unavailable()

    @staticmethod
    def terminate(process: subprocess.Popen[bytes]) -> None:
        del process

    @staticmethod
    def memory_bytes(pid: int) -> int:
        del pid
        return 0
