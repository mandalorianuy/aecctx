from __future__ import annotations

from pathlib import Path

import pytest

from aecctx.plugins import IsolatedPluginRunner, PluginExecutionError, PluginLimits


def test_builtin_plugin_describe_runs_in_isolated_worker() -> None:
    runner = IsolatedPluginRunner()

    descriptor = runner.run("geometry", "describe")

    assert descriptor["plugin_id"] == "aecctx.adapter.geometry.trimesh"
    assert descriptor["network_mode"] == "disabled"


def test_plugin_timeout_terminates_process_group() -> None:
    runner = IsolatedPluginRunner(limits=PluginLimits(wall_time_seconds=0.1), allow_conformance_plugins=True)

    with pytest.raises(PluginExecutionError) as captured:
        runner.run("_conformance_sleep", "describe")

    assert captured.value.code == "AECCTX_PLUGIN_TIMEOUT"


def test_python_worker_blocks_network_by_default() -> None:
    runner = IsolatedPluginRunner(allow_conformance_plugins=True)

    with pytest.raises(PluginExecutionError) as captured:
        runner.run("_conformance_network", "describe")

    assert captured.value.code == "AECCTX_PLUGIN_NETWORK_DENIED"


def test_plugin_output_and_input_limits_are_enforced() -> None:
    output_runner = IsolatedPluginRunner(
        limits=PluginLimits(max_output_bytes=256),
        allow_conformance_plugins=True,
    )
    with pytest.raises(PluginExecutionError) as output_error:
        output_runner.run("_conformance_flood", "describe")
    assert output_error.value.code == "AECCTX_PLUGIN_OUTPUT_LIMIT_EXCEEDED"

    input_runner = IsolatedPluginRunner(limits=PluginLimits(max_input_bytes=4))
    with pytest.raises(PluginExecutionError) as input_error:
        input_runner.probe("geometry", b"12345")
    assert input_error.value.code == "AECCTX_PLUGIN_INPUT_LIMIT_EXCEEDED"

    record_runner = IsolatedPluginRunner(limits=PluginLimits(max_records=0))
    fixture = Path(__file__).parents[1] / "fixtures" / "geometry" / "minimal-triangle.obj"
    with pytest.raises(PluginExecutionError) as record_error:
        record_runner.run("geometry", "extract", {"source_path": str(fixture), "source_id": "src_fixture"})
    assert record_error.value.code == "AECCTX_PLUGIN_RECORD_LIMIT_EXCEEDED"


def test_unknown_or_conformance_plugins_are_not_available_by_default() -> None:
    runner = IsolatedPluginRunner()

    with pytest.raises(PluginExecutionError) as unknown:
        runner.run("arbitrary.module:Plugin", "describe")
    assert unknown.value.code == "AECCTX_PLUGIN_NOT_REGISTERED"

    with pytest.raises(PluginExecutionError) as conformance:
        runner.run("_conformance_network", "describe")
    assert conformance.value.code == "AECCTX_PLUGIN_NOT_REGISTERED"


def test_plugin_limits_publish_all_required_policy_axes() -> None:
    policy = PluginLimits().to_dict()

    assert set(policy) == {
        "cpu_seconds",
        "max_input_bytes",
        "max_memory_bytes",
        "max_open_files",
        "max_output_bytes",
        "max_records",
        "wall_time_seconds",
    }
