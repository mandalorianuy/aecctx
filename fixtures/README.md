# Public Conformance Fixtures

Unless a fixture directory states otherwise, files in this directory are project-authored minimal conformance data distributed under the repository's Apache-2.0 license. They contain no production project data or consumer-specific semantics.

- `minimal-aecctx/`: normative minimal package fixture.
- `sources/opaque-sample.bin`: opaque-ingest identity fixture.
- `ifc/minimal-wall.ifc`: minimal IFC4 hierarchy, wall representation, property, and material fixture generated with IfcOpenShell and then fixed for deterministic publication.
- `dxf/minimal-plan.dxf`: minimal ASCII DXF with layouts, layers, block/insert, unopened xref, XDATA, text, dimension, hatch, and 2D geometry generated with ezdxf and fixed for deterministic publication.
- `pdf/minimal-vector.pdf`: minimal uncompressed PDF with vector path operators and text.
- `pdf/minimal-raster.pdf`: minimal uncompressed PDF with one embedded raster XObject.
- `images/minimal-grid.pgm`: minimal 3x2 grayscale pixel fixture.
