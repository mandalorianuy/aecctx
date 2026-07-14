# AECCTX Mesh Coordinate v0.3 Profile

Version: `mesh-coordinate-v03-profile-v1`
Date: 2026-07-14
Status: Normative ACX-31 implementation profile
Decision authority: ACXD-040

## 1. Purpose and authority

This profile qualifies caller-supplied mesh coordinate reference identifiers against one offline registry runtime and applies one explicit reversible datum operation as manual/derived evidence. It does not change source vertices, source-declared coordinate state, the v0.2 package schema or the default v0.1/v0.2 mesh behavior.

The original mesh bytes and observed vertices remain authoritative. Registry validation establishes only that an identifier exists in the bound registry. It does not establish that the source mesh was surveyed, authored or positioned in that CRS.

## 2. Exact runtime and registry profile

The only positive runtime profile is `pyproj-epsg-v11.022-offline-v1`:

- optional `pyproj==3.7.2`, MIT;
- exact runtime and compiled PROJ `9.5.1`;
- EPSG dataset `v11.022`, dated `2024-11-05`;
- recommended PROJ data version `1.20`;
- PROJ database layout `1.4`;
- Python 3.12+ on Linux, macOS and Windows where those exact values are reported;
- network forced disabled through the pyproj API before registry or operation use.

The raw SQLite `proj.db` SHA-256 is runtime attestation, not cross-platform registry identity: official wheels may serialize the same selected registry content into different database bytes. `registry_digest` is instead SHA-256 over the canonical JSON of the exact normalized selected records plus the metadata above. A metadata mismatch, record mismatch or logical digest mismatch fails closed.

The closed selected CRS set is:

- `EPSG:4269` NAD83, geographic 2D;
- `EPSG:4326` WGS 84, geographic 2D;
- `EPSG:4979` WGS 84, geographic 3D;
- `EPSG:4978` WGS 84, geocentric;
- `EPSG:3857` WGS 84 / Pseudo-Mercator, projected;
- `EPSG:5703` NAVD88 height, vertical;
- `EPSG:6349` NAD83(2011) + NAVD88 height, compound;
- `EPSG:4328` WGS 84 (geocentric), deprecated.

Identifiers are exact uppercase `AUTHORITY:CODE` strings. Names, WKT, embedded vendor cues, filenames and coordinate magnitude never infer an identifier. Unknown identifiers remain unknown; deprecated records remain explicitly deprecated; compound and vertical records are validation evidence only unless a separately accepted operation names them.

## 3. Registry document

`schemas/v0.2/crs-registry.schema.json` governs a closed document containing:

- profile, library, PROJ, EPSG, PROJ-data and database-layout versions;
- the logical `registry_digest` and optional platform `database_sha256` attestation;
- exact selected normalized CRS records with identifier, name, type, deprecation, axes and normalized WKT digest;
- exact datum operations with source/target identifiers, native axis order, stated accuracy, round-trip tolerance and required grids;
- author and evidence classification.

Duplicate identifiers or operations, conflicting normalized records, unknown fields, non-finite values, path-like resources and digest drift are invalid. The document is bounded to 64 CRS records, 16 operations, 8 axes per CRS and 1 MiB canonical JSON.

## 4. Exact datum-operation profile

The only positive operation is `EPSG:1252`, NAD83 to WGS 84 (3):

- source `EPSG:4269`, target `EPSG:4326`;
- native input and output axes `Lat`, `Lon`, `h`;
- three-parameter Helmert operation selected by exact operation identifier, never by best-match search;
- stated accuracy `4.0 m`;
- zero required grids;
- at most 100,000 three-dimensional points;
- latitude in `[-90, 90]`, longitude in `[-180, 180]`, finite height with absolute value at most 100,000 m;
- inverse round-trip maximum of `1e-9` degrees for horizontal axes and `1e-6` m for height.

The SDK MUST use `Transformer.from_pipeline("EPSG:1252")`, reject runtime operation metadata drift and call forward plus inverse with error checking. The result records transformed points, exact registry/operation/configuration digests, stated accuracy and measured round-trip residuals. Operation accuracy is registry metadata, not measured survey accuracy.

## 5. Grid and external-resource boundary

