# Optional IfcOpenShell Dependency

AECCTX's currently claimed IFC profiles, including the ACX-27 bounded IFC4X3 ADD2 2D and `IfcMapConversionScaled` profiles, use the separately distributed `ifcopenshell` Python package, version `0.8.5`. Its installed package metadata classifies it as GNU Lesser General Public License v3 or later (LGPLv3+). A different version requires a governed conformance rerun before it enters the public provider scope.

The dependency is exposed only through the `aecctx[ifc]` extra, is not bundled into the Apache-2.0 core wheel, and is reported by the plugin descriptor as `optional-not-bundled`. ACX-27 uses project-authored Apache-2.0 IFC fixtures and adds no GPL model payload. The artifact conformance gate rejects a bundled IfcOpenShell native library. Distributors that install the optional extra remain responsible for satisfying the dependency's license and notice obligations.
