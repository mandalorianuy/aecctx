from __future__ import annotations

from pathlib import Path

from .models import OCIRuntimeTarget, ProviderDescriptor, ProviderRegistration, REQUIRED_ENFORCEMENT_AXES
from .registry import ProviderRegistry


PROVIDER_ID = "org.aecctx.ocr.tesseract-tsv"
IMAGE = "aecctx-tesseract-ocr:0.2.0"
IMAGE_ID = "sha256:6d52ebcafef0ccdf59f58beccc7483c16a6e160fc94e3c3ea59f3f10c991f492"
OCI_TARGETS = (
    OCIRuntimeTarget(
        "linux",
        "arm64",
        "aecctx-tesseract-ocr:0.3.0-linux-arm64",
        "sha256:dea431488eee5a4e6c9e532319a27d96c420f502ead87b7d99d6881f46e0fdb2",
    ),
    OCIRuntimeTarget(
        "linux",
        "amd64",
        "aecctx-tesseract-ocr:0.3.0-linux-amd64",
        "sha256:97f8f4ffea37f1fc597506ffdad230988e541e3785a9a6f88cc062c1ded01a83",
    ),
)
WORKER_MODULE = "aecctx.external.tesseract_ocr_worker"


def tesseract_ocr_descriptor() -> ProviderDescriptor:
    return ProviderDescriptor.from_dict(
        {
            "actions": ["extract"],
            "deterministic": True,
            "distribution": "operator-built-oci-image",
            "enforced_axes": {axis: True for axis in sorted(REQUIRED_ENFORCEMENT_AXES)},
            "enforcement_profile": "oci-docker-v1",
            "formats": ["image/x-portable-graymap"],
            "license_spdx": "Apache-2.0 AND HPND",
            "network_mode": "disabled",
            "platforms": ["linux-container"],
            "protocol_version": "0.2",
            "provider_id": PROVIDER_ID,
            "provider_version": "0.2.0",
            "runtime_digest": IMAGE_ID,
            "runtime_version": "tesseract-5.3.4+capi+eng",
        }
    )


def tesseract_ocr_registry(*, repository_root: str | Path | None = None) -> ProviderRegistry:
    root = Path(repository_root) if repository_root is not None else Path(__file__).resolve().parents[3]
    registry = ProviderRegistry(allowed_worker_modules={WORKER_MODULE})
    registry.register(
        ProviderRegistration(
            descriptor=tesseract_ocr_descriptor(),
            worker_module=WORKER_MODULE,
            container_image=IMAGE,
            container_image_id=IMAGE_ID,
            container_command=("python3", "/provider/worker.py"),
            worker_path=root / "providers" / "tesseract-ocr" / "worker.py",
            oci_targets=OCI_TARGETS,
        )
    )
    return registry
