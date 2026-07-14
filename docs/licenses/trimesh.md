# Optional trimesh Dependency

AECCTX's mesh adapter uses the separately distributed `trimesh` Python package, version `>=4.12,<5`, classified under the MIT License.

The dependency is installed through `aecctx[geometry]`, is not bundled into the Apache-2.0 core wheel, and is reported as `optional-not-bundled` by the plugin descriptor.

## Optional CRS runtime

The bounded ACX-31 profile uses the separately distributed `pyproj==3.7.2` package and its PROJ runtime under the MIT License. It is installed only through `aecctx[crs]`, `aecctx[all]`, or the test environment and is not a dependency of the Apache-2.0 core wheel.

The wheel-provided `proj.db` contains EPSG registry data under the EPSG dataset terms distributed by PROJ. AECCTX does not copy that database into its own wheel: it records exact logical registry metadata plus a platform-specific SHA-256 attestation of the caller-installed database. Network access and external grid acquisition are disabled by the governed profile.
