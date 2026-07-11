# AECCTX v0.1 Geometry Artifact Conventions

Version: `0.1.0`
Date: 2026-07-11
Status: Normative reference implementation profile

## Authority

SVG and GLB files are derived artifacts. Every geometry reference cites source/evidence records, an exact artifact hash, status, dimensionality, bounds, unit state, coordinate metadata, and any reversible transform. Source primitives remain authoritative.

## GLB

- Output is GLB 2.0 with stable object names, sorted source objects, no timestamps, and deterministic exporter settings.
- The artifact uses the glTF Y-up convention.
- For sources retained in their numeric local coordinates, AECCTX applies `source (x,y,z) -> GLB (x,z,-y)` and records both the 4x4 transform and its inverse.
- Unknown source units remain `unknown`; GLB viewer conventions do not convert them into construction metres.
- Tessellation is marked derived and does not replace parametric/B-Rep source representation evidence.

## SVG

- Output uses UTF-8, LF, stable numeric formatting, sorted faces/paths, a deterministic `viewBox`, and no timestamp or host metadata.
- Supported views are `top`, `front`, and `side`; adapters may define additional named views without changing source coordinates.
- Stroke width uses non-scaling presentation. SVG geometry is a preview and is not a measurement authority.

## Preview scopes

Preview descriptors support `scene`, `level`, `sheet`, and `page` scopes. Each descriptor includes scope kind/ID, view, artifact path, source record IDs and `derived-preview` status. A renderer emits a structured success or failure diagnostic; absence of a preview never deletes geometry evidence.
