# AECCTX v0.3 IFC expansion profile

Version: `0.3.0-draft.1`
Date: 2026-07-13
Status: Normative ACX-27 implementation profile
Decision authority: ACXD-035

## 1. Purpose and compatibility boundary

This profile expands the opt-in AECCTX v0.2 IFC evidence emitted by `ingest_ifc(..., aecctx_version="0.2.0")`. It does not add a new package version and does not change default v0.1 output. New source structures use namespaced record members under `ifc_v03`; existing v0.2 coordinate and fidelity fields retain their meaning.

The claims are `ifc.native-2d.v03` and `ifc.georeferencing.v03`. Both have a public ceiling of `partial` and require exact conformance evidence before promotion from `target`.

## 2. Dependency and schema profile

The exact runtime is optional `ifcopenshell==0.8.5`, LGPL-3.0-or-later and not bundled in the Apache-2.0 core. Positive v0.3 evidence is limited to STEP physical files declaring `IFC4X3_ADD2` and parsed by that runtime. Existing ACX-13 IFC2X3 TC1 and IFC4 Add2 TC1 claims remain unchanged.

Official authorities reviewed for this cut:

- IfcOpenShell representation traversal and resolved items: <https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/representation/index.html>
- IfcOpenShell placements: <https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/placement/index.html>
- IfcOpenShell geolocation/Helmert parameters: <https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/geolocation/index.html>
- buildingSMART IFC4.3 `IfcMapConversion`: <https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcMapConversion.htm>
- buildingSMART curve, annotation and presentation entities: `IfcCompositeCurve`, `IfcIndexedPolyCurve`, `IfcTrimmedCurve`, `IfcAnnotation`, `IfcTextStyle`, `IfcFillAreaStyle` and `IfcFillAreaStyleHatching` in the IFC 4.3.2 lexical documentation.

IFC4.1, IFC4.2, other IFC4X3 editions, IFCXML, IFCZIP and other IfcOpenShell versions remain unclaimed.

## 3. Source-native 2D expansion

The ACX-13 declaration test for a source-native 2D representation remains mandatory. A 3D context, projection or tessellation cannot enter this profile.

The following additional IFC4X3 ADD2 items are structurally supported:

| Item | Exact accepted form | Authoritative evidence |
|---|---|---|
| `IfcCircle` | finite 2D placement; positive finite radius | placement matrix and radius |
| `IfcEllipse` | finite 2D placement; two positive finite semi-axes | placement matrix and semi-axes |
| `IfcTrimmedCurve` | supported circle/ellipse basis; exactly one finite parameter at each trim; `PARAMETER` master representation | basis ID, trim parameters and sense |
| `IfcCompositeCurve` | finite ordered `IfcCompositeCurveSegment` list; each parent is a supported curve; explicit transition and same-sense values | segment IDs, parent IDs and ordering |
| `IfcIndexedPolyCurve` | 2D point list with explicit `IfcLineIndex` and/or three-index `IfcArcIndex` segments | coordinates and typed indices; no inferred segments |
| `IfcTextLiteral` | bounded literal, finite 2D placement and explicit path | literal, placement matrix and path |
| `IfcAnnotationFillArea` | supported outer curve and zero or more supported inner curves | boundary IDs and curve evidence |

An associated `IfcStyledItem` is evidence only when it explicitly references the item. The bounded style projection preserves IDs/classes and source attributes for `IfcTextStyle`, `IfcCurveStyle`, `IfcFillAreaStyle` and `IfcFillAreaStyleHatching`. Externally defined fonts/hatches, raster textures, tiles, unsupported selects and implicit style inheritance remain structured loss.

Source records precede neutral interpretation. Curves are never sampled into authoritative coordinates. Any polygonal path used by SVG is a deterministic derived preview with explicit approximation metadata and citations to the source item records. Text glyph outlines and hatch expansion are not rendered.

Stable outcomes are:

- absent representation: `AECCTX_IFC_2D_REPRESENTATION_NOT_DECLARED`;
- declared empty representation: `AECCTX_IFC_2D_REPRESENTATION_EMPTY`;
- unlisted class/form/style: `AECCTX_IFC_V03_2D_ITEM_UNSUPPORTED`;
- malformed, non-finite, cyclic or over-limit structure: `AECCTX_IFC_V03_2D_EXTRACTION_FAILED`.

## 4. IFC4X3 scaled map conversion

`IfcMapConversionScaled` is `known` only when exactly one operation and one `IfcProjectedCRS` form a valid explicit relationship and all ACX-13 requirements hold, plus explicit finite positive `FactorX`, `FactorY` and `FactorZ`.

The base `Scale` remains the source-to-map unit conversion. The coordinate factors multiply the local X, Y and Z axes respectively and are not unit conversions. The project-to-map matrix applies the normalized X-axis rotation, base scale times each explicit factor, and then explicit translation. Its inverse must be finite and the determinant non-zero.

The operation source primitive preserves the three factors and exact relationship path. Multiple operations/CRSs are `conflicted`; missing factors are `unsupported`; zero, negative, non-finite or non-invertible factors are `unsupported`. No factor, scale, axis, elevation, CRS or operation is defaulted.

IFC2X3 `ePSet_MapConversion`/`ePSet_ProjectedCRS` data, site latitude/longitude, true north, CRS-looking names and informal properties remain observed source evidence only. This profile does not promote them to a complete transform and never infers or validates EPSG authority.

## 5. Bounds and hostile input

The adapter enforces deterministic maxima of 1,024 characters per text literal, 256 composite segments, 4,096 indexed points, 4,096 curve members per representation and 32 nested curve references. Cycles, duplicate relationship paths, malformed select values and non-finite values fail closed with stable diagnostics. Source files remain subject to existing package and parser limits.

## 6. Conformance and non-claims

The project-authored Apache-2.0 fixture corpus must cover every positive item and operation plus absent, empty, unsupported, multiple, conflicted, non-invertible, false-EPSG and large-coordinate cases. Repeated generation and package ingestion must be byte-deterministic. Public promotion requires exact source hashes, reversible transform evidence, derived-only SVG, dependency/package scans, portable/full gates and GitHub CI on Python 3.12 Linux, macOS and Windows.

This profile does not claim 3D projection as native 2D, exact rendered glyphs, hatch expansion, topology, B-splines, offsets, spirals, arbitrary trims, externally defined presentation resources, IFC2X3 georeferencing, other coordinate operations, CRS validation, survey authority, consumer classification or source mutation.
