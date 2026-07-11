from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

from ..ingest import CAPABILITIES, IngestResult, _timestamp
from ..package import PackageArtifact, PackageWriter, canonical_json, hash_file


PLUGIN_ID = "aecctx.adapter.pdf.pypdf"
PLUGIN_VERSION = "0.1.0"
PATH_OPERATORS = {b"m", b"l", b"c", b"v", b"y", b"h", b"re"}
PAINT_OPERATORS = {b"S", b"s", b"f", b"F", b"f*", b"B", b"B*", b"b", b"b*", b"n"}


class PDFDependencyError(RuntimeError):
    code = "AECCTX_PDF_DEPENDENCY_MISSING"


def _pypdf() -> tuple[Any, Any]:
    try:
        import pypdf
        from pypdf.generic import ContentStream
    except ImportError as error:
        raise PDFDependencyError("Install AECCTX with the 'pdf' extra to use the PDF adapter") from error
    return pypdf, ContentStream


def _stable_id(prefix: str, source_digest: str, key: str) -> str:
    suffix = hashlib.sha256(f"{source_digest}\0{key}".encode()).hexdigest()[:24]
    return f"{prefix}_{suffix}"


def _known(value: Any) -> dict[str, Any]:
    return {"state": "known", "value": value}


def _unknown(reason: str) -> dict[str, str]:
    return {"state": "unknown", "reason_code": reason}


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return round(value, 9)
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    try:
        return round(float(value), 9)
    except (TypeError, ValueError):
        return str(value)


def _provenance(instant: str, parents: list[str], runtime: str, method: str = "pypdf-extraction") -> dict[str, Any]:
    return {
        "method": method,
        "parent_record_ids": sorted(parents),
        "producer_id": PLUGIN_ID,
        "producer_version": f"{PLUGIN_VERSION}+pypdf.{runtime}",
        "recorded_at": instant,
    }


class PDFPlugin:
    def describe(self) -> dict[str, Any]:
        runtime = "not-installed"
        try:
            runtime = str(_pypdf()[0].__version__)
        except PDFDependencyError:
            pass
        return {
            "deterministic": True,
            "distribution_posture": "optional-not-bundled",
            "execution_mode": "in-process-optional",
            "implementation_runtime": f"pypdf/{runtime}",
            "input_capabilities": ["PDF vector content streams", "PDF embedded raster images"],
            "license_identifier": "BSD-3-Clause",
            "network_mode": "disabled",
            "output_capabilities": list(CAPABILITIES),
            "plugin_id": PLUGIN_ID,
            "plugin_version": PLUGIN_VERSION,
            "resource_limits": {"bytes": True, "records": True, "wall_time": False, "memory": False},
            "supported_extensions": [".pdf"],
            "supported_media_types": ["application/pdf"],
        }

    def probe(self, prefix: bytes) -> dict[str, Any]:
        bounded = prefix[:64 * 1024]
        detected = bounded.startswith(b"%PDF-")
        return {
            "confidence": 1.0 if detected else 0.0,
            "format": "pdf" if detected else "unknown",
            "mutated": False,
            "observed_bytes": min(len(prefix), 64 * 1024),
        }

    def extract(self, source_path: str | Path, *, source_id: str) -> Iterable[dict[str, Any]]:
        pypdf, _ = _pypdf()
        reader = pypdf.PdfReader(source_path, strict=True)
        sequence = 0
        for page_number, page in enumerate(reader.pages, 1):
            yield {
                "diagnostics": [],
                "event_type": "container",
                "event_version": "0.1",
                "extraction_confidence": {"band": "full", "method": "pypdf-page-tree"},
                "parent_references": [],
                "payload": {"media_box": [float(value) for value in page.mediabox], "page": page_number},
                "sequence": sequence,
                "source_id": source_id,
                "source_locator": f"page:{page_number}",
            }
            sequence += 1
            text = (page.extract_text() or "").strip()
            if text:
                yield {
                    "diagnostics": [],
                    "event_type": "primitive",
                    "event_version": "0.1",
                    "extraction_confidence": {"band": "full", "method": "pypdf-text-extraction"},
                    "parent_references": [f"page:{page_number}"],
                    "payload": {"original_class": "PDF_TEXT", "text": text},
                    "sequence": sequence,
                    "source_id": source_id,
                    "source_locator": f"page:{page_number}/text",
                }
                sequence += 1

    def finalize(self, capabilities: dict[str, str], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "capabilities": capabilities,
            "diagnostic_count": len(diagnostics),
            "network_used": False,
            "plugin_id": PLUGIN_ID,
            "sanitization": ["actions-not-executed", "links-not-followed", "javascript-not-executed"],
        }


