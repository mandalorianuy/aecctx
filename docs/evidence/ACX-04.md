# ACX-04 Acceptance Evidence

Date: 2026-07-11
Status: completed

## Implemented

- Optional IfcOpenShell 0.8.x adapter with `describe`, bounded `probe`, ordered `extract`, and `finalize` lifecycle surfaces.
- Exact IFC source hash, schema, STEP ID, GlobalId, original class, raw attribute value states, and parser provenance.
- Neutral indexes for object definitions, materials, and property-set definitions backed by primitive evidence.
- Spatial/aggregate/type/material and native IFC relationship records with role-preserving endpoints.
- Property and quantity assertions with IFC names, extraction/interpretation confidence, and no engineering approval claim.
- Placement matrices, representation references, and deterministic adapter-native tessellated mesh artifacts.
- IfcOpenShell schema validation diagnostics plus dynamic capability degradation for unsupported attributes, tessellation failure, absent georeferencing, and partial 2D handling.
- Auto-probed CLI ingest with explicit `--adapter ifc` override.

## Conformance fixture and commands

`fixtures/ifc/minimal-wall.ifc` is a project-authored, legally public IFC4 fixture containing a project/site/building/storey hierarchy, one wall, placement, swept-solid body, property set, material assignment, and relationships.

```text
uv sync --extra test
uv run pytest tests/test_ifc_adapter.py
./scripts/verify.sh
aecctx ingest fixtures/ifc/minimal-wall.ifc --output minimal-wall.aecctx --form zip --json
aecctx validate minimal-wall.aecctx --json
```

Observed result: 51 total tests passed. The IFC fixture parsed and validated; repeated ZIP ingest was byte-identical; the package preserved 41 IFC STEP primitives, neutral entity/relation indexes, `Pset_WallCommon.IsExternal=false`, material assignment, placement, representation references, and non-empty tessellated vertices/triangles.

## Licensing and scope

IfcOpenShell is an optional, separately installed LGPL-3.0-or-later dependency and is not bundled into the Apache-2.0 core artifact. The adapter performs no network access and executes no source-provided links or commands. No DXF, PDF/image, generic SVG/GLB preview, MCP, consumer mapping, or WoodFraming code was implemented in ACX-04.
