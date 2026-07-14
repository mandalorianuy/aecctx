from __future__ import annotations

from pathlib import Path

from .models import OCIRuntimeTarget, ProviderDescriptor, ProviderRegistration, REQUIRED_ENFORCEMENT_AXES
from .registry import ProviderRegistry

PROVIDER_ID = "org.aecctx.vision.raster-rules"
IMAGE = "aecctx-vision-raster-rules:0.3.0"
IMAGE_ID = "sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db"
WORKER_MODULE = "aecctx.external.vision_raster_rules_worker"
OCI_TARGETS = (
    OCIRuntimeTarget("linux", "arm64", IMAGE + "-linux-arm64", "sha256:8331cca8ad96ec3fae8985165fa862f6960948f84a7c6abe0b2b7eed6101f65b"),
    OCIRuntimeTarget("linux", "amd64", IMAGE + "-linux-amd64", "sha256:22f267f763684240816835a3345f8562e7c7c768e14559b44909ccaa8cced500"),
)
CONFIGURATION = {"emit_reconstruction": True, "foreground_threshold": 32, "maximum_candidates": 128, "minimum_component_pixels": 5}


def vision_descriptor() -> ProviderDescriptor:
    return ProviderDescriptor.from_dict({"actions": ["extract"], "deterministic": True, "distribution": "operator-built-oci-image", "enforced_axes": {axis: True for axis in sorted(REQUIRED_ENFORCEMENT_AXES)}, "enforcement_profile": "oci-docker-v1", "formats": ["image/x-portable-graymap"], "license_spdx": "Apache-2.0 AND PSF-2.0", "network_mode": "disabled", "platforms": ["linux-container"], "protocol_version": "0.2", "provider_id": PROVIDER_ID, "provider_version": "0.3.0", "runtime_digest": IMAGE_ID, "runtime_version": "python-3.12.10-stdlib-raster-rules-v1"})


def vision_registry(*, repository_root: str | Path | None = None) -> ProviderRegistry:
    root = Path(repository_root) if repository_root is not None else Path(__file__).resolve().parents[3]
    registry = ProviderRegistry(allowed_worker_modules={WORKER_MODULE})
    registry.register(ProviderRegistration(descriptor=vision_descriptor(), worker_module=WORKER_MODULE, container_image=IMAGE, container_image_id=IMAGE_ID, container_command=("python3", "/provider/worker.py"), worker_path=root / "providers/vision-raster-rules/worker.py", oci_targets=OCI_TARGETS))
    return registry