No grid-backed operation is positive in this profile. pyproj wheels do not bundle transformation grids and AECCTX MUST NOT download them. Any operation requiring a grid returns `AECCTX_CRS_GRID_OPERATION_UNSUPPORTED`. A future grid profile requires a separately governed file name, exact content hash, origin, license, redistribution review, registry relation and offline packaging gate.

Paths, URLs, `PROJ_DATA`, `PROJ_LIB`, `PROJ_AUX_DB`, user-writable caches and caller-selected pipelines are not accepted profile inputs. Embedded mesh extensions and vendor metadata are inert data and cannot select registry records, operations or resources.

## 6. Mesh evidence mapping

The opt-in mesh input is `--mesh-crs-profile` / `crs_profile=` and requires `aecctx_version="0.2.0"` with the geometry adapter. It is mutually exclusive with the existing manual affine/control-point coordinate profile in v1 of this profile.

For a valid profile AECCTX emits:

1. unchanged observed source mesh primitives;
2. a manual registry/operation assertion bound to the profile and source digest;
3. a separate derived mesh-coordinate primitive and content-addressed JSON artifact containing transformed vertices and unchanged faces;
4. namespaced `aecctx.mesh_crs.v1` details with registry, operation, accuracy, residual, axes, runtime and database attestations;
5. `georeferencing=partial` with a stable loss reason stating caller-supplied, non-survey authority.

Source `spatial_reference`, declared units and detected units remain unchanged. Registry validity cannot turn unknown source CRS or units into source-known values. Markdown may summarize the result but is never authority.

## 7. Failure contract

Stable failure codes include:

- `AECCTX_CRS_DEPENDENCY_MISSING`;
- `AECCTX_CRS_RUNTIME_UNSUPPORTED`;
- `AECCTX_CRS_NETWORK_ENABLED`;
- `AECCTX_CRS_REGISTRY_INVALID`;
- `AECCTX_CRS_REGISTRY_CONFLICT`;
- `AECCTX_CRS_REGISTRY_DIGEST_MISMATCH`;
- `AECCTX_CRS_IDENTIFIER_UNKNOWN`;
- `AECCTX_CRS_IDENTIFIER_DEPRECATED` when policy requires current identifiers;
- `AECCTX_CRS_OPERATION_UNKNOWN`;
- `AECCTX_CRS_OPERATION_METADATA_MISMATCH`;
- `AECCTX_CRS_GRID_OPERATION_UNSUPPORTED`;
- `AECCTX_CRS_POINT_LIMIT_EXCEEDED`;
- `AECCTX_CRS_POINT_INVALID`;
- `AECCTX_CRS_ROUND_TRIP_TOLERANCE_EXCEEDED`.

Failure never mutates source evidence or emits a derived transform. Missing optional dependencies keep core import, validation, query, diff and context usable offline.

## 8. Fixtures and conformance

The project-authored v0.3 corpus contains valid NAD83 mesh/profile, registry-only valid/deprecated/vertical/compound records, unknown/conflicting registry documents, large/invalid points, missing-grid/unknown-operation documents, prohibited external-resource/vendor-extension inputs and inherited insufficient/singular/reflected/tolerance cases from the v0.2 coordinate corpus.

Conformance proves:

- deterministic registry normalization and logical digest on Linux, macOS and Windows;
- exact forward/inverse EPSG:1252 output and bounded residuals;
- unchanged source vertices/faces and separate manual/derived evidence;
- v0.1/v0.2 default byte compatibility;
- clean-core failure without pyproj and clean `crs` extra installation;
- schema/package-data parity, fixture hashes, claim mapping and offline operation;
- no WoodFraming or consumer mapping.

## 9. Claims and non-claims

`mesh.crs-registry` and `mesh.datum-transform` may become public `partial` only for the exact profile above after all ACX-31 gates pass.

Unsupported or unclaimed: other registry/library/PROJ/EPSG versions; implicit best-operation selection; network lookup; grids; time-dependent, velocity, vertical or compound transformations; arbitrary pipelines; source CRS discovery; unit guessing; survey truth; engineering approval; source vertex mutation; general georeferencing completeness; consumer semantics.
