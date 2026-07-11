# Landscape Research

Date: 2026-07-11
Status: Informative snapshot

## Closest projects and standards

| Project | Useful capability | Gap relative to AECCTX |
|---|---|---|
| [BimDown](https://github.com/NovaShang/BimDown) | AI-readable CSV plus GeoJSON/SVG, CLI, query, diff, Revit round trip | Lightweight editable BIM with declared LOD/detail losses; not a general loss-aware evidence package |
| [IfcOpenShell](https://docs.ifcopenshell.org/) | Open IFC parsing, validation, geometry, conversions and utilities | IFC-specific rather than a cross-format package contract |
| [IfcMCP](https://docs.ifcopenshell.org/ifcmcp.html) | Agent query/edit/render tools over an in-memory IFC model | Tool interface rather than persistent multi-format context interchange |
| [buildingSMART IFC formats](https://technical.buildingsmart.org/standards/ifc/ifc-formats/) | Standard STEP, XML, JSON and RDF encodings | Faithful interoperability formats are not token-budgeted agent context |
| [Speckle schemas](https://docs.speckle.systems/developers/data-schema/connectors/ifc-schema) | Cross-application object/geometry normalization | Platform/object model with connector semantics, not an evidence-first portable package |
| [ezdxf](https://github.com/mozman/ezdxf) | MIT DXF parsing, audit, rendering, unknown-tag retention | DXF-only extraction library |
| [GNU LibreDWG](https://www.gnu.org/software/libredwg/manual/html_node/Programs.html) | DWG to JSON/DXF/GeoJSON/SVG tools | GPLv3 and incomplete/variable coverage require an optional isolated adapter |
| [Autodesk Model Derivative](https://aps.autodesk.com/model-derivative-api-2d-3d-conversions) | Cloud translation and metadata extraction for many proprietary formats | Proprietary network service; unsuitable as a core local dependency |
| [ODA Drawings SDK](https://www.opendesign.com/products/drawings) | Broad native DWG/DGN access | Commercial dependency requiring a separately distributed plugin |

## Conclusion

The ecosystem already has strong parsers and converters. The missing reusable layer is a portable specification that combines source identity, extraction evidence, neutral records, geometry references, explicit loss, deterministic packaging, and progressive agent context. AECCTX should orchestrate existing engines rather than reimplement geometric kernels or proprietary decoders.
