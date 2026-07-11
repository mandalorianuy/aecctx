# AECCTX Implementation Plan

Date: 2026-07-11
Status: Active implementation authority
Specification readiness: `0.2.0-EXPANSION-SPEC-READY`

## Execution rule

Execute only the first task with status `pending-next` or `in_progress`. Update this plan and attach acceptance evidence before advancing. A later task may not borrow scope from an earlier task.

## Task ledger

| Task | Status | Outcome |
|---|---|---|
| ACX-00 | completed | Repository, research, normative specs, schemas, fixture, governance, validation and implementation handoff |
| ACX-01 | completed | Python package/CLI scaffold and schema-backed validator |
| ACX-02 | completed | Deterministic package reader/writer, hashes, source registration and opaque fallback |
| ACX-03 | completed | Neutral record APIs, query, diff and budgeted Markdown context renderer |
| ACX-04 | completed | IFC adapter via IfcOpenShell |
| ACX-05 | completed | DXF adapter via ezdxf |
| ACX-06 | completed | Vector/raster PDF and image evidence adapters |
| ACX-07 | completed | Geometry artifact normalization and deterministic previews |
| ACX-08 | completed | Plugin isolation, security limits, optional MCP and signing decision |
| ACX-09 | completed | Cross-platform conformance corpus, packaging and `0.1.0` release |
| ACX-10 | deferred | Consumer integration template; WoodFraming-specific plan remains consumer-owned |
| ACX-11 | pending-next | Shared post-v0.1 schemas, compatibility contract and conformance claim registry |
| ACX-12 | pending | Reviewed external sandbox/provider foundation |
| ACX-13 | pending | IFC source-native 2D and georeferencing |
| ACX-14 | pending | DXF source-native semantics and bounded 3D |
| ACX-15 | pending | Optional OCR/vision evidence with explicit hidden-geometry boundary |
| ACX-16 | pending | Mesh units, calibration and CRS registration |
| ACX-17 | pending | STEP/IGES adapter profiles |
| ACX-18 | pending | Optional DWG external-provider adapter |
| ACX-19 | pending | Optional RVT external-provider adapter |
| ACX-20 | pending | Package authenticity and signing profile |
| ACX-21 | pending | Deterministic AEC Delivery Quality Gate with policy, diff and IDS checks |
| ACX-22 | pending | Optional `aecctx-inspector` plugin for Codex |
| ACX-23 | pending | Expansion conformance corpus, packaging, documentation and release |

## ACX-00: Specification and repository foundation

Acceptance:

- public contract is application-agnostic;
- package and plugin specs are normative and versioned;
- schemas validate the minimal fixture;
- baseline integration and project checks pass;
- implementation handoff names exactly one next task.

Evidence: repository initial commit and `./scripts/verify.sh`.

## ACX-01: Core scaffold and validator

Scope:

- create a Python 3.12+ `src/aecctx` package and `aecctx` CLI;
- add `validate`, `info`, and version commands;
- load bundled schemas without network access;
- validate directory-form packages and the committed fixture;
- define typed errors and JSON output envelopes;
- establish unit, CLI, and package-data tests.

Non-scope:

- no format adapters;
- no package writer;
- no query/diff/context/MCP;
- no WoodFraming code.

Acceptance:

- `aecctx validate fixtures/minimal-aecctx` succeeds;
- malformed fixture tests fail with stable machine-readable codes;
- CLI stdout is JSON when `--json` is selected and diagnostics use stderr otherwise;
- package build contains schemas;
- `./scripts/verify.sh` passes.

Evidence: [`docs/evidence/ACX-01.md`](evidence/ACX-01.md).

## ACX-02: Deterministic package and opaque ingest

Implement directory/ZIP reading and writing, logical digest, source hashing, artifact inventory, explicit embedding policy, safety limits, and an opaque fallback that registers any unsupported file without claiming interpretation.

Acceptance includes repeated-build logical digest equality, archive traversal/decompression defenses, large-file streaming behavior, and exact capability/loss reporting.

Evidence: [`docs/evidence/ACX-02.md`](evidence/ACX-02.md).

