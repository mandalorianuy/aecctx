from __future__ import annotations

import re
from typing import Any


PROVIDER_ID = "org.aecctx.step-iges.ocp"
RUNTIME_DIGEST = "sha256:875cbbbc5198ae44e8957e3a90c9a8afd0dc541f01029fb5186a296e3d2a0d47"
CONFIGURATION = {
    "angular_deflection": 0.5,
    "brep_format": "occt-ascii-brep-7.9.3",
    "linear_deflection": 0.1,
    "read_shape_healing": "translator-default-observed",
    "schema_profile": "acx17-v1",
    "tessellation_units": "source",
}


def _configuration(request: dict[str, Any]) -> dict[str, Any]:
    configured = request.get("configuration")
    if configured != CONFIGURATION:
        raise ValueError("AECCTX_STEP_IGES_CONFIGURATION_INVALID")
    return dict(CONFIGURATION)


def _probe(data: bytes) -> str:
    if data.lstrip().startswith(b"ISO-10303-21;"):
        return "step"
    lines = data.splitlines()
    sections = {chr(line[72]) for line in lines if len(line) == 80 and line[72] in b"SGDPT"}
    if {"S", "G", "D", "P", "T"}.issubset(sections):
        return "iges"
    raise ValueError("AECCTX_STEP_IGES_FORMAT_UNSUPPORTED")


def _ascii(data: bytes) -> str:
    try:
        return data.decode("ascii")
    except UnicodeDecodeError as error:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED") from error


def _step_statements(section: str, max_recursion_depth: int) -> list[str]:
    statements: list[str] = []
    start = 0
    in_string = False
    in_comment = False
    depth = 0
    index = 0
    while index < len(section):
        pair = section[index : index + 2]
        character = section[index]
        if in_comment:
            if pair == "*/":
                in_comment = False
                index += 2
                continue
            index += 1
            continue
        if not in_string and pair == "/*":
            in_comment = True
            index += 2
            continue
        if character == "'":
            if in_string and index + 1 < len(section) and section[index + 1] == "'":
                index += 2
                continue
            in_string = not in_string
        elif not in_string:
            if character == "(":
                depth += 1
                if depth > max_recursion_depth:
                    raise ValueError("AECCTX_STEP_IGES_REFERENCE_DEPTH_EXCEEDED")
            elif character == ")":
                depth -= 1
                if depth < 0:
                    raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
            elif character == ";" and depth == 0:
                statement = section[start : index + 1].strip()
                if statement:
                    statements.append(statement)
                start = index + 1
        index += 1
    if in_string or in_comment or depth != 0 or section[start:].strip():
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    return statements


def _reference_view(value: str) -> str:
    result = list(value)
    in_string = False
    in_comment = False
    index = 0
    while index < len(value):
        pair = value[index : index + 2]
        if in_comment:
            result[index] = " "
            if pair == "*/":
                result[index + 1] = " "
                in_comment = False
                index += 2
                continue
            index += 1
            continue
        if not in_string and pair == "/*":
            result[index] = result[index + 1] = " "
            in_comment = True
            index += 2
            continue
        if value[index] == "'":
            result[index] = " "
            if in_string and index + 1 < len(value) and value[index + 1] == "'":
                result[index + 1] = " "
                index += 2
                continue
            in_string = not in_string
        elif in_string:
            result[index] = " "
        index += 1
    return "".join(result)


