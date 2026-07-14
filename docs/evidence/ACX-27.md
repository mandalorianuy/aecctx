# ACX-27 acceptance evidence

Date: 2026-07-13
Status: acceptance candidate; authoritative after the governed GitHub squash merge
Decision/profile: ACXD-035 and `docs/specs/ifc-v03-profile.md`

## Implemented result

- Exact optional runtime `ifcopenshell==0.8.5` and project-authored IFC4X3 ADD2 STEP corpus.
- Namespaced `ifc_v03` source evidence for finite circles, ellipses, parameter trims, bounded composite curves, indexed line/three-point-arc segments, bounded text literals, annotation fill boundaries and directly associated bounded text/curve/fill/hatching styles.
- Deterministic polygonal SVG paths remain derived previews with explicit approximation metadata; source curves, text and hatch definitions remain authoritative records.
- Exact `IfcMapConversionScaled` factors X/Y/Z are preserved separately from unit scale and applied to distinct local axes; the emitted transform includes a finite inverse.
- Absent, empty, unsupported, malformed, over-limit, cyclic, incomplete, multiple and conflicted cases fail closed with stable machine diagnostics. Default v0.1 output and the ACX-13 v0.2 IFC profiles remain unchanged.

## TDD and local evidence

- Baseline: `pytest tests/test_ifc_adapter.py tests/test_ifc_v02.py -q` passed 17 tests.
- Initial RED: `pytest tests/test_ifc_v03.py -q` failed all 8 initial tests before fixtures, descriptor and production behavior existed.
- Bound-corpus RED: after fixture generation, 5 tests still failed specifically on missing v0.3 descriptor/evidence/factors/degradation/preview behavior.
- Focused GREEN: `pytest tests/test_ifc_adapter.py tests/test_ifc_v02.py tests/test_ifc_v03.py -q` passed 26 tests.
- Full suite before promotion: 688 tests collected; 678 passed and 10 pre-existing conditional skips.
- Target-state checker: `python scripts/check_ifc_v03_conformance.py` passed three exact-schema entries, deterministic regeneration and runtime/license boundaries.
- Claim-promotion RED: `python scripts/check_ifc_v03_conformance.py --require-public` failed with `AECCTX_IFC_V03_CLAIM_INVALID` while both claims remained `target`.
- Clean wheel/sdist build and target-state artifact scan passed; the wheel contained the IFC adapter and no IfcOpenShell/native payload.
- Canonical gate: `PYTHONPATH=src PATH=/Users/facundo/desarrollo/aecctx/.venv/bin:$PATH PYTHON=/Users/facundo/desarrollo/aecctx/.venv/bin/python AGENT_BASELINE_ROOT=/Users/facundo/desarrollo/codex-agent-baseline ./scripts/verify.sh` passed. Its portable cut passed 251 tests; the complete promoted suite passed 679 tests with 10 conditional skips; wheel/sdist checks, ACX-27 public-claim artifact scan, healthy `baseline-shared-v1` integration with zero issues, v0.1/v0.2 release corpus, clean install and optional extras all passed.

The final `--require-public`, portable, full, baseline and exact-SHA GitHub CI gates are mandatory before merge. The GitHub PR/check/squash record is the delivery authority; the task is not accepted on `main` until those gates pass.

## Fixtures, claims and provenance

- `fixtures/v0.3/ifc/` is original Apache-2.0 project-authored content; the generator reproduces all three files byte-for-byte.
- `conformance/v0.3/ifc-corpus.json` binds the exact `IFC4X3_ADD2` schema identifier, fixture hashes, generator hash and normative profile hash.
- `ifc.native-2d.v03` and `ifc.georeferencing.v03` have a public ceiling of `partial` on Python 3.12 Linux, macOS and Windows with optional `ifcopenshell==0.8.5`.
- IfcOpenShell remains LGPL-3.0-or-later, optional and unbundled from the Apache-2.0 core; no GPL/commercial decoder or third-party model payload was added.

## Residual non-claims and risk

No exact glyph/hatch rendering, topology, B-splines, offsets, spirals, arbitrary trims, external presentation resources, IFC2X3 property-set georeferencing, other IFC schemas/editions or coordinate operations, CRS/EPSG validation, survey authority, consumer classification or source mutation is claimed. A malicious file still reaches the separately distributed parser before AECCTX's structural limits; deployment-level parser isolation remains advisable for hostile inputs and is not expanded by this in-process profile.

`/Users/facundo/desarrollo/woodframing` was not modified. ACX-28 is the sole next task because DXF expansion is the next dependency-ordered functional residual; it was not executed.
