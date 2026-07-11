# ACX-08 Acceptance Evidence

Date: 2026-07-11
Status: completed

## Implemented

- Allowlisted isolated Python plugin worker with bounded JSON lifecycle protocol.
- Private cwd/HOME/TMPDIR, deterministic environment, no shell, new session/process group, and sanitized error envelopes.
- Default network denial before plugin import.
- Input/output/record/wall-time/CPU/address-space/open-file/file-size limits with stable failure codes.
- Timeout process-group termination and file-backed output capture.
- Optional `aecctx[mcp]` stdio server with exactly `validate`, `info`, `query`, `diff`, and `context` wrappers.
- MCP wrapper equivalence tests against the stable Python APIs; no MCP-only semantics.
- ACXD-011 resolved: signatures deferred; v0.1 claims integrity but not authenticity.

## Acceptance commands

```text
uv sync --extra test
uv run pytest tests/test_plugin_isolation.py tests/test_mcp_server.py
./scripts/verify.sh
aecctx-mcp
```

Observed result: 81 total tests passed. A built-in plugin described itself in the isolated worker; unregistered IDs were rejected; network creation was denied; timeout killed the session; input/output/record limits returned stable codes; MCP tool names and wrapper outputs matched library semantics; wheel/sdist and baseline gates passed.

## Residual boundary

The built-in runner is for reviewed Python adapters. Native, GPL, commercial or network-backed decoders still require a separately reviewed OS sandbox/provider and are not enabled by v0.1. No release artifact, consumer mapping, or WoodFraming code was implemented in ACX-08.
