from __future__ import annotations

from pathlib import Path

from .models import ProviderDescriptor, ProviderRegistration, REQUIRED_ENFORCEMENT_AXES
from .registry import ProviderRegistry


STEP_IGES_PROVIDER_ID = "org.aecctx.step-iges.ocp"
STEP_IGES_IMAGE = "aecctx-step-iges-ocp:0.2.0"
STEP_IGES_IMAGE_ID = "sha256:875cbbbc5198ae44e8957e3a90c9a8afd0dc541f01029fb5186a296e3d2a0d47"
STEP_IGES_WORKER_MODULE = "aecctx.external.step_iges_ocp_worker"
STEP_IGES_CONFIGURATION = {
    "angular_deflection": 0.5,
    "brep_format": "occt-ascii-brep-7.9.3",
    "linear_deflection": 0.1,
    "read_shape_healing": "translator-default-observed",
    "schema_profile": "acx17-v1",
    "tessellation_units": "source",
}


def step_iges_descriptor() -> ProviderDescriptor:
    return ProviderDescriptor.from_dict(
        {
            "actions": ["extract"],
            "deterministic": True,
            "distribution": "operator-built-oci-image",
            "enforced_axes": {axis: True for axis in sorted(REQUIRED_ENFORCEMENT_AXES)},
            "enforcement_profile": "oci-docker-v1",
            "formats": ["model/step", "model/iges"],
            "license_spdx": "Apache-2.0 AND LGPL-2.1-only WITH OCCT-exception",
            "network_mode": "disabled",
            "platforms": ["linux-container"],
            "protocol_version": "0.2",
            "provider_id": STEP_IGES_PROVIDER_ID,
            "provider_version": "0.2.0",
            "runtime_digest": STEP_IGES_IMAGE_ID,
            "runtime_version": "python-3.12+cadquery-ocp-7.9.3.1.1+occt-7.9.3",
        }
    )


def step_iges_registry(*, repository_root: str | Path | None = None) -> ProviderRegistry:
    root = Path(repository_root) if repository_root is not None else Path(__file__).resolve().parents[3]
    registry = ProviderRegistry(allowed_worker_modules={STEP_IGES_WORKER_MODULE})
    registry.register(
        ProviderRegistration(
            descriptor=step_iges_descriptor(),
            worker_module=STEP_IGES_WORKER_MODULE,
            container_image=STEP_IGES_IMAGE,
            container_image_id=STEP_IGES_IMAGE_ID,
            container_command=("python3", "/provider/worker.py"),
            worker_path=root / "providers" / "step-iges-ocp" / "worker.py",
        )
    )
    return registry
