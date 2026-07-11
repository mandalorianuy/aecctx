# ACX-02 Acceptance Evidence

Date: 2026-07-11
Status: completed

## Implemented

- Public deterministic `PackageReader`, `PackageWriter`, and `PackageArtifact` APIs for directory and ZIP forms.
- Streaming SHA-256 and byte-size calculation.
- Reproducible ZIP metadata, ordering, permissions, compression profile, and bytes.
- Archive member, path, symlink, size, aggregate-size, and decompression-ratio limits.
- Opaque fallback ingest with immutable source identity, explicit value states, and no semantic inference.
- Explicit `external`, `embedded`, and `redacted` policies; `external` is the default under ACXD-012.
- Complete ten-axis capability summary and detailed diagnostics for every opaque capability.
- `aecctx ingest` plus archive-form `validate` and `info` support.

## Acceptance commands

```text
uv run pytest
./scripts/verify.sh
aecctx ingest fixtures/sources/opaque-sample.bin --output sample.aecctx --form zip --json
aecctx validate sample.aecctx --json
```

Observed result: 25 tests passed; repeated archive builds were byte-identical; directory and ZIP logical digests matched; traversal, decompression ratio, and member-count attacks were rejected with stable codes; large-file hashing stayed below the memory bound; wheel/sdist and baseline gates passed.

## Capability claim

Unknown inputs have `full` byte identity and package validation. Hierarchy, properties, relationships, text, 2D geometry, 3D geometry, materials/styles, and georeferencing remain `opaque`, each with a structured loss record and fallback guidance. No interpretation is claimed.

## Scope confirmation

No neutral query/diff/context API, format-specific adapter, geometry preview, plugin isolation, MCP surface, consumer mapping, or WoodFraming code was implemented in ACX-02.
