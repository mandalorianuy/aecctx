from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any, Iterable

from ..ingest import CAPABILITIES, IngestResult, _timestamp
from ..inference import InferenceMappingError, canonical_ocr_pgm, map_ocr_result
from ..vision import VisionMappingError, map_vision_result
from ..package import PackageArtifact, PackageWriter, canonical_json, hash_file
from ..providers.protocol import ProviderResult


PLUGIN_ID = "aecctx.adapter.image.pillow"
PLUGIN_VERSION = "0.1.0"


class ImageDependencyError(RuntimeError):
    code = "AECCTX_IMAGE_DEPENDENCY_MISSING"


def _pillow() -> tuple[Any, str]:
    try:
        import PIL
        from PIL import Image
    except ImportError as error:
        raise ImageDependencyError("Install AECCTX with the 'image' extra to use the image adapter") from error
    return Image, str(PIL.__version__)


def _stable_id(prefix: str, source_digest: str, key: str) -> str:
    suffix = hashlib.sha256(f"{source_digest}\0{key}".encode()).hexdigest()[:24]
    return f"{prefix}_{suffix}"


def _known(value: Any) -> dict[str, Any]:
    return {"state": "known", "value": value}


def _unknown(reason: str) -> dict[str, str]:
    return {"state": "unknown", "reason_code": reason}


def _provenance(instant: str, parents: list[str], runtime: str) -> dict[str, Any]:
    return {
        "method": "pillow-image-metadata",
        "parent_record_ids": sorted(parents),
        "producer_id": PLUGIN_ID,
        "producer_version": f"{PLUGIN_VERSION}+pillow.{runtime}",
        "recorded_at": instant,
    }


class ImagePlugin:
    def describe(self) -> dict[str, Any]:
        runtime = "not-installed"
        try:
            _, runtime = _pillow()
        except ImageDependencyError:
            pass
        return {
            "deterministic": True,
            "distribution_posture": "optional-not-bundled",
            "execution_mode": "in-process-optional",
            "implementation_runtime": f"pillow/{runtime}",
            "input_capabilities": ["Pillow-supported raster image formats"],
            "license_identifier": "MIT-CMU",
            "network_mode": "disabled",
            "output_capabilities": list(CAPABILITIES),
            "plugin_id": PLUGIN_ID,
            "plugin_version": PLUGIN_VERSION,
            "resource_limits": {"bytes": True, "pixels": True, "records": True, "wall_time": False, "memory": False},
            "supported_extensions": [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".pgm", ".ppm"],
            "supported_media_types": ["image/*"],
        }

    def probe(self, prefix: bytes) -> dict[str, Any]:
        Image, _ = _pillow()
        detected: str | None = None
        try:
            with Image.open(io.BytesIO(prefix)) as image:
                detected = image.format
        except Exception:
            pass
        if prefix.startswith((b"P1", b"P2", b"P4", b"P5")):
            detected = "PGM"
        elif prefix.startswith((b"P3", b"P6")):
            detected = "PPM"
        return {
            "confidence": 1.0 if detected else 0.0,
            "format": detected or "unknown",
            "mutated": False,
            "observed_bytes": min(len(prefix), 64 * 1024),
        }

    def extract(self, source_path: str | Path, *, source_id: str) -> Iterable[dict[str, Any]]:
        Image, _ = _pillow()
        with Image.open(source_path) as image:
            width, height = image.size
            mode = image.mode
            image_format = image.format
        yield {
            "diagnostics": [],
            "event_type": "primitive",
            "event_version": "0.1",
            "extraction_confidence": {"band": "full", "method": "pillow-header"},
            "parent_references": [],
            "payload": {"format": image_format, "height": height, "mode": mode, "original_class": "RASTER_IMAGE", "width": width},
            "sequence": 0,
            "source_id": source_id,
            "source_locator": "pixel-canvas",
        }

    def finalize(self, capabilities: dict[str, str], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "capabilities": capabilities,
            "diagnostic_count": len(diagnostics),
            "network_used": False,
            "plugin_id": PLUGIN_ID,
            "sanitization": ["pixel-limit-enforced", "metadata-treated-as-data"],
        }