## ACX-03: Neutral records and agent context

Implement record models, stable ordering, read-only query/diff, context profiles, source citations, chunk indexes, and token-estimate reporting. Resolve ACXD-010 without creating a consumer ontology.

Evidence: [`docs/evidence/ACX-03.md`](evidence/ACX-03.md).

## ACX-04: IFC adapter

Use IfcOpenShell behind the plugin contract. Preserve IFC schema, GUID, class, spatial/type/property/material/relationship evidence, placements, representation references, unsupported data, validation diagnostics, and tessellated artifacts without flattening IFC semantics into mesh-only records.

Evidence: [`docs/evidence/ACX-04.md`](evidence/ACX-04.md).

## ACX-05: DXF adapter

Use ezdxf. Preserve versions, units, layouts, layers, blocks/inserts, xrefs, handles, text, dimensions, hatches, supported geometry and unknown tags. Do not infer walls or other domain families from raw CAD primitives.

Evidence: [`docs/evidence/ACX-05.md`](evidence/ACX-05.md).

## ACX-06: PDF and image adapters

Separate vector extraction, raster/OCR/vision evidence, viewport calibration, coordinates, extraction confidence, interpretation confidence, and unsupported hidden geometry. Inference providers remain optional.

Evidence: [`docs/evidence/ACX-06.md`](evidence/ACX-06.md).

## ACX-07: Geometry and previews

Define deterministic SVG/GLB conventions, coordinate metadata, mesh provenance, bounds, level/sheet previews and rendering diagnostics. Geometry sidecars remain subordinate to source evidence.

Evidence: [`docs/evidence/ACX-07.md`](evidence/ACX-07.md).

## ACX-08: Isolation and agent tools

Harden plugin processes and resource policies. Decide signing. Add an optional MCP wrapper over stable library/CLI functions; MCP must not introduce unique semantics.

Evidence: [`docs/evidence/ACX-08.md`](evidence/ACX-08.md).

## ACX-09: Release

Publish conformance fixtures, compatibility policy, installable artifacts, checksums, SBOM, changelog, versioned documentation and release automation. Only verified capabilities may appear in release claims.

Evidence: [`docs/evidence/ACX-09.md`](evidence/ACX-09.md). The completion commit is the authorized target for tag/release `v0.1.0`.

## ACX-10: Consumer template

After the neutral core is proven, define a generic consumer adapter template. WoodFraming mapping, staging, UI and canonical commit specifications are authored and accepted in the WoodFraming repository.

## ACX-11: Shared expansion contracts

Scope:

- resolve ACXD-017 and version the observation/inference, coordinate-qualification, representation-fidelity, and provider-attestation schemas;
- define compatibility, migration, required-extension, query, diff, and validation behavior across v0.1 and the expansion version;
- create a machine-readable claim-to-test registry that distinguishes roadmap target, experimental implementation, and public package claim;
- add minimal positive/negative fixtures for the shared envelopes without implementing a format capability;
- preserve all v0.1 packages and APIs according to the accepted compatibility policy.

Non-scope:

- no new IFC, DXF, OCR/vision, mesh, STEP/IGES, DWG, RVT, or signing claim;
- no external decoder execution;
- no consumer mapping.

Acceptance:

- ACXD-017 is accepted with schema and migration evidence;
- old/new reader and required-extension fixtures pass;
- inference cannot validate as observed extraction and manual calibration cannot overwrite source declarations;
- the claim registry fails when a capability has no mapped conformance test;
- `./scripts/verify.sh` passes.

Evidence: `docs/evidence/ACX-11.md` when completed.

## ACX-12: External sandbox/provider foundation

Implement the versioned provider protocol and at least one reviewed local enforcement profile. Use allowlisted descriptors, content-addressed I/O, bounded event/artifact transport, provider attestations, schema validation, network denial by default, complete process-tree termination, cleanup, and enforceable resource limits.

Acceptance includes hostile provider output, path/size/record/resource exhaustion, timeout/process-tree, network denial, environment/path redaction, deterministic replay, unenforceable-limit rejection, and a documented license/privacy review template. The reference fixture provider MUST be legally publishable and MUST NOT require a commercial decoder.