def _scan_step(data: bytes, *, max_records: int, max_recursion_depth: int) -> dict[str, Any]:
    text = _ascii(data)
    if not text.lstrip().startswith("ISO-10303-21;") or "END-ISO-10303-21;" not in text:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    header_start = text.find("HEADER;")
    data_start = text.find("DATA;", header_start + 7)
    if header_start < 0 or data_start < 0:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    header_end = text.find("ENDSEC;", header_start + 7)
    data_end = text.find("ENDSEC;", data_start + 5)
    if header_end < 0 or data_end < 0 or header_end > data_start:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    header = text[header_start + 7 : header_end]
    schema_match = re.search(r"FILE_SCHEMA\s*\(\s*\((.*?)\)\s*\)\s*;", header, flags=re.DOTALL)
    if schema_match is None:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    schemas = [item.replace("''", "'") for item in re.findall(r"'((?:[^']|'')*)'", schema_match.group(1))]
    if not schemas:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    entities: list[dict[str, Any]] = []
    identifiers: set[int] = set()
    statements = _step_statements(text[data_start + 5 : data_end], max_recursion_depth)
    if len(statements) > max_records:
        raise ValueError("AECCTX_STEP_IGES_ENTITY_LIMIT_EXCEEDED")
    for statement in statements:
        match = re.fullmatch(r"#([1-9][0-9]*)\s*=\s*([A-Z][A-Z0-9_]*)\s*\((.*)\)\s*;", statement, flags=re.DOTALL)
        complex_match = None if match is not None else re.fullmatch(r"#([1-9][0-9]*)\s*=\s*\((.*)\)\s*;", statement, flags=re.DOTALL)
        if match is None and complex_match is None:
            raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
        selected = match or complex_match
        assert selected is not None
        identifier = int(selected.group(1))
        if identifier in identifiers:
            raise ValueError("AECCTX_STEP_IGES_ENTITY_DUPLICATE")
        identifiers.add(identifier)
        payload = match.group(3) if match is not None else complex_match.group(2)  # type: ignore[union-attr]
        visible_payload = _reference_view(payload)
        references = sorted({int(value) for value in re.findall(r"#([1-9][0-9]*)", visible_payload)})
        entity = {
            "id": identifier,
            "original_class": match.group(2) if match is not None else "COMPLEX_INSTANCE",
            "raw": statement,
            "references": references,
        }
        if complex_match is not None:
            component_classes = re.findall(r"(?:^|\s)([A-Z][A-Z0-9_]*)\s*\(", visible_payload)
            if len(component_classes) < 2:
                raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
            entity["component_classes"] = component_classes
        entities.append(entity)
    referenced = {reference for entity in entities for reference in entity["references"]}
    if not referenced.issubset(identifiers):
        raise ValueError("AECCTX_STEP_IGES_REFERENCE_INVALID")
    entities.sort(key=lambda item: item["id"])
    return {
        "entities": entities,
        "external_references": any(item["original_class"] == "EXTERNAL_FILE_ID_AND_LOCATION" for item in entities),
        "format": "step",
        "headers": {"FILE_SCHEMA": schemas},
        "schemas": schemas,
    }


def _iges_int(value: bytes, *, default: int = 0) -> int:
    stripped = value.strip()
    if not stripped:
        return default
    try:
        return int(stripped)
    except ValueError as error:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED") from error


def _scan_iges(data: bytes, *, max_records: int, max_recursion_depth: int) -> dict[str, Any]:
    del max_recursion_depth
    lines = data.splitlines()
    if not lines or any(len(line) != 80 or line[72] not in b"SGDPT" for line in lines):
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    by_section = {section: [line for line in lines if line[72:73] == section] for section in (b"S", b"G", b"D", b"P", b"T")}
    if any(not by_section[section] for section in by_section) or len(by_section[b"D"]) % 2:
        raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
    if len(by_section[b"D"]) // 2 > max_records:
        raise ValueError("AECCTX_STEP_IGES_ENTITY_LIMIT_EXCEEDED")
    directory: list[dict[str, Any]] = []
    for index in range(0, len(by_section[b"D"]), 2):
        first = by_section[b"D"][index]
        second = by_section[b"D"][index + 1]
        first_sequence = _iges_int(first[73:80])
        second_sequence = _iges_int(second[73:80])
        entity_type = _iges_int(first[0:8])
        if first_sequence <= 0 or second_sequence != first_sequence + 1 or _iges_int(second[0:8]) != entity_type:
            raise ValueError("AECCTX_STEP_IGES_PARSE_FAILED")
        directory.append(
            {
                "entity_type": entity_type,
                "form": _iges_int(second[32:40]),
                "label": second[56:64].decode("ascii").strip(),
                "level": _iges_int(first[32:40]),
                "parameter_pointer": _iges_int(first[8:16]),
                "sequence": first_sequence,
                "subscript": _iges_int(second[64:72]),
                "transform_pointer": _iges_int(first[48:56]),
            }
        )
    directory.sort(key=lambda item: item["sequence"])
    return {
        "directory": directory,
        "external_references": any(item["entity_type"] == 416 for item in directory),
        "format": "iges",
        "global_raw": b"".join(line[:72] for line in by_section[b"G"]).decode("ascii").rstrip(),
        "version": "5.3",
    }
