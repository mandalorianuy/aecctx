from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .package import PackageReader


RECORD_PATHS = (
    "sources/sources.jsonl",
    "evidence/primitives.jsonl",
    "evidence/assertions.jsonl",
    "model/entities.jsonl",
    "model/relations.jsonl",
    "diagnostics/diagnostics.jsonl",
)
VALUE_STATES = {"known", "unknown", "not_applicable", "conflicted", "explicit_null", "unsupported"}
REPRODUCIBILITY_CLASSES = {"deterministic", "seeded", "non_deterministic"}
DERIVED_FIDELITY_CLASSES = {"tessellated", "rasterized", "projection_2d", "preview", "inferred"}


class RecordModelError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class ValueState:
    state: str
    value: Any = None
    unit: str | None = None
    reason_code: str | None = None

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> ValueState:
        state = raw.get("state")
        if state not in VALUE_STATES:
            raise RecordModelError("AECCTX_VALUE_STATE_INVALID", f"Unsupported value state: {state!r}")
        if state == "known":
            if "value" not in raw:
                raise RecordModelError("AECCTX_VALUE_STATE_VALUE_REQUIRED", "known state requires value")
            return cls(state=state, value=raw["value"], unit=raw.get("unit"))
        reason = raw.get("reason_code")
        if not isinstance(reason, str) or not reason:
            raise RecordModelError("AECCTX_VALUE_STATE_REASON_REQUIRED", f"{state} state requires reason_code")
        if "value" in raw:
            raise RecordModelError("AECCTX_VALUE_STATE_VALUE_FORBIDDEN", f"{state} state cannot synthesize value")
        return cls(state=state, reason_code=reason, unit=raw.get("unit"))


@dataclass(frozen=True, slots=True)
class InferenceMetadata:
    provider_id: str
    provider_version: str
    execution_mode: str
    input_artifact_sha256: str
    input_region_sha256: str
    request_digest: str
    response_digest: str
    extraction_confidence: float
    interpretation_confidence: float
    reproducibility: str
    verification_state: str
    model_version: str | None = None

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> InferenceMetadata:
        digest_fields = ("input_artifact_sha256", "input_region_sha256", "request_digest", "response_digest")
        for field in digest_fields:
            value = raw.get(field)
            if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise RecordModelError("AECCTX_INFERENCE_DIGEST_INVALID", f"{field} must be a lowercase SHA-256 digest")
        extraction = raw.get("extraction_confidence")
        interpretation = raw.get("interpretation_confidence")
        if not isinstance(extraction, (int, float)) or not 0 <= extraction <= 1:
            raise RecordModelError("AECCTX_INFERENCE_CONFIDENCE_INVALID", "extraction_confidence must be between 0 and 1")
        if not isinstance(interpretation, (int, float)) or not 0 <= interpretation <= 1:
            raise RecordModelError("AECCTX_INFERENCE_CONFIDENCE_INVALID", "interpretation_confidence must be between 0 and 1")
        reproducibility = raw.get("reproducibility")
        if reproducibility not in REPRODUCIBILITY_CLASSES:
            raise RecordModelError("AECCTX_INFERENCE_REPRODUCIBILITY_INVALID", "Unsupported reproducibility class")
        return cls(
            provider_id=_required_string(raw, "provider_id", "AECCTX_INFERENCE_PROVIDER_INVALID"),
            provider_version=_required_string(raw, "provider_version", "AECCTX_INFERENCE_PROVIDER_INVALID"),
            execution_mode=_required_choice(raw, "execution_mode", {"local", "network"}, "AECCTX_INFERENCE_EXECUTION_MODE_INVALID"),
            input_artifact_sha256=str(raw["input_artifact_sha256"]),
            input_region_sha256=str(raw["input_region_sha256"]),
            request_digest=str(raw["request_digest"]),
            response_digest=str(raw["response_digest"]),
            extraction_confidence=float(extraction),
            interpretation_confidence=float(interpretation),
            reproducibility=str(reproducibility),
            verification_state=_required_choice(raw, "verification_state", {"unverified", "verified", "rejected"}, "AECCTX_INFERENCE_VERIFICATION_INVALID"),
            model_version=raw.get("model_version") if isinstance(raw.get("model_version"), str) else None,
        )


