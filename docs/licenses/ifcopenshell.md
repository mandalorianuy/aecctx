# Optional IfcOpenShell Dependency

AECCTX's currently claimed IFC profiles use the separately distributed `ifcopenshell` Python package, version `0.8.5`. Its installed package metadata classifies it as GNU Lesser General Public License v3 or later (LGPLv3+). A different version requires a governed conformance rerun before it enters the public provider scope.

The dependency is exposed only through the `aecctx[ifc]` extra, is not bundled into the Apache-2.0 core wheel, and is reported by the plugin descriptor as `optional-not-bundled`. Distributors are responsible for satisfying the dependency's license and notice obligations.
