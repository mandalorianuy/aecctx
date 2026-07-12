# ACX-11 Acceptance Evidence

Date: 2026-07-11
Status: `completed`
Completion commit: governed ACX-11 milestone commit containing this evidence

## Authority covered

- Expansion spec sections 1-4 and 15-16.
- ACXD-013 claim honesty and accepted ACXD-017 v0.2 schema/compatibility boundary.
- ACX-11 only; no ACX-12 provider execution or later format capability was implemented.

## Implemented

- Immutable v0.1 plus new public/packaged `schemas/v0.2` manifest and common-record schemas.
- Typed `InferenceMetadata`, `CoordinateQualification`, `RepresentationFidelity`, and `ProviderAttestation` record models.
- Dual v0.1/v0.2 directory/ZIP validation and explicit v0.2 writing.
- Required-extension negotiation with stable `AECCTX_REQUIRED_EXTENSION_UNSUPPORTED` rejection.
- Semantic rejection for inferred records without provider metadata, manual calibration in source-declared slots, incomplete transform chains claiming global location, non-derived preview/inferred fidelity, and network attestations without allowlisted mode.
- Cross-version diff fields `before_version`, `after_version`, and `version_changed`; shared v0.2 fields remain available to normal query and budgeted context projection.
- Machine-readable `conformance/v0.2/claims.json` with public claim-to-fixture/test/evidence mappings and future targets that do not claim implementation.
- Claim registry validator with duplicate, reference, fixture, test-function and evidence-path checks wired into portable verification.
- Explicit v0.2 writer behavior, compatibility/migration documentation, package-data coverage and sdist inclusion.

## Claim evidence

| Claim | Support | Conformance evidence |
|---|---|---|
| dual v0.1/v0.2 validation | `full` for the shared reader profile | `test_v02_package_and_optional_extension_validate`, existing v0.1 fixture test |
| required-extension negotiation | `full` | `test_unknown_required_extension_is_rejected` |
| observation/inference separation | `full` for the shared schema/model profile | inference schema/model positive and negative tests |
| coordinate qualification | `full` for the shared schema/model profile | manual-slot and incomplete-chain rejection tests |
| representation fidelity | `full` for the shared schema/model profile | typed and package-level derived-fidelity rejection tests |
| provider attestation | `full` for the shared schema/model profile | local positive and network-policy negative tests |
| v0.2 query/diff/context | `full` for validated shared records | committed fixture query/context and cross-version diff tests |

These claims cover the shared substrate only. IFC, DXF, OCR/vision, meshes, STEP/IGES, DWG, RVT, signing, quality-gate and Codex-plugin targets remain unchanged.

## Fixtures and hashes

- `fixtures/minimal-aecctx`: existing legally publishable v0.1 compatibility fixture.
- `fixtures/v0.2/shared/minimal-v02`: hand-authored Apache-2.0-project fixture; manifest SHA-256 `c92fec63d28520f6857f331968aab3fdf3866d579fcdeeab4cf483c6c1b5226e`.
- Negative/degraded fixtures are deterministic mutations of those committed packages in `tests/test_v02_compatibility.py`.

## Validation evidence

- TDD RED states were observed for dual-version validation, unknown required extensions, record-version mismatch, inference metadata, coordinate authority, incomplete transforms, typed models, registry mappings, v0.2 writer/package data, derived fidelity and network attestation.
- Task-specific suite: 37 tests passed.
- Full local suite and portable verification: 115 tests passed.
- Wheel and sdist built successfully; wheel contains packaged v0.2 schemas and sdist contains v0.2 schemas, fixture and claim registry.
- `python3 scripts/check_spec_contract.py`, JSON validation and `git diff --check` passed.
- Final full `./scripts/verify.sh` result is recorded by the closing task run.

## Determinism, security, licensing and platform scope

- All schema, fixture, registry and model behavior is local/offline and deterministic.
- No dependency was added. Inputs/extensions remain data; no command, network, provider or executable behavior was introduced.
- The fixture is repository-authored and legally publishable. v0.2 schemas and conformance material ship under the repository Apache-2.0 license.
- Shared behavior is platform-neutral Python/JSON Schema and is exercised by the portable gate used by Linux, macOS and Windows CI.

## Residuals and non-scope

- The reference distribution remains version `0.1.0` until ACX-23; ACX-11 does not authorize a v0.2 release.
- No automatic migration command is provided. Explicit recompilation/migration requirements are documented.
- The supported required-extension set is intentionally empty until a later governed capability defines one.
- Provider attestation is a data contract, not proof of sandbox enforcement; ACX-12 owns enforcement.
- All later format, signing, gate and Codex-plugin capabilities remain target/partial/unsupported as already recorded.

## Boundary and next promotion

No file under `/Users/facundo/desarrollo/woodframing` was read or modified, and no WoodFraming, `WFDomain`, `WFImport` or consumer ontology dependency was added.

ACX-12 is promoted to `pending-next` because every native, GPL, commercial and network-backed capability depends on a reviewed external provider boundary. ACX-12 was not executed as part of this task.
