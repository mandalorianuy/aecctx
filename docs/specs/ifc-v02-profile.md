# AECCTX v0.2 IFC 2D and georeferencing profile

Version: `0.2.0-draft.1`
Date: 2026-07-12
Status: Normative ACX-13 capability profile

## 1. Dependency and schema boundary

The reference implementation uses `ifcopenshell==0.8.5` as an optional LGPL-3.0-or-later dependency. The public ACX-13 corpus and claims are limited to IFC2X3 TC1 and IFC4 Add2 TC1 STEP physical files parsed with that exact version. Other IfcOpenShell versions, IFC4.1, IFC4.2, IFC4X3, IFCZIP and XML may remain parseable or target formats, but ACX-13 makes no public 2D/georeferencing claim for them without a governed conformance rerun.

IfcOpenShell documents extensive geometric support for IFC2X3 TC1 and IFC4 Add2 TC1, parsing support for later IFC4 families, `get_representations_iter`/`resolve_items` for representation traversal, `calculate_unit_scale` for project units, and geolocation utilities for WCS/CRS/Helmert data:

- https://docs.ifcopenshell.org/ifcopenshell.html
- https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/representation/index.html
- https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/unit/index.html
- https://docs.ifcopenshell.org/autoapi/ifcopenshell/util/geolocation/index.html

## 2. Source-native 2D profile

A representation is source-native 2D only when its IFC evidence declares one or more of:

- a geometric context with `CoordinateSpaceDimension = 2`;
- a subcontext `TargetView` of `PLAN_VIEW`, `REFLECTED_PLAN_VIEW`, `SECTION_VIEW`, `ELEVATION_VIEW`, `GRAPH_VIEW`, or `SKETCH_VIEW`;
- a representation/context identifier of `Axis`, `FootPrint`, `Annotation`, or `Plan`.

The following bounded items are structurally extracted without invoking 3D projection:

| Item/profile | IFC2X3 | IFC4 | Output |
|---|---:|---:|---|
| `IfcPolyline` with finite 2D/3D Cartesian points | public | public | ordered source coordinates |
| `IfcIndexedPolyCurve` over `IfcCartesianPointList2D`, with no segments or only `IfcLineIndex` | not in schema | public | ordered coordinates and line indices |
| `IfcGeometricCurveSet` containing only supported curves | public | public | ordered member evidence |
| `IfcMappedItem` whose mapped representation resolves only to supported items | public | public | base item evidence plus explicit mapping matrix |

IfcOpenShell 0.8.5 `ifcopenshell.util.representation.resolve_items()` does not return a usable matrix for `IfcCartesianTransformationOperator2D`. For this exact mapped-2D profile, AECCTX reads `MappingSource.MappedRepresentation`, `MappingSource.MappingOrigin`, and `MappingTarget` attributes directly and emits the corresponding finite 4x4 affine matrix. This is structural IFC evidence extraction, not a geometry-kernel replacement. Other mapping-target classes or malformed/non-invertible operators remain `AECCTX_IFC_2D_ITEM_UNSUPPORTED`.

`IfcArcIndex`, conics, trimmed/composite curves, text, hatches, styled annotations, topology and other representation items remain preserved raw evidence with `AECCTX_IFC_2D_ITEM_UNSUPPORTED`. They are not silently tessellated or projected.

Every declared representation preserves STEP ID, `RepresentationIdentifier`, `RepresentationType`, context/subcontext IDs and attributes, target view/scale, item IDs/classes and source relationship path. Supported coordinates remain in source project units. Any SVG is a deterministic derived preview that cites representation/item primitive IDs and never upgrades source fidelity.

The adapter distinguishes:

- absent: `AECCTX_IFC_2D_REPRESENTATION_NOT_DECLARED`;
- declared but empty: `AECCTX_IFC_2D_REPRESENTATION_EMPTY`;
- unsupported item/profile: `AECCTX_IFC_2D_ITEM_UNSUPPORTED`;
- extraction failure/malformed finite coordinate: `AECCTX_IFC_2D_EXTRACTION_FAILED`.

The public `2d_geometry` claim remains `partial` because it covers only the table above.

## 3. Coordinate and georeferencing profile

All v0.2 IFC packages preserve project length-unit evidence, each geometric context WCS/precision/true-north value, each coordinate operation and each target CRS as raw primitives before emitting qualification.

### 3.1 IFC4 complete projected profile

A project-to-map link is `known` only when exactly one `IfcMapConversion` relates a geometric representation context to one `IfcProjectedCRS` and all of these are explicit, finite and valid:

- Eastings, Northings and OrthogonalHeight;
- XAxisAbscissa and XAxisOrdinate with non-zero magnitude;
- positive Scale;
- source project length unit and target map length unit;
- a finite invertible WCS and map-conversion matrix;
- a non-empty source-declared CRS Name.

The transformation preserves the source operation parameters and relationship STEP IDs. The matrix follows the buildingSMART order: uniform scale, anticlockwise Z rotation, then translation. It is emitted row-major with its inverse and exact from/to frame names.

If project and map units differ, the explicit `Scale` must equal the source-to-map unit ratio within the declared context precision. Otherwise the link and `global_location` are `conflicted`; AECCTX does not choose a convenient unit.

### 3.2 Local, incomplete and excluded profiles

- With a valid WCS but no coordinate operation/CRS, source-local to project is `known`; project to map is `unknown` with `AECCTX_IFC_GEOREFERENCING_NOT_DECLARED`.
- Missing required explicit parameters, zero axes, non-positive scale, non-finite values, multiple competing operations/CRSs, non-invertible transforms or invalid relationship paths produce `unknown`, `unsupported`, or `conflicted` with stable reasons. No omitted map parameter is defaulted for a public complete claim.
- IFC2X3 `ePSet_MapConversion`/`ePSet_ProjectedCRS`, `IfcSite.RefLatitude/RefLongitude`, true north alone, and informal property names remain preserved evidence but do not establish a complete global transform in ACX-13.
- A CRS name is preserved exactly. AECCTX does not infer, normalize or validate an EPSG identifier from names, projection, zone, coordinates or locale.

The public `georeferencing` claim is `partial`: the complete-link behavior is bounded to the IFC4 profile above, while local-only and every excluded profile remain explicit structured loss.

## 4. Package/version behavior

The stable `ingest_ifc()` default remains AECCTX v0.1. A caller must explicitly request `aecctx_version="0.2.0"` to receive the ACX-13 records. V0.2 records use `record_version="0.2"` and an explicit `evidence_class`; v0.1 output and fixtures remain byte-compatible.

The v0.2 source record owns package-level `coordinate_qualification`. Representation and item primitives own source-native 2D evidence. A derived preview primitive owns preview fidelity and artifact citation. Generated Markdown may summarize these records but is never their authority.
