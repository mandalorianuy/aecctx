# Optional MCP Server

Install with `pip install 'aecctx[mcp]'` and run `aecctx-mcp` over stdio.

The tools `aecctx_validate`, `aecctx_info`, `aecctx_query`, `aecctx_diff`, and `aecctx_context` call the same read-only Python functions used by the CLI. MCP does not ingest sources, mutate packages, add network/inference requirements, or introduce unique semantics.
