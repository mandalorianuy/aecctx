from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from jsonschema import Draft202012Validator

from .mesh_coordinates import CoordinateSolution


PROFILE_ID = "pyproj-epsg-v11.022-offline-v1"
SCHEMA_VERSION = "aecctx.crs-registry.v1"
SELECTED_CRS = ("EPSG:3857", "EPSG:4269", "EPSG:4326", "EPSG:4328", "EPSG:4978", "EPSG:4979", "EPSG:5703", "EPSG:6349")
EXPECTED_RUNTIME = {
    "database_layout": "1.4",
    "epsg_date": "2024-11-05",
    "epsg_version": "v11.022",
    "library": "pyproj",
    "library_version": "3.7.2",
    "proj_data_version": "1.20",
    "proj_version": "9.5.1",
}
_IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9_]{1,15}:[1-9][0-9]{0,9}$")
_TYPE_NAMES = {
    "Compound CRS": "compound",
    "Geocentric CRS": "geocentric",
    "Geographic 2D CRS": "geographic_2d",
    "Geographic 3D CRS": "geographic_3d",
    "Projected CRS": "projected",
    "Vertical CRS": "vertical",
}


class CRSProfileError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class CRSRecord:
    identifier: str
    name: str
    crs_type: str
    deprecated: bool
    axes: tuple[Mapping[str, Any], ...]
    wkt_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "axes": [dict(axis) for axis in self.axes],
            "deprecated": self.deprecated,
            "identifier": self.identifier,
            "name": self.name,
            "type": self.crs_type,
            "wkt_sha256": self.wkt_sha256,
        }


@dataclass(frozen=True, slots=True)
class DatumOperation:
    operation_id: str
    source_crs: str
    target_crs: str
    description: str
    definition_sha256: str
    input_axes: tuple[str, str, str]
    output_axes: tuple[str, str, str]
    stated_accuracy: float
    accuracy_unit: str
    required_grids: tuple[str, ...]
    maximum_points: int
    horizontal_tolerance: float
    vertical_tolerance: float
    registry_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "accuracy": self.stated_accuracy,
            "accuracy_unit": self.accuracy_unit,
            "definition_sha256": self.definition_sha256,
            "description": self.description,
            "horizontal_tolerance": self.horizontal_tolerance,
            "input_axes": list(self.input_axes),
            "maximum_points": self.maximum_points,
            "operation_id": self.operation_id,
            "output_axes": list(self.output_axes),
            "required_grids": list(self.required_grids),
            "source_crs": self.source_crs,
            "target_crs": self.target_crs,
            "vertical_tolerance": self.vertical_tolerance,
        }


@dataclass(frozen=True, slots=True)
class CRSRegistry:
    profile_id: str
    runtime: Mapping[str, str]
    records: Mapping[str, CRSRecord]
    operations: Mapping[str, DatumOperation]
    registry_digest: str
    database_sha256: str
    author: Mapping[str, str]


