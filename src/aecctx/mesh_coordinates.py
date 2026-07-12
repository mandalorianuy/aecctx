from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from importlib.resources import files
from typing import Any, Mapping, Sequence

import numpy as np
from jsonschema import Draft202012Validator


class CoordinateProfileError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class CoordinateProfile:
    raw: Mapping[str, Any]
    mode: str
    author: Mapping[str, str]
    tolerance: float
    source_units: str | None
    source_frame: Mapping[str, Any] | None
    target_units: str
    target_frame: Mapping[str, Any]
    target_crs: Mapping[str, str] | None
    configuration_digest: str


@dataclass(frozen=True, slots=True)
class CoordinateSolution:
    status: str
    configuration_digest: str
    transform_class: str | None = None
    forward_matrix: tuple[float, ...] | None = None
    inverse_matrix: tuple[float, ...] | None = None
    determinant: float | None = None
    uniform_scale: float | None = None
    max_residual: float | None = None
    rms_residual: float | None = None
    conflicts: tuple[Mapping[str, Any], ...] = ()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _number(value: float) -> float:
    normalized = float(format(float(value), ".15g"))
    return 0.0 if normalized == 0.0 else normalized


def _finite(value: Any) -> bool:
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return math.isfinite(float(value))
    if isinstance(value, Mapping):
        return all(_finite(item) for item in value.values())
    if isinstance(value, list):
        return all(_finite(item) for item in value)
    return True


def _valid_frame(frame: Mapping[str, Any]) -> bool:
    axes = frame.get("axes")
    return isinstance(axes, list) and len({str(axis)[-1] for axis in axes}) == 3


