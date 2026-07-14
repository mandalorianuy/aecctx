# ACX-31 Acceptance Evidence

Status: local acceptance complete; exact-head GitHub delivery pending
Decision: ACXD-040
Profile: `pyproj-epsg-v11.022-offline-v1`

## Acceptance mapping

- `mesh.crs-registry`: exact offline pyproj 3.7.2 / PROJ 9.5.1 / EPSG v11.022 normalized registry, caller-file validation and explicit valid, deprecated, vertical, compound, unknown and conflict states.
- `mesh.datum-transform`: exact grid-free EPSG:1252 NAD83-to-WGS84 operation with native axes, stated 4 m accuracy, bounded input, reversible residual checks and separate manual/derived evidence.
- Source mesh vertices, source units and source CRS remain observed or unknown. No registry validity, transformation or residual establishes survey truth.

## Evidence owners

- Normative profile: `docs/specs/mesh-coordinate-v03-profile.md`
- Schema: `schemas/v0.2/crs-registry.schema.json` and packaged mirror
- Corpus: `conformance/v0.3/mesh-crs-corpus.json`
- Fixtures: `fixtures/v0.3/mesh/`
- Tests: `tests/test_mesh_v03.py`
- Gate: `scripts/check_mesh_crs_v03_conformance.py`

## Validation

- RED: the first focused collection failed with `ModuleNotFoundError: No module named 'aecctx.crs'`, proving the new contract was absent before implementation.
- Focused: `pytest -q tests/test_mesh_v03.py tests/test_geometry_v02.py tests/test_mesh_coordinates_v02.py tests/test_package_data.py tests/test_v03_claim_registry.py` passes 44 tests.
- Conformance: `python scripts/check_mesh_crs_v03_conformance.py --require-public --artifact dist/aecctx-0.2.0-py3-none-any.whl --artifact dist/aecctx-0.2.0.tar.gz` passes two claims and four hash-bound fixtures.
- Canonical: `./scripts/verify.sh` passes 719 tests with 10 intentional skips and six inherited ezdxf/NumPy deprecation warnings; portable verification, wheel/sdist, baseline integration and release verification are green.
- Clean Python 3.12 installs: the wheel core imports and exposes CLI with `pyproj` absent; `aecctx[crs]` installs exact pyproj 3.7.2 / PROJ 9.5.1, validates EPSG:4326 offline and does not require NumPy.
- Delivery: exact-head GitHub CI, non-draft PR review, squash merge and merged-main CI remain mandatory before this candidate is accepted on `main`.

## Residual non-claims

Only the eight enumerated CRS records and EPSG:1252 are covered. Dynamic registry lookup, network access, external/vendor extensions, grid operations, unlisted CRS/operations, survey authority, coordinate epoch, vertical datum conversion, engineering approval and cross-database equivalence remain unsupported or unknown as specified by the profile.
