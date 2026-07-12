from __future__ import annotations

from pathlib import Path

from .models import ProviderDescriptor, ProviderRegistration, REQUIRED_ENFORCEMENT_AXES
from .oci import OCIDockerProfile
from .registry import ProviderRegistry


REFERENCE_PROVIDER_ID = "org.aecctx.reference-provider"
REFERENCE_WORKER_MODULE = "aecctx.reference_provider_worker"


def reference_provider_registry() -> ProviderRegistry:
    descriptor = ProviderDescriptor.from_dict(
        {
            "actions": ["describe", "extract", "finalize"],
            "deterministic": True,
            "distribution": "bundled-reference",
            "enforced_axes": {axis: True for axis in sorted(REQUIRED_ENFORCEMENT_AXES)},
            "enforcement_profile": "oci-docker-v1",
            "formats": ["application/x-aecctx-provider-fixture"],
            "license_spdx": "Apache-2.0",
            "network_mode": "disabled",
            "platforms": ["linux-container"],
            "protocol_version": "0.2",
            "provider_id": REFERENCE_PROVIDER_ID,
            "provider_version": "0.2.0",
            "runtime_version": "python-3.12",
            "runtime_digest": "sha256:6d43704baacd1bfbe7c295d7f13079d5d8104ed33568873133f8fc69980419df",
        }
    )
    worker_path = Path(__file__).resolve().parents[1] / "reference_provider_worker.py"
    registration = ProviderRegistration(
        descriptor=descriptor,
        worker_module=REFERENCE_WORKER_MODULE,
        container_image=OCIDockerProfile.DEFAULT_IMAGE,
        container_command=("python", "/provider/worker.py"),
        worker_path=worker_path,
    )
    registry = ProviderRegistry(allowed_worker_modules={REFERENCE_WORKER_MODULE})
    registry.register(registration)
    return registry
