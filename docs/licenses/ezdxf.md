# Optional ezdxf Dependency

AECCTX's bounded public DXF profiles use the separately distributed `ezdxf` Python package, version `==1.4.4`. Its installed package metadata and official documentation classify it under the MIT License. Other ezdxf versions are not covered by the ACX-14 or ACX-28 claims.

The dependency is exposed only through the `aecctx[dxf]` extra, is not bundled into the Apache-2.0 core wheel, and is reported by the plugin descriptor as `optional-not-bundled`.

ACX-28 reviewed the official ezdxf 1.4.4 release/entity/xref APIs. The public v0.3 profile uses read-only parsing and entity geometry APIs but deliberately does not call the xref importer: unsupported/proxy/custom entities may be omitted by that importer, and importing would collapse the required source separation. No ACIS kernel ships with ezdxf or AECCTX; ACIS/SAT/SAB interpretation remains unsupported. Project-authored fixtures are Apache-2.0 and contain no vendor payload.