def ingest_image(
    source_path: str | Path,
    output_path: str | Path,
    *,
    created_at: str | None = None,
    embedding_policy: str = "external",
    package_form: str = "directory",
    max_pixels: int = 100_000_000,
    aecctx_version: str = "0.1.0",
    ocr_result: ProviderResult | None = None,
    vision_result: ProviderResult | None = None,
) -> IngestResult:
    Image, runtime = _pillow()
    source = Path(source_path)
    output = Path(output_path)
    if not source.is_file() or source.is_symlink():
        raise ValueError("source_path must be a regular image file")
    if embedding_policy not in {"external", "embedded", "redacted"}:
        raise ValueError("embedding_policy must be external, embedded, or redacted")
    if aecctx_version not in {"0.1.0", "0.2.0"}:
        raise ValueError("aecctx_version must be 0.1.0 or 0.2.0")
    if (ocr_result is not None or vision_result is not None) and aecctx_version != "0.2.0":
        raise ValueError("inference results require aecctx_version of 0.2.0")
    source_digest, source_bytes = hash_file(source)
    identity = source_digest[:24]
    source_id = f"src_{identity}"
    package_id = f"pkg_{identity}"
    instant = _timestamp(created_at)
    with Image.open(source) as image:
        width, height = image.size
        if width * height > max_pixels:
            raise ValueError("image pixel count exceeds safety limit")
        image.verify()
    with Image.open(source) as image:
        image_format = image.format or "unknown"
        mode = image.mode
        metadata = {str(key): str(value) for key, value in sorted(image.info.items()) if key not in {"exif", "icc_profile"}}
        ocr_input = canonical_ocr_pgm(width, height, image.convert("L").tobytes())
    primitive_id = _stable_id("prim_image", source_digest, "image")
    primitive = {
        "calibration": _unknown("AECCTX_IMAGE_CALIBRATION_NOT_DECLARED"),
        "container": _known("image-canvas"),
        "extraction_confidence": {"band": "full", "method": "pillow-header-and-decode-validation"},
        "interpretation_confidence": {"band": "unknown", "method": "no-vision-provider"},
        "metadata": metadata,
        "ocr": {"state": "unsupported", "reason_code": "AECCTX_OCR_PROVIDER_NOT_CONFIGURED"},
        "original_class": "RASTER_IMAGE",
        "pixel_geometry": {"height": height, "origin": "top-left", "unit": "px", "width": width},
        "pixel_mode": mode,
        "provenance": _provenance(instant, [source_id], runtime),
        "record_id": primitive_id,
        "record_type": "primitive",
        "record_version": "0.1",
        "source_refs": [{"locator": "pixel-canvas", "source_id": source_id}],
    }
    primitives = [primitive]
    assertions: list[dict[str, Any]] = []
    capabilities = {name: "full" for name in CAPABILITIES}
    capabilities.update(
        {
            "hierarchy": "opaque",
            "properties": "partial",
            "relationships": "opaque",
            "text": "unsupported",
            "3d_geometry": "unsupported",
            "materials_styles": "partial",
            "georeferencing": "unsupported",
        }
    )
    mapping = None
    ocr_error: InferenceMappingError | None = None
    if ocr_result is not None:
        try:
            mapping = map_ocr_result(
                ocr_result,
                input_bytes=ocr_input,
                source_id=source_id,
                parent_record_id=primitive_id,
                source_locator="pixel-canvas",
                width=width,
                height=height,
                recorded_at=instant,
            )
        except InferenceMappingError as error:
            ocr_error = error
        else:
            layout = any(event.get("payload", {}).get("schema") == "aecctx.ocr.layout.v1" for event in ocr_result.events)
            primitive["ocr"] = _known("inferred-layout-evidence" if layout else "inferred-word-evidence")
            capabilities["text"] = "partial"
            primitives.extend(mapping.primitives)
            assertions.extend(mapping.assertions)
    vision_mapping = None
    vision_error: VisionMappingError | None = None
    if vision_result is not None:
        try:
            vision_mapping = map_vision_result(vision_result, input_bytes=ocr_input, source_id=source_id, parent_record_id=primitive_id, source_locator="pixel-canvas", width=width, height=height, recorded_at=instant)
        except VisionMappingError as error:
            vision_error = error
        else:
            primitive["vision"] = _known("inferred-visible-raster-candidates")
            primitives.extend(vision_mapping.primitives)
            assertions.extend(vision_mapping.assertions)
    reasons = {
        "hierarchy": "AECCTX_IMAGE_HIERARCHY_OPAQUE",
        "properties": "AECCTX_IMAGE_METADATA_PARTIAL",
        "relationships": "AECCTX_IMAGE_RELATIONSHIPS_OPAQUE",
        "text": "AECCTX_OCR_INFERRED_UNVERIFIED" if mapping is not None else "AECCTX_OCR_PROVIDER_RESULT_REJECTED" if ocr_error is not None else "AECCTX_OCR_PROVIDER_NOT_CONFIGURED",
        "3d_geometry": "AECCTX_IMAGE_HIDDEN_GEOMETRY_UNSUPPORTED",
        "materials_styles": "AECCTX_IMAGE_COLOR_PROFILE_PARTIAL",
        "georeferencing": "AECCTX_IMAGE_GEOREFERENCING_UNSUPPORTED",
    }
    diagnostics = []
    for capability in CAPABILITIES:
        level = capabilities[capability]
        if level == "full":
            continue
        diagnostics.append(
            {
                "affected_count": 1,
                "capability": capability,
                "code": reasons[capability],
                "fallback": "Inspect exact source pixels and explicit metadata; configure an optional provider only when policy permits.",
                "message": f"Image capability is {level}: {capability}",
                "provenance": _provenance(instant, [source_id], runtime),
                "record_id": _stable_id("diag_image_loss", source_digest, capability),
                "record_type": "diagnostic",
                "record_version": "0.1",
                "severity": "info",
                "source_refs": [{"locator": "image", "source_id": source_id}],
                "support_level": level,
            }
        )
    if vision_mapping is not None:
        diagnostics.extend(vision_mapping.diagnostics)
    elif vision_error is not None:
        diagnostics.append({"affected_count": 1, "capability": "2d_geometry", "code": "AECCTX_VISION_PROVIDER_RESULT_REJECTED", "fallback": "Inspect exact source pixels.", "message": str(vision_error), "provenance": _provenance(instant, [source_id], runtime), "severity": "warning", "source_refs": [{"locator": "pixel-canvas", "source_id": source_id}]})
    if mapping is not None:
        diagnostics.extend(mapping.diagnostics)
    if ocr_error is not None:
        diagnostics.append(
            {
                "affected_count": 1,
                "capability": "text",
                "code": ocr_error.code,
                "fallback": "Retain the observed raster and inspect or rerun the rejected provider result.",
                "message": "OCR provider result was rejected; baseline image evidence remains available.",
                "provenance": _provenance(instant, [primitive_id], runtime),
                "record_id": _stable_id("diag_image_ocr_rejected", source_digest, ocr_error.code),
                "record_type": "diagnostic",
                "record_version": "0.1",
                "severity": "warning",
                "source_refs": [{"locator": "pixel-canvas", "source_id": source_id}],
                "support_level": "unsupported",
            }
        )
    diagnostics.sort(key=lambda item: item["record_id"])
    loss_summary = [reasons[name] for name in CAPABILITIES if capabilities[name] != "full"]
    storage_ref = f"sources/content/{source.name}" if embedding_policy == "embedded" else None
    source_record: dict[str, Any] = {
        "acquisition_origin": "local-file",
        "byte_size": source_bytes,
        "declared_format": _known(image_format),
        "declared_units": _known("px"),
        "detected_format": _known(image_format),
        "detected_producer": _known(f"Pillow/{runtime}"),
        "detected_units": _known("px"),
        "display_name": source.name,
        "embedding_policy": embedding_policy,
        "extractor": {"plugin_id": PLUGIN_ID, "plugin_version": PLUGIN_VERSION},
        "media_type": Image.MIME.get(image_format, "application/octet-stream"),
        "prior_source_revision": _unknown("AECCTX_PRIOR_REVISION_NOT_PROVIDED"),
        "provenance": _provenance(instant, [], runtime),
        "record_id": source_id,
        "record_type": "source",
        "record_version": "0.1",
        "safety_diagnostics": ["AECCTX_IMAGE_INPUT_TREATED_AS_DATA", "AECCTX_IMAGE_PIXEL_LIMIT_ENFORCED"],
        "sha256": source_digest,
        "source_id": source_id,
        "source_refs": [],
        "spatial_reference": _unknown("AECCTX_IMAGE_GEOREFERENCING_UNSUPPORTED"),
    }
    if storage_ref:
        source_record["storage_ref"] = storage_ref
    elif embedding_policy == "redacted":
        source_record["redaction_reason"] = "AECCTX_SOURCE_CONTENT_REDACTED_BY_POLICY"
    if aecctx_version == "0.2.0":
        for record in [source_record, *primitives, *assertions, *diagnostics]:
            record.setdefault("evidence_class", "observed")
            record["record_version"] = "0.2"
    record_sets = {
        "sources/sources.jsonl": [source_record],
        "evidence/primitives.jsonl": primitives,
        "evidence/assertions.jsonl": assertions,
        "model/entities.jsonl": [],
        "model/relations.jsonl": [],
        "diagnostics/diagnostics.jsonl": diagnostics,
    }
    artifacts = [
        PackageArtifact(path, b"".join(canonical_json(item) for item in sorted(items, key=lambda value: value["record_id"])), "application/x-ndjson", path.split("/")[-1].removesuffix(".jsonl"), True)
        for path, items in record_sets.items()
    ]
    context = (
        f"# Raster image AECCTX package\n\nPackage `{package_id}` preserves a {width}x{height} `{mode}` image in pixel coordinates. "
        "Pixels are not construction units without explicit calibration; vision interpretation, hidden geometry, and georeferencing are not inferred. "
        f"OCR word evidence is {'present but inferred and unverified' if mapping is not None else 'rejected with structured loss' if ocr_error is not None else 'not configured'}.\n"
    ).encode()
    artifacts.append(PackageArtifact("context/index.md", context, "text/markdown", "agent-context", False))
    if storage_ref:
        artifacts.append(PackageArtifact(storage_ref, source, Image.MIME.get(image_format, "application/octet-stream"), "embedded-source", True))
    manifest = PackageWriter(output, package_form=package_form).write(
        package_id=package_id,
        created_at=instant,
        source_ids=[source_id],
        capabilities=capabilities,
        loss_summary=loss_summary,
        embedding_policy=embedding_policy,
        producer={"name": PLUGIN_ID, "version": f"{PLUGIN_VERSION}+pillow.{runtime}"},
        artifacts=artifacts,
        aecctx_version=aecctx_version,
    )
    return IngestResult(package_id, source_id, manifest["logical_digest"], output)