def _canonical(value: Any) -> bytes:
    return json.dumps(value, allow_nan=False, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest_payload(document: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "operations": document["operations"],
        "profile_id": document["profile_id"],
        "records": document["records"],
        "runtime": document["runtime"],
        "schema_version": document["schema_version"],
    }


def canonical_registry_digest(document: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical(_digest_payload(document))).hexdigest()


def _pyproj() -> Any:
    try:
        import pyproj
    except ImportError as error:
        raise CRSProfileError("AECCTX_CRS_DEPENDENCY_MISSING", "Install AECCTX with the 'crs' extra") from error
    return pyproj


def _runtime(pyproj: Any) -> tuple[dict[str, str], str]:
    pyproj.network.set_network_enabled(active=False)
    if pyproj.network.is_network_enabled():
        raise CRSProfileError("AECCTX_CRS_NETWORK_ENABLED", "PROJ network access could not be disabled")
    database = pyproj.database
    runtime = {
        "database_layout": f"{database.get_database_metadata('DATABASE.LAYOUT.VERSION.MAJOR')}.{database.get_database_metadata('DATABASE.LAYOUT.VERSION.MINOR')}",
        "epsg_date": str(database.get_database_metadata("EPSG.DATE")),
        "epsg_version": str(database.get_database_metadata("EPSG.VERSION")),
        "library": "pyproj",
        "library_version": str(pyproj.__version__),
        "proj_data_version": str(database.get_database_metadata("PROJ_DATA.VERSION")),
        "proj_version": str(pyproj.__proj_version__),
    }
    if runtime != EXPECTED_RUNTIME or str(pyproj.__proj_compiled_version__) != EXPECTED_RUNTIME["proj_version"]:
        raise CRSProfileError("AECCTX_CRS_RUNTIME_UNSUPPORTED", "pyproj, PROJ or registry metadata is outside the governed profile")
    database_path = Path(pyproj.datadir.get_data_dir()) / "proj.db"
    if not database_path.is_file() or database_path.is_symlink():
        raise CRSProfileError("AECCTX_CRS_RUNTIME_UNSUPPORTED", "PROJ database is not a regular offline file")
    database_sha256 = "sha256:" + hashlib.sha256(database_path.read_bytes()).hexdigest()
    return runtime, database_sha256


def _runtime_records(pyproj: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for identifier in SELECTED_CRS:
        crs = pyproj.CRS.from_user_input(identifier)
        crs_type = _TYPE_NAMES.get(crs.type_name)
        if crs_type is None:
            raise CRSProfileError("AECCTX_CRS_RUNTIME_UNSUPPORTED", f"Unexpected CRS type for {identifier}")
        axes = [
            {
                "abbreviation": axis.abbrev,
                "direction": axis.direction,
                "unit_conversion_factor": float(format(float(axis.unit_conversion_factor), ".15g")),
                "unit_name": axis.unit_name,
            }
            for axis in crs.axis_info
        ]
        wkt = crs.to_wkt(version="WKT2_2019", pretty=False)
        records.append(
            {
                "axes": axes,
                "deprecated": bool(crs.is_deprecated),
                "identifier": identifier,
                "name": crs.name,
                "type": crs_type,
                "wkt_sha256": hashlib.sha256(wkt.encode("utf-8")).hexdigest(),
            }
        )
    return records


def _runtime_operations(pyproj: Any) -> list[dict[str, Any]]:
    transformer = pyproj.Transformer.from_pipeline("EPSG:1252")
    if transformer.name != "pipeline" or transformer.description != "NAD83 to WGS 84 (3)" or float(transformer.accuracy) != 4.0:
        raise CRSProfileError("AECCTX_CRS_OPERATION_METADATA_MISMATCH", "EPSG:1252 metadata drifted")
    return [
        {
            "accuracy": 4.0,
            "accuracy_unit": "m",
            "definition_sha256": hashlib.sha256(transformer.definition.encode("utf-8")).hexdigest(),
            "description": transformer.description,
            "horizontal_tolerance": 1e-9,
            "input_axes": ["Lat", "Lon", "h"],
            "maximum_points": 100000,
            "operation_id": "EPSG:1252",
            "output_axes": ["Lat", "Lon", "h"],
            "required_grids": [],
            "source_crs": "EPSG:4269",
            "target_crs": "EPSG:4326",
            "vertical_tolerance": 1e-6,
        }
    ]


def build_runtime_registry_document(*, author: Mapping[str, str]) -> dict[str, Any]:
    pyproj = _pyproj()
    runtime, _database_sha256 = _runtime(pyproj)
    document: dict[str, Any] = {
        "author": dict(author),
        "operations": _runtime_operations(pyproj),
        "profile_id": PROFILE_ID,
        "records": _runtime_records(pyproj),
        "runtime": runtime,
        "schema_version": SCHEMA_VERSION,
    }
    document["registry_digest"] = canonical_registry_digest(document)
    return document


def _schema() -> Mapping[str, Any]:
    return json.loads(files("aecctx.schemas.v0_2").joinpath("crs-registry.schema.json").read_text(encoding="utf-8"))


def load_crs_registry(document: Mapping[str, Any]) -> CRSRegistry:
    try:
        raw = json.loads(_canonical(dict(document)))
    except (TypeError, ValueError) as error:
        raise CRSProfileError("AECCTX_CRS_REGISTRY_INVALID", "CRS registry is not canonical JSON") from error
    if len(_canonical(raw)) > 1024 * 1024:
        raise CRSProfileError("AECCTX_CRS_REGISTRY_INVALID", "CRS registry exceeds 1 MiB")
    errors = sorted(Draft202012Validator(_schema()).iter_errors(raw), key=lambda item: list(item.absolute_path))
    if errors:
        raise CRSProfileError("AECCTX_CRS_REGISTRY_INVALID", errors[0].message)
    seen: dict[str, bytes] = {}
    for record in raw["records"]:
        serialized = _canonical(record)
        if record["identifier"] in seen and seen[record["identifier"]] != serialized:
            raise CRSProfileError("AECCTX_CRS_REGISTRY_CONFLICT", f"CRS registry has conflicting record {record['identifier']}")
        if record["identifier"] in seen:
            raise CRSProfileError("AECCTX_CRS_REGISTRY_CONFLICT", f"CRS registry has duplicate record {record['identifier']}")
        seen[record["identifier"]] = serialized
    operation_ids = [item["operation_id"] for item in raw["operations"]]
    if len(set(operation_ids)) != len(operation_ids):
        raise CRSProfileError("AECCTX_CRS_REGISTRY_CONFLICT", "CRS registry has duplicate operations")
    digest = canonical_registry_digest(raw)
    if digest != raw["registry_digest"]:
        raise CRSProfileError("AECCTX_CRS_REGISTRY_DIGEST_MISMATCH", "CRS registry logical digest does not match")
    pyproj = _pyproj()
    runtime, database_sha256 = _runtime(pyproj)
    expected = build_runtime_registry_document(author=raw["author"])
    if raw["runtime"] != runtime or raw["records"] != expected["records"] or raw["operations"] != expected["operations"]:
        raise CRSProfileError("AECCTX_CRS_RUNTIME_UNSUPPORTED", "CRS registry content differs from the governed runtime")
    records = {
        item["identifier"]: CRSRecord(
            identifier=item["identifier"],
            name=item["name"],
            crs_type=item["type"],
            deprecated=item["deprecated"],
            axes=tuple(MappingProxyType(dict(axis)) for axis in item["axes"]),
            wkt_sha256=item["wkt_sha256"],
        )
        for item in raw["records"]
    }
    operations = {
        item["operation_id"]: DatumOperation(
            operation_id=item["operation_id"],
            source_crs=item["source_crs"],
            target_crs=item["target_crs"],
            description=item["description"],
            definition_sha256=item["definition_sha256"],
            input_axes=tuple(item["input_axes"]),
            output_axes=tuple(item["output_axes"]),
            stated_accuracy=float(item["accuracy"]),
            accuracy_unit=item["accuracy_unit"],
            required_grids=tuple(item["required_grids"]),
            maximum_points=int(item["maximum_points"]),
            horizontal_tolerance=float(item["horizontal_tolerance"]),
            vertical_tolerance=float(item["vertical_tolerance"]),
            registry_digest=digest,
        )
        for item in raw["operations"]
    }
    return CRSRegistry(
        profile_id=raw["profile_id"],
        runtime=MappingProxyType(dict(runtime)),
        records=MappingProxyType(records),
        operations=MappingProxyType(operations),
        registry_digest=digest,
        database_sha256=database_sha256,
        author=MappingProxyType(dict(raw["author"])),
    )


def validate_crs_identifier(registry: CRSRegistry, identifier: str, *, require_current: bool = False) -> CRSRecord:
    if not isinstance(identifier, str) or not _IDENTIFIER.fullmatch(identifier):
        raise CRSProfileError("AECCTX_CRS_IDENTIFIER_UNKNOWN", "CRS identifier is unknown to the governed registry")
    record = registry.records.get(identifier)
    if record is None:
        raise CRSProfileError("AECCTX_CRS_IDENTIFIER_UNKNOWN", f"CRS identifier {identifier} is unknown")
    if require_current and record.deprecated:
        raise CRSProfileError("AECCTX_CRS_IDENTIFIER_DEPRECATED", f"CRS identifier {identifier} is deprecated")
    return record


def _number(value: float) -> float:
    normalized = float(format(float(value), ".15g"))
    return 0.0 if normalized == 0.0 else normalized


def apply_datum_operation(points: Sequence[Sequence[float]], operation: DatumOperation) -> CoordinateSolution:
    if operation.operation_id != "EPSG:1252":
        raise CRSProfileError("AECCTX_CRS_OPERATION_UNKNOWN", "Datum operation is outside the governed profile")
    if operation.required_grids:
        raise CRSProfileError("AECCTX_CRS_GRID_OPERATION_UNSUPPORTED", "Grid-backed datum operations are unsupported")
    if not points or len(points) > operation.maximum_points:
        raise CRSProfileError("AECCTX_CRS_POINT_LIMIT_EXCEEDED", "Datum operation point count is outside limits")
    normalized: list[tuple[float, float, float]] = []
    for point in points:
        if len(point) != 3 or any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in point):
            raise CRSProfileError("AECCTX_CRS_POINT_INVALID", "Datum operation points must contain three finite numbers")
        latitude, longitude, height = (float(value) for value in point)
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180 and abs(height) <= 100000):
            raise CRSProfileError("AECCTX_CRS_POINT_INVALID", "Datum operation point lies outside the governed axis domain")
        normalized.append((latitude, longitude, height))
    pyproj = _pyproj()
    _runtime(pyproj)
    transformer = pyproj.Transformer.from_pipeline(operation.operation_id)
    if (
        transformer.description != operation.description
        or float(transformer.accuracy) != operation.stated_accuracy
        or hashlib.sha256(transformer.definition.encode("utf-8")).hexdigest() != operation.definition_sha256
    ):
        raise CRSProfileError("AECCTX_CRS_OPERATION_METADATA_MISMATCH", "Datum operation metadata differs from the registry")
    transformed_raw = [tuple(float(value) for value in transformer.transform(*point, errcheck=True)) for point in normalized]
    reversed_raw = [tuple(float(value) for value in transformer.transform(*point, direction="INVERSE", errcheck=True)) for point in transformed_raw]
    horizontal = max(max(abs(source[0] - inverse[0]), abs(source[1] - inverse[1])) for source, inverse in zip(normalized, reversed_raw, strict=True))
    vertical = max(abs(source[2] - inverse[2]) for source, inverse in zip(normalized, reversed_raw, strict=True))
    if horizontal > operation.horizontal_tolerance or vertical > operation.vertical_tolerance:
        raise CRSProfileError("AECCTX_CRS_ROUND_TRIP_TOLERANCE_EXCEEDED", "Datum operation inverse residual exceeds tolerance")
    transformed = tuple(tuple(_number(value) for value in point) for point in transformed_raw)
    operation_dict = operation.to_dict()
    configuration_digest = hashlib.sha256(_canonical(operation_dict)).hexdigest()
    return CoordinateSolution(
        status="known",
        configuration_digest=configuration_digest,
        transform_class="datum-operation",
        operation_id=operation.operation_id,
        source_crs=operation.source_crs,
        target_crs=operation.target_crs,
        registry_digest=operation.registry_digest,
        stated_accuracy=operation.stated_accuracy,
        accuracy_unit=operation.accuracy_unit,
        input_axes=operation.input_axes,
        output_axes=operation.output_axes,
        transformed_points=transformed,
        max_horizontal_residual=_number(horizontal),
        max_vertical_residual=_number(vertical),
        input_digest=hashlib.sha256(_canonical(normalized)).hexdigest(),
        output_digest=hashlib.sha256(_canonical(transformed)).hexdigest(),
    )