@dataclass(frozen=True, slots=True)
class CoordinateQualification:
    global_location: ValueState
    transform_chain: tuple[Mapping[str, Any], ...]
    raw: Mapping[str, Any]

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CoordinateQualification:
        global_raw = raw.get("global_location")
        links = raw.get("transform_chain")
        if not isinstance(global_raw, Mapping) or not isinstance(links, list):
            raise RecordModelError("AECCTX_COORDINATE_STRUCTURE_INVALID", "Coordinate qualification requires global_location and transform_chain")
        global_location = ValueState.from_dict(global_raw)
        tolerance = 1e-6
        tolerance_raw = raw.get("tolerance")
        if isinstance(tolerance_raw, Mapping) and tolerance_raw.get("state") == "known":
            tolerance_value = tolerance_raw.get("value")
            if isinstance(tolerance_value, (int, float)) and math.isfinite(float(tolerance_value)) and float(tolerance_value) > 0:
                tolerance = float(tolerance_value)
        if global_location.state == "known" and any(not isinstance(link, Mapping) or link.get("state") != "known" for link in links):
            raise RecordModelError(
                "AECCTX_COORDINATE_GLOBAL_STATE_INVALID",
                "Known global location requires a complete known transform chain",
            )
        for link in links:
            if not isinstance(link, Mapping) or link.get("state") != "known":
                continue
            matrix = link.get("matrix")
            inverse = link.get("inverse_matrix")
            if not _inverse_matrices_match(matrix, inverse, tolerance=tolerance):
                raise RecordModelError(
                    "AECCTX_COORDINATE_INVERSE_INVALID",
                    "Known transform matrix and inverse_matrix must round trip within tolerance",
                )
        return cls(global_location=global_location, transform_chain=tuple(links), raw=raw)


def _inverse_matrices_match(matrix: Any, inverse: Any, *, tolerance: float = 1e-6) -> bool:
    if (
        not isinstance(matrix, list)
        or not isinstance(inverse, list)
        or len(matrix) != 16
        or len(inverse) != 16
        or any(not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in [*matrix, *inverse])
    ):
        return False
    for left, right in ((matrix, inverse), (inverse, matrix)):
        for row in range(4):
            for column in range(4):
                value = sum(float(left[row * 4 + index]) * float(right[index * 4 + column]) for index in range(4))
                expected = 1.0 if row == column else 0.0
                if not math.isclose(value, expected, rel_tol=0.0, abs_tol=tolerance):
                    return False
    return True


@dataclass(frozen=True, slots=True)
class RepresentationFidelity:
    fidelity_class: str
    derived: bool
    source_representation_ids: tuple[str, ...]

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> RepresentationFidelity:
        fidelity_class = _required_choice(
            raw,
            "class",
            {"source_exact", "parametric", "brep", *DERIVED_FIDELITY_CLASSES},
            "AECCTX_FIDELITY_CLASS_INVALID",
        )
        derived = raw.get("derived")
        if not isinstance(derived, bool):
            raise RecordModelError("AECCTX_FIDELITY_DERIVATION_INVALID", "derived must be a boolean")
        if fidelity_class in DERIVED_FIDELITY_CLASSES and not derived:
            raise RecordModelError("AECCTX_FIDELITY_DERIVATION_INVALID", f"{fidelity_class} fidelity must remain derived")
        source_ids = raw.get("source_representation_ids")
        if not isinstance(source_ids, list) or not source_ids or any(not isinstance(item, str) or not item for item in source_ids):
            raise RecordModelError("AECCTX_FIDELITY_SOURCE_INVALID", "source_representation_ids must contain source evidence IDs")
        return cls(fidelity_class=fidelity_class, derived=derived, source_representation_ids=tuple(source_ids))


