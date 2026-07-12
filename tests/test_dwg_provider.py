from __future__ import annotations

from pathlib import Path

from aecctx.providers.dwg import (
    DWG_CONFIGURATION,
    DWG_IMAGE,
    DWG_IMAGE_ID,
    DWG_PROVIDER_ID,
    dwg_descriptor,
    dwg_registry,
)


ROOT = Path(__file__).parents[1]


def test_dwg_profile_registration_pins_reviewed_runtime_and_worker() -> None:
    descriptor = dwg_descriptor()
    registration = dwg_registry(repository_root=ROOT).resolve(DWG_PROVIDER_ID)

    assert descriptor.provider_id == "org.aecctx.dwg.libredwg"
    assert descriptor.provider_version == "0.2.0"
    assert descriptor.runtime_version == "python-3.12+libredwg-0.13.4-api1"
    assert descriptor.runtime_digest == DWG_IMAGE_ID
    assert DWG_IMAGE_ID.startswith("sha256:") and len(DWG_IMAGE_ID) == 71
    assert DWG_IMAGE_ID != "sha256:" + "0" * 64
    assert descriptor.license_spdx == "GPL-3.0-or-later"
    assert descriptor.formats == ("image/vnd.dwg",)
    assert descriptor.platforms == ("linux-container",)
    assert descriptor.network_mode == "disabled"
    assert all(descriptor.enforced_axes.values())
    assert registration.container_image == DWG_IMAGE == "aecctx-dwg-libredwg:0.2.0"
    assert registration.container_image_id == DWG_IMAGE_ID
    assert registration.container_command == ("python3", "/provider/worker.py")
    assert registration.worker_path == ROOT / "providers" / "libredwg" / "worker.py"
    assert DWG_CONFIGURATION == {
        "dwg_version": "AC1015",
        "dxf_version": "r2000",
        "json_format": "JSON",
        "profile": "acx18-r2000-v1",
        "resolve_external_references": False,
    }


def test_dwg_gpl_runtime_is_absent_from_core_distribution_dependencies() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()

    assert "libredwg" not in pyproject
    assert "real-dwg" not in pyproject
    assert "opendesign" not in pyproject
    assert "autodesk" not in pyproject
