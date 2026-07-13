from __future__ import annotations

from typing import Any

from .context import render_context
from .diff import diff_packages
from .query import query_package
from .validation import validate_package


def mcp_validate(package_path: str) -> dict[str, Any]:
    """Validate an AECCTX package using the same library validator as the CLI."""
    return validate_package(package_path).to_dict()


def mcp_info(package_path: str) -> dict[str, Any]:
    """Return validated package identity and capability information."""
    result = validate_package(package_path)
    if not result.valid or result.manifest is None:
        return result.to_dict()
    return {
        key: result.manifest[key]
        for key in ("aecctx_version", "package_id", "logical_digest", "package_form", "source_ids", "capabilities", "loss_summary")
    }


def mcp_query(package_path: str, expression: str) -> dict[str, Any]:
    """Run the stable read-only AECCTX query grammar."""
    return query_package(package_path, expression).to_dict()


def mcp_diff(before_path: str, after_path: str) -> dict[str, Any]:
    """Compute the same semantic package diff exposed by the CLI."""
    return diff_packages(before_path, after_path).to_dict()


def mcp_context(package_path: str, profile: str = "agent", token_budget: int = 40_000, chunk_token_budget: int = 4_000) -> dict[str, Any]:
    """Render deterministic context from authoritative records."""
    return render_context(
        package_path,
        profile=profile,
        token_budget=token_budget,
        chunk_token_budget=chunk_token_budget,
    ).to_dict()


def mcp_gate(
    package_path: str,
    policy_path: str,
    baseline_path: str | None = None,
    ids_path: str | None = None,
    ifc_source_path: str | None = None,
) -> dict[str, Any]:
    """Evaluate the stable gate contract without creating projections or files."""
    from .gate import GateLimits, evaluate_gate, load_gate_policy, read_gate_document

    limits = GateLimits()
    policy = load_gate_policy(
        read_gate_document(
            policy_path,
            maximum_bytes=limits.max_policy_bytes,
            label="gate policy",
        ),
        limits=limits,
    )
    return evaluate_gate(
        package_path,
        policy,
        baseline_package=baseline_path,
        ids_document=ids_path,
        ifc_source=ifc_source_path,
        limits=limits,
    ).to_dict()


def create_server() -> Any:
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as error:
        raise RuntimeError("Install AECCTX with the 'mcp' extra to run the MCP server") from error
    server = FastMCP("AECCTX", instructions="Read-only wrappers over the stable AECCTX Python/CLI APIs.")
    server.tool(name="aecctx_validate")(mcp_validate)
    server.tool(name="aecctx_info")(mcp_info)
    server.tool(name="aecctx_query")(mcp_query)
    server.tool(name="aecctx_diff")(mcp_diff)
    server.tool(name="aecctx_context")(mcp_context)
    server.tool(name="aecctx_gate")(mcp_gate)
    return server


def main() -> None:
    create_server().run(transport="stdio")
