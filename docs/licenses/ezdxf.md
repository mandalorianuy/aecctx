# Optional ezdxf Dependency

AECCTX's bounded public DXF profiles use the separately distributed `ezdxf` Python package, version `==1.4.4`. Its installed package metadata classifies it under the MIT License. Other ezdxf versions are not covered by the ACX-14 claims.

The dependency is exposed only through the `aecctx[dxf]` extra, is not bundled into the Apache-2.0 core wheel, and is reported by the plugin descriptor as `optional-not-bundled`.