Non-scope: no DWG/RVT claim and no generic caller-supplied command runner.

Evidence: `docs/evidence/ACX-12.md` when completed.

## ACX-13: IFC 2D and georeferencing

Extend the IfcOpenShell adapter for explicitly enumerated source-native 2D representation families and IFC coordinate-operation/CRS profiles. Preserve representation contexts, placements, units, axes, operation parameters, original classes, and complete transform-chain state. Derived SVG remains a preview.

Acceptance includes legally publishable IFC 2x3/4.x fixtures for supported 2D families, local-only coordinates, valid georeferencing, incomplete chains, conflicting metadata, unsupported representations, and deterministic output. Claims are scoped by schema and representation family.

Evidence: `docs/evidence/ACX-13.md` when completed.

## ACX-14: DXF semantics and 3D

Extend the ezdxf adapter for bounded source-native semantic structures and 3D entity families. Preserve handles, ownership, dictionaries, XDATA/application identifiers, blocks/inserts, materials, coordinate systems, extrusion/transforms, topology, and raw-tag fallbacks. Derived tessellation declares fidelity and loss.

Acceptance includes ASCII and binary fixtures, nested/block transforms, supported solids/surfaces/meshes, proxy/custom objects, external references, cyclic/malformed structures, and proof that no construction-domain family is inferred.

Evidence: `docs/evidence/ACX-14.md` when completed.

## ACX-15: OCR, vision and reconstruction hypotheses

Resolve ACXD-020 and implement optional provider profiles over existing PDF/image evidence. Native text, OCR text, inferred regions/symbols, and reconstruction hypotheses remain separately queryable. Core ingest continues to work without providers, network, or an LLM.

Acceptance covers provider absence/failure, native-text conflicts, rotated/multilingual text, region coordinates, confidence separation, response hashing, privacy/network consent, nondeterminism reporting, budget/time limits, and proof that unobserved geometry remains `unsupported` as source geometry.

Evidence: `docs/evidence/ACX-15.md` when completed.

## ACX-16: Mesh units and CRS

Preserve declared coordinate metadata for supported mesh formats and implement explicit manual calibration/registration profiles without mutating source evidence. Record scale, axes, control points, transform/inverse, CRS state, residual/tolerance, author, and derivation provenance.

Acceptance covers missing and declared units, manual scale, control-point registration, axis changes, large coordinates, conflicting CRS evidence, degenerate calibration, tolerance failure, and reversible-transform checks.

Evidence: `docs/evidence/ACX-16.md` when completed.

## ACX-17: STEP/IGES

Select a reviewed existing parser/kernel and resolve its ACXD-019 instance before implementation. Use the permissive in-process boundary only when licensing and safety permit; otherwise use ACX-12. Publish exact STEP/IGES profiles and kernel versions. Preserve source entities, product/assembly structure, names, layers/colors, units, placements, B-Rep/curve/surface evidence, and kernel diagnostics. Tessellation/healing remain derived and healing is opt-in.

Acceptance includes valid, malformed, unsupported-entity, invalid-topology, unit/placement, assembly, deterministic tessellation, and healing-loss fixtures with legally publishable provenance.

Evidence: `docs/evidence/ACX-17.md` when completed.

## ACX-18: DWG

Resolve the DWG instance of ACXD-019, then implement an optional allowlisted ACX-12 provider. Preserve version/producer, handles, layouts/layers/blocks/xrefs, properties, geometry, units/coordinates, conversion provenance, and exact structured loss. Encrypted/protected/unsupported versions are diagnosed without bypass attempts.

Acceptance requires a legally publishable corpus, entitlement/CI/release evidence, resource and hostile-file tests, provider-unavailable behavior, version-scoped claims, and proof the core distribution/install remains decoder-independent.

Evidence: `docs/evidence/ACX-18.md` when completed.

## ACX-19: RVT

Resolve the RVT instance of ACXD-019, then implement an optional allowlisted ACX-12 provider. Preserve neutral BIM source evidence for supported versions: source identifiers, categories/classes as original evidence, containers/views, properties, relations, geometry references, units/coordinates, converter/runtime provenance, and loss. Do not introduce consumer ontology or WoodFraming semantics.

