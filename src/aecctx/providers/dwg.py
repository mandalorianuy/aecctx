from __future__ import annotations

from pathlib import Path

from .models import OCIRuntimeTarget, ProviderDescriptor, ProviderRegistration, REQUIRED_ENFORCEMENT_AXES
from .registry import ProviderRegistry


DWG_PROVIDER_ID = "org.aecctx.dwg.libredwg"
DWG_IMAGE = "aecctx-dwg-libredwg:0.2.0"
DWG_IMAGE_ID = "sha256:bb237d62599b5204b550fb075ee9f738e4198e031b71f3a6d7f85eae07c0c7c1"
DWG_OCI_TARGETS = (
    OCIRuntimeTarget(
        "linux",
        "arm64",
        "aecctx-dwg-libredwg:0.3.0-linux-arm64",
        "sha256:bb237d62599b5204b550fb075ee9f738e4198e031b71f3a6d7f85eae07c0c7c1",
    ),
    OCIRuntimeTarget(
        "linux",
        "amd64",
        "aecctx-dwg-libredwg:0.3.0-linux-amd64",
        "sha256:bcff6c67080688cb2d4f2cecef36ad5c687e1b895ef2adf23a3e3fb7a9248713",
    ),
)
DWG_WORKER_MODULE = "aecctx.external.libredwg_worker"
DWG_CONFIGURATION = {
    "dwg_version": "AC1015",
    "dxf_version": "r2000",
    "json_format": "JSON",
    "profile": "acx18-r2000-v1",
    "resolve_external_references": False,
}
DWG_CONFIGURATIONS = {
    "acx33-r13-v1": {
        "dwg_version": "AC1012",
        "dxf_version": "r13",
        "json_format": "JSON",
        "profile": "acx33-r13-v1",
        "resolve_external_references": False,
    },
    "acx33-r14-v1": {
        "dwg_version": "AC1014",
        "dxf_version": "r14",
        "json_format": "JSON",
        "profile": "acx33-r14-v1",
        "resolve_external_references": False,
    },
    "acx33-r2000-v1": {
        "dwg_version": "AC1015",
        "dxf_version": "r2000",
        "json_format": "JSON",
        "profile": "acx33-r2000-v1",
        "resolve_external_references": False,
    },
}


def dwg_descriptor() -> ProviderDescriptor:
    return ProviderDescriptor.from_dict(
        {
            "actions": ["extract"],
            "deterministic": True,
            "distribution": "operator-built-oci-image",
            "enforced_axes": {axis: True for axis in sorted(REQUIRED_ENFORCEMENT_AXES)},
            "enforcement_profile": "oci-docker-v1",
            "formats": ["image/vnd.dwg"],
            "license_spdx": "GPL-3.0-or-later",
            "network_mode": "disabled",
            "platforms": ["linux-container"],
            "protocol_version": "0.2",
            "provider_id": DWG_PROVIDER_ID,
            "provider_version": "0.2.0",
            "runtime_digest": DWG_IMAGE_ID,
            "runtime_version": "python-3.12+libredwg-0.13.4-api1",
        }
    )


def dwg_v03_descriptor() -> ProviderDescriptor:
    value = dwg_descriptor().to_dict()
    value["provider_version"] = "0.3.0"
    return ProviderDescriptor.from_dict(value)


def dwg_registry(*, repository_root: str | Path | None = None) -> ProviderRegistry:
    root = Path(repository_root) if repository_root is not None else Path(__file__).resolve().parents[3]
    registry = ProviderRegistry(allowed_worker_modules={DWG_WORKER_MODULE})
    registry.register(
        ProviderRegistration(
            descriptor=dwg_descriptor(),
            worker_module=DWG_WORKER_MODULE,
            container_image=DWG_IMAGE,
            container_image_id=DWG_IMAGE_ID,
            container_command=("python3", "/provider/worker.py"),
            container_pids_limit=2,
            worker_path=root / "providers" / "libredwg" / "worker.py",
            oci_targets=DWG_OCI_TARGETS,
        )
    )
    return registry


def dwg_v03_registry(*, repository_root: str | Path | None = None) -> ProviderRegistry:
    root = Path(repository_root) if repository_root is not None else Path(__file__).resolve().parents[3]
    registry = ProviderRegistry(allowed_worker_modules={DWG_WORKER_MODULE})
    registry.register(
        ProviderRegistration(
            descriptor=dwg_v03_descriptor(),
            worker_module=DWG_WORKER_MODULE,
            container_image=DWG_IMAGE,
            container_image_id=DWG_IMAGE_ID,
            container_command=("python3", "/provider/worker.py"),
            container_pids_limit=2,
            worker_path=root / "providers" / "libredwg" / "worker.py",
            oci_targets=DWG_OCI_TARGETS,
        )
    )
    return registry
