from __future__ import annotations

import hashlib
import json
import socket
import sys
from importlib.metadata import PackageNotFoundError, version as metadata_version
from pathlib import Path
from typing import Any

from .policy import canonical_gate_json


EXPECTED_DEPENDENCIES = {"ifcopenshell": "0.8.5", "ifctester": "0.8.5"}
ALLOWED_SCHEMAS = frozenset({"IFC2X3", "IFC4"})
ALLOWED_FACETS = frozenset({"Entity", "Attribute", "Classification", "Property", "Material"})


def _fail(code: str) -> int:
    sys.stderr.write(code + "\n")
    return 2


def _request() -> dict[str, Any]:
    raw = sys.stdin.buffer.read(16_777_217)
    if len(raw) > 16_777_216:
        raise ValueError("request too large")
    value = json.loads(raw)
    if not isinstance(value, dict) or set(value) != {
        "version", "ids_path", "ids_digest", "ifc_path", "ifc_digest", "ifc_schema", "limits"
    }:
        raise ValueError("invalid request envelope")
    if value["version"] != "1" or value["ifc_schema"] not in ALLOWED_SCHEMAS:
        raise ValueError("invalid request profile")
    limits = value["limits"]
    if not isinstance(limits, dict) or set(limits) != {
        "max_specifications", "max_facets", "max_entities", "max_findings"
    }:
        raise ValueError("invalid limits")
    if any(isinstance(item, bool) or not isinstance(item, int) or item <= 0 for item in limits.values()):
        raise ValueError("invalid limits")
    return value


def _bound_path(raw: Any, digest: Any, suffix: str) -> Path:
    if not isinstance(raw, str) or not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("invalid content address")
    path = Path(raw)
    if path.is_symlink() or not path.is_file() or path.name != f"{digest}.{suffix}":
        raise ValueError("invalid content-addressed path")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("content digest mismatch")
    return path


def _entity_ref(entity: Any) -> str:
    try:
        step_id = int(entity.id())
    except (AttributeError, TypeError, ValueError):
        raise ValueError("invalid IFC entity identity")
    return f"ifc-step:{step_id}"


def _normalize(ids_file: Any, ifc_schema: str, limits: dict[str, int]) -> dict[str, Any]:
    if len(ids_file.specifications) > limits["max_specifications"]:
        raise ValueError("specification limit exceeded")
    specifications: list[dict[str, Any]] = []
    entity_observations = 0
    finding_observations = 0
    facet_count = 0
    for specification_index, specification in enumerate(ids_file.specifications):
        facet_count += len(specification.applicability) + len(specification.requirements)
        if facet_count > limits["max_facets"]:
            raise ValueError("facet limit exceeded")
        for facet in (*specification.applicability, *specification.requirements):
            if type(facet).__name__ not in ALLOWED_FACETS:
                raise ValueError("unsupported facet reached worker")
        applicable = sorted({_entity_ref(entity) for entity in specification.applicable_entities})
        failed = sorted({_entity_ref(entity) for entity in specification.failed_entities})
        entity_observations += len(applicable) + len(failed)
        requirements: list[dict[str, Any]] = []
        for requirement_index, requirement in enumerate(specification.requirements):
            requirement_failed = sorted(
                {
                    _entity_ref(failure["element"])
                    for failure in requirement.failures
                    if isinstance(failure, dict) and "element" in failure
                }
            )
            entity_observations += len(requirement_failed)
            if requirement.status is False:
                finding_observations += 1
            requirements.append(
                {
                    "id": f"ids-specification:{specification_index:04d}:requirement:{requirement_index:04d}",
                    "kind": type(requirement).__name__.lower(),
                    "status": requirement.status is True,
                    "failed_entities": requirement_failed,
                }
            )
        if specification.status is not True:
            finding_observations += 1
        if entity_observations > limits["max_entities"] or finding_observations > limits["max_findings"]:
            raise ValueError("result count limit exceeded")
        specifications.append(
            {
                "id": f"ids-specification:{specification_index:04d}",
                "status": specification.status is True,
                "applicable_entities": applicable,
                "failed_entities": failed,
                "requirements": requirements,
            }
        )
    return {"version": "1", "ifc_schema": ifc_schema, "specifications": specifications}


def main() -> int:
    try:
        request = _request()
        for name, expected in EXPECTED_DEPENDENCIES.items():
            try:
                actual = metadata_version(name)
            except PackageNotFoundError as error:
                raise ValueError("dependency unavailable") from error
            if actual != expected:
                raise ValueError("dependency version mismatch")
        ids_path = _bound_path(request["ids_path"], request["ids_digest"], "ids")
        ifc_path = _bound_path(request["ifc_path"], request["ifc_digest"], "ifc")

        import ifcopenshell
        from ifctester import ids

        def deny_network(*args: Any, **kwargs: Any) -> Any:
            raise OSError("network disabled")

        socket.create_connection = deny_network
        socket.getaddrinfo = deny_network

        ids_file = ids.open(str(ids_path), validate=True)
        ifc_file = ifcopenshell.open(str(ifc_path))
        if ifc_file.schema_identifier != request["ifc_schema"] or ifc_file.schema_identifier not in ALLOWED_SCHEMAS:
            raise ValueError("IFC schema mismatch")
        ids_file.validate(ifc_file, should_filter_version=True)
        response = _normalize(ids_file, request["ifc_schema"], request["limits"])
        sys.stdout.buffer.write(canonical_gate_json(response))
        return 0
    except Exception:
        return _fail("AECCTX_GATE_IDS_WORKER_FAILURE")


if __name__ == "__main__":
    raise SystemExit(main())