def load_coordinate_profile(value: Mapping[str, Any]) -> CoordinateProfile:
    try:
        raw = json.loads(_canonical(dict(value)))
    except (TypeError, ValueError) as error:
        raise CoordinateProfileError("AECCTX_MESH_COORDINATE_PROFILE_INVALID", f"Profile is not canonical JSON: {error}") from error
    schema = json.loads(files("aecctx.schemas.v0_2").joinpath("mesh-coordinate-profile.schema.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(raw), key=lambda error: list(error.absolute_path))
    frames = [raw.get("target_frame"), raw.get("source_frame")]
    if errors or not _finite(raw) or any(frame is not None and not _valid_frame(frame) for frame in frames):
        detail = errors[0].message if errors else "profile contains non-finite numbers or an invalid frame"
        raise CoordinateProfileError("AECCTX_MESH_COORDINATE_PROFILE_INVALID", detail)
    return CoordinateProfile(
        raw=raw,
        mode=raw["mode"],
        author=raw["author"],
        tolerance=float(raw["tolerance"]),
        source_units=raw.get("source_units"),
        source_frame=raw.get("source_frame"),
        target_units=raw["target_units"],
        target_frame=raw["target_frame"],
        target_crs=raw.get("target_crs"),
        configuration_digest=hashlib.sha256(_canonical(raw)).hexdigest(),
    )


def _matrix_tuple(matrix: np.ndarray) -> tuple[float, ...]:
    return tuple(_number(value) for value in matrix.reshape(16).tolist())


def _conflicts(profile: CoordinateProfile, declared_units: str | None, declared_frame: Mapping[str, Any] | None) -> tuple[Mapping[str, Any], ...]:
    conflicts: list[Mapping[str, Any]] = []
    if declared_units is not None and profile.source_units is not None and declared_units != profile.source_units:
        conflicts.append({"alternatives": [declared_units, profile.source_units], "field": "units", "reason_code": "AECCTX_MESH_SOURCE_MANUAL_UNITS_CONFLICT"})
    if declared_frame is not None and profile.source_frame is not None and _canonical(declared_frame) != _canonical(profile.source_frame):
        conflicts.append({"alternatives": [dict(declared_frame), dict(profile.source_frame)], "field": "frame", "reason_code": "AECCTX_MESH_SOURCE_MANUAL_FRAME_CONFLICT"})
    return tuple(conflicts)


def _solution(profile: CoordinateProfile, matrix: np.ndarray, transform_class: str, *, uniform_scale: float | None = None, max_residual: float | None = None, rms_residual: float | None = None) -> CoordinateSolution:
    linear = matrix[:3, :3]
    determinant = float(np.linalg.det(linear))
    if abs(determinant) <= 1e-15:
        raise CoordinateProfileError("AECCTX_MESH_MATRIX_SINGULAR", "Coordinate matrix is singular")
    inverse = np.linalg.inv(matrix)
    identity = matrix @ inverse
    if not np.allclose(identity, np.eye(4), atol=max(profile.tolerance, 1e-12), rtol=0.0):
        raise CoordinateProfileError("AECCTX_MESH_MATRIX_ROUND_TRIP_FAILED", "Coordinate matrix inverse does not round trip")
    return CoordinateSolution(
        status="known",
        configuration_digest=profile.configuration_digest,
        transform_class=transform_class,
        forward_matrix=_matrix_tuple(matrix),
        inverse_matrix=_matrix_tuple(inverse),
        determinant=_number(determinant),
        uniform_scale=_number(uniform_scale) if uniform_scale is not None else None,
        max_residual=_number(max_residual) if max_residual is not None else None,
        rms_residual=_number(rms_residual) if rms_residual is not None else None,
    )


def _reflection(source: np.ndarray, target: np.ndarray) -> bool:
    if np.linalg.matrix_rank(source - source.mean(axis=0)) < 3 or np.linalg.matrix_rank(target - target.mean(axis=0)) < 3:
        return False
    for indices in itertools.combinations(range(len(source)), 4):
        s = source[list(indices)]
        t = target[list(indices)]
        source_volume = float(np.linalg.det(np.stack((s[1] - s[0], s[2] - s[0], s[3] - s[0]))))
        target_volume = float(np.linalg.det(np.stack((t[1] - t[0], t[2] - t[0], t[3] - t[0]))))
        if abs(source_volume) > 1e-15 and abs(target_volume) > 1e-15:
            return source_volume * target_volume < 0
    return False


def _similarity(profile: CoordinateProfile) -> CoordinateSolution:
    points = profile.raw["control_points"]
    if len(points) < 3:
        raise CoordinateProfileError("AECCTX_MESH_CONTROL_POINTS_INSUFFICIENT", "At least three control points are required")
    identifiers = [point["id"] for point in points]
    if len(set(identifiers)) != len(identifiers):
        raise CoordinateProfileError("AECCTX_MESH_COORDINATE_PROFILE_INVALID", "Control point IDs must be unique")
    source = np.asarray([point["source"] for point in points], dtype=float)
    target = np.asarray([point["target"] for point in points], dtype=float)
    source_centered = source - source.mean(axis=0)
    target_centered = target - target.mean(axis=0)
    if np.linalg.matrix_rank(source_centered) < 2 or np.linalg.matrix_rank(target_centered) < 2:
        raise CoordinateProfileError("AECCTX_MESH_CONTROL_POINTS_COLLINEAR", "Control points must be non-collinear")
    if _reflection(source, target):
        raise CoordinateProfileError("AECCTX_MESH_REGISTRATION_REFLECTION_UNSUPPORTED", "Control points imply a reflection")
    covariance = target_centered.T @ source_centered / len(source)
    u, singular_values, vt = np.linalg.svd(covariance)
    correction = np.eye(3)
    if np.linalg.det(u @ vt) < 0:
        correction[-1, -1] = -1
    rotation = u @ correction @ vt
    variance = float(np.sum(source_centered * source_centered) / len(source))
    scale = float(np.sum(singular_values * np.diag(correction)) / variance)
    if scale <= 0 or np.linalg.det(rotation) <= 0:
        raise CoordinateProfileError("AECCTX_MESH_REGISTRATION_REFLECTION_UNSUPPORTED", "Similarity must preserve orientation with positive scale")
    translation = target.mean(axis=0) - scale * rotation @ source.mean(axis=0)
    matrix = np.eye(4)
    matrix[:3, :3] = scale * rotation
    matrix[:3, 3] = translation
    transformed = (scale * (rotation @ source.T)).T + translation
    residuals = np.linalg.norm(transformed - target, axis=1)
    maximum = float(np.max(residuals))
    rms = float(np.sqrt(np.mean(residuals * residuals)))
    if maximum > profile.tolerance:
        raise CoordinateProfileError("AECCTX_MESH_REGISTRATION_TOLERANCE_EXCEEDED", "Control point residual exceeds tolerance")
    return _solution(profile, matrix, "similarity-control-points", uniform_scale=scale, max_residual=maximum, rms_residual=rms)


def solve_coordinate_profile(profile: CoordinateProfile, *, declared_units: str | None, declared_frame: Mapping[str, Any] | None) -> CoordinateSolution:
    conflicts = _conflicts(profile, declared_units, declared_frame)
    if conflicts:
        return CoordinateSolution(status="conflicted", configuration_digest=profile.configuration_digest, conflicts=conflicts)
    if profile.mode == "scale":
        if profile.source_frame is not None and _canonical(profile.source_frame) != _canonical(profile.target_frame):
            raise CoordinateProfileError("AECCTX_MESH_SCALE_FRAME_MISMATCH", "Scale mode requires identical source and target frames")
        scale = float(profile.raw["scale"])
        matrix = np.diag([scale, scale, scale, 1.0])
        return _solution(profile, matrix, "uniform-scale", uniform_scale=scale)
    if profile.mode == "matrix":
        matrix = np.asarray(profile.raw["matrix"], dtype=float).reshape((4, 4))
        if not np.allclose(matrix[3], [0.0, 0.0, 0.0, 1.0], atol=1e-12, rtol=0.0):
            raise CoordinateProfileError("AECCTX_MESH_MATRIX_NOT_AFFINE", "Matrix last row must be affine")
        return _solution(profile, matrix, "affine-explicit")
    return _similarity(profile)


def transform_point(matrix: Sequence[float], point: Sequence[float]) -> tuple[float, float, float]:
    transformed = np.asarray(matrix, dtype=float).reshape((4, 4)) @ np.asarray([*point, 1.0], dtype=float)
    return tuple(_number(value) for value in transformed[:3])  # type: ignore[return-value]
