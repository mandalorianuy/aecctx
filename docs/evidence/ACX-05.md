# ACX-05 Acceptance Evidence

Date: 2026-07-11
Status: completed

## Implemented

- Optional ezdxf 1.4.x adapter with descriptor, bounded ASCII/binary probe, extraction events, and structured finalization.
- DXF version/release, units, layouts, layers, block definitions, inserts, xref declarations, handles, and exact source hash.
- Raw ordered DXF tags and XDATA retained for every graphical primitive, including tags not normalized by the adapter.
- Neutral indexes for graphical entities, block definitions, and layers without consumer-domain inference.
- Supported LINE, LWPOLYLINE, CIRCLE, ARC, POINT, SOLID/TRACE/3DFACE, TEXT/MTEXT, INSERT, DIMENSION, and HATCH geometry/evidence.
- Block representation relations, layer assertions, text, dimension measurements, hatch metadata, and auditor diagnostics.
- Dynamic 2D capability degradation when an entity lacks normalized geometry; raw tags and native type remain preserved.
- Auto-probed CLI ingest with explicit `--adapter dxf` override.

## Conformance fixture and commands

`fixtures/dxf/minimal-plan.dxf` is a project-authored, legally public AC1032 fixture using metres. It contains Model and Sheet A layouts, A-WALL/A-TEXT layers, a door-symbol block/insert, an unopened external xref declaration, XDATA, text, MText, dimension, hatch, and supported geometry.

```text
uv sync --extra test
uv run pytest tests/test_dxf_adapter.py
./scripts/verify.sh
aecctx ingest fixtures/dxf/minimal-plan.dxf --output minimal-plan.aecctx --form zip --json
aecctx validate minimal-plan.aecctx --json
```

Observed result: 57 total tests passed; the fixture audited without errors; repeated ZIP ingest was byte-identical; package validation passed; the XDATA value `unmapped-source-tag` survived in raw tags; and no neutral kind was inferred from the `A-WALL` layer name.

## Licensing and scope

ezdxf is an optional, separately installed MIT dependency and is not bundled into the Apache-2.0 core artifact. Xrefs are registered but never opened, links are not followed, and source commands are not executed. No PDF/image, generic SVG/GLB preview, MCP, consumer mapping, or WoodFraming code was implemented in ACX-05.
