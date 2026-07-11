# ACX-07 Acceptance Evidence

Date: 2026-07-11
Status: completed

## Implemented

- Optional trimesh adapter for OBJ, STL, glTF and GLB with content probing and no external resource fetching.
- Exact mesh object names, vertices, faces, source hash, original format, bounds, and evidence provenance.
- Deterministic GLB 2.0 output using a documented source-to-Y-up transform and explicit inverse.
- Deterministic top/front SVG previews with stable numbers, sorted faces, viewBox, no timestamps, and render diagnostics.
- Preview descriptors for scene, level, sheet and page scopes.
- Explicit unit and CRS states; the OBJ fixture's units remain `unknown` rather than guessed.
- Face-count safety limit and structured capability/loss report.

## Conformance fixture and commands

`fixtures/geometry/minimal-triangle.obj` is a project-authored named triangle with three vertices, one face, and intentionally undeclared units/CRS.

```text
uv sync --extra test
uv run pytest tests/test_geometry_adapter.py
./scripts/verify.sh
aecctx ingest fixtures/geometry/minimal-triangle.obj --output triangle.aecctx --form zip --json
aecctx validate triangle.aecctx --json
```

Observed result: 73 total tests passed. GLB reloaded as a real mesh; SVG was byte-identical with no timestamp; bounds were `[0,0,0]..[4,3,0]`; transforms were reversible; repeated package ZIPs were byte-identical; and rendering diagnostics listed both preview artifacts.

## Licensing and scope

trimesh is an optional, separately installed MIT dependency and is not bundled into the core wheel. External mesh resources are not fetched. No plugin process isolation, MCP, signing, release automation, consumer mapping, or WoodFraming code was implemented in ACX-07.
