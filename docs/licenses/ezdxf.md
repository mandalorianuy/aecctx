# Optional ezdxf Dependency

AECCTX's DXF adapter uses the separately distributed `ezdxf` Python package, version `>=1.4.4,<2`. Its installed package metadata classifies it under the MIT License.

The dependency is exposed only through the `aecctx[dxf]` extra, is not bundled into the Apache-2.0 core wheel, and is reported by the plugin descriptor as `optional-not-bundled`.
