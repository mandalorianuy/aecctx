from __future__ import annotations

import math

import pytest


FRAME = {"axes": ["+X", "+Y", "+Z"], "handedness": "right"}


def scale_profile(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "author": {"id": "surveyor:test"},
        "mode": "scale",
        "profile_version": "0.2.0",
        "scale": 0.001,
        "source_units": "mm",
        "source_frame": FRAME,
        "target_frame": FRAME,
        "target_units": "m",
        "tolerance": 1e-9,
    }
    value.update(changes)
    return value


def test_profile_schema_accepts_exact_scale_and_rejects_unknown_or_nonfinite_values() -> None:
    from aecctx.mesh_coordinates import CoordinateProfileError, load_coordinate_profile

    profile = load_coordinate_profile(scale_profile())
    assert profile.mode == "scale"
    assert profile.target_units == "m"
    assert len(profile.configuration_digest) == 64

    for invalid in (
        scale_profile(command="scale-mesh"),
        scale_profile(target_units="yards"),
        scale_profile(tolerance=math.inf),
        scale_profile(scale=-1.0),
        scale_profile(target_crs={"horizontal": "EPSG:32721"}),
    ):
        with pytest.raises(CoordinateProfileError) as captured:
            load_coordinate_profile(invalid)
        assert captured.value.code == "AECCTX_MESH_COORDINATE_PROFILE_INVALID"


def test_scale_mode_emits_reversible_uniform_matrix() -> None:
    from aecctx.mesh_coordinates import load_coordinate_profile, solve_coordinate_profile

    solution = solve_coordinate_profile(load_coordinate_profile(scale_profile()), declared_units=None, declared_frame=None)

    assert solution.status == "known"
    assert solution.transform_class == "uniform-scale"
    assert solution.forward_matrix == (0.001, 0.0, 0.0, 0.0, 0.0, 0.001, 0.0, 0.0, 0.0, 0.0, 0.001, 0.0, 0.0, 0.0, 0.0, 1.0)
    assert solution.inverse_matrix[0] == 1000.0
    assert solution.determinant == 1e-09


def test_matrix_mode_accepts_explicit_affine_and_rejects_singular_or_non_affine() -> None:
    from aecctx.mesh_coordinates import CoordinateProfileError, load_coordinate_profile, solve_coordinate_profile

    base = scale_profile(
        mode="matrix",
        matrix=[2, 0.5, 0, 10, 0, 3, 0, -20, 0, 0, 4, 30, 0, 0, 0, 1],
    )
    base.pop("scale")
    solution = solve_coordinate_profile(load_coordinate_profile(base), declared_units=None, declared_frame=None)
    assert solution.transform_class == "affine-explicit"
    assert solution.forward_matrix[3] == 10.0
    assert solution.inverse_matrix[0] == 0.5

    for matrix, code in (
        ([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1], "AECCTX_MESH_MATRIX_SINGULAR"),
        ([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 1, 0, 0, 1], "AECCTX_MESH_MATRIX_NOT_AFFINE"),
    ):
        invalid = {**base, "matrix": matrix}
        with pytest.raises(CoordinateProfileError) as captured:
            solve_coordinate_profile(load_coordinate_profile(invalid), declared_units=None, declared_frame=None)
        assert captured.value.code == code


def control_profile(points: list[dict[str, object]], *, tolerance: float = 1e-8) -> dict[str, object]:
    value = scale_profile(mode="control_points", control_points=points, tolerance=tolerance)
    value.pop("scale")
    return value


def test_control_points_solve_orientation_preserving_similarity_with_residuals() -> None:
    from aecctx.mesh_coordinates import load_coordinate_profile, solve_coordinate_profile, transform_point

    points = [
        {"id": "a", "source": [0, 0, 0], "target": [100, 200, 300]},
        {"id": "b", "source": [1, 0, 0], "target": [100, 202, 300]},
        {"id": "c", "source": [0, 1, 0], "target": [98, 200, 300]},
        {"id": "d", "source": [0, 0, 1], "target": [100, 200, 302]},
    ]
    solution = solve_coordinate_profile(load_coordinate_profile(control_profile(points)), declared_units=None, declared_frame=None)

    assert solution.transform_class == "similarity-control-points"
    assert solution.uniform_scale == 2.0
    assert solution.max_residual <= 1e-12
    assert solution.rms_residual <= 1e-12
    assert transform_point(solution.forward_matrix, [1, 0, 0]) == pytest.approx((100.0, 202.0, 300.0))


def test_control_points_reject_insufficient_collinear_reflected_and_tolerance_failure() -> None:
    from aecctx.mesh_coordinates import CoordinateProfileError, load_coordinate_profile, solve_coordinate_profile

    invalid_cases = (
        (
            [
                {"id": "a", "source": [0, 0, 0], "target": [0, 0, 0]},
                {"id": "b", "source": [1, 0, 0], "target": [1, 0, 0]},
            ],
            "AECCTX_MESH_CONTROL_POINTS_INSUFFICIENT",
            1e-8,
        ),
        (
            [
                {"id": "a", "source": [0, 0, 0], "target": [0, 0, 0]},
                {"id": "b", "source": [1, 0, 0], "target": [1, 0, 0]},
                {"id": "c", "source": [2, 0, 0], "target": [2, 0, 0]},
            ],
            "AECCTX_MESH_CONTROL_POINTS_COLLINEAR",
            1e-8,
        ),
        (
            [
                {"id": "a", "source": [0, 0, 0], "target": [0, 0, 0]},
                {"id": "b", "source": [1, 0, 0], "target": [-1, 0, 0]},
                {"id": "c", "source": [0, 1, 0], "target": [0, 1, 0]},
                {"id": "d", "source": [0, 0, 1], "target": [0, 0, 1]},
            ],
            "AECCTX_MESH_REGISTRATION_REFLECTION_UNSUPPORTED",
            1e-8,
        ),
        (
            [
                {"id": "a", "source": [0, 0, 0], "target": [0, 0, 0]},
                {"id": "b", "source": [1, 0, 0], "target": [1, 0, 0]},
                {"id": "c", "source": [0, 1, 0], "target": [0, 1, 0]},
                {"id": "d", "source": [0, 0, 1], "target": [0, 0, 1.1]},
            ],
            "AECCTX_MESH_REGISTRATION_TOLERANCE_EXCEEDED",
            1e-6,
        ),
    )
    for points, code, tolerance in invalid_cases:
        with pytest.raises(CoordinateProfileError) as captured:
            solve_coordinate_profile(load_coordinate_profile(control_profile(points, tolerance=tolerance)), declared_units=None, declared_frame=None)
        assert captured.value.code == code


def test_source_manual_unit_or_frame_mismatch_is_conflicted_not_precedence() -> None:
    from aecctx.mesh_coordinates import load_coordinate_profile, solve_coordinate_profile

    profile = load_coordinate_profile(scale_profile(source_units="mm"))
    solution = solve_coordinate_profile(profile, declared_units="m", declared_frame=FRAME)

    assert solution.status == "conflicted"
    assert solution.conflicts == (
        {"alternatives": ["m", "mm"], "field": "units", "reason_code": "AECCTX_MESH_SOURCE_MANUAL_UNITS_CONFLICT"},
    )
    assert solution.forward_matrix is None
