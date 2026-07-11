from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from ..ingest import CAPABILITIES, IngestResult, _timestamp
from ..package import PackageArtifact, PackageWriter, canonical_json, hash_file


PLUGIN_ID = "aecctx.adapter.ifc.ifcopenshell"
PLUGIN_VERSION = "0.1.0"


class IFCDependencyError(RuntimeError):
    code = "AECCTX_IFC_DEPENDENCY_MISSING"


def _ifcopenshell() -> tuple[Any, Any, Any, Any, Any]:
    try:
        import ifcopenshell
        import ifcopenshell.geom
        import ifcopenshell.util.element
        import ifcopenshell.util.placement
        import ifcopenshell.validate
    except ImportError as error:
        raise IFCDependencyError("Install AECCTX with the 'ifc' extra to use the IFC adapter") from error
    return (
        ifcopenshell,
        ifcopenshell.geom,
        ifcopenshell.util.element,
        ifcopenshell.util.placement,
        ifcopenshell.validate,
    )


def _stable_id(prefix: str, source_digest: str, key: str) -> str:
    suffix = hashlib.sha256(f"{source_digest}\0{key}".encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{suffix}"


def _known(value: Any, **extra: Any) -> dict[str, Any]:
    return {"state": "known", "value": value, **extra}


def _null(reason: str = "IFC_EXPLICIT_NULL") -> dict[str, str]:
    return {"state": "explicit_null", "reason_code": reason}


def _unsupported(reason: str) -> dict[str, str]:
    return {"state": "unsupported", "reason_code": reason}


def _json_value(value: Any) -> tuple[Any, bool]:
    if value is None or isinstance(value, (str, int, bool)):
        return value, True
    if isinstance(value, float):
        return round(value, 12), True
    if isinstance(value, (tuple, list)):
        converted = []
        supported = True
        for item in value:
            normalized, item_supported = _json_value(item)
            converted.append(normalized)
            supported = supported and item_supported
        return converted, supported
    if hasattr(value, "id") and hasattr(value, "is_a"):
        return {"ifc_class": value.is_a(), "ifc_step_id": value.id()}, True
    wrapped = getattr(value, "wrappedValue", None)
    if wrapped is not None:
        return _json_value(wrapped)
    return repr(value), False


def _value_state(value: Any) -> dict[str, Any]:
    if value is None:
        return _null()
    normalized, supported = _json_value(value)
    return _known(normalized) if supported else _unsupported("IFC_ATTRIBUTE_TYPE_UNSUPPORTED")


def _provenance(instant: str, parents: Iterable[str], runtime_version: str, method: str = "ifcopenshell-extraction") -> dict[str, Any]:
    return {
        "method": method,
        "parent_record_ids": sorted(parents),
        "producer_id": PLUGIN_ID,
        "producer_version": f"{PLUGIN_VERSION}+ifcopenshell.{runtime_version}",
        "recorded_at": instant,
    }


def _source_refs(source_id: str, step_id: int) -> list[dict[str, str]]:
    return [{"locator": f"ifc-step:#{step_id}", "source_id": source_id}]


def _neutral_kind(instance: Any) -> str:
    if instance.is_a("IfcSpatialStructureElement") or instance.is_a("IfcProject"):
        return "aecctx:spatial-container"
    if instance.is_a("IfcElement"):
        return "aecctx:solid-element"
    return "aecctx:opaque-object"


def _relation_type(ifc_class: str) -> str:
    mapping = {
        "IfcRelAggregates": "aecctx:aggregation",
        "IfcRelContainedInSpatialStructure": "aecctx:containment",
        "IfcRelDefinesByType": "aecctx:type-assignment",
        "IfcRelAssociatesMaterial": "aecctx:material-assignment",
        "IfcRelConnectsElements": "aecctx:connection",
    }
    return mapping.get(ifc_class, f"ifc:{ifc_class}")


class IFCPlugin:
    def describe(self) -> dict[str, Any]:
        runtime = "not-installed"
        try:
            runtime = str(_ifcopenshell()[0].version)
        except IFCDependencyError:
            pass
        return {
            "deterministic": True,
            "distribution_posture": "optional-not-bundled",
            "execution_mode": "in-process-optional",
            "implementation_runtime": f"ifcopenshell/{runtime}",
            "input_capabilities": ["IFC2X3", "IFC4", "IFC4X3"],
            "license_identifier": "LGPL-3.0-or-later",
            "network_mode": "disabled",
            "output_capabilities": list(CAPABILITIES),
            "plugin_id": PLUGIN_ID,
            "plugin_version": PLUGIN_VERSION,
            "resource_limits": {"bytes": True, "records": True, "wall_time": False, "memory": False},
            "supported_extensions": [".ifc", ".ifczip"],
            "supported_media_types": ["application/x-step", "application/vnd.ifc"],
        }

    def probe(self, prefix: bytes) -> dict[str, Any]:
        bounded = prefix[:64 * 1024].upper()
        is_step = b"ISO-10303-21" in bounded and b"FILE_SCHEMA" in bounded and b"IFC" in bounded
        return {
            "confidence": 1.0 if is_step else 0.0,
            "format": "ifc-step" if is_step else "unknown",
            "mutated": False,
            "observed_bytes": min(len(prefix), 64 * 1024),
        }

    def extract(self, source_path: str | Path, *, source_id: str) -> Iterable[dict[str, Any]]:
        ifcopenshell, _, ifc_element, _, _ = _ifcopenshell()
        model = ifcopenshell.open(Path(source_path))
        instances = sorted(list(model), key=lambda item: item.id())
        sequence = 0

        def event(event_type: str, instance: Any, payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal sequence
            result = {
                "diagnostics": [],
                "event_type": event_type,
                "event_version": "0.1",
                "extraction_confidence": {"band": "full", "method": "ifcopenshell"},
                "parent_references": [],
                "payload": payload,
                "sequence": sequence,
                "source_id": source_id,
                "source_locator": f"ifc-step:#{instance.id()}",
            }
            sequence += 1
            return result

        for instance in instances:
            yield event(
                "primitive",
                instance,
                {"ifc_class": instance.is_a(), "ifc_step_id": instance.id()},
            )
        entity_instances = [
            instance
            for instance in instances
            if instance.is_a("IfcObjectDefinition")
            or instance.is_a("IfcMaterial")
            or instance.is_a("IfcPropertySetDefinition")
        ]
        for instance in entity_instances:
            yield event(
                "entity",
                instance,
                {
                    "ifc_class": instance.is_a(),
                    "ifc_step_id": instance.id(),
                    "kind": _neutral_kind(instance),
                    "original_class": instance.is_a(),
                },
            )
            if instance.is_a("IfcObject"):
                for set_name, values in sorted(ifc_element.get_psets(instance).items()):
                    for property_name, value in sorted(values.items()):
                        if property_name == "id":
                            continue
                        yield event(
                            "assertion",
                            instance,
                            {
                                "ifc_step_id": instance.id(),
                                "predicate": f"ifc:{set_name}.{property_name}",
                                "value": _value_state(value),
                            },
                        )
        for instance in (item for item in instances if item.is_a("IfcRelationship")):
            yield event(
                "relation",
                instance,
                {
                    "ifc_step_id": instance.id(),
                    "original_class": instance.is_a(),
                    "relation_type": _relation_type(instance.is_a()),
                },
            )

    def finalize(self, capabilities: dict[str, str], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "capabilities": capabilities,
            "diagnostic_count": len(diagnostics),
            "network_used": False,
            "plugin_id": PLUGIN_ID,
            "sanitization": ["embedded-active-content-not-executed", "external-links-not-followed"],
        }


def ingest_ifc(
    source_path: str | Path,
    output_path: str | Path,
    *,
    created_at: str | None = None,
    embedding_policy: str = "external",
    package_form: str = "directory",
) -> IngestResult:
    ifcopenshell, ifc_geom, ifc_element, ifc_placement, ifc_validate = _ifcopenshell()
    source = Path(source_path)
    output = Path(output_path)
    if not source.is_file() or source.is_symlink():
        raise ValueError("source_path must be a regular IFC file")
    if embedding_policy not in {"external", "embedded", "redacted"}:
        raise ValueError("embedding_policy must be external, embedded, or redacted")
    source_digest, source_bytes = hash_file(source)
    instant = _timestamp(created_at)
    identity = source_digest[:24]
    source_id = f"src_{identity}"
    package_id = f"pkg_{identity}"
    model = ifcopenshell.open(source)
    runtime_version = str(ifcopenshell.version)
    all_instances = sorted(list(model), key=lambda item: item.id())

    primitives: list[dict[str, Any]] = []
    primitive_ids: dict[int, str] = {}
    unsupported_fields: list[tuple[int, str]] = []
    for instance in all_instances:
        primitive_id = _stable_id("prim_ifc", source_digest, str(instance.id()))
        primitive_ids[instance.id()] = primitive_id
        raw_attributes: dict[str, Any] = {}
        info = instance.get_info(include_identifier=False, recursive=False)
        for name, value in sorted(info.items()):
            if name == "type":
                continue
            state = _value_state(value)
            raw_attributes[name] = state
            if state["state"] == "unsupported":
                unsupported_fields.append((instance.id(), name))
        primitives.append(
            {
                "container": _known("ifc-data-section"),
                "extraction_confidence": {"band": "full", "method": "ifcopenshell-step-entity"},
                "original_class": instance.is_a(),
                "provenance": _provenance(instant, [source_id], runtime_version),
                "raw_attributes": raw_attributes,
                "record_id": primitive_id,
                "record_type": "primitive",
                "record_version": "0.1",
                "source_refs": _source_refs(source_id, instance.id()),
            }
        )

    entity_instances = [
        instance
        for instance in all_instances
        if instance.is_a("IfcObjectDefinition")
        or instance.is_a("IfcMaterial")
        or instance.is_a("IfcPropertySetDefinition")
    ]
    entity_ids = {instance.id(): _stable_id("entity_ifc", source_digest, str(instance.id())) for instance in entity_instances}
    geometry_artifacts: list[PackageArtifact] = []
    entities: list[dict[str, Any]] = []
    geometry_failures: list[tuple[int, str]] = []
    settings = ifc_geom.settings()
    for instance in entity_instances:
        entity_id = entity_ids[instance.id()]
        name = getattr(instance, "Name", None)
        entity: dict[str, Any] = {
            "entity_id": entity_id,
            "geometry_refs": [],
            "kind": _neutral_kind(instance),
            "label": _known(name) if name is not None else _null(),
            "original_class": instance.is_a(),
            "parent_evidence_ids": [primitive_ids[instance.id()]],
            "property_assertion_refs": [],
            "provenance": _provenance(instant, [primitive_ids[instance.id()]], runtime_version, "ifc-neutral-index"),
            "record_id": entity_id,
            "record_type": "entity",
            "record_version": "0.1",
            "representation_refs": [],
            "source_local_identifiers": {"ifc_step_id": instance.id()},
            "source_refs": _source_refs(source_id, instance.id()),
        }
        global_id = getattr(instance, "GlobalId", None)
        if global_id:
            entity["source_local_identifiers"]["global_id"] = global_id
        placement = getattr(instance, "ObjectPlacement", None)
        if placement is not None:
            try:
                matrix = ifc_placement.get_local_placement(placement).tolist()
                entity["placement"] = _known([[round(float(value), 12) for value in row] for row in matrix])
            except Exception:
                entity["placement"] = _unsupported("IFC_PLACEMENT_EXTRACTION_FAILED")
        elif instance.is_a("IfcProduct"):
            entity["placement"] = _null()
        representation = getattr(instance, "Representation", None)
        if representation is not None:
            representations = getattr(representation, "Representations", ()) or ()
            entity["representation_refs"] = [
                {"ifc_class": item.is_a(), "ifc_step_id": item.id(), "source_evidence_id": primitive_ids[item.id()]}
                for item in sorted(representations, key=lambda item: item.id())
            ]
            try:
                shape = ifc_geom.create_shape(settings, instance)
                vertices_flat = [round(float(value), 12) for value in shape.geometry.verts]
                faces_flat = [int(value) for value in shape.geometry.faces]
                vertices = [vertices_flat[index : index + 3] for index in range(0, len(vertices_flat), 3)]
                triangles = [faces_flat[index : index + 3] for index in range(0, len(faces_flat), 3)]
                mesh_path = f"geometry/ifc/mesh-{instance.id():08d}.json"
                mesh = {
                    "coordinate_space": "ifc-product-local",
                    "ifc_step_id": instance.id(),
                    "representation": "tessellated",
                    "source_evidence_id": primitive_ids[instance.id()],
                    "source_record_id": entity_id,
                    "triangles": triangles,
                    "unit": "m",
                    "vertices": vertices,
                }
                mesh_bytes = canonical_json(mesh)
                mesh_digest = hashlib.sha256(mesh_bytes).hexdigest()
                geometry_artifacts.append(
                    PackageArtifact(mesh_path, mesh_bytes, "application/vnd.aecctx.ifc-mesh+json", "ifc-tessellated-geometry", False)
                )
                coordinates = vertices or [[0.0, 0.0, 0.0]]
                bounds = {
                    "max": [max(point[axis] for point in coordinates) for axis in range(3)],
                    "min": [min(point[axis] for point in coordinates) for axis in range(3)],
                }
                entity["geometry_refs"] = [
                    {
                        "artifact_path": mesh_path,
                        "dimensionality": 3,
                        "representation_role": "tessellated",
                        "sha256": mesh_digest,
                        "status": "derived",
                        "units": _known("m"),
                        "bounds": bounds,
                    }
                ]
            except Exception as error:
                geometry_failures.append((instance.id(), type(error).__name__))
        entities.append(entity)

    assertions: list[dict[str, Any]] = []
    for instance in entity_instances:
        if not instance.is_a("IfcObject"):
            continue
        psets = ifc_element.get_psets(instance, psets_only=False, qtos_only=False)
        for set_name, values in sorted(psets.items()):
            for property_name, value in sorted(values.items()):
                if property_name == "id":
                    continue
                assertion_id = _stable_id("assert_ifc", source_digest, f"{instance.id()}:{set_name}:{property_name}")
                assertion = {
                    "evidence_record_ids": [primitive_ids[instance.id()]],
                    "extraction_confidence": {"band": "full", "method": "ifcopenshell-property-set"},
                    "interpretation_confidence": {"band": "full", "method": "ifc-schema-name-preserved"},
                    "predicate": f"ifc:{set_name}.{property_name}",
                    "provenance": _provenance(instant, [primitive_ids[instance.id()]], runtime_version),
                    "record_id": assertion_id,
                    "record_type": "assertion",
                    "record_version": "0.1",
                    "source_refs": _source_refs(source_id, instance.id()),
                    "subject_id": entity_ids[instance.id()],
                    "value": _value_state(value),
                    "verification_state": "extracted-not-engineering-approved",
                }
                assertions.append(assertion)
                next(entity for entity in entities if entity["record_id"] == entity_ids[instance.id()])["property_assertion_refs"].append(assertion_id)

    relations: list[dict[str, Any]] = []
    for instance in (item for item in all_instances if item.is_a("IfcRelationship")):
        endpoints: list[dict[str, Any]] = []
        for index in range(len(instance)):
            attribute_name = instance.attribute_name(index)
            value = instance[index]
            values = value if isinstance(value, tuple) else (value,)
            for target in values:
                target_id = getattr(target, "id", lambda: 0)()
                if target_id in entity_ids:
                    endpoints.append({"record_id": entity_ids[target_id], "role": attribute_name})
        relation_id = _stable_id("relation_ifc", source_digest, str(instance.id()))
        relations.append(
            {
                "endpoints": endpoints,
                "evidence_record_ids": [primitive_ids[instance.id()]],
                "original_class": instance.is_a(),
                "provenance": _provenance(instant, [primitive_ids[instance.id()]], runtime_version),
                "record_id": relation_id,
                "record_type": "relation",
                "record_version": "0.1",
                "relation_id": relation_id,
                "relation_type": _relation_type(instance.is_a()),
                "source_refs": _source_refs(source_id, instance.id()),
            }
        )

    diagnostics: list[dict[str, Any]] = []
    logger = ifc_validate.json_logger()
    ifc_validate.validate(model, logger)
    for index, statement in enumerate(logger.statements):
        diagnostics.append(
            {
                "code": "AECCTX_IFC_SCHEMA_VALIDATION",
                "ifc_validation": _json_value(statement)[0],
                "message": str(statement.get("message", "IFC validation diagnostic")),
                "provenance": _provenance(instant, [source_id], runtime_version, "ifcopenshell-validation"),
                "record_id": _stable_id("diag_ifc_validation", source_digest, str(index)),
                "record_type": "diagnostic",
                "record_version": "0.1",
                "severity": "warning",
                "source_refs": [{"locator": "ifc-file", "source_id": source_id}],
            }
        )
    capabilities = {name: "full" for name in CAPABILITIES}
    capabilities["2d_geometry"] = "partial"
    has_georeferencing = bool(model.by_type("IfcProjectedCRS") or model.by_type("IfcMapConversion"))
    capabilities["georeferencing"] = "full" if has_georeferencing else "partial"
    if geometry_failures:
        capabilities["3d_geometry"] = "partial"
    if unsupported_fields:
        capabilities["properties"] = "partial"
    partial_reasons = {
        "2d_geometry": "AECCTX_IFC_2D_REPRESENTATION_PARTIAL",
        "georeferencing": "AECCTX_IFC_GEOREFERENCING_NOT_DECLARED",
        "3d_geometry": "AECCTX_IFC_TESSELLATION_PARTIAL",
        "properties": "AECCTX_IFC_ATTRIBUTE_UNSUPPORTED",
    }
    for capability, support_level in capabilities.items():
        if support_level == "full":
            continue
        code = partial_reasons[capability]
        diagnostics.append(
            {
                "affected_count": len(geometry_failures) if capability == "3d_geometry" else len(unsupported_fields) if capability == "properties" else 1,
                "capability": capability,
                "code": code,
                "fallback": "Inspect preserved IFC primitives and native representation references.",
                "message": f"IFC capability is {support_level}: {capability}",
                "provenance": _provenance(instant, [source_id], runtime_version),
                "record_id": _stable_id("diag_ifc_loss", source_digest, capability),
                "record_type": "diagnostic",
                "record_version": "0.1",
                "severity": "info",
                "source_refs": [{"locator": "ifc-file", "source_id": source_id}],
                "support_level": support_level,
            }
        )
    diagnostics.sort(key=lambda item: item["record_id"])
    loss_summary = [partial_reasons[name] for name in CAPABILITIES if capabilities[name] != "full"]
    storage_ref = f"sources/content/{source.name}" if embedding_policy == "embedded" else None
    source_record: dict[str, Any] = {
        "acquisition_origin": "local-file",
        "byte_size": source_bytes,
        "declared_format": _known("IFC STEP physical file"),
        "declared_units": _known("IFC unit assignment"),
        "detected_format": _known(model.schema),
        "detected_producer": _known(runtime_version),
        "detected_units": _known("schema-declared; geometry normalized to m"),
        "display_name": source.name,
        "embedding_policy": embedding_policy,
        "extractor": {"plugin_id": PLUGIN_ID, "plugin_version": PLUGIN_VERSION},
        "media_type": "application/vnd.ifc",
        "prior_source_revision": {"state": "unknown", "reason_code": "AECCTX_PRIOR_REVISION_NOT_PROVIDED"},
        "provenance": _provenance(instant, [], runtime_version),
        "record_id": source_id,
        "record_type": "source",
        "record_version": "0.1",
        "safety_diagnostics": ["AECCTX_IFC_INPUT_TREATED_AS_DATA", "AECCTX_EXTERNAL_LINKS_NOT_FOLLOWED"],
        "sha256": source_digest,
        "source_id": source_id,
        "source_refs": [],
        "spatial_reference": _known("IFC projected CRS") if has_georeferencing else {"state": "unknown", "reason_code": "AECCTX_IFC_GEOREFERENCING_NOT_DECLARED"},
    }
    if storage_ref:
        source_record["storage_ref"] = storage_ref
    elif embedding_policy == "redacted":
        source_record["redaction_reason"] = "AECCTX_SOURCE_CONTENT_REDACTED_BY_POLICY"

    records = {
        "sources/sources.jsonl": [source_record],
        "evidence/primitives.jsonl": primitives,
        "evidence/assertions.jsonl": assertions,
        "model/entities.jsonl": entities,
        "model/relations.jsonl": relations,
        "diagnostics/diagnostics.jsonl": diagnostics,
    }
    artifacts = [
        PackageArtifact(path, b"".join(canonical_json(item) for item in sorted(items, key=lambda value: value["record_id"])), "application/x-ndjson", path.split("/")[-1].removesuffix(".jsonl"), True)
        for path, items in records.items()
    ]
    context = (
        f"# IFC AECCTX package\n\nPackage `{package_id}` preserves IFC schema `{model.schema}`, {len(primitives)} STEP instances, "
        f"{len(entities)} neutral index entities, {len(relations)} relations, and {len(geometry_artifacts)} tessellated artifacts. "
        "Use authoritative JSONL records for exact inspection; this Markdown is generated navigation only.\n"
    ).encode("utf-8")
    artifacts.append(PackageArtifact("context/index.md", context, "text/markdown", "agent-context", False))
    artifacts.extend(geometry_artifacts)
    if storage_ref:
        artifacts.append(PackageArtifact(storage_ref, source, "application/vnd.ifc", "embedded-source", True))
    manifest = PackageWriter(output, package_form=package_form).write(
        package_id=package_id,
        created_at=instant,
        source_ids=[source_id],
        capabilities=capabilities,
        loss_summary=loss_summary,
        embedding_policy=embedding_policy,
        producer={"name": PLUGIN_ID, "version": f"{PLUGIN_VERSION}+ifcopenshell.{runtime_version}"},
        artifacts=artifacts,
    )
    return IngestResult(package_id, source_id, manifest["logical_digest"], output)
