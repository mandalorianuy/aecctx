from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable

from ..ingest import CAPABILITIES, IngestResult, _timestamp
from ..package import PackageArtifact, PackageWriter, canonical_json, hash_file


PLUGIN_ID = "aecctx.adapter.dxf.ezdxf"
PLUGIN_VERSION = "0.1.0"


class DXFDependencyError(RuntimeError):
    code = "AECCTX_DXF_DEPENDENCY_MISSING"


def _ezdxf() -> tuple[Any, Any, Any]:
    try:
        import ezdxf
        from ezdxf.lldxf.tagwriter import TagCollector
        from ezdxf.lldxf.const import acad_release
    except ImportError as error:
        raise DXFDependencyError("Install AECCTX with the 'dxf' extra to use the DXF adapter") from error
    return ezdxf, TagCollector, acad_release


def _stable_id(prefix: str, source_digest: str, key: str) -> str:
    suffix = hashlib.sha256(f"{source_digest}\0{key}".encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{suffix}"


def _known(value: Any) -> dict[str, Any]:
    return {"state": "known", "value": value}


def _unknown(reason: str) -> dict[str, str]:
    return {"state": "unknown", "reason_code": reason}


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        return round(value, 12)
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if hasattr(value, "x") and hasattr(value, "y"):
        result = [round(float(value.x), 12), round(float(value.y), 12)]
        if hasattr(value, "z"):
            result.append(round(float(value.z), 12))
        return result
    return str(value)


def _provenance(instant: str, parents: Iterable[str], runtime_version: str, method: str = "ezdxf-extraction") -> dict[str, Any]:
    return {
        "method": method,
        "parent_record_ids": sorted(parents),
        "producer_id": PLUGIN_ID,
        "producer_version": f"{PLUGIN_VERSION}+ezdxf.{runtime_version}",
        "recorded_at": instant,
    }


def _unit_symbol(unit_code: int) -> str | None:
    return {
        1: "in",
        2: "ft",
        4: "mm",
        5: "cm",
        6: "m",
        7: "km",
    }.get(unit_code)


def _kind(dxftype: str) -> str:
    if dxftype in {"TEXT", "MTEXT", "ATTRIB", "ATTDEF", "DIMENSION"}:
        return "aecctx:annotation"
    if dxftype in {"LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE"}:
        return "aecctx:linear-element"
    if dxftype in {"HATCH", "SOLID", "TRACE", "3DFACE"}:
        return "aecctx:surface-element"
    return "aecctx:opaque-object"


def _geometry(entity: Any) -> dict[str, Any]:
    kind = entity.dxftype()
    dxf = entity.dxf
    if kind == "LINE":
        return _known({"end": _json_value(dxf.end), "start": _json_value(dxf.start), "type": "line"})
    if kind == "LWPOLYLINE":
        return _known({"closed": entity.closed, "points": [_json_value(point) for point in entity.get_points("xyseb")], "type": "lwpolyline"})
    if kind == "CIRCLE":
        return _known({"center": _json_value(dxf.center), "radius": round(float(dxf.radius), 12), "type": "circle"})
    if kind == "ARC":
        return _known({"center": _json_value(dxf.center), "end_angle": float(dxf.end_angle), "radius": float(dxf.radius), "start_angle": float(dxf.start_angle), "type": "arc"})
    if kind in {"TEXT", "MTEXT"}:
        insert = dxf.insert if dxf.hasattr("insert") else None
        text = entity.plain_text() if kind == "MTEXT" else dxf.text
        return _known({"insert": _json_value(insert), "text": text, "type": kind.lower()})
    if kind == "INSERT":
        return _known({"block_name": dxf.name, "insert": _json_value(dxf.insert), "rotation": float(dxf.get("rotation", 0.0)), "type": "insert"})
    if kind == "DIMENSION":
        try:
            measurement = round(float(entity.get_measurement()), 12)
        except Exception:
            measurement = None
        return _known({"dimension_type": int(dxf.dimtype), "measurement": measurement, "type": "dimension"})
    if kind == "HATCH":
        return _known({"boundary_path_count": len(entity.paths), "pattern_name": dxf.pattern_name, "solid_fill": bool(dxf.solid_fill), "type": "hatch"})
    if kind in {"SOLID", "TRACE", "3DFACE"}:
        vertices = [_json_value(dxf.get(name)) for name in ("vtx0", "vtx1", "vtx2", "vtx3") if dxf.hasattr(name)]
        return _known({"type": kind.lower(), "vertices": vertices})
    if kind == "POINT":
        return _known({"location": _json_value(dxf.location), "type": "point"})
    return {"state": "unsupported", "reason_code": "AECCTX_DXF_GEOMETRY_NOT_NORMALIZED"}


class DXFPlugin:
    def describe(self) -> dict[str, Any]:
        runtime = "not-installed"
        try:
            runtime = str(_ezdxf()[0].__version__)
        except DXFDependencyError:
            pass
        return {
            "deterministic": True,
            "distribution_posture": "optional-not-bundled",
            "execution_mode": "in-process-optional",
            "implementation_runtime": f"ezdxf/{runtime}",
            "input_capabilities": ["ASCII DXF", "Binary DXF"],
            "license_identifier": "MIT",
            "network_mode": "disabled",
            "output_capabilities": list(CAPABILITIES),
            "plugin_id": PLUGIN_ID,
            "plugin_version": PLUGIN_VERSION,
            "resource_limits": {"bytes": True, "records": True, "wall_time": False, "memory": False},
            "supported_extensions": [".dxf"],
            "supported_media_types": ["application/dxf", "application/x-dxf"],
        }

    def probe(self, prefix: bytes) -> dict[str, Any]:
        bounded = prefix[:64 * 1024]
        binary = bounded.startswith(b"AutoCAD Binary DXF")
        ascii_dxf = b"SECTION" in bounded and (b"$ACADVER" in bounded or b"HEADER" in bounded)
        return {
            "confidence": 1.0 if binary or ascii_dxf else 0.0,
            "format": "dxf-binary" if binary else "dxf-ascii" if ascii_dxf else "unknown",
            "mutated": False,
            "observed_bytes": min(len(prefix), 64 * 1024),
        }

    def extract(self, source_path: str | Path, *, source_id: str) -> Iterable[dict[str, Any]]:
        ezdxf, _, _ = _ezdxf()
        document = ezdxf.readfile(source_path)
        sequence = 0
        seen: set[str] = set()
        for layout in document.layouts:
            for entity in layout:
                handle = entity.dxf.get("handle", f"layout-{layout.name}-{sequence}")
                if handle in seen:
                    continue
                seen.add(handle)
                yield {
                    "diagnostics": [],
                    "event_type": "primitive",
                    "event_version": "0.1",
                    "extraction_confidence": {"band": "full", "method": "ezdxf"},
                    "parent_references": [],
                    "payload": {"dxf_type": entity.dxftype(), "handle": handle},
                    "sequence": sequence,
                    "source_id": source_id,
                    "source_locator": f"layout:{layout.name}/handle:{handle}",
                }
                sequence += 1

    def finalize(self, capabilities: dict[str, str], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "capabilities": capabilities,
            "diagnostic_count": len(diagnostics),
            "network_used": False,
            "plugin_id": PLUGIN_ID,
            "sanitization": ["links-not-followed", "commands-not-executed", "xrefs-not-opened"],
        }


def ingest_dxf(
    source_path: str | Path,
    output_path: str | Path,
    *,
    created_at: str | None = None,
    embedding_policy: str = "external",
    package_form: str = "directory",
) -> IngestResult:
    ezdxf, TagCollector, acad_release = _ezdxf()
    source = Path(source_path)
    output = Path(output_path)
    if not source.is_file() or source.is_symlink():
        raise ValueError("source_path must be a regular DXF file")
    if embedding_policy not in {"external", "embedded", "redacted"}:
        raise ValueError("embedding_policy must be external, embedded, or redacted")
    source_digest, source_bytes = hash_file(source)
    identity = source_digest[:24]
    source_id = f"src_{identity}"
    package_id = f"pkg_{identity}"
    instant = _timestamp(created_at)
    document = ezdxf.readfile(source)
    runtime_version = str(ezdxf.__version__)
    audit = document.audit()
    unit = _unit_symbol(int(document.units))

    container_by_handle: dict[str, str] = {}
    graphical: dict[str, Any] = {}
    for layout in document.layouts:
        for entity in layout:
            handle = entity.dxf.get("handle")
            if handle:
                graphical[handle] = entity
                container_by_handle[handle] = f"layout:{layout.name}"
    for block in document.blocks:
        if block.block_record.is_any_layout:
            continue
        for entity in block:
            handle = entity.dxf.get("handle")
            if handle and handle not in graphical:
                graphical[handle] = entity
                container_by_handle[handle] = f"block:{block.name}"

    primitives: list[dict[str, Any]] = []
    entity_records: list[dict[str, Any]] = []
    entity_ids: dict[str, str] = {}
    unsupported_handles: list[str] = []
    for handle, entity in sorted(graphical.items()):
        primitive_id = _stable_id("prim_dxf", source_digest, handle)
        entity_id = _stable_id("entity_dxf", source_digest, handle)
        entity_ids[handle] = entity_id
        collector = TagCollector(dxfversion=document.dxfversion)
        entity.export_dxf(collector)
        raw_tags = [{"code": tag.code, "value": _json_value(tag.value)} for tag in collector.tags]
        xdata: dict[str, list[dict[str, Any]]] = {}
        for appid in sorted(document.appids, key=lambda item: item.dxf.name):
            appid_name = appid.dxf.name
            if entity.has_xdata(appid_name):
                xdata[appid_name] = [{"code": tag.code, "value": _json_value(tag.value)} for tag in entity.get_xdata(appid_name)]
        geometry = _geometry(entity)
        if geometry["state"] == "unsupported":
            unsupported_handles.append(handle)
        locator = f"{container_by_handle[handle]}/handle:{handle}"
        primitive = {
            "container": _known(container_by_handle[handle]),
            "extraction_confidence": {"band": "full", "method": "ezdxf-entity-tags"},
            "geometry": geometry,
            "handle": handle,
            "layer": _known(entity.dxf.get("layer", "0")),
            "original_class": entity.dxftype(),
            "provenance": _provenance(instant, [source_id], runtime_version),
            "raw_tags": raw_tags,
            "record_id": primitive_id,
            "record_type": "primitive",
            "record_version": "0.1",
            "source_refs": [{"locator": locator, "source_id": source_id}],
        }
        if xdata:
            primitive["xdata"] = xdata
        primitives.append(primitive)
        entity_records.append(
            {
                "entity_id": entity_id,
                "kind": _kind(entity.dxftype()),
                "label": _known(entity.dxf.get("text")) if entity.dxftype() == "TEXT" else _unknown("AECCTX_DXF_LABEL_NOT_APPLICABLE"),
                "original_class": entity.dxftype(),
                "parent_evidence_ids": [primitive_id],
                "provenance": _provenance(instant, [primitive_id], runtime_version, "dxf-neutral-index"),
                "record_id": entity_id,
                "record_type": "entity",
                "record_version": "0.1",
                "source_local_identifiers": {"dxf_handle": handle, "layout_or_block": container_by_handle[handle]},
                "source_refs": [{"locator": locator, "source_id": source_id}],
            }
        )

    block_ids: dict[str, str] = {}
    for block in sorted(document.blocks, key=lambda item: item.name):
        if block.block_record.is_any_layout:
            continue
        block_id = _stable_id("entity_dxf_block", source_digest, block.name)
        block_ids[block.name] = block_id
        entity_records.append(
            {
                "block": {
                    "base_point": _json_value(block.block.dxf.base_point),
                    "is_anonymous": bool(block.block.is_anonymous),
                    "is_xref": bool(block.block_record.is_xref),
                    "name": block.name,
                    "xref_path": block.block.dxf.get("xref_path", ""),
                },
                "entity_id": block_id,
                "kind": "aecctx:opaque-object",
                "label": _known(block.name),
                "original_class": "DXF_BLOCK_DEFINITION",
                "parent_evidence_ids": [],
                "provenance": _provenance(instant, [source_id], runtime_version, "dxf-block-index"),
                "record_id": block_id,
                "record_type": "entity",
                "record_version": "0.1",
                "source_local_identifiers": {"block_name": block.name},
                "source_refs": [{"locator": f"block:{block.name}", "source_id": source_id}],
            }
        )

    layer_ids: dict[str, str] = {}
    for layer in sorted(document.layers, key=lambda item: item.dxf.name):
        layer_id = _stable_id("entity_dxf_layer", source_digest, layer.dxf.name)
        layer_ids[layer.dxf.name] = layer_id
        entity_records.append(
            {
                "entity_id": layer_id,
                "kind": "aecctx:opaque-object",
                "label": _known(layer.dxf.name),
                "layer": {"color": layer.color, "linetype": layer.dxf.linetype, "name": layer.dxf.name},
                "original_class": "DXF_LAYER",
                "parent_evidence_ids": [],
                "provenance": _provenance(instant, [source_id], runtime_version, "dxf-layer-index"),
                "record_id": layer_id,
                "record_type": "entity",
                "record_version": "0.1",
                "source_local_identifiers": {"layer_name": layer.dxf.name},
                "source_refs": [{"locator": f"table:LAYER/name:{layer.dxf.name}", "source_id": source_id}],
            }
        )

    relations: list[dict[str, Any]] = []
    for handle, entity in sorted(graphical.items()):
        if entity.dxftype() == "INSERT" and entity.dxf.name in block_ids:
            relation_id = _stable_id("relation_dxf_insert", source_digest, handle)
            relations.append(
                {
                    "endpoints": [
                        {"record_id": entity_ids[handle], "role": "insert"},
                        {"record_id": block_ids[entity.dxf.name], "role": "block-definition"},
                    ],
                    "evidence_record_ids": [_stable_id("prim_dxf", source_digest, handle)],
                    "original_class": "INSERT",
                    "provenance": _provenance(instant, [_stable_id("prim_dxf", source_digest, handle)], runtime_version),
                    "record_id": relation_id,
                    "record_type": "relation",
                    "record_version": "0.1",
                    "relation_id": relation_id,
                    "relation_type": "aecctx:representation",
                    "source_refs": [{"locator": f"{container_by_handle[handle]}/handle:{handle}", "source_id": source_id}],
                }
            )

    assertions: list[dict[str, Any]] = []
    for handle, entity in sorted(graphical.items()):
        layer = entity.dxf.get("layer", "0")
        assertion_id = _stable_id("assert_dxf_layer", source_digest, handle)
        assertions.append(
            {
                "evidence_record_ids": [_stable_id("prim_dxf", source_digest, handle)],
                "extraction_confidence": {"band": "full", "method": "ezdxf-dxf-namespace"},
                "interpretation_confidence": {"band": "full", "method": "dxf-layer-name-preserved"},
                "predicate": "dxf:layer",
                "provenance": _provenance(instant, [_stable_id("prim_dxf", source_digest, handle)], runtime_version),
                "record_id": assertion_id,
                "record_type": "assertion",
                "record_version": "0.1",
                "source_refs": [{"locator": f"{container_by_handle[handle]}/handle:{handle}", "source_id": source_id}],
                "subject_id": entity_ids[handle],
                "value": _known(layer),
                "verification_state": "extracted-not-domain-classified",
            }
        )

    capabilities = {name: "full" for name in CAPABILITIES}
    capabilities.update(
        {
            "properties": "partial",
            "relationships": "partial",
            "3d_geometry": "partial",
            "materials_styles": "partial",
            "georeferencing": "partial",
        }
    )
    if unsupported_handles:
        capabilities["2d_geometry"] = "partial"
    reason_codes = {
        "properties": "AECCTX_DXF_PROPERTIES_PARTIAL",
        "relationships": "AECCTX_DXF_RELATIONSHIPS_PARTIAL",
        "2d_geometry": "AECCTX_DXF_ENTITY_GEOMETRY_UNSUPPORTED",
        "3d_geometry": "AECCTX_DXF_3D_GEOMETRY_PARTIAL",
        "materials_styles": "AECCTX_DXF_STYLES_PARTIAL",
        "georeferencing": "AECCTX_DXF_GEOREFERENCING_NOT_DECLARED",
    }
    diagnostics: list[dict[str, Any]] = []
    for capability in CAPABILITIES:
        if capabilities[capability] == "full":
            continue
        diagnostics.append(
            {
                "affected_count": len(unsupported_handles) if capability == "2d_geometry" else 1,
                "capability": capability,
                "code": reason_codes[capability],
                "fallback": "Inspect preserved DXF raw tags, handles, layouts, blocks, and native class names.",
                "message": f"DXF capability is partial: {capability}",
                "provenance": _provenance(instant, [source_id], runtime_version),
                "record_id": _stable_id("diag_dxf_loss", source_digest, capability),
                "record_type": "diagnostic",
                "record_version": "0.1",
                "severity": "info",
                "source_refs": [{"locator": "dxf-document", "source_id": source_id}],
                "support_level": "partial",
            }
        )
    for index, error in enumerate(audit.errors):
        diagnostics.append(
            {
                "code": "AECCTX_DXF_AUDIT_ERROR",
                "message": str(error),
                "provenance": _provenance(instant, [source_id], runtime_version, "ezdxf-audit"),
                "record_id": _stable_id("diag_dxf_audit", source_digest, str(index)),
                "record_type": "diagnostic",
                "record_version": "0.1",
                "severity": "warning",
                "source_refs": [{"locator": "dxf-document", "source_id": source_id}],
            }
        )
    diagnostics.sort(key=lambda item: item["record_id"])
    loss_summary = [reason_codes[name] for name in CAPABILITIES if capabilities[name] != "full"]
    storage_ref = f"sources/content/{source.name}" if embedding_policy == "embedded" else None
    source_record: dict[str, Any] = {
        "acquisition_origin": "local-file",
        "byte_size": source_bytes,
        "declared_format": _known("DXF"),
        "declared_units": _known(unit) if unit else _unknown("AECCTX_DXF_UNITS_UNITLESS"),
        "detected_format": _known(document.dxfversion),
        "detected_producer": _known(f"ezdxf/{runtime_version}"),
        "detected_units": _known(unit) if unit else _unknown("AECCTX_DXF_UNITS_UNITLESS"),
        "display_name": source.name,
        "dxf_release": acad_release.get(document.dxfversion, "unknown"),
        "embedding_policy": embedding_policy,
        "extractor": {"plugin_id": PLUGIN_ID, "plugin_version": PLUGIN_VERSION},
        "layouts": sorted(document.layout_names()),
        "media_type": "application/dxf",
        "prior_source_revision": _unknown("AECCTX_PRIOR_REVISION_NOT_PROVIDED"),
        "provenance": _provenance(instant, [], runtime_version),
        "record_id": source_id,
        "record_type": "source",
        "record_version": "0.1",
        "safety_diagnostics": ["AECCTX_DXF_INPUT_TREATED_AS_DATA", "AECCTX_XREFS_NOT_OPENED", "AECCTX_COMMANDS_NOT_EXECUTED"],
        "sha256": source_digest,
        "source_id": source_id,
        "source_refs": [],
        "spatial_reference": _unknown("AECCTX_DXF_GEOREFERENCING_NOT_DECLARED"),
    }
    if storage_ref:
        source_record["storage_ref"] = storage_ref
    elif embedding_policy == "redacted":
        source_record["redaction_reason"] = "AECCTX_SOURCE_CONTENT_REDACTED_BY_POLICY"

    record_sets = {
        "sources/sources.jsonl": [source_record],
        "evidence/primitives.jsonl": primitives,
        "evidence/assertions.jsonl": assertions,
        "model/entities.jsonl": entity_records,
        "model/relations.jsonl": relations,
        "diagnostics/diagnostics.jsonl": diagnostics,
    }
    artifacts = [
        PackageArtifact(path, b"".join(canonical_json(item) for item in sorted(items, key=lambda value: value["record_id"])), "application/x-ndjson", path.split("/")[-1].removesuffix(".jsonl"), True)
        for path, items in record_sets.items()
    ]
    context = (
        f"# DXF AECCTX package\n\nPackage `{package_id}` preserves DXF `{document.dxfversion}`, {len(primitives)} graphical primitives, "
        f"{len(document.layout_names())} layouts, {len(block_ids)} block definitions, and {len(layer_ids)} layers. "
        "Layer names and entity classes are source evidence, not consumer-domain classifications.\n"
    ).encode("utf-8")
    artifacts.append(PackageArtifact("context/index.md", context, "text/markdown", "agent-context", False))
    if storage_ref:
        artifacts.append(PackageArtifact(storage_ref, source, "application/dxf", "embedded-source", True))
    manifest = PackageWriter(output, package_form=package_form).write(
        package_id=package_id,
        created_at=instant,
        source_ids=[source_id],
        capabilities=capabilities,
        loss_summary=loss_summary,
        embedding_policy=embedding_policy,
        producer={"name": PLUGIN_ID, "version": f"{PLUGIN_VERSION}+ezdxf.{runtime_version}"},
        artifacts=artifacts,
    )
    return IngestResult(package_id, source_id, manifest["logical_digest"], output)
