# Optional IfcOpenShell Dependency

AECCTX's IFC adapter uses the separately distributed `ifcopenshell` Python package, version `>=0.8.5,<0.9`. Its installed package metadata classifies it as GNU Lesser General Public License v3 or later (LGPLv3+).

The dependency is exposed only through the `aecctx[ifc]` extra, is not bundled into the Apache-2.0 core wheel, and is reported by the plugin descriptor as `optional-not-bundled`. Distributors are responsible for satisfying the dependency's license and notice obligations.
