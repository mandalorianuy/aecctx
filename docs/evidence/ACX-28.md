# ACX-28 acceptance evidence

Date: 2026-07-14
Status: acceptance candidate; authoritative after the governed GitHub squash merge
Decision/profile: ACXD-036 and `docs/specs/dxf-v03-profile.md`

## Implemented result

- Exact optional `ezdxf==1.4.4` profiles for project-authored AC1009, AC1018 and AC1021 ASCII/binary cases, extending the existing AC1015/AC1032 claims.
- Source-first `dxf_v03` evidence for ELLIPSE, SPLINE, HELIX, RAY, XLINE, MLINE and R2007 MESH topology. Fixed-tolerance sampled paths remain derived `tessellated` evidence with a 4,096-vertex ceiling.
- Public `SourceBundle` SDK and CLI auto-detection for schema-validated, content-addressed DXF bundles. All paths, types, byte counts and hashes are validated before xref parsing; traversal is deterministic, depth/file/byte bounded and source-separated.
- Stable failures cover traversal, symlinks, digest drift, undeclared/unreachable members, cycles, depth and resource limits. Ambient/network paths are never followed.
- ACIS/SAT/SAB, proxy/custom, protected content and exact surfaces/B-Rep remain unsupported or opaque. Raw tags remain authoritative and no consumer wall/beam/panel vocabulary is introduced.

## TDD and validation evidence

- Initial RED: `pytest tests/test_dxf_v03.py -q` failed during collection because `SourceBundleError`/`load_source_bundle` did not exist.
- Behavioral RED: after contract/fixture creation, v0.3 tests failed on missing descriptor, source mappings, derived fidelity and xref traversal; `scripts/check_dxf_v03_conformance.py --require-public` failed while claims remained `target`.
- Focused GREEN: `pytest tests/test_dxf_adapter.py tests/test_dxf_v02.py tests/test_dxf_v03.py tests/test_package_data.py -q` passed 34 tests.
- Target-state checker passed six digest-bound entries, deterministic fixture regeneration, exact runtime/release/container mapping, schema mirror, bundle validation and optional-license boundary.
- `python3 scripts/check_spec_contract.py` passed.
- Public checker: `python scripts/check_dxf_v03_conformance.py --require-public` passed six entries and both partial claims.
- Portable gate: `verify_portable.sh` passed 253 tests, deterministic corpora, wheel/sdist build and artifact scans.
- Canonical gate: `PYTHONPATH=src PATH=/Users/facundo/desarrollo/aecctx/.venv/bin:$PATH PYTHON=/Users/facundo/desarrollo/aecctx/.venv/bin/python AGENT_BASELINE_ROOT=/Users/facundo/desarrollo/codex-agent-baseline ./scripts/verify.sh` passed 691 tests with 10 intentional conditional skips, healthy `baseline-shared-v1` integration with zero issues, v0.1/v0.2 release verification, clean builds and clean-install checks.
- Exact-SHA GitHub CI and squash merge remain mandatory delivery evidence; the task is accepted on `main` only after those checks pass.

## Fixtures, claims and provenance

- `fixtures/v0.3/dxf/` is original Apache-2.0 project-authored content generated with `PYTHONHASHSEED=0` and ezdxf fixed test metadata; regeneration is byte-for-byte.
- `conformance/v0.3/dxf-corpus.json` binds six source files, exact releases/containers, generator/profile hashes and the three-member source bundle.
- `dxf.source-semantics.v03` and `dxf.geometry.v03` have ceiling `partial` on Python 3.12 Linux, macOS and Windows under optional `ezdxf==1.4.4`.
- ezdxf is MIT, optional and unbundled. The core wheel contains the adapter and source-bundle schema but no ezdxf/native/GPL/commercial payload.

## Security, loss and residual risk

Every bundle member is treated as untrusted data; symlinks, escapes, URI/network paths, duplicate paths, mismatched bytes/hashes, missing/unreachable members, cycles and resource overflow fail closed. Embedded commands and links are inert. A malicious standalone or validated-bundle DXF still reaches the optional in-process parser; deployment-level parser isolation remains advisable for hostile inputs.

No exact B-Rep/surface kernel, ACIS interpretation, proxy/custom semantics, encrypted/protected DXF, external images/underlays, DWG xrefs, unlisted releases/entities, unit/CRS inference, source mutation, engineering approval or consumer classification is claimed.

`/Users/facundo/desarrollo/woodframing` was not modified. ACX-29 is the sole governed successor and was not executed.
