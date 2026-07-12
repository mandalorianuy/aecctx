from __future__ import annotations

from pathlib import Path

from aecctx.providers.step_iges import (
    STEP_IGES_IMAGE,
    STEP_IGES_IMAGE_ID,
    STEP_IGES_PROVIDER_ID,
    step_iges_descriptor,
    step_iges_registry,
)


ROOT = Path(__file__).parents[1]


def test_step_iges_profile_registration_pins_reviewed_runtime_and_worker() -> None:
    descriptor = step_iges_descriptor()
    registration = step_iges_registry(repository_root=ROOT).resolve(STEP_IGES_PROVIDER_ID)

    assert descriptor.provider_id == "org.aecctx.step-iges.ocp"
    assert descriptor.provider_version == "0.2.0"
    assert descriptor.runtime_version == "python-3.12+cadquery-ocp-7.9.3.1.1+occt-7.9.3"
    assert descriptor.runtime_digest == STEP_IGES_IMAGE_ID
    assert descriptor.license_spdx == "Apache-2.0 AND LGPL-2.1-only WITH OCCT-exception"
    assert descriptor.formats == ("model/step", "model/iges")
    assert descriptor.platforms == ("linux-container",)
    assert descriptor.network_mode == "disabled"
    assert set(descriptor.enforced_axes) == {
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
    assert registration.container_image == STEP_IGES_IMAGE
    assert registration.container_image_id == STEP_IGES_IMAGE_ID
    assert registration.container_command == ("python3", "/provider/worker.py")
    assert registration.worker_path == ROOT / "providers" / "step-iges-ocp" / "worker.py"


def test_step_iges_native_kernel_is_absent_from_core_distribution_dependencies() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()

    assert "cadquery-ocp" not in pyproject
    assert "pythonocc" not in pyproject
    assert "opencascade" not in pyproject