@dataclass(frozen=True, slots=True)
class ProviderAttestation:
    provider_id: str
    provider_version: str
    runtime_version: str
    execution_mode: str
    network_mode: str
    deterministic: bool
    request_digest: str
    response_digest: str

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> ProviderAttestation:
        deterministic = raw.get("deterministic")
        if not isinstance(deterministic, bool):
            raise RecordModelError("AECCTX_PROVIDER_ATTESTATION_INVALID", "deterministic must be a boolean")
        for field in ("request_digest", "response_digest"):
            value = raw.get(field)
            if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                raise RecordModelError("AECCTX_PROVIDER_ATTESTATION_DIGEST_INVALID", f"{field} must be a lowercase SHA-256 digest")
        execution_mode = _required_choice(raw, "execution_mode", {"local", "network"}, "AECCTX_PROVIDER_ATTESTATION_INVALID")
        network_mode = _required_choice(raw, "network_mode", {"disabled", "allowlisted"}, "AECCTX_PROVIDER_ATTESTATION_INVALID")
        if execution_mode == "network" and network_mode != "allowlisted":
            raise RecordModelError(
                "AECCTX_PROVIDER_ATTESTATION_NETWORK_INVALID",
                "Network execution requires an explicit allowlisted network mode",
            )
        return cls(
            provider_id=_required_string(raw, "provider_id", "AECCTX_PROVIDER_ATTESTATION_INVALID"),
            provider_version=_required_string(raw, "provider_version", "AECCTX_PROVIDER_ATTESTATION_INVALID"),
            runtime_version=_required_string(raw, "runtime_version", "AECCTX_PROVIDER_ATTESTATION_INVALID"),
            execution_mode=execution_mode,
            network_mode=network_mode,
            deterministic=deterministic,
            request_digest=str(raw["request_digest"]),
            response_digest=str(raw["response_digest"]),
        )


def _required_string(raw: Mapping[str, Any], field: str, code: str) -> str:
    value = raw.get(field)
    if not isinstance(value, str) or not value:
        raise RecordModelError(code, f"{field} must be a non-empty string")
    return value


def _required_choice(raw: Mapping[str, Any], field: str, choices: set[str], code: str) -> str:
    value = raw.get(field)
    if value not in choices:
        raise RecordModelError(code, f"Unsupported {field}: {value!r}")
    return str(value)


@dataclass(frozen=True, slots=True)
class RecordLocation:
    path: str
    line: int


@dataclass(frozen=True, slots=True)
class NeutralRecord:
    record_id: str
    record_type: str
    raw: Mapping[str, Any]
    location: RecordLocation


class RecordStore:
    def __init__(self, reader: PackageReader, records: dict[str, NeutralRecord]) -> None:
        self.reader = reader
        self.records = records
        self.manifest = reader.manifest
        self.logical_digest = str(reader.manifest["logical_digest"])

    @classmethod
    def open(cls, package_path: str | Path) -> RecordStore:
        from .validation import validate_package

        validation = validate_package(package_path)
        if not validation.valid:
            first = validation.diagnostics[0]
            raise RecordModelError("AECCTX_PACKAGE_INVALID", f"{first.code}: {first.message}")
        reader = PackageReader(package_path)
        records: dict[str, NeutralRecord] = {}
        for logical_path in RECORD_PATHS:
            text = reader.read_bytes(logical_path).decode("utf-8")
            for line_number, line in enumerate(text.splitlines(), 1):
                if not line.strip():
                    continue
                raw = json.loads(line)
                record_id = raw["record_id"]
                records[record_id] = NeutralRecord(
                    record_id=record_id,
                    record_type=raw["record_type"],
                    raw=raw,
                    location=RecordLocation(logical_path, line_number),
                )
        return cls(reader, {record_id: records[record_id] for record_id in sorted(records)})
