# ACX-03 Acceptance Evidence

Date: 2026-07-11
Status: completed

## Implemented

- Strict typed `ValueState` handling for all six normative states without presentation defaults.
- Validated `RecordStore` with stable global ordering and authoritative path/line locations.
- Safe read-only query grammar for record type, nested field, equality, inequality, and JSON literals.
- Semantic diff for stable records, identities, artifacts, capabilities, loss, and producer versions; manifest creation time and archive metadata are ignored.
- Deterministic `agent`, `audit`, and `compact` Markdown projections with source citations, chunks, included/omitted IDs, package digest, and token estimates.
- Versioned open neutral vocabulary registry under ACXD-010.
- `query`, `diff`, and `context` CLI commands using the same library APIs.

## Acceptance commands

```text
uv run pytest
./scripts/verify.sh
aecctx query fixtures/minimal-aecctx 'entity.original_class == "LINE"' --json
aecctx diff fixtures/minimal-aecctx fixtures/minimal-aecctx --json
aecctx context fixtures/minimal-aecctx --profile agent --token-budget 600 --json
```

Observed result: 44 tests passed. Queries returned deterministic record IDs and package digest; executable syntax was rejected; diff ignored `created_at` alone and reported record/capability changes; context chunks cited authoritative JSONL locations and stayed within the selected estimate budget without modifying source records.

## Scope confirmation

Markdown remains a generated projection. Exact query and diff operate on validated records and artifacts. No IFC, DXF, PDF/image, geometry preview, plugin isolation, MCP, consumer mapping, or WoodFraming code was implemented in ACX-03.
