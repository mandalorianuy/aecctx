from __future__ import annotations

import hashlib
import json
import math
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
        if not math.isfinite(value):
            return repr(value), False
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
    return _known(normalized) if supported else {"state": "unsupported", "reason_code": "IFC_ATTRIBUTE_TYPE_UNSUPPORTED", "source_value": normalized}


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


def _matrix_values(matrix: Any) -> list[float]:
    return [round(float(value), 12) for row in matrix for value in row]


def _known_transform(from_frame: str, to_frame: str, matrix: Any) -> dict[str, Any]:
    import numpy

    forward = numpy.array(_matrix_values(matrix)).reshape((4, 4))
    return {
        "from_frame": from_frame,
        "inverse_matrix": _matrix_values(numpy.linalg.inv(forward)),
        "matrix": _matrix_values(forward),
        "state": "known",
        "to_frame": to_frame,
    }


def _qualified(value: Any, authority: str = "source_declared") -> dict[str, Any]:
    return {"authority": authority, "state": "known", "value": value}


def _coordinate_qualification(model: Any) -> dict[str, Any]:
    import numpy
    import ifcopenshell.util.geolocation as ifc_geolocation
    import ifcopenshell.util.unit as ifc_unit

    project_unit = ifc_unit.get_project_unit(model, "LENGTHUNIT")
    project_unit_name = ifc_unit.get_full_unit_name(project_unit) if project_unit is not None else None
    contexts = sorted(model.by_type("IfcGeometricRepresentationContext", include_subtypes=False), key=lambda item: item.id())
    precision_values = [float(item.Precision) for item in contexts if getattr(item, "Precision", None) is not None]
    tolerance = min(precision_values) if precision_values else None
    chain: list[dict[str, Any]] = []
    wcs = ifc_geolocation.get_wcs(model)
    if wcs is None:
        chain.append(
            {
                "from_frame": "ifc-source-local",
                "reason_code": "AECCTX_IFC_WCS_NOT_RESOLVED",
                "state": "unknown",
                "to_frame": "ifc-project",
            }
        )
    else:
        chain.append(_known_transform("ifc-source-local", "ifc-project", wcs))

    operations = sorted(model.by_type("IfcMapConversion"), key=lambda item: item.id()) if model.schema != "IFC2X3" else []
    crs_entities = sorted(model.by_type("IfcProjectedCRS"), key=lambda item: item.id()) if model.schema != "IFC2X3" else []
    base: dict[str, Any] = {
        "axis_order": _qualified(["easting", "northing", "height"], "detected"),
        "declared_units": _qualified(project_unit_name) if project_unit_name else {"authority": "source_declared", "reason_code": "AECCTX_IFC_PROJECT_UNIT_NOT_DECLARED", "state": "unknown"},
        "global_location": {"reason_code": "AECCTX_IFC_GEOREFERENCING_NOT_DECLARED", "state": "unknown"},
        "handedness": _qualified("right-handed", "detected"),
        "tolerance": _qualified(tolerance) if tolerance is not None else {"authority": "source_declared", "reason_code": "AECCTX_IFC_PRECISION_NOT_DECLARED", "state": "unknown"},
        "transform_chain": chain,
    }
    if not operations and not crs_entities:
        chain.append(
            {
                "from_frame": "ifc-project",
                "reason_code": "AECCTX_IFC_GEOREFERENCING_NOT_DECLARED",
                "state": "unknown",
                "to_frame": "ifc-map-crs",
            }
        )
        return base
    if len(operations) != 1 or len(crs_entities) != 1:
        base["global_location"] = {"reason_code": "AECCTX_IFC_GEOREFERENCING_CONFLICTED", "state": "conflicted"}
        chain.append(
            {
                "from_frame": "ifc-project",
                "reason_code": "AECCTX_IFC_GEOREFERENCING_CONFLICTED",
                "state": "conflicted",
                "to_frame": "ifc-map-crs",
            }
        )
        return base

    operation = operations[0]
    crs = crs_entities[0]
    values = (
        operation.Eastings,
        operation.Northings,
        operation.OrthogonalHeight,
        operation.XAxisAbscissa,
        operation.XAxisOrdinate,
        operation.Scale,
    )
    crs_name = getattr(crs, "Name", None)
    map_unit = getattr(crs, "MapUnit", None)
    if (
        not isinstance(crs_name, str)
        or not crs_name
        or map_unit is None
        or any(value is None or not math.isfinite(float(value)) for value in values)
        or math.hypot(float(operation.XAxisAbscissa), float(operation.XAxisOrdinate)) == 0
        or float(operation.Scale) <= 0
    ):
        base["global_location"] = {"reason_code": "AECCTX_IFC_GEOREFERENCING_INCOMPLETE", "state": "unsupported"}
        chain.append(
            {
                "from_frame": "ifc-project",
                "reason_code": "AECCTX_IFC_GEOREFERENCING_INCOMPLETE",
                "state": "unsupported",
                "to_frame": f"ifc-crs:{crs_name or 'unknown'}",
            }
        )
        return base

    expected_scale = float(ifc_unit.convert_unit(1.0, project_unit, map_unit)) if project_unit is not None else None
    scale = float(operation.Scale)
    comparison_tolerance = max(abs(float(tolerance or 0.0) * float(expected_scale or 1.0)), 1e-12)
    if expected_scale is None or not math.isclose(scale, expected_scale, rel_tol=0.0, abs_tol=comparison_tolerance):
        base["global_location"] = {"reason_code": "AECCTX_IFC_COORDINATE_UNITS_CONFLICT", "state": "conflicted"}
        chain.append(
            {
                "from_frame": "ifc-project",
                "reason_code": "AECCTX_IFC_COORDINATE_UNITS_CONFLICT",
                "state": "conflicted",
                "to_frame": f"ifc-crs:{crs_name}",
            }
        )
        return base

    x = float(operation.XAxisAbscissa)
    y = float(operation.XAxisOrdinate)
    magnitude = math.hypot(x, y)
    x /= magnitude
    y /= magnitude
    matrix = numpy.array(
        [
            [scale * x, -scale * y, 0.0, float(operation.Eastings)],
            [scale * y, scale * x, 0.0, float(operation.Northings)],
            [0.0, 0.0, scale, float(operation.OrthogonalHeight)],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    map_unit_name = ifc_unit.get_full_unit_name(map_unit)
    base.update(
        {
            "declared_crs": _qualified(crs_name),
            "global_location": _known(crs_name),
            "horizontal_crs": _qualified(crs_name),
            "origin": _qualified([float(operation.Eastings), float(operation.Northings), float(operation.OrthogonalHeight)]),
            "scale": _qualified(scale),
            "transform_direction": _qualified(f"ifc-source-local->ifc-project->ifc-crs:{crs_name}"),
            "vertical_crs": _qualified(crs.VerticalDatum) if getattr(crs, "VerticalDatum", None) else {"authority": "source_declared", "reason_code": "AECCTX_IFC_VERTICAL_CRS_NOT_DECLARED", "state": "explicit_null"},
        }
    )
    base["detected_units"] = _qualified(map_unit_name, "detected")
    chain.append(_known_transform("ifc-project", f"ifc-crs:{crs_name}", matrix))
    return base


def _ifc_2d_context(context: Any, identifier: str | None) -> dict[str, Any] | None:
    dimension = getattr(context, "CoordinateSpaceDimension", None)
    target_view = getattr(context, "TargetView", None)
    context_identifier = getattr(context, "ContextIdentifier", None)
    declared_2d = (
        dimension == 2
        or target_view in {"PLAN_VIEW", "REFLECTED_PLAN_VIEW", "SECTION_VIEW", "ELEVATION_VIEW", "GRAPH_VIEW", "SKETCH_VIEW"}
        or identifier in {"Axis", "FootPrint", "Annotation", "Plan"}
        or context_identifier in {"Axis", "FootPrint", "Annotation", "Plan"}
    )
    if not declared_2d:
        return None
    parent = getattr(context, "ParentContext", None)
    return {
        "context_class": context.is_a(),
        "context_identifier": context_identifier,
        "context_step_id": context.id(),
        "context_type": getattr(context, "ContextType", None),
        "coordinate_space_dimension": dimension,
        "parent_context_step_id": parent.id() if parent is not None else None,
        "precision": getattr(context, "Precision", None),
        "target_scale": getattr(context, "TargetScale", None),
        "target_view": target_view,
    }


def _coordinates(value: Any) -> list[float] | None:
    try:
        result = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    if len(result) not in {2, 3} or any(not math.isfinite(item) for item in result):
        return None
    return result


def _mapping_2d(item: Any) -> tuple[list[float], list[Any]] | None:
    import numpy

    source = getattr(item, "MappingSource", None)
    target = getattr(item, "MappingTarget", None)
    if source is None or target is None or not target.is_a("IfcCartesianTransformationOperator2D"):
        return None
    axis1 = _coordinates(getattr(getattr(target, "Axis1", None), "DirectionRatios", None))
    axis2 = _coordinates(getattr(getattr(target, "Axis2", None), "DirectionRatios", None))
    origin = _coordinates(getattr(getattr(target, "LocalOrigin", None), "Coordinates", None))
    scale = getattr(target, "Scale", None)
    if axis1 is None or axis2 is None or origin is None or scale is None or not math.isfinite(float(scale)) or float(scale) <= 0:
        return None
    if len(axis1) != 2 or len(axis2) != 2 or len(origin) != 2:
        return None
    target_matrix = numpy.array(
        [
            [float(scale) * axis1[0], float(scale) * axis2[0], 0.0, origin[0]],
            [float(scale) * axis1[1], float(scale) * axis2[1], 0.0, origin[1]],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )
    if not math.isfinite(float(numpy.linalg.det(target_matrix))) or abs(float(numpy.linalg.det(target_matrix))) < 1e-15:
        return None
    representation = getattr(source, "MappedRepresentation", None)
    resolved = sorted(list(getattr(representation, "Items", ()) or ()), key=lambda value: value.id())
    return _matrix_values(target_matrix), resolved


def _geometry_2d(item: Any) -> tuple[dict[str, Any] | None, list[list[list[float]]]]:
    if item.is_a("IfcPolyline"):
        points = [_coordinates(point.Coordinates) for point in item.Points]
        if any(point is None for point in points):
            return None, []
        coordinates = [point for point in points if point is not None]
        return {"coordinates": coordinates, "kind": "polyline"}, [coordinates]
    if item.is_a("IfcIndexedPolyCurve"):
        coordinates = [_coordinates(point) for point in item.Points.CoordList]
        if any(point is None or len(point) != 2 for point in coordinates):
            return None, []
        segments: list[list[int]] = []
        for segment in item.Segments or ():
            if not segment.is_a("IfcLineIndex"):
                return None, []
            segments.append([int(index) for index in list(segment)[0]])
        clean = [point for point in coordinates if point is not None]
        return {"coordinates": clean, "kind": "indexed_polycurve", "line_indices": segments}, [clean]
    if item.is_a("IfcGeometricCurveSet"):
        member_ids: list[int] = []
        paths: list[list[list[float]]] = []
        for member in sorted(item.Elements, key=lambda value: value.id()):
            geometry, member_paths = _geometry_2d(member)
            if geometry is None:
                return None, []
            member_ids.append(member.id())
            paths.extend(member_paths)
        return {"kind": "geometric_curve_set", "member_step_ids": member_ids}, paths
    if item.is_a("IfcMappedItem"):
        mapped = _mapping_2d(item)
        if mapped is None:
            return None, []
        matrix, resolved = mapped
        transformed_paths: list[list[list[float]]] = []
        for resolved_item in resolved:
            geometry, paths = _geometry_2d(resolved_item)
            if geometry is None:
                return None, []
            for path in paths:
                transformed_paths.append(
                    [
                        [
                            round(matrix[0] * point[0] + matrix[1] * point[1] + matrix[3], 12),
                            round(matrix[4] * point[0] + matrix[5] * point[1] + matrix[7], 12),
                        ]
                        for point in path
                    ]
                )
        return {"kind": "mapped_item", "mapping_matrix": matrix, "resolved_item_ids": [value.id() for value in resolved]}, transformed_paths
    return None, []


def _ifc_2d_svg(representation_ids: list[str], paths: list[list[list[float]]]) -> bytes:
    points = [point for path in paths for point in path]
    if points:
        min_x = min(point[0] for point in points)
        min_y = min(point[1] for point in points)
        max_x = max(point[0] for point in points)
        max_y = max(point[1] for point in points)
    else:
        min_x = min_y = 0.0
        max_x = max_y = 1.0
    width = max(max_x - min_x, 1.0)
    height = max(max_y - min_y, 1.0)
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min_x:g} {min_y:g} {width:g} {height:g}">',
        '<g fill="none" stroke="black" stroke-width="1">',
    ]
    for representation_id in representation_ids:
        lines.append(f'<g data-source-record-id="{representation_id}"/>')
    for path in paths:
        rendered = " ".join(f"{point[0]:g},{point[1]:g}" for point in path)
        lines.append(f'<polyline points="{rendered}"/>')
    lines.extend(("</g>", "</svg>"))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _augment_ifc_v02_2d(
    model: Any,
    primitives: list[dict[str, Any]],
    primitive_ids: dict[int, str],
    source_digest: str,
    source_id: str,
    instant: str,
    runtime_version: str,
) -> tuple[list[PackageArtifact], list[tuple[str, int]]]:
    by_record_id = {record["record_id"]: record for record in primitives}
    by_step_id = {step_id: by_record_id[record_id] for step_id, record_id in primitive_ids.items()}
    representations: dict[int, Any] = {}
    for product in sorted(model.by_type("IfcProduct"), key=lambda value: value.id()):
        shape = getattr(product, "Representation", None)
        for representation in getattr(shape, "Representations", ()) or ():
            representations[representation.id()] = representation
    representation_ids: list[str] = []
    preview_paths: list[list[list[float]]] = []
    issues: list[tuple[str, int]] = []
    products_without_representation = [
        product.id()
        for product in sorted(model.by_type("IfcProduct"), key=lambda value: value.id())
        if getattr(product, "Representation", None) is None
    ]
    if products_without_representation:
        issues.append(("AECCTX_IFC_2D_REPRESENTATION_NOT_DECLARED", products_without_representation[0]))
    for representation in sorted(representations.values(), key=lambda value: value.id()):
        identifier = getattr(representation, "RepresentationIdentifier", None)
        context = _ifc_2d_context(representation.ContextOfItems, identifier)
        if context is None:
            continue
        record = by_step_id[representation.id()]
        record_id = primitive_ids[representation.id()]
        representation_ids.append(record_id)
        item_ids = [primitive_ids[item.id()] for item in sorted(representation.Items, key=lambda value: value.id())]
        item_states: list[str] = []
        for item in sorted(representation.Items, key=lambda value: value.id()):
            geometry, paths = _geometry_2d(item)
            if geometry is None:
                state = (
                    "extraction_failed"
                    if item.is_a("IfcPolyline") or item.is_a("IfcIndexedPolyCurve")
                    else "unsupported"
                )
                item_states.append(state)
                continue
            item_states.append("supported")
            item_record = by_step_id[item.id()]
            item_record.setdefault("ifc_2d_parent_representation_ids", []).append(record_id)
            if item.is_a("IfcMappedItem"):
                mapping_source = item.MappingSource
                mapped_representation = mapping_source.MappedRepresentation
                geometry.update(
                    {
                        "mapping_source_representation_step_id": mapped_representation.id(),
                        "relationship_path": [
                            f"{representation.is_a()}#{representation.id()}",
                            f"{item.is_a()}#{item.id()}",
                            f"{mapping_source.is_a()}#{mapping_source.id()}",
                            f"{mapped_representation.is_a()}#{mapped_representation.id()}",
                        ],
                    }
                )
            item_record["geometry_2d"] = geometry
            preview_paths.extend(paths)
            if item.is_a("IfcGeometricCurveSet"):
                for member in item.Elements:
                    member_geometry, _ = _geometry_2d(member)
                    if member_geometry is not None:
                        by_step_id[member.id()]["geometry_2d"] = member_geometry
            if item.is_a("IfcMappedItem"):
                for resolved_id in geometry["resolved_item_ids"]:
                    resolved = model.by_id(resolved_id)
                    resolved_geometry, _ = _geometry_2d(resolved)
                    if resolved_geometry is not None:
                        by_step_id[resolved_id]["geometry_2d"] = resolved_geometry
        profile_state = (
            "empty"
            if not item_ids
            else "extraction_failed"
            if "extraction_failed" in item_states
            else "unsupported"
            if "unsupported" in item_states
            else "supported"
        )
        record["ifc_2d_representation"] = {
            "context": context,
            "identifier": identifier,
            "item_record_ids": item_ids,
            "profile_state": profile_state,
            "representation_type": getattr(representation, "RepresentationType", None),
        }
        if profile_state == "empty":
            issues.append(("AECCTX_IFC_2D_REPRESENTATION_EMPTY", representation.id()))
        elif profile_state == "unsupported":
            issues.append(("AECCTX_IFC_2D_ITEM_UNSUPPORTED", representation.id()))
        elif profile_state == "extraction_failed":
            issues.append(("AECCTX_IFC_2D_EXTRACTION_FAILED", representation.id()))
        record["representation_fidelity"] = {
            "class": "source_exact",
            "derived": False,
            "source_representation_ids": [record_id],
        }
    if not representation_ids:
        return [], issues
    svg_bytes = _ifc_2d_svg(representation_ids, preview_paths)
    svg_path = "previews/ifc/source-native-2d.svg"
    svg_digest = hashlib.sha256(svg_bytes).hexdigest()
    preview_id = _stable_id("prim_ifc_preview", source_digest, "source-native-2d")
    primitives.append(
        {
            "artifact_refs": [{"artifact_path": svg_path, "media_type": "image/svg+xml", "sha256": svg_digest}],
            "container": _known("ifc-derived-preview"),
            "evidence_class": "derived",
            "extraction_confidence": {"band": "full", "method": "aecctx-deterministic-ifc-svg"},
            "original_class": "AECCTXDerivedIFC2DPreview",
            "provenance": _provenance(instant, representation_ids, runtime_version, "aecctx-deterministic-ifc-svg"),
            "raw_attributes": {},
            "record_id": preview_id,
            "record_type": "primitive",
            "record_version": "0.2",
            "representation_fidelity": {"class": "preview", "derived": True, "source_representation_ids": representation_ids},
            "source_refs": [{"locator": "ifc-derived-preview:source-native-2d", "source_id": source_id}],
        }
    )
    return [PackageArtifact(svg_path, svg_bytes, "image/svg+xml", "ifc-source-native-2d-preview", False)], issues


def _augment_ifc_v02_coordinate_evidence(
    model: Any,
    primitives: list[dict[str, Any]],
    primitive_ids: dict[int, str],
) -> None:
    import ifcopenshell.util.placement as ifc_placement
    import ifcopenshell.util.unit as ifc_unit

    by_record_id = {record["record_id"]: record for record in primitives}
    by_step_id = {step_id: by_record_id[record_id] for step_id, record_id in primitive_ids.items()}
    for context in sorted(model.by_type("IfcGeometricRepresentationContext", include_subtypes=False), key=lambda value: value.id()):
        try:
            matrix = _matrix_values(ifc_placement.get_axis2placement(context.WorldCoordinateSystem))
            wcs = _known(matrix)
        except Exception:
            wcs = _unsupported("AECCTX_IFC_WCS_NOT_RESOLVED")
        true_north = getattr(context, "TrueNorth", None)
        by_step_id[context.id()]["coordinate_frame"] = {
            "coordinate_space_dimension": int(context.CoordinateSpaceDimension),
            "precision": _value_state(getattr(context, "Precision", None)),
            "true_north": _value_state(getattr(true_north, "DirectionRatios", None)),
            "world_coordinate_system": wcs,
        }

    if model.schema == "IFC2X3":
        return
    for crs in sorted(model.by_type("IfcProjectedCRS"), key=lambda value: value.id()):
        map_unit = getattr(crs, "MapUnit", None)
        by_step_id[crs.id()]["coordinate_reference_system"] = {
            "crs_class": crs.is_a(),
            "geodetic_datum": _value_state(getattr(crs, "GeodeticDatum", None)),
            "map_projection": _value_state(getattr(crs, "MapProjection", None)),
            "map_unit": ifc_unit.get_full_unit_name(map_unit) if map_unit is not None else None,
            "map_zone": _value_state(getattr(crs, "MapZone", None)),
            "name": getattr(crs, "Name", None),
            "vertical_datum": _value_state(getattr(crs, "VerticalDatum", None)),
        }
        if by_step_id[crs.id()]["coordinate_reference_system"]["vertical_datum"]["state"] == "explicit_null":
            by_step_id[crs.id()]["coordinate_reference_system"]["vertical_datum"]["reason_code"] = "AECCTX_IFC_VERTICAL_CRS_NOT_DECLARED"
    for operation in sorted(model.by_type("IfcMapConversion"), key=lambda value: value.id()):
        source_crs = getattr(operation, "SourceCRS", None)
        target_crs = getattr(operation, "TargetCRS", None)
        source_id = source_crs.id() if source_crs is not None else None
        target_id = target_crs.id() if target_crs is not None else None
        by_step_id[operation.id()]["coordinate_operation"] = {
            "operation_class": operation.is_a(),
            "parameters": {
                "eastings": operation.Eastings,
                "northings": operation.Northings,
                "orthogonal_height": operation.OrthogonalHeight,
                "scale": operation.Scale,
                "x_axis_abscissa": operation.XAxisAbscissa,
                "x_axis_ordinate": operation.XAxisOrdinate,
            },
            "relationship_path": [
                f"{source_crs.is_a()}#{source_id}" if source_crs is not None else "unknown-source-crs",
                f"{operation.is_a()}#{operation.id()}",
                f"{target_crs.is_a()}#{target_id}" if target_crs is not None else "unknown-target-crs",
            ],
            "source_crs_step_id": source_id,
            "target_crs_step_id": target_id,
        }


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
            "v02_public_profiles": {
                "georeferencing": "ifc4-add2tc1-explicit-mapconversion-projectedcrs-v1:partial",
                "native_2d": "ifc2x3-tc1-ifc4-add2tc1-native-2d-v1:partial",
            },
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
    aecctx_version: str = "0.1.0",
) -> IngestResult:
    ifcopenshell, ifc_geom, ifc_element, ifc_placement, ifc_validate = _ifcopenshell()
    source = Path(source_path)
    output = Path(output_path)
    if not source.is_file() or source.is_symlink():
        raise ValueError("source_path must be a regular IFC file")
    if embedding_policy not in {"external", "embedded", "redacted"}:
        raise ValueError("embedding_policy must be external, embedded, or redacted")
    if aecctx_version not in {"0.1.0", "0.2.0"}:
        raise ValueError("aecctx_version must be 0.1.0 or 0.2.0")
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

    if aecctx_version == "0.2.0":
        _augment_ifc_v02_coordinate_evidence(model, primitives, primitive_ids)
        v02_2d_artifacts, v02_2d_issues = _augment_ifc_v02_2d(
            model, primitives, primitive_ids, source_digest, source_id, instant, runtime_version
        )
    else:
        v02_2d_artifacts, v02_2d_issues = [], []

    entity_instances = [
        instance
        for instance in all_instances
        if instance.is_a("IfcObjectDefinition")
        or instance.is_a("IfcMaterial")
        or instance.is_a("IfcPropertySetDefinition")
    ]
    entity_ids = {instance.id(): _stable_id("entity_ifc", source_digest, str(instance.id())) for instance in entity_instances}
    geometry_artifacts: list[PackageArtifact] = list(v02_2d_artifacts)
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
    has_georeferencing = bool(model.by_type("IfcProjectedCRS") or model.by_type("IfcMapConversion")) if model.schema != "IFC2X3" else False
    capabilities["georeferencing"] = "partial" if aecctx_version == "0.2.0" else "full" if has_georeferencing else "partial"
    if geometry_failures:
        capabilities["3d_geometry"] = "partial"
    if unsupported_fields:
        capabilities["properties"] = "partial"
    partial_reasons = {
        "2d_geometry": "AECCTX_IFC_2D_REPRESENTATION_PARTIAL",
        "georeferencing": "AECCTX_IFC_GEOREFERENCING_PROFILE_PARTIAL" if aecctx_version == "0.2.0" else "AECCTX_IFC_GEOREFERENCING_NOT_DECLARED",
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

    if aecctx_version == "0.2.0":
        qualification = _coordinate_qualification(model)
        source_record["coordinate_qualification"] = qualification
        source_record["spatial_reference"] = qualification["global_location"]
        for code, step_id in v02_2d_issues:
            evidence_id = primitive_ids.get(step_id)
            diagnostics.append(
                {
                    "affected_count": 1,
                    "capability": "2d_geometry",
                    "code": code,
                    "fallback": "Inspect preserved IFC representation and item primitives.",
                    "message": f"IFC source-native 2D profile excluded or degraded at STEP #{step_id}.",
                    "provenance": _provenance(instant, [evidence_id] if evidence_id else [source_id], runtime_version),
                    "record_id": _stable_id("diag_ifc_v02_2d", source_digest, f"{code}:{step_id}"),
                    "record_type": "diagnostic",
                    "record_version": "0.2",
                    "severity": "info",
                    "source_refs": _source_refs(source_id, step_id),
                    "support_level": "partial",
                }
            )
        global_location = qualification["global_location"]
        georeferencing_code = global_location.get("reason_code")
        if georeferencing_code:
            diagnostics.append(
                {
                    "affected_count": 1,
                    "capability": "georeferencing",
                    "code": georeferencing_code,
                    "fallback": "Use local/project coordinates and inspect preserved CRS/operation primitives.",
                    "message": "IFC global coordinate qualification is not known for the bounded profile.",
                    "provenance": _provenance(instant, [source_id], runtime_version),
                    "record_id": _stable_id("diag_ifc_v02_georef", source_digest, str(georeferencing_code)),
                    "record_type": "diagnostic",
                    "record_version": "0.2",
                    "severity": "info",
                    "source_refs": [{"locator": "ifc-file", "source_id": source_id}],
                    "support_level": "partial",
                }
            )
        for record in [source_record, *primitives, *assertions, *entities, *relations, *diagnostics]:
            record.setdefault("evidence_class", "observed")
            record["record_version"] = "0.2"
        diagnostics.sort(key=lambda item: item["record_id"])

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
        aecctx_version=aecctx_version,
    )
    return IngestResult(package_id, source_id, manifest["logical_digest"], output)