def ingest_pdf(
    source_path: str | Path,
    output_path: str | Path,
    *,
    created_at: str | None = None,
    embedding_policy: str = "external",
    package_form: str = "directory",
) -> IngestResult:
    pypdf, ContentStream = _pypdf()
    source = Path(source_path)
    output = Path(output_path)
    if not source.is_file() or source.is_symlink():
        raise ValueError("source_path must be a regular PDF file")
    if embedding_policy not in {"external", "embedded", "redacted"}:
        raise ValueError("embedding_policy must be external, embedded, or redacted")
    source_digest, source_bytes = hash_file(source)
    identity = source_digest[:24]
    source_id = f"src_{identity}"
    package_id = f"pkg_{identity}"
    instant = _timestamp(created_at)
    reader = pypdf.PdfReader(source, strict=True)
    runtime = str(pypdf.__version__)
    primitives: list[dict[str, Any]] = []
    entities: list[dict[str, Any]] = []
    derived_artifacts: list[PackageArtifact] = []
    text_count = 0
    image_count = 0
    path_count = 0
    for page_index, page in enumerate(reader.pages, 1):
        media_box = [round(float(value), 9) for value in (page.mediabox.left, page.mediabox.bottom, page.mediabox.right, page.mediabox.top)]
        page_id = _stable_id("entity_pdf_page", source_digest, str(page_index))
        entities.append(
            {
                "entity_id": page_id,
                "kind": "aecctx:spatial-container",
                "label": _known(f"Page {page_index}"),
                "original_class": "PDF_PAGE",
                "parent_evidence_ids": [],
                "provenance": _provenance(instant, [source_id], runtime, "pdf-page-index"),
                "record_id": page_id,
                "record_type": "entity",
                "record_version": "0.1",
                "source_local_identifiers": {"page": page_index},
                "source_refs": [{"locator": f"page:{page_index}", "source_id": source_id}],
                "viewport": {"media_box": media_box, "origin": "bottom-left", "unit": "pt"},
            }
        )
        pending_path: list[dict[str, Any]] = []
        try:
            stream = ContentStream(page.get_contents(), reader)
            operations = stream.operations
        except Exception:
            operations = []
        for operands, operator in operations:
            if operator in PATH_OPERATORS:
                pending_path.append({"operands": [_json_value(value) for value in operands], "operator": operator.decode("ascii")})
            elif operator in PAINT_OPERATORS and pending_path:
                path_count += 1
                record_id = _stable_id("prim_pdf_path", source_digest, f"{page_index}:{path_count}")
                primitives.append(
                    {
                        "container": _known(f"page:{page_index}"),
                        "coordinate_system": {"axis_x": "right", "axis_y": "up", "origin": "bottom-left", "unit": "pt"},
                        "extraction_confidence": {"band": "full", "method": "pypdf-content-operators"},
                        "interpretation_confidence": {"band": "unknown", "method": "no-drawing-semantics-inferred"},
                        "original_class": "PDF_PATH",
                        "paint_operator": operator.decode("ascii"),
                        "path_operations": pending_path,
                        "provenance": _provenance(instant, [source_id], runtime),
                        "record_id": record_id,
                        "record_type": "primitive",
                        "record_version": "0.1",
                        "source_refs": [{"locator": f"page:{page_index}/path:{path_count}", "source_id": source_id}],
                        "viewport": {"media_box": media_box},
                    }
                )
                pending_path = []
        extracted_text = (page.extract_text() or "").strip()
        if extracted_text:
            text_count += 1
            record_id = _stable_id("prim_pdf_text", source_digest, f"{page_index}:{text_count}")
            primitives.append(
                {
                    "container": _known(f"page:{page_index}"),
                    "coordinate_system": {"axis_x": "right", "axis_y": "up", "origin": "bottom-left", "unit": "pt"},
                    "extraction_confidence": {"band": "full", "method": "pypdf-text-extraction"},
                    "interpretation_confidence": {"band": "unknown", "method": "no-document-semantics-inferred"},
                    "original_class": "PDF_TEXT",
                    "provenance": _provenance(instant, [source_id], runtime),
                    "record_id": record_id,
                    "record_type": "primitive",
                    "record_version": "0.1",
                    "source_refs": [{"locator": f"page:{page_index}/text", "source_id": source_id}],
                    "value": _known(extracted_text),
                    "viewport": {"media_box": media_box},
                }
            )
        for page_image_index, image_file in enumerate(page.images, 1):
            image_count += 1
            suffix = Path(image_file.name).suffix.lower() or ".bin"
            artifact_path = f"artifacts/pdf/page-{page_index:04d}-image-{page_image_index:04d}{suffix}"
            data = image_file.data
            digest = hashlib.sha256(data).hexdigest()
            width, height = image_file.image.size
            derived_artifacts.append(PackageArtifact(artifact_path, data, image_file.image.get_format_mimetype() or "application/octet-stream", "pdf-raster-image", False))
            record_id = _stable_id("prim_pdf_raster", source_digest, f"{page_index}:{page_image_index}")
            primitives.append(
                {
                    "artifact_ref": {"path": artifact_path, "sha256": digest, "status": "derived-decoded-image"},
                    "calibration": _unknown("AECCTX_PDF_PIXEL_CALIBRATION_NOT_DECLARED"),
                    "container": _known(f"page:{page_index}"),
                    "extraction_confidence": {"band": "full", "method": "pypdf-image-xobject"},
                    "interpretation_confidence": {"band": "unknown", "method": "no-vision-provider"},
                    "original_class": "PDF_RASTER_IMAGE",
                    "pixel_geometry": {"height": height, "origin": "top-left", "unit": "px", "width": width},
                    "provenance": _provenance(instant, [source_id], runtime),
                    "record_id": record_id,
                    "record_type": "primitive",
                    "record_version": "0.1",
                    "source_refs": [{"locator": f"page:{page_index}/image:{image_file.name}", "source_id": source_id}],
                    "viewport": {"media_box": media_box},
                }
            )

    capabilities = {name: "full" for name in CAPABILITIES}
    capabilities.update(
        {
            "properties": "partial",
            "relationships": "opaque",
            "2d_geometry": "partial",
            "3d_geometry": "unsupported",
            "materials_styles": "partial",
            "georeferencing": "unsupported",
        }
    )
    capabilities["text"] = "full" if text_count else "unsupported"
    reasons = {
        "properties": "AECCTX_PDF_PROPERTIES_PARTIAL",
        "relationships": "AECCTX_PDF_RELATIONSHIPS_OPAQUE",
        "text": "AECCTX_OCR_PROVIDER_NOT_CONFIGURED",
        "2d_geometry": "AECCTX_PDF_VECTOR_EXTRACTION_PARTIAL" if path_count else "AECCTX_PDF_RASTER_PIXEL_GEOMETRY_PARTIAL",
        "3d_geometry": "AECCTX_PDF_HIDDEN_GEOMETRY_UNSUPPORTED",
        "materials_styles": "AECCTX_PDF_STYLES_PARTIAL",
        "georeferencing": "AECCTX_PDF_GEOREFERENCING_UNSUPPORTED",
    }
    diagnostics = []
    for capability in CAPABILITIES:
        level = capabilities[capability]
        if level == "full":
            continue
        diagnostics.append(
            {
                "affected_count": len(reader.pages),
                "capability": capability,
                "code": reasons[capability],
                "fallback": "Inspect preserved PDF page primitives, content operators, text, and raster artifacts.",
                "message": f"PDF capability is {level}: {capability}",
                "provenance": _provenance(instant, [source_id], runtime),
                "record_id": _stable_id("diag_pdf_loss", source_digest, capability),
                "record_type": "diagnostic",
                "record_version": "0.1",
                "severity": "info",
                "source_refs": [{"locator": "pdf-document", "source_id": source_id}],
                "support_level": level,
            }
        )
    diagnostics.sort(key=lambda item: item["record_id"])
    loss_summary = [reasons[name] for name in CAPABILITIES if capabilities[name] != "full"]
    storage_ref = f"sources/content/{source.name}" if embedding_policy == "embedded" else None
    metadata = {str(key): _json_value(value) for key, value in sorted((reader.metadata or {}).items())}
    source_record: dict[str, Any] = {
        "acquisition_origin": "local-file",
        "byte_size": source_bytes,
        "declared_format": _known("PDF"),
        "declared_units": _known("pt"),
        "detected_format": _known("PDF"),
        "detected_producer": _known(f"pypdf/{runtime}"),
        "detected_units": _known("pt"),
        "display_name": source.name,
        "embedding_policy": embedding_policy,
        "extractor": {"plugin_id": PLUGIN_ID, "plugin_version": PLUGIN_VERSION},
        "media_type": "application/pdf",
        "metadata": metadata,
        "page_count": len(reader.pages),
        "prior_source_revision": _unknown("AECCTX_PRIOR_REVISION_NOT_PROVIDED"),
        "provenance": _provenance(instant, [], runtime),
        "record_id": source_id,
        "record_type": "source",
        "record_version": "0.1",
        "safety_diagnostics": ["AECCTX_PDF_INPUT_TREATED_AS_DATA", "AECCTX_PDF_ACTIONS_NOT_EXECUTED", "AECCTX_PDF_LINKS_NOT_FOLLOWED"],
        "sha256": source_digest,
        "source_id": source_id,
        "source_refs": [],
        "spatial_reference": _unknown("AECCTX_PDF_GEOREFERENCING_UNSUPPORTED"),
    }
    if storage_ref:
        source_record["storage_ref"] = storage_ref
    elif embedding_policy == "redacted":
        source_record["redaction_reason"] = "AECCTX_SOURCE_CONTENT_REDACTED_BY_POLICY"
    record_sets = {
        "sources/sources.jsonl": [source_record],
        "evidence/primitives.jsonl": primitives,
        "evidence/assertions.jsonl": [],
        "model/entities.jsonl": entities,
        "model/relations.jsonl": [],
        "diagnostics/diagnostics.jsonl": diagnostics,
    }
    artifacts = [
        PackageArtifact(path, b"".join(canonical_json(item) for item in sorted(items, key=lambda value: value["record_id"])), "application/x-ndjson", path.split("/")[-1].removesuffix(".jsonl"), True)
        for path, items in record_sets.items()
    ]
    context = (
        f"# PDF AECCTX package\n\nPackage `{package_id}` contains {len(reader.pages)} pages, {path_count} vector path records, "
        f"{text_count} text records, and {image_count} raster image records. Pixels are not construction units without calibration; no hidden 3D geometry is inferred.\n"
    ).encode()
    artifacts.append(PackageArtifact("context/index.md", context, "text/markdown", "agent-context", False))
    artifacts.extend(derived_artifacts)
    if storage_ref:
        artifacts.append(PackageArtifact(storage_ref, source, "application/pdf", "embedded-source", True))
    manifest = PackageWriter(output, package_form=package_form).write(
        package_id=package_id,
        created_at=instant,
        source_ids=[source_id],
        capabilities=capabilities,
        loss_summary=loss_summary,
        embedding_policy=embedding_policy,
        producer={"name": PLUGIN_ID, "version": f"{PLUGIN_VERSION}+pypdf.{runtime}"},
        artifacts=artifacts,
    )
    return IngestResult(package_id, source_id, manifest["logical_digest"], output)
