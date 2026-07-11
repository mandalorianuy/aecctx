from __future__ import annotations

from pathlib import Path

from aecctx.context import render_context
from aecctx.diff import diff_packages
from aecctx.mcp_server import create_server, mcp_context, mcp_diff, mcp_info, mcp_query, mcp_validate
from aecctx.query import query_package
from aecctx.validation import validate_package


FIXTURE = Path(__file__).parents[1] / "fixtures" / "minimal-aecctx"


def test_mcp_wrappers_return_the_same_library_semantics() -> None:
    assert mcp_validate(str(FIXTURE)) == validate_package(FIXTURE).to_dict()
    assert mcp_query(str(FIXTURE), 'entity.original_class == "LINE"') == query_package(FIXTURE, 'entity.original_class == "LINE"').to_dict()
    assert mcp_diff(str(FIXTURE), str(FIXTURE)) == diff_packages(FIXTURE, FIXTURE).to_dict()
    assert mcp_context(str(FIXTURE), profile="agent", token_budget=600, chunk_token_budget=220) == render_context(
        FIXTURE, profile="agent", token_budget=600, chunk_token_budget=220
    ).to_dict()
    assert mcp_info(str(FIXTURE))["package_id"] == "pkg_minimal_fixture"


def test_optional_mcp_server_exposes_only_stable_library_tools() -> None:
    server = create_server()

    assert server.name == "AECCTX"
    assert {tool.name for tool in server._tool_manager.list_tools()} == {
        "aecctx_context",
        "aecctx_diff",
        "aecctx_info",
        "aecctx_query",
        "aecctx_validate",
    }