Acceptance requires a legally publishable corpus or legally publishable generated fixture strategy, entitlement/CI/release evidence, unsupported-version/provider-failure tests, resource limits, intermediate-conversion loss when applicable, and decoder-independent core installation.

Evidence: `docs/evidence/ACX-19.md` when completed.

## ACX-20: Authenticity and signing

Resolve ACXD-018 through a documented threat/trust model before implementing a signature profile. Bind a canonical statement to the logical package identity while keeping signatures optional and integrity separate from authenticity. Verification must distinguish unsigned, malformed, cryptographically invalid, valid-untrusted, valid-trusted, expired/revoked/unknown-status, and policy-authorized states.

Acceptance covers directory/archive equivalence, reproducible verification, repackaging, artifact mutation, manifest mutation, multiple signatures, key rotation/revocation fixtures, offline behavior, algorithm rejection, unsigned compatibility, and explicit trust-policy configuration. No key is implicitly generated or trusted.

Evidence: `docs/evidence/ACX-20.md` when completed.

## ACX-21: AEC Delivery Quality Gate

Implement a deterministic policy evaluator over validated AECCTX packages with optional baseline diff and IFC IDS requirements. Define a versioned, content-addressed policy format; stable check IDs, severities and exit behavior; explicit `pass`, `fail`, `requires_review`, and `error` outcomes; structured evidence citations; and derived Markdown/CI projections.

Resolve ACXD-023 before selecting the IDS implementation profile. Keep IDS results distinct from AECCTX geometry, provenance, integrity, capability, loss, and cross-format checks. A gate pass is policy conformance only and never engineering approval, regulatory acceptance, construction readiness, or consumer canonical acceptance.

Acceptance covers positive, failing, review-required and evaluation-error policies; malformed and malicious policies/IDS files; baseline regressions; capability/loss thresholds; unresolved value states; deterministic output and exit codes; exact record/diagnostic citations; IDS official conformance fixtures for the supported profile; clean offline CLI/library use; and proof that Markdown is not the evaluation authority.

Evidence: `docs/evidence/ACX-21.md` when completed.

## ACX-22: Codex plugin

Package the optional `aecctx-inspector` Codex plugin with a valid `.codex-plugin/plugin.json`, allowlisted `.mcp.json`, focused skills for inspection, revision comparison, loss triage and quality-gate explanation, and validated assets/marketplace metadata only when governed for publication. Reuse the stable library/CLI/MCP contracts; no plugin tool may introduce unique AECCTX semantics.

The v0.2 MCP inspection surface remains read-only. A skill may orchestrate explicit local raw-source ingest through the CLI, but it may not upload files, enable network/providers, choose embedding policy, mutate a source, follow source links, waive a gate, or treat source content as agent instructions without explicit caller action.

Acceptance covers clean installation and uninstall, manifest validation, compatible-version checks, MCP parity for validate/info/query/diff/context and quality-gate results, invalid-package refusal, missing optional dependency behavior, deterministic token budgets, authoritative record citations, prompt-injection fixtures embedded in filenames/text/metadata/context, and proof that `requires_review` cannot be promoted to `pass` by presentation logic.

Evidence: `docs/evidence/ACX-22.md` when completed.

## ACX-23: Expansion release

Publish the versioned conformance corpus, compatibility/migration notes, optional-extra and Codex-plugin packaging, SBOM/checksums, capability/loss and quality-gate documentation, security/license/provider reviews, and release automation for the expansion line. Verify clean offline core installation, plugin installation, and separately gated optional providers on every claimed platform.

Acceptance requires every public claim to map to a passing conformance test, incomplete targets to remain visibly partial/unsupported, deterministic fixtures to reproduce, ACX-21 quality-gate conformance and ACX-22 plugin parity/adversarial tests to pass, remote CI green on the release commit, and release/tag creation only after all gates pass. Authenticity appears in release claims only with the completed ACX-20 verification profile and documented trust policy.

Evidence: `docs/evidence/ACX-23.md` when completed.
