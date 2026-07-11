# ACX-01 Acceptance Evidence

Date: 2026-07-11
Status: completed

## Implemented

- Python 3.12+ `src/aecctx` package and installed `aecctx` entry point.
- `validate`, `info`, and `version` commands with deterministic JSON envelopes.
- Offline JSON Schema loading from wheel package data.
- Directory-form structural and integrity validation with typed, stable diagnostics.
- Artifact size/hash/logical-digest checks and JSONL schema/order/unique-ID checks.
- Unit, CLI, package-data, wheel, and sdist gates.

## Acceptance commands

```text
uv sync --extra test
./scripts/verify.sh
.venv/bin/aecctx validate fixtures/minimal-aecctx --json
.venv/bin/aecctx info fixtures/minimal-aecctx --json
```

Observed result: 12 tests passed; wheel and sdist built; portable verification passed; baseline integration reported healthy; the committed fixture validated with package ID `pkg_minimal_fixture` and logical digest `7ca4067f732dc1aed30c1be1257437ed009742e8d85f318a1ee1d0b6b6026b1b`.

## Scope confirmation

No package writer, archive reader, query, diff, context renderer, format adapter, geometry conversion, MCP surface, consumer mapping, or WoodFraming code was implemented in ACX-01.
