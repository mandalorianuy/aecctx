from __future__ import annotations

from pathlib import Path

from aecctx.context import render_context
from aecctx.diff import diff_packages
from aecctx.gate import GateLimits, evaluate_gate, load_gate_policy, read_gate_document
from aecctx.mcp_server import create_server, mcp_context, mcp_diff, mcp_gate, mcp_info, mcp_query, mcp_validate
from aecctx.query import query_package
from aecctx.validation import validate_package


FIXTURE = Path(__file__).parents[1] / "fixtures" / "minimal-aecctx"
GATE_FIXTURES = Path(__file__).parents[1] / "fixtures" / "v0.2" / "gate"


def test_mcp_wrappers_return_the_same_library_semantics() -> None:
    assert mcp_validate(str(FIXTURE)) == validate_package(FIXTURE).to_dict()
    assert mcp_query(str(FIXTURE), 'entity.original_class == "LINE"') == query_package(FIXTURE, 'entity.original_class == "LINE"').to_dict()
    assert mcp_diff(str(FIXTURE), str(FIXTURE)) == diff_packages(FIXTURE, FIXTURE).to_dict()
    assert mcp_context(str(FIXTURE), profile="agent", token_budget=600, chunk_token_budget=220) == render_context(
        FIXTURE, profile="agent", token_budget=600, chunk_token_budget=220
    ).to_dict()
    assert mcp_info(str(FIXTURE))["package_id"] == "pkg_minimal_fixture"


def test_mcp_gate_returns_the_same_read_only_library_result() -> None:
    package = GATE_FIXTURES / "packages" / "core.aecctx"
    policy_path = GATE_FIXTURES / "policies" / "pass.json"
    limits = GateLimits()
    policy = load_gate_policy(
        read_gate_document(policy_path, maximum_bytes=limits.max_policy_bytes, label="gate policy"),
        limits=limits,
    )

    assert mcp_gate(str(package), str(policy_path)) == evaluate_gate(package, policy, limits=limits).to_dict()


def test_optional_mcp_server_exposes_only_stable_library_tools() -> None:
    server = create_server()

    assert server.name == "AECCTX"
    assert {tool.name for tool in server._tool_manager.list_tools()} == {
        "aecctx_context",
        "aecctx_diff",
        "aecctx_gate",
        "aecctx_info",
        "aecctx_query",
        "aecctx_validate",
    }
