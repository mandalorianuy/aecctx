from __future__ import annotations

from pathlib import Path

from .models import ProviderDescriptor, ProviderRegistration, REQUIRED_ENFORCEMENT_AXES
from .registry import ProviderRegistry


DWG_PROVIDER_ID = "org.aecctx.dwg.libredwg"
DWG_IMAGE = "aecctx-dwg-libredwg:0.2.0"
DWG_IMAGE_ID = "sha256:9bae0e6084613c08f7f283381a2be45ba3b480992ddef92887f7ed4ddf425679"
DWG_WORKER_MODULE = "aecctx.external.libredwg_worker"
DWG_CONFIGURATION = {
    "dwg_version": "AC1015",
    "dxf_version": "r2000",
    "json_format": "JSON",
    "profile": "acx18-r2000-v1",
    "resolve_external_references": False,
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
            worker_path=root / "providers" / "libredwg" / "worker.py",
        )
    )
    return registry
