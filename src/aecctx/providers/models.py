from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping


class ProviderExecutionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ProviderLimits:
    max_input_bytes: int = 512 * 1024 * 1024
    max_output_bytes: int = 64 * 1024 * 1024
    max_records: int = 1_000_000
    max_files: int = 1_000
    max_recursion_depth: int = 64
    max_decompression_ratio: float = 200.0
    wall_time_seconds: float = 120.0
    cpu_seconds: int = 120
    max_memory_bytes: int = 2 * 1024 * 1024 * 1024
    max_open_files: int = 64

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


REQUIRED_ENFORCEMENT_AXES = frozenset(
    {
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
)


@dataclass(frozen=True, slots=True)
class ProviderDescriptor:
    provider_id: str
    provider_version: str
    runtime_version: str
    runtime_digest: str
    protocol_version: str
    license_spdx: str
    distribution: str
    actions: tuple[str, ...]
    formats: tuple[str, ...]
    platforms: tuple[str, ...]
    network_mode: str
    deterministic: bool
    enforcement_profile: str
    enforced_axes: Mapping[str, bool]

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> ProviderDescriptor:
        axes = raw.get("enforced_axes")
        if not isinstance(axes, Mapping) or set(axes) != REQUIRED_ENFORCEMENT_AXES or any(axes.get(axis) is not True for axis in REQUIRED_ENFORCEMENT_AXES):
            raise ProviderExecutionError(
                "AECCTX_PROVIDER_ENFORCEMENT_INCOMPLETE",
                "Provider descriptor must attest every required enforcement axis",
            )
        actions = _string_list(raw, "actions")
        formats = _string_list(raw, "formats")
        platforms = _string_list(raw, "platforms")
        deterministic = raw.get("deterministic")
        if not isinstance(deterministic, bool):
            raise ProviderExecutionError("AECCTX_PROVIDER_DESCRIPTOR_INVALID", "deterministic must be a boolean")
        protocol_version = _string(raw, "protocol_version")
        if protocol_version != "0.2":
            raise ProviderExecutionError("AECCTX_PROVIDER_PROTOCOL_UNSUPPORTED", f"Unsupported provider protocol: {protocol_version}")
        network_mode = _string(raw, "network_mode")
        if network_mode not in {"disabled", "allowlisted"}:
            raise ProviderExecutionError("AECCTX_PROVIDER_DESCRIPTOR_INVALID", "network_mode must be disabled or allowlisted")
        return cls(
            provider_id=_string(raw, "provider_id"),
            provider_version=_string(raw, "provider_version"),
            runtime_version=_string(raw, "runtime_version"),
            runtime_digest=_runtime_digest(raw),
            protocol_version=protocol_version,
            license_spdx=_string(raw, "license_spdx"),
            distribution=_string(raw, "distribution"),
            actions=actions,
            formats=formats,
            platforms=platforms,
            network_mode=network_mode,
            deterministic=deterministic,
            enforcement_profile=_string(raw, "enforcement_profile"),
            enforced_axes={axis: True for axis in sorted(REQUIRED_ENFORCEMENT_AXES)},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "actions": list(self.actions),
            "deterministic": self.deterministic,
            "distribution": self.distribution,
            "enforced_axes": dict(self.enforced_axes),
            "enforcement_profile": self.enforcement_profile,
            "formats": list(self.formats),
            "license_spdx": self.license_spdx,
            "network_mode": self.network_mode,
            "platforms": list(self.platforms),
            "protocol_version": self.protocol_version,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "runtime_version": self.runtime_version,
            "runtime_digest": self.runtime_digest,
        }


@dataclass(frozen=True, slots=True)
class ProviderRegistration:
    descriptor: ProviderDescriptor
    worker_module: str
    runtime_roots: tuple[str, ...] = field(default_factory=tuple)
    container_image: str | None = None
    container_image_id: str | None = None
    container_command: tuple[str, ...] = field(default_factory=tuple)
    worker_path: Path | None = None


def _string(raw: Mapping[str, Any], field: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value:
        raise ProviderExecutionError("AECCTX_PROVIDER_DESCRIPTOR_INVALID", f"{field} must be a non-empty string")
    return value


def _string_list(raw: Mapping[str, Any], field: str) -> tuple[str, ...]:
    value = raw.get(field)
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item for item in value):
        raise ProviderExecutionError("AECCTX_PROVIDER_DESCRIPTOR_INVALID", f"{field} must be a non-empty string array")
    if len(set(value)) != len(value):
        raise ProviderExecutionError("AECCTX_PROVIDER_DESCRIPTOR_INVALID", f"{field} entries must be unique")
    return tuple(value)


def _runtime_digest(raw: Mapping[str, Any]) -> str:
    value = _string(raw, "runtime_digest")
    prefix = "sha256:"
    digest = value.removeprefix(prefix)
    if not value.startswith(prefix) or len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise ProviderExecutionError("AECCTX_PROVIDER_DESCRIPTOR_INVALID", "runtime_digest must be a sha256 digest")
    return value
