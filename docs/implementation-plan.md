# AECCTX Implementation Plan

Date: 2026-07-13
Status: Active implementation authority
Specification readiness: `0.3.0-FUNCTIONAL-DEBT-PLAN-READY`

## Execution rule

Execute only the first task with status `pending-next` or `in_progress`. Update this plan and attach acceptance evidence before advancing. A later task may not borrow scope from an earlier task.

## Status and promotion protocol

Allowed ledger states are:

- `pending`: sequenced but not executable;
- `pending-next`: the only task authorized to start;
- `in_progress`: the only task currently executing;
- `completed`: every acceptance item has evidence and all required gates pass;
- `blocked`: execution was attempted but a repository-external legal, credential, platform, provider, or human decision prevents completion; the evidence document records impact, alternatives attempted, retained support level, and the exact decision required;
- `deferred`: deliberately outside this implementation line.

There MUST be exactly one `pending-next` or `in_progress` task while executable work remains. A `blocked` task is not a successful capability claim and MUST remain `partial`, `opaque`, or `unsupported` in the capability matrix. It permits promotion of the next independent task only after the blocker is documented in its evidence file and decision log. ACX-23 MUST enumerate every blocked predecessor and omit its target from release claims.

Task promotion is performed in the same change that closes the current task:

1. attach `docs/evidence/ACX-NN.md`;
2. update capability claims only for tested, bounded support;
3. resolve or update owned decision-log entries;
4. set the task to `completed` or documented `blocked`;
5. promote exactly the following task to `pending-next`;
6. run `./scripts/verify.sh`;
7. commit one coherent ACX milestone without rewriting published history.

## Definition of ready

Before a task moves to `in_progress`:

- every earlier non-deferred task is `completed` or documented `blocked`;
- its normative spec sections and decision owners are identified;
- required libraries/providers have official API, version, license, distribution and security notes, or the task begins with that review;
- positive, negative, degraded and adversarial fixtures are listed with publication rights;
- expected claim boundaries and non-claims are written before implementation;
- the narrow test commands and final repository gate are named.

## Definition of done

Every ACX completion requires:

- tests written from the acceptance contract, including at least one failing/degraded path before the implementation claim;
- implementation, schema, CLI/SDK, fixture and documentation changes required by that task only;
- structured capability/loss and stable diagnostic coverage for every non-full result;
- deterministic replay evidence or an explicit reproducibility class and external-input hashes;
- security, privacy, license and platform evidence proportional to the capability;
- `python3 scripts/check_spec_contract.py`, the task-specific tests, `./scripts/verify_portable.sh`, and `./scripts/verify.sh` passing;
- no uncommitted generated timestamps or unrelated workspace changes;
- no new WoodFraming, `WFDomain`, `WFImport`, network, or LLM dependency in the core.

## Acceptance evidence template

Each new `docs/evidence/ACX-NN.md` MUST contain:

1. task status, completion commit and date;
2. spec sections and decision-log entries covered;
3. implemented deliverables and explicit non-scope;
4. claim table with capability, source/profile/version, support level and conformance test IDs;
5. fixtures with origin/license and hashes;
6. commands run with results;
7. determinism or reproducibility evidence;
8. capability/loss and diagnostic evidence;
9. dependency, license, security, privacy and platform review;
10. known residual risks and unsupported cases;
11. proof that WoodFraming was not modified;
12. next-task promotion or exact blocker/decision required.

## Cross-task directory contract

Expected implementation surfaces are listed to prevent rediscovery; a task MAY refine a path only with equivalent ownership and an updated evidence document.

| Surface | Intended ownership |
|---|---|
| `schemas/v0.2/` and `src/aecctx/schemas/v0_2/` | public and packaged v0.2 schemas |
| `src/aecctx/records.py`, `validation.py`, `query.py`, `diff.py`, `context.py` | shared record semantics and projections |
| `src/aecctx/providers/` | external provider descriptors, protocol and reviewed runners |
| `src/aecctx/adapters/` | format-specific evidence extraction only |
| `src/aecctx/signing.py` | optional signature statement and verification policy |
| `src/aecctx/gate/` | quality-gate policy, evaluation and result projection |
| `plugins/aecctx-inspector/` | optional Codex plugin distribution |
| `fixtures/v0.2/` | legally publishable source and package fixtures |
| `conformance/v0.2/` | claim registry, corpus manifests and expected results |
| `tests/` | unit, integration, adversarial and parity tests |
| `docs/evidence/` | immutable milestone acceptance evidence |

## Dependency spine

All tasks execute sequentially even when a later task has no direct code dependency. The logical dependencies are:

```text
ACX-11 schemas/claims
  -> ACX-12 provider sandbox
  -> ACX-13..16 open-format capabilities
  -> ACX-17..19 restricted/kernel-backed formats
  -> ACX-20 signing
  -> ACX-21 quality gate
  -> ACX-22 Codex plugin
  -> ACX-23 conformance release
```

ACX-13 through ACX-16 consume ACX-11. ACX-15, ACX-17 when restricted, ACX-18 and ACX-19 consume ACX-12. ACX-21 consumes the stable capability/loss, diff, validation and optional signing results. ACX-22 consumes only stable library/CLI/MCP/gate behavior. ACX-23 consumes all completed or documented-blocked outcomes.

The accepted post-v0.2 dependency line is:

```text
ACX-24 OCI multiarch
  -> ACX-25 local enforcement
  -> ACX-26 remote providers
  -> ACX-27..31 open-format and inference expansion
  -> ACX-32..34 kernel/proprietary formats
  -> ACX-35..37 trust, gate and distribution
  -> ACX-38 aggregate conformance and release
```

ACX-24 through ACX-38 are governed by `docs/specs/aecctx-post-v02-functional-debt-spec.md` and the detailed execution plan `docs/plans/post-v02-functional-debt-implementation.md`. They reuse v0.2 shared evidence and namespaced extensions. If an owning task needs to modify a standard v0.2 field, only that task stops until a compatibility/schema/migration decision is accepted.

## Specification traceability

| Expansion spec section | Owning task | Required durable output |
|---|---|---|
| 1-3 purpose, boundaries and claim lifecycle | ACX-11, ACX-23 | versioned claims registry and release claim audit |
| 4 shared evidence extensions | ACX-11 | v0.2 schemas, models and compatibility fixtures |
| 5 external sandbox provider contract | ACX-12 | provider protocol, reference profile and adversarial suite |
| 6 IFC 2D/georeferencing | ACX-13 | bounded IFC profiles and conformance corpus |
| 7 DXF semantics/3D | ACX-14 | bounded DXF profiles and conformance corpus |
| 8 OCR/vision/hidden geometry | ACX-15 | optional provider profile, replay corpus and hypothesis boundary tests |
| 9 mesh units/CRS | ACX-16 | calibration schema, transforms and coordinate corpus |
| 10 STEP/IGES | ACX-17 | reviewed kernel adapter and profile-specific corpus |
| 11 DWG/RVT | ACX-18, ACX-19 | separate reviewed provider decisions/adapters/corpora |
| 12 authenticity/signing | ACX-20 | threat model, signature profile and verification corpus |
| 13 delivery quality gate | ACX-21 | policy/IDS evaluator and outcome corpus |
| 14 Codex plugin | ACX-22 | optional plugin package and parity/adversarial corpus |
| 15 compatibility/migration | ACX-11, ACX-23 | reader matrix, migration guide and release compatibility tests |
| 16 security/privacy/licensing | every owning task | task evidence review and abuse fixtures |
| 17 release claim gate | ACX-23 | published corpus, artifacts, CI and release evidence |

## Verification cadence

Every task uses this order:

1. targeted unit/schema tests for the changed contract;
2. targeted integration tests for adapter/provider/CLI behavior;
3. deterministic or replay comparison for records/artifacts;
4. adversarial/resource tests appropriate to the input boundary;
5. `python3 scripts/check_spec_contract.py`;
6. `./scripts/verify_portable.sh`;
7. `./scripts/verify.sh` before completion and promotion.

ACX-23 additionally runs clean-install artifact verification, the complete v0.1/v0.2 conformance corpus, all claimed platform/provider matrices, plugin validation, and remote CI/release verification.

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
| ACX-11 | completed | Shared post-v0.1 schemas, compatibility contract and conformance claim registry |
| ACX-12 | completed | Reviewed external sandbox/provider foundation |
| ACX-13 | completed | IFC source-native 2D and georeferencing |
| ACX-14 | completed | DXF source-native semantics and bounded 3D |
| ACX-15 | completed | Experimental bounded OCR evidence; vision remains target and hidden geometry remains public unsupported |
| ACX-16 | completed | Mesh units, calibration and CRS registration |
| ACX-17 | completed | Experimental bounded STEP/IGES source graph and translator-derived BREP profiles |
| ACX-18 | completed | Experimental bounded R2000/AC1015 DWG source-object and converted-DXF evidence profile |
| ACX-19 | blocked | No admissible RVT provider; public unsupported boundary with deterministic opaque anti-claim evidence |
| ACX-20 | completed | Optional detached JWS/Ed25519 signing and caller-owned offline trust-policy evaluation |
| ACX-21 | completed | Bounded deterministic policy/IDS quality gate is public partial under the exact accepted profile |
| ACX-22 | completed | Optional `aecctx-inspector-v1` plugin is public partial with parity/adversarial/install evidence |
| ACX-23 | completed | Expansion conformance corpus, packaging, documentation and `0.2.0` release |
| ACX-24 | completed | Live OCI providers on Linux arm64 and amd64 with cross-architecture equivalence |
| ACX-25 | completed | Additional reviewed local enforcement profiles |
| ACX-26 | in_progress | Optional remote/customer-managed provider protocol |
| ACX-27 | pending | Expanded IFC 2D and georeferencing profiles |
| ACX-28 | pending | Expanded DXF semantics, geometry and bounded xrefs |
| ACX-29 | pending | Multilingual and layout-aware OCR profiles |
| ACX-30 | pending | Bounded vision inference and reconstruction hypotheses |
| ACX-31 | pending | Mesh CRS registry and datum-operation qualification |
| ACX-32 | pending | STEP/IGES XDE and fidelity expansion |
| ACX-33 | pending | DWG version, xref, units and geometry expansion |
| ACX-34 | pending | RVT provider reopening or renewed executable blocker |
| ACX-35 | pending | Advanced optional signing and trust profiles |
| ACX-36 | pending | Expanded bounded IDS and quality-gate profiles |
| ACX-37 | pending | Inspector distribution and host portability |
| ACX-38 | pending | Aggregate conformance, packaging and `0.3.0` release |

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

Objective: establish the v0.2 record and conformance substrate without implementing a new format capability.

Entry gates:

- ACX-01 through ACX-09 remain green;
- ACXD-017 is the only design decision this task may resolve;
- v0.1 fixtures remain immutable compatibility inputs.

Deliverables:

- `schemas/v0.2/manifest.schema.json`, `record.schema.json`, extension schemas and packaged mirrors;
- typed record models for observation/inference, coordinate qualification, representation fidelity and provider attestation;
- compatibility and migration document covering v0.1 read, v0.2 read/write, required extensions, query, diff and context;
- `conformance/v0.2/claims.json` mapping every target/experimental/public claim to tests and fixtures;
- positive and negative shared-envelope fixtures under `fixtures/v0.2/shared/`;
- schema and claim-registry validation wired into portable verification.

Work breakdown:

1. Inventory every new field in expansion-spec sections 3, 4 and 15 and classify it as base, optional extension or required extension.
2. Record the compatibility choice in ACXD-017 before creating implementation schemas.
3. Write failing schema/semantic tests for observed-versus-inferred provenance, manual calibration precedence, fidelity classes, transform-chain incompleteness and unsupported required extensions.
4. Add the public schemas and packaged copies with an automated byte-equality/package-data check.
5. Extend record loading, validation, query, diff and context so v0.1 behavior remains stable and v0.2 fields remain queryable without Markdown authority.
6. Implement the claim registry checker: unique claim IDs, bounded profile/version, support level, fixture IDs, test IDs, platform/provider scope and evidence link.
7. Add compatibility fixtures for v0.1-only consumer, v0.2-aware consumer, ignored optional extension and rejected unknown required extension.
8. Document migration and close ACXD-017 with evidence.

Test matrix:

- valid observed extraction and valid provider inference;
- inference mislabeled as source-observed must fail;
- original, manual and derived coordinate assertions remain independently addressable;
- incomplete/conflicted transform chain cannot validate as globally located;
- B-Rep, tessellation, projection and preview fidelity remain distinct;
- v0.1 packages retain identical logical digest/query/diff behavior;
- missing, duplicate or unmapped claim-registry entries fail verification;
- public/package schemas remain synchronized.

Non-scope:

- no new IFC, DXF, OCR/vision, mesh, STEP/IGES, DWG, RVT, or signing claim;
- no external decoder execution;
- no consumer mapping.

Acceptance:

- ACXD-017 is accepted with schema and migration evidence;
- old/new reader and required-extension fixtures pass;
- inference cannot validate as observed extraction and manual calibration cannot overwrite source declarations;
- the claim registry fails when a capability has no mapped conformance test;
- public v0.1 behavior and release corpus remain unchanged;
- `./scripts/verify.sh` passes.

Evidence: [`docs/evidence/ACX-11.md`](evidence/ACX-11.md).

## ACX-12: External sandbox/provider foundation

Objective: provide the only admissible execution boundary for native, GPL, commercial and network-backed decoders.

Deliverables:

- versioned provider request, response, descriptor and attestation schemas;
- `src/aecctx/providers/` registry, content-addressed staging, protocol client and result validator;
- one reviewed local reference sandbox profile using a harmless publishable fixture provider;
- resource-limit model for bytes, records, files, recursion, decompression, CPU, memory, wall time, child processes and output;
- security and license/privacy review templates;
- stable diagnostics for registration, policy, launch, timeout, resource, protocol, attestation and cleanup failures.

Work breakdown:

1. Threat-model parent/core, sandbox launcher, decoder, filesystem, network, artifacts and returned events.
2. Specify allowlisted provider resolution; reject caller paths, shell strings, environment-selected imports and source-controlled callbacks.
3. Write protocol-contract tests and a deterministic fake provider before the runner.
4. Implement content-addressed input/output staging with private temporary directories, normalized environment and no host-path leakage.
5. Enforce OS-supported limits and reject a provider profile when any required axis cannot be enforced.
6. Deny network by default; make any reviewed egress policy explicit, bounded and attested.
7. Validate every event/artifact before package construction and retain capability/loss after partial/fatal provider failure.
8. Kill the complete process tree on timeout/cancellation and prove cleanup.
9. Publish provider-author review checklists and portability evidence.

Test matrix:

- valid deterministic round trip with identical response/artifact hashes;
- unregistered provider, supplied command and descriptor mismatch;
- invalid JSON/schema, duplicate sequence, forged hash, absolute/traversal/symlink path and oversized output;
- CPU, memory, wall-time, process, file, record and recursion exhaustion;
- child/grandchild process termination and temporary-data cleanup;
- socket/network attempt denied and reported;
- host path, HOME, locale, clock and environment leakage normalized/redacted;
- provider unavailable, crash and partial-output behavior;
- unsupported enforcement platform rejected, not degraded silently.

Non-scope:

- no DWG, RVT, STEP/IGES or inference capability claim;
- no generic caller-supplied command runner;
- no assumption that sandbox output is trusted.

Acceptance: all enforcement axes have conformance evidence on each claimed platform; the reference provider is legally publishable; core install remains provider-independent; `./scripts/verify.sh` passes.

Evidence: [`docs/evidence/ACX-12.md`](evidence/ACX-12.md).

## Governed residual backlog

### ACXB-001: Additional external enforcement profiles

Functional outcome: restricted decoders can run on Linux and Windows only through reviewed profiles that enforce the complete ACX-12 axis set rather than trusting descriptor declarations.

Owner: the first of ACX-17, ACX-18 or ACX-19 that proposes a public claim on the affected platform. It MUST update the plan before implementation.

Acceptance:

- Linux OCI/namespace/cgroup or equivalent profile has runtime conformance for filesystem/user/process/network/resource isolation, process-tree termination and cleanup;
- Windows AppContainer/job-object or equivalent profile has the same bounded evidence;
- unavailable runtimes reject execution deterministically;
- provider/core packaging remains separated;
- the capability matrix and claim registry name exact platform/provider scope.

Until accepted, only the digest-pinned Linux-container environment under `oci-docker-v1` is executable. Native Linux/macOS and Windows restricted-decoder claims remain `unsupported`.

## ACX-13: IFC 2D and georeferencing

Objective: replace broad IFC 2D/georeferencing partial claims with bounded, schema-specific conformance claims.

Normative profile: [`docs/specs/ifc-v02-profile.md`](specs/ifc-v02-profile.md), accepted by ACXD-025 before implementation.

Deliverables:

- enumerated IFC schema/representation support table;
- source-native 2D primitive and representation-relationship extraction in `adapters/ifc.py` or focused IFC modules;
- coordinate-operation/CRS evidence and transform-chain records using ACX-11 schemas;
- deterministic optional SVG projections clearly labeled derived;
- `fixtures/v0.2/ifc/` corpus and claim entries.

Work breakdown:

1. Review the official IfcOpenShell API and supported IFC schema entities; record exact dependency versions.
2. Enumerate supported curve, annotation, footprint, axis, plan and mapped 2D representation families before coding.
3. Write fixtures/tests that distinguish source-native 2D, empty representation, absent representation, unsupported type and extraction failure.
4. Extract representation IDs, contexts, items, placements, units and relationships without converting a 3D projection into source-native evidence.
5. Enumerate supported coordinate-reference/operation profiles and preserve original class, parameters, axes, units and relationship paths.
6. Build explicit local-to-project-to-CRS transform chains with known/unknown/conflicted/unsupported states and reversible matrices when complete.
7. Generate deterministic SVG only as cited preview evidence.
8. Update claims only for exact schema and representation combinations proven by the corpus.

Test matrix:

- IFC2X3 and IFC4-family supported fixtures;
- native plan/axis/annotation/curve/mapped representation;
- local-only model, complete projected CRS, incomplete operation, conflicting units/axes and malformed parameters;
- large coordinates and precision/tolerance behavior;
- unsupported representation retained with stable loss;
- repeated ingest produces identical semantic records/artifact hashes;
- no guessed EPSG, origin, scale, rotation or elevation.

Non-scope: no universal IFC representation claim, no engineering validation and no consumer classification.

Acceptance: every `full`/`partial` claim is schema/profile bounded; all excluded cases have structured loss; v0.1 IFC fixtures remain compatible; `./scripts/verify.sh` passes.

Evidence: [`docs/evidence/ACX-13.md`](evidence/ACX-13.md).

## ACX-14: DXF semantics and 3D

Objective: preserve bounded source-native DXF structure and 3D geometry without inventing domain semantics or exact-kernel support.

Normative profile: [`docs/specs/dxf-v02-profile.md`](specs/dxf-v02-profile.md), accepted by ACXD-026 before implementation.

Deliverables:

- DXF version/entity/semantic support table tied to ezdxf versions;
- evidence records for ownership, dictionaries, extension dictionaries, XDATA, application IDs, groups, attributes, materials and block structure;
- bounded 3D extraction for declared entity families with OCS/WCS and insert transforms;
- derived GLB/tessellation path with fidelity/loss metadata;
- ASCII/binary positive and adversarial fixtures plus claim entries.

Work breakdown:

1. Inventory current raw-tag fallback and choose exact semantic/entity profiles from official ezdxf APIs.
2. Write tests for semantic evidence identity and preservation before normalized records.
3. Implement handle ownership and dictionary/XDATA/application/group/material extraction with unknown tags retained.
4. Implement 3D coordinates, extrusion, OCS/WCS, nested inserts and topology for enumerated entities.
5. Keep ACIS/proxy/custom/encrypted/external-reference content bounded as raw/opaque/unsupported unless a reviewed kernel exists.
6. Produce derived tessellation with source IDs, transforms, tolerance and fidelity class.
7. Add malformed/cyclic/resource fixtures and verify stable diagnostics.
8. Prove neutral kinds never classify CAD shapes as consumer construction families.

Test matrix:

- supported ASCII and binary versions;
- dictionaries/XDATA/groups/attributes/materials and unknown tags;
- nested inserts, non-default extrusion and OCS/WCS transforms;
- 3DFACE, meshes/polymeshes and only the explicitly supported solid/surface profiles;
- proxy/custom objects, xrefs, invalid handles, cycles and malformed tag streams;
- tessellation failure and partial topology;
- deterministic output and exact raw-tag fallback;
- vocabulary scan rejecting wall/beam/panel inference from geometry alone.

Non-scope: no automatic construction semantics, no proprietary kernel bundling and no claim beyond listed entity/version profiles.

Acceptance: source semantics and 3D claims map to fixtures/tests; unsupported kernel content stays explicit; `./scripts/verify.sh` passes.

Evidence: [`docs/evidence/ACX-14.md`](evidence/ACX-14.md).

## ACX-15: OCR, vision and reconstruction hypotheses

Objective: add optional OCR/vision evidence while keeping core ingest offline and hidden geometry unsupported as source evidence.

Normative profile: [`docs/specs/inference-v02-profile.md`](specs/inference-v02-profile.md), accepted by ACXD-020 before implementation. ACX-15 first strengthens the shared OCI preflight to verify a registered local image tag against its allowlisted immutable image ID; this is a functional prerequisite for the selected provider and does not broaden ACX-12 platform claims.

Decision gate: resolve ACXD-020 separately for each provider profile, including license, install extra, execution boundary, model/runtime versioning, network/privacy/retention and reproducibility.

Deliverables:

- provider-neutral OCR/vision request and result mapping over ACX-11 inference records;
- at least one reviewed optional profile, preferably deterministic/local when technically adequate;
- explicit CLI/SDK opt-in with budgets, languages/profile and network-consent controls;
- native-text/OCR conflict records and reconstruction-hypothesis type;
- publishable raster/PDF and provider-response fixtures, including offline replay.

Work breakdown:

1. Define profile vocabulary for text spans, regions, symbols, dimensions, tables, relationships and reconstruction hypotheses.
2. Resolve ACXD-020 using official provider/runtime documentation; do not add it to core dependencies.
3. Write golden provider-response fixtures so most conformance tests require neither network nor model download.
4. Implement region rasterization/input hashing and bounded provider invocation through the appropriate reviewed boundary.
5. Map output with provider/model/config/request/response hashes, coordinates, confidence separation and reproducibility class.
6. Preserve native PDF text and OCR text independently; emit explicit conflicts rather than choosing silently.
7. Enforce budgets, timeouts, size/page/region limits, consent and failure fallback.
8. Add prompt-like/source content tests proving provider/source output remains data.

Test matrix:

- provider absent, disabled, timeout, malformed response and partial page failure;
- native text equal to/conflicting with OCR;
- rotated, multilingual, low-confidence and empty regions;
- pixel/page coordinate transforms and uncalibrated measurement state;
- seeded/non-deterministic provenance and response-hash replay;
- privacy/network disabled by default;
- reconstruction marked inferred and excluded from identity, measurement, georeferencing and geometry completeness;
- no-provider core ingest/query/diff/context regression.

Non-scope: no mandatory LLM/network, no implicit upload, no hidden-geometry extraction claim and no consumer acceptance.

Acceptance: ACXD-020 profile decisions are recorded; optional installs and offline replay pass; hidden geometry remains `unsupported`; `./scripts/verify.sh` passes.

Evidence: [`docs/evidence/ACX-15.md`](evidence/ACX-15.md).

Completion resolution: ACXD-020 selected only the exact local English OCR profile in `docs/specs/inference-v02-profile.md`. The provider-neutral v0.2 inference envelope, OCI execution, replay, PDF/image SDK/CLI opt-in, native/OCR comparisons, confidence/provenance mapping and failure degradation are implemented and tested. No vision/reconstruction vocabulary or provider was accepted, so those work-breakdown branches close as governed `unsupported` boundaries rather than implementation claims. Cropped/rotated regions, other languages and portable live-runtime matrices remain registered residuals requiring a future plan update before work begins.

## ACX-16: Mesh units and CRS

Objective: qualify mesh coordinates honestly and support explicit, provenance-bearing calibration/registration.

Normative profile: [`docs/specs/mesh-coordinate-v02-profile.md`](specs/mesh-coordinate-v02-profile.md), governed by ACXD-016 and ACXD-027. Control-point registration uses an orientation-preserving uniform-scale similarity; automatic affine/shear/reflection fitting is outside the claim.

Execution cut: [`docs/plans/acx-16-implementation.md`](plans/acx-16-implementation.md). It is subordinate to this plan and the normative profile; it adds no scope.

Deliverables:

- format-specific declared metadata extraction for OBJ/STL/glTF-family inputs where available;
- calibration/registration profile schema and CLI/SDK input;
- transform solver/validator with inverse, residual and tolerance reporting;
- derived geometry/artifact path that leaves original mesh coordinates unchanged;
- mesh coordinate conformance fixtures and claim entries.

Work breakdown:

1. Inventory which metadata is source-declared versus library/viewer convention for each supported format.
2. Add failing tests that keep absent units/CRS `unknown`.
3. Preserve declared units, axes, transforms and coordinate metadata with source locators.
4. Define manual scale, explicit matrix and control-point registration modes with author and configuration hash.
5. Validate dimensionality, non-degenerate control points, invertibility, residuals, tolerances and transform direction.
6. Emit manual assertions and derived artifacts without rewriting source evidence.
7. Detect and retain conflicts between source declarations and manual calibration.
8. Verify large-coordinate stability and round-trip transform accuracy.

Test matrix:

- missing, valid and conflicting declared units;
- absent, declared and manually supplied CRS;
- manual scale, matrix and control-point registration;
- insufficient/collinear points, singular matrix, tolerance failure and axis mismatch;
- large/small coordinate magnitudes and numeric canonicalization;
- forward/inverse round trip within declared tolerance;
- source mesh hash/coordinates unchanged after calibration.

Non-scope: no guessed units/CRS, no survey authority and no silent precedence between conflicting sources.

Acceptance: all calibration modes preserve original evidence and explicit states; deterministic transforms pass; `./scripts/verify.sh` passes.

Evidence: `docs/evidence/ACX-16.md` when completed.

## ACX-17: STEP/IGES

Objective: implement bounded STEP/IGES evidence extraction using an existing reviewed parser/geometry kernel.

Normative profile: [`docs/specs/step-iges-v02-profile.md`](specs/step-iges-v02-profile.md), governed by ACXD-014, the ACX-17 instance of ACXD-019 and ACXD-028. The native OCP/OCCT runtime is restricted to the reviewed ACX-12 OCI boundary.

Execution cut: [`docs/plans/acx-17-implementation.md`](plans/acx-17-implementation.md). It is subordinate to this plan and the normative profile; it adds no scope.

Decision gate: resolve an ACXD-019 instance before linking or executing the selected kernel. The record MUST cover API/version, license, redistribution, wheels/platforms, CI, fixture rights, telemetry/network, security history and maintenance posture.

Deliverables:

- adapter design selecting permissive in-process execution or ACX-12 provider execution;
- exact STEP application protocols and IGES versions/flavors in the support table;
- source entity, product/assembly, name, layer/color, unit, placement and B-Rep/curve/surface evidence;
- derived deterministic tessellation and explicit fixed translator-processing/healing reports;
- legally publishable STEP/IGES corpus and kernel license evidence.

Work breakdown:

1. Evaluate existing official APIs and record a decision matrix; do not implement a parser or geometry kernel from scratch.
2. Resolve ACXD-019 and pin the tested kernel/runtime range.
3. Write probe, malformed-file and minimal product/assembly tests before adapter implementation.
4. Preserve schema/flavor, entity IDs, product hierarchy, names, colors/layers, units and placements.
5. Preserve exact B-Rep/curve/surface references where the kernel exposes them; never substitute tessellation as exact geometry.
6. Add deterministic tessellation with tolerance/version provenance.
7. Keep translator processing fixed by the reviewed runtime, reject caller healing options, retain original evidence and emit changed-topology/tolerance loss.
8. Register only exact profile/kernel/platform claims proven by conformance.

Test matrix:

- each claimed STEP protocol and IGES flavor;
- single part, nested assembly, colors/layers, units and placements;
- curves/surfaces/solids and unsupported entities;
- invalid topology, truncated/malformed records and extreme entity counts;
- tessellation repeatability and kernel-version provenance;
- fixed translator-processing report, rejected caller healing configuration, changed topology and tolerance diagnostics;
- missing optional dependency/provider failure;
- clean core install without the kernel.

Non-scope: no authoring write-back, no self-built B-Rep kernel, no generic STEP/IGES claim and no implicit healing.

Acceptance: ACXD-019 is accepted for the chosen path; exact profiles and losses are published; `./scripts/verify.sh` passes.

Evidence: `docs/evidence/ACX-17.md` when completed.

Completion resolution: ACXD-028 selects the exact operator-built OCP/OCCT OCI provider. The portable corpus proves AP203, AP214, AP242 edition 1 and IGES 5.3 protocol/mapping determinism; the exact Linux-arm64 image proves live transfer, BREP and tessellation. Claims remain `experimental partial`. XDE/source correlation, normalized styles/units/placements, per-root tolerance summaries, partial-root recovery, source-exact BREP and other schemas/platforms remain explicit unsupported residuals rather than scaffold claims.

## ACX-18: DWG

Objective: provide optional, version-scoped DWG extraction through a legally reviewed ACX-12 provider.

Normative profile: [`docs/specs/dwg-v02-profile.md`](specs/dwg-v02-profile.md), governed by ACXD-007, ACXD-014, ACXD-019, ACXD-024 and ACXD-029. The selected GPL runtime is restricted to the reviewed ACX-12 OCI boundary.

Execution cut: [`docs/plans/acx-18-implementation.md`](plans/acx-18-implementation.md). It is subordinate to this plan and the normative profile; it adds no scope.

Decision gate: resolve the DWG ACXD-019 instance, including SDK/service entitlement, user deployment model, CI credentials, redistribution, telemetry/retention, version support and publishable fixture rights. If no compliant provider is available, record `blocked` evidence and retain opaque fallback.

Deliverables:

- allowlisted DWG provider descriptor/profile separate from the core distribution;
- version/producer, handle, layout/layer/block/xref, property, geometry and coordinate evidence mapping;
- direct-versus-converted extraction provenance, including intermediate hashes and conversion loss;
- encrypted/protected/unsupported-version diagnostics without bypass;
- publishable versioned corpus or documented blocker.

Work breakdown:

1. Compare official provider APIs and licensing terms; close the provider decision before code.
2. Add descriptor, entitlement and provider-unavailable tests using ACX-12 fake/replay responses.
3. Implement bounded probe and extraction mapping for enumerated DWG versions.
4. Preserve source IDs/handles, containers, layouts, layers, blocks/inserts, xrefs, properties, units, coordinates and geometry fidelity.
5. If conversion is used, record converter/runtime/settings and input/intermediate/output hashes; never label it direct extraction.
6. Exercise ACX-12 resource, network, cleanup and hostile-output controls with DWG-specific cases.
7. Verify core wheel/sdist and normal install contain no commercial binaries or required entitlement.

Test matrix:

- each claimed DWG version and feature profile;
- nested blocks/xrefs, model/paper layouts, layers/properties, 2D/3D supported geometry;
- unsupported custom/proxy objects and partial conversion;
- encrypted/protected, future/old unsupported, corrupt and oversized files;
- entitlement missing/expired, provider unavailable/timeout/crash;
- intermediate conversion provenance and loss;
- deterministic replay where provider permits and declared nondeterminism otherwise;
- core install/import/CLI without provider.

Non-scope: no license bypass, no commercial binary redistribution in core, no universal DWG claim and no domain classification.

Acceptance: provider/legal review and corpus support every claim, or the exact external blocker is documented; `./scripts/verify.sh` passes.

Evidence: `docs/evidence/ACX-18.md` when completed.

Completion resolution: ACXD-029 selected only GNU LibreDWG 0.13.4 behind the exact reviewed Linux-arm64 `oci-docker-v1` image. ACX-18 implements self-contained R2000/`AC1015` content probing, direct bounded LibreDWG JSON object evidence, explicitly converted DXF/simple-geometry evidence, deterministic replay/CLI, duplicate-handle conflict preservation, GPL/security review and opaque v0.1 compatibility. Other DWG releases/platforms, encrypted/protected content, xref traversal, ACIS/proxy/custom semantics, qualified units/CRS and complete 3D remain registered unsupported/unknown residuals. ACX-19 is promoted to `pending-next`; no RVT implementation is included.

## ACX-19: RVT

Objective: provide optional, version-scoped RVT neutral evidence extraction through a legally reviewed ACX-12 provider.

Normative blocked profile: [`docs/specs/rvt-v02-blocked-profile.md`](specs/rvt-v02-blocked-profile.md), approved under ACXD-019 and ACXD-030. Its detailed TDD execution plan is [`docs/superpowers/plans/2026-07-12-acx-19-rvt-blocked-boundary.md`](superpowers/plans/2026-07-12-acx-19-rvt-blocked-boundary.md); no provider implementation is authorized.

Decision gate: resolve the RVT ACXD-019 instance for API/service/runtime, entitlement, supported host versions/platform, automation constraints, CI, telemetry/retention, redistribution and fixture rights. If unavailable, document `blocked` and retain opaque fallback.

Deliverables:

- when a provider is selected through a future reopening decision: allowlisted RVT provider descriptor/profile outside core dependencies, neutral mappings, converter provenance and a publishable generated corpus;
- for the current ACXD-030 no-provider decision: the machine-readable decision record, executable anti-claim/opaque-fallback boundary, restricted-dependency scans and exact reopening requirements defined by the blocked profile;
- explicit scan proving no WoodFraming, `WFDomain`, `WFImport` or consumer classification enters output/code.

Work breakdown:

1. Review official supported APIs/providers and close the legal/operational decision.
2. If the decision selects a provider, stop and govern its version-specific source locator, identity, extraction, provenance, sandbox and corpus contract before implementation.
3. If the decision selects no provider, stop adapter work and execute only the separately approved blocked-profile implementation plan.

Test matrix:

- selected-provider branch: each claimed RVT version/profile, neutral evidence, loss, failures, replay parity, provenance and core isolation;
- current blocked branch: decision-record schema, anti-claim registry, extension-independent opaque ingest determinism, core distribution/dependency isolation and consumer-boundary scans.

Non-scope: no authoring mutation, no engineering approval, no consumer ontology and no WoodFraming integration.

Acceptance: claims are version/provider bounded or the blocker is explicit; consumer-boundary scans pass; `./scripts/verify.sh` passes.

Evidence: `docs/evidence/ACX-19.md` when completed.

Completion resolution: ACXD-030 selected no provider because Revit desktop, APS Automation, ODA BimRv and the Revit IFC exporter do not satisfy the repository's combined entitlement, runtime, sandbox, CI, privacy and fixture-rights gates. ACX-19 therefore closes as documented `blocked` with a machine-validated decision, exact public `unsupported` claim, deterministic opaque anti-claim sentinel and source/wheel/sdist enforcement. No provider, adapter, descriptor, replay, RVT version or semantic claim was added. ACX-20 alone is promoted to `pending-next`.

## ACX-20: Authenticity and signing

Objective: define and implement optional package signature verification without conflating integrity, identity, trust or authorization.

Normative profile: [`docs/specs/signing-v1-profile.md`](specs/signing-v1-profile.md), accepted under ACXD-018. Its threat boundary is [`docs/security/signing-threat-model.md`](security/signing-threat-model.md). Acceptance authorizes implementation planning but does not create an authenticity claim.

Execution cut: [`docs/plans/acx-20-implementation.md`](plans/acx-20-implementation.md). It is subordinate to the normative profile, threat model and this plan; it adds no ACX-21 scope.

Decision gate: resolved. ACXD-018 selects detached JWS General JSON, the fully specified `Ed25519` JOSE identifier, canonical semantic-manifest binding, protected statement digest and caller-owned offline registry/policy evaluation with independent key-lifecycle/trust fields. The written profile and subordinate TDD execution cut require explicit user approval before implementation begins.

Deliverables:

- accepted signing profile: canonical statement, package/digest binding, envelope, serialization, algorithms, identity reference and trust-policy model;
- `src/aecctx/signing.py` with explicit sign/verify APIs and stable diagnostic/result states;
- CLI commands/options that never generate/select/trust keys implicitly;
- offline test PKI/key fixtures, revocation/expiry policy fixtures and multi-signature corpus;
- security/license review for cryptographic dependencies.

Work breakdown:

1. Produce threat/trust model and compare standards/library options.
2. Decide how signatures bind logical digest, manifest fields, required extensions and directory/archive equivalence.
3. Specify unsigned, malformed, invalid, valid-untrusted, valid-trusted, expired, revoked, unknown-status and policy-authorized result records.
4. Write canonicalization/mutation/algorithm-policy tests before implementation.
5. Implement detached or selected envelope signing with explicit caller key material and deterministic statement bytes.
6. Implement offline verification with caller-owned trust roots/policy; keep online status optional and explicit.
7. Support multiple signatures and rotation without making container metadata authoritative.
8. Integrate integrity and signature results as separate validation sections and queryable records.

Governed execution rule: no implementation file, schema, fixture or dependency change begins until the accepted written profile and committed subordinate ACX-20 implementation plan have explicit user approval. The execution cut preserves the work breakdown and test matrix above, orders tests before implementation, names narrow commands per slice and contains no ACX-21 scope.

Test matrix:

- unsigned valid package;
- directory/archive/repacked equivalent package;
- artifact, manifest, digest, statement and signature mutation;
- malformed/unknown/disallowed algorithms and serialization;
- valid-untrusted versus valid-trusted versus authorized signer;
- expiry, revocation fixture, rotation, multiple signatures and countersignature policy if selected;
- offline unknown-status behavior;
- no implicit key generation, discovery, network or trust-root selection.

Non-scope: no universal authorization policy, no mandatory signing, no secret/key management service and no claim that cryptographic validity equals engineering approval.

Acceptance: ACXD-018 is accepted, all states are machine-distinct, unsigned v0.1/v0.2 compatibility passes and `./scripts/verify.sh` passes.

Evidence: `docs/evidence/ACX-20.md` when completed.

Completion resolution: ACX-20 publishes the bounded `detached-jws-ed25519-offline-v1` profile as optional public `partial` support. Valid v0.1/v0.2 packages can be signed and verified through detached sidecars with explicit caller-owned registry/policy inputs; integrity, cryptographic validity, lifecycle, trust and authorization remain machine-distinct. X.509, online revocation/discovery, timestamps, countersignatures, implicit trust and universal approval remain unsupported. ACX-21 alone is promoted to `pending-next`.

## ACX-21: AEC Delivery Quality Gate

Objective: implement a deterministic policy-conformance evaluator over validated package evidence, optional baseline diff and bounded IFC IDS requirements.

Normative profile: [`docs/specs/quality-gate-v02-profile.md`](specs/quality-gate-v02-profile.md), accepted under ACXD-021 and ACXD-023. Acceptance authorizes detailed implementation but does not create a quality-gate claim.

Execution cut: [`docs/plans/acx-21-implementation.md`](plans/acx-21-implementation.md). It is subordinate to the normative profile and this plan; it adds no ACX-22 scope.

Decision gate: resolved. ACXD-023 selects the closed canonical `https://aecctx.dev/gate/v1` policy/result/waiver model, stable checks/outcomes/exits, exact-finding waivers, optional baseline diff and bounded buildingSMART IDS v1.0 simple-value evaluation through optional `ifctester==0.8.5` plus `ifcopenshell==0.8.5`. IDS requires caller-supplied bytes bound to an authoritative candidate source hash; unproved facets/versions remain unsupported.

Deliverables:

- versioned JSON policy schema and content digest;
- `src/aecctx/gate/` evaluator, result records and derived Markdown/CI annotations;
- CLI/SDK `gate` entry point with stable JSON and exit behavior;
- checks for validation/integrity, capabilities, loss budgets, value states, diagnostics, baseline regressions and selected IDS profile;
- positive/fail/review/error/malicious/baseline/IDS corpus.

Work breakdown:

1. Define trust boundary and reject executable expressions, callbacks, links, macros or source commands in policy/IDS.
2. Resolve ACXD-023 and publish policy/check/outcome/waiver schemas.
3. Write outcome aggregation and exit-code tests before checks.
4. Implement structural/integrity/capability/loss/value-state/diagnostic checks over authoritative records.
5. Add baseline semantic-diff regression checks using stable diff APIs.
6. Integrate only the selected IDS versions/facets and label IDS results separately from other AECCTX checks.
7. Emit `pass`, `fail`, `requires_review` or `error` with policy/package digests, evaluator versions and exact evidence IDs.
8. Generate Markdown/CI annotations from the JSON result and prove projection parity.

Governed execution rule: Tasks 1-9 completed the closed schemas/models, strict deterministic policy parser, exact-finding waivers, authoritative checks, semantic baseline diff, bounded IDS v1.0 simple-value evaluation, deterministic CLI/projections, hash-bound corpus, clean-install boundaries and cross-platform acceptance. ACX-21 is `completed`; only the exact `aecctx-gate-v1-ids-1.0-simple-v1` subset is public `partial`. ACX-22 alone is promoted to `pending-next` and MUST NOT execute without a new continuation request.

Test matrix:

- positive, deterministic failure, explicit review and evaluator error;
- unknown/unsupported/conflicted/explicit-null/not-applicable policy handling;
- capability/loss thresholds and diagnostic severity budgets;
- baseline added/removed/changed records and producer/capability regressions;
- allowed/expired/invalid waiver with provenance;
- malformed, recursive, oversized and prompt/command-like policy/IDS inputs;
- official IDS conformance cases for enumerated facets and explicit unsupported facets;
- identical inputs yield semantically identical JSON/exit code;
- Markdown cannot change the result and pass language never implies engineering approval.

Non-scope: no workflow approval, regulatory certification, construction readiness, consumer canonical acceptance or policy inference.

Acceptance: ACXD-023 is accepted; authoritative JSON/result parity and offline execution pass; `./scripts/verify.sh` passes.

Evidence: `docs/evidence/ACX-21.md` when completed.

Completion resolution: ACX-21 publishes `quality-gate.policy-ids` as public `partial` on Python 3.12 Linux/macOS/Windows for the exact core checks and bounded IDS 1.0 simple-value combinations mapped by the 27-case corpus. Unlisted IDS combinations, `partOf`, URI/bSDD lookup, geometry/quantity interpretation, remote validation and engineering/consumer approval remain unsupported. ACX-22 alone is promoted to `pending-next`.

## ACX-22: Codex plugin

Objective: package `aecctx-inspector` as an optional Codex orchestration layer with no unique AECCTX semantics.

Execution cut: [`docs/plans/acx-22-implementation.md`](plans/acx-22-implementation.md). It is subordinate to expansion-spec section 14, ACXD-022 and this plan; it adds no ACX-23 scope.

Deliverables:

- `plugins/aecctx-inspector/.codex-plugin/plugin.json` and allowlisted `.mcp.json`;
- focused skills for validate/inspect, revision diff, capability/loss triage, budgeted context and quality-gate explanation;
- read-only MCP parity for stable inspection/gate operations;
- plugin validation/install/uninstall scripts and compatibility metadata;
- adversarial source/prompt-injection fixtures and parity tests.

Work breakdown:

1. Inventory stable CLI/library/MCP/gate operations; exclude anything not already authoritative outside the plugin.
2. Define minimal plugin manifest, MCP allowlist and compatible AECCTX versions.
3. Write skills that always validate first and distinguish observed, normalized, inferred, derived and policy-result layers.
4. Keep MCP inspection read-only; any raw ingest workflow must require explicit local paths/options and normal core policies.
5. Add structured citations to package digest, record IDs and diagnostic/check IDs.
6. Add prompt-injection defenses treating filenames, source text, metadata, annotations and context as data.
7. Prove missing Codex/plugin dependencies do not affect core package operation.
8. Validate install/uninstall and package only referenced assets.

Test matrix:

- manifest/schema and MCP allowlist validation;
- clean plugin install, compatible/incompatible core version and uninstall;
- validate/info/query/diff/context/gate parity with direct library/CLI results;
- invalid package refusal and missing optional dependency;
- deterministic token-budget selection and correct record citations;
- prompt-like filenames, PDF text, IFC/DXF metadata, OCR response and generated context;
- no implicit upload/network/provider/embedding-policy change/source mutation/link following;
- `requires_review`/`fail` cannot become `pass` in skill prose;
- no tool introduces unique semantics or consumer/engineering claims.

Non-scope: no LLM requirement for core, no write tool, no trust-root/waiver selection, no marketplace publication without separate governed authorization.

Acceptance: plugin is optional, installable and parity-tested; adversarial behavior passes; `./scripts/verify.sh` passes.

Evidence: `docs/evidence/ACX-22.md` when completed.

Governed execution rule: Tasks 1-7 completed the bounded manifest, exact local stdio MCP allowlist, six read-only parity operations, five validate-first skills, adversarial source-data contract, safe install/uninstall, hash-bound corpus, clean packaging boundary and cross-platform acceptance. ACX-22 is `completed`; only `aecctx-inspector-v1` is public `partial`. ACX-23 alone is promoted to `pending-next` and MUST NOT execute without a new continuation request.

Completion resolution: ACX-22 publishes `codex.aecctx-inspector` as public `partial` on Python 3.12 Linux/macOS/Windows for the exact local distribution and conformance mapping. Marketplace publication, universal model behavior, third-party Codex hosts, native/GPL/commercial sandbox approval and any semantics beyond the stable library/CLI/MCP/gate surfaces remain unclaimed.

## ACX-23: Expansion release

Objective: release the expansion line only with claim-complete evidence, reproducible artifacts and truthful unsupported/blocked reporting.

Execution cut: [`docs/plans/acx-23-implementation.md`](plans/acx-23-implementation.md). It is subordinate to expansion-spec section 17 and this plan; it adds no capability scope.

Deliverables:

- `conformance/v0.2/corpus.json` and expected claim/gate/plugin results;
- compatibility/migration guide and versioned release notes;
- core, optional-extra and plugin packaging with pinned compatibility ranges;
- checksums, SBOM, dependency/license/provider/security/privacy reports;
- release workflow for build, clean install, corpus, signing verification when supported, artifact upload and tag/release checks;
- final capability matrix and evidence index.

Work breakdown:

1. Audit ACX-11 through ACX-22 evidence and list completed versus documented-blocked tasks.
2. Fail release verification for any claim without a unique conformance test/fixture/evidence mapping.
3. Build the v0.2 corpus from legally publishable fixtures and offline provider replays.
4. Publish migration and compatibility behavior for v0.1 readers/packages and optional extensions/providers.
5. Build wheel/sdist/plugin artifacts in clean environments; inspect contents and dependency boundaries.
6. Generate checksums and SBOM; verify licenses and that restricted binaries/credentials/fixtures are absent.
7. Run Linux/macOS/Windows public CI plus separately authorized provider matrices for each claimed platform.
8. Verify deterministic artifacts/results where declared and explicit reproducibility metadata otherwise.
9. Update capability matrix, README, changelog, docs and handoff with exact support profiles and residual risks.
10. Create tag/release only from the reviewed green commit and verify published assets/checksums/CI.

Release matrix:

- clean core install without optional adapters, providers, Codex, network or LLM;
- each public optional extra install/import/CLI smoke;
- directory/ZIP validation, ingest, query, diff, context and v0.1 compatibility;
- claimed IFC, DXF, OCR/vision, mesh, STEP/IGES, DWG and RVT profiles;
- sandbox adversarial suite and provider-unavailable fallback;
- signing states when ACX-20 is completed;
- quality-gate policy/IDS corpus;
- Codex plugin install/parity/adversarial corpus;
- sdist/wheel/plugin content, checksum and SBOM verification;
- remote CI green for the exact release SHA.

Non-scope: no claim for a blocked/unproven profile, no hidden geometry authority, no proprietary binary redistribution, no WoodFraming integration and no `1.0` stability promise.

Acceptance:

- every claim maps to passing evidence and every blocked/unsupported target remains explicit;
- all local and remote gates pass on the release commit;
- clean install and published artifact verification pass;
- version/tag/release are created only after those gates;
- final handoff identifies the exact neutral integration boundary for consumer-owned planning.

Evidence: [`docs/evidence/ACX-23.md`](evidence/ACX-23.md).

Completion resolution: AECCTX `0.2.0` is released from immutable tag `v0.2.0` with 23/23 non-target claims mapped to evidence, one explicit future target, ACX-19 documented blocked, deterministic plugin/checksum metadata, SPDX SBOM, clean core/all-extras installation and verified public assets. A GNU-tar `pipefail` portability defect discovered by the first tag workflow was root-caused, regression-tested and corrected without moving or deleting the tag; the governed recovery workflow rebuilt from that exact tag and published the verified release. No task is promoted to `pending-next`. ACX-10 remains deferred and consumer-owned planning begins only from `docs/integration/woodframing-boundary.md` under a future separately accepted plan.

## ACX-24 through ACX-38: Post-v0.2 functional debt program

Normative specification: [`docs/specs/aecctx-post-v02-functional-debt-spec.md`](specs/aecctx-post-v02-functional-debt-spec.md), accepted under ACXD-031.

Detailed implementation authority: [`docs/plans/post-v02-functional-debt-implementation.md`](plans/post-v02-functional-debt-implementation.md). Its file ownership, interfaces, TDD cuts, fixtures, claims, provider/security/license gates and exact closure commands are subordinate to this ledger and the normative spec.

Program rules:

- ACX-24 and ACX-25 are complete and ACX-26 alone is `in_progress`; no later ACX may execute or borrow scope.
- Existing `0.2.0` public claims remain unchanged until an owning milestone passes its complete acceptance bundle.
- Replay cannot satisfy a live platform/provider acceptance item.
- A standard v0.2 schema-field change requires a separately governed compatibility decision; namespaced extensions remain permitted under existing contracts.
- An unavailable provider, platform, entitlement or legally publishable fixture may close only the affected task as documented `blocked` with executable anti-claim evidence.
- ACX-38 excludes every target, blocked or unmapped capability from release claims.
- ACX-10 remains `deferred`; the post-v0.2 program includes no WoodFraming or consumer work.

Promotion note: ACX-23 historically closed the v0.2 line with no successor. The separately accepted ACXD-031 post-v0.2 program now promotes ACX-24; this does not alter ACX-23 evidence or `v0.2.0` claims.

ACX-24 completion resolution: exact `linux/arm64` and `linux/amd64` OCI targets for the reviewed Tesseract, OCP/OCCT and LibreDWG providers passed six live positive executions, cross-architecture canonical/artifact equality, fourteen architecture-specific adversarial outcomes, digest/package-lock corpus validation, full local gates and exact-SHA CI on Ubuntu, macOS and Windows. `sandbox.oci-multiarch` is public `partial`; native macOS/Windows, other architectures/providers, automatic acquisition, remote execution and image signing remain explicit residuals. Only ACX-25 is promoted.

ACX-25 execution cut: ACXD-033 and `docs/specs/provider-local-enforcement-v03-profile.md` evaluate native Linux, macOS and Windows independently. No draft-1 profile is admissible: each must produce a complete deterministic report and reject before workspace creation or provider launch. This is an executable `unsupported` outcome, not successful sandbox evidence. ACX-26 remains `pending`.

ACX-25 completion resolution: `linux-native-v1`, `macos-app-sandbox-v1` and `windows-appcontainer-job-v1` each publish a deterministic complete 16-axis rejection report and fail before workspace creation or provider launch. The digest-bound ten-case attack corpus, wheel/sdist restricted-binary scan, full local gates and exact-SHA CI on Ubuntu, macOS and Windows passed. `sandbox.local-enforcement` is public `unsupported`; no native profile, dependency, broker, decoder or positive execution claim was admitted. Only ACX-26 is promoted to `pending-next` and MUST NOT execute without a new continuation request.

ACX-26 execution cut: ACXD-034 and `docs/specs/provider-remote-v03-profile.md` select only `remote-https-spki-v1` with explicit invocation consent, exact registered origin/SPKI identity, fixed route, no redirects/proxies/ambient credentials/trust store/clock/discovery, bounded canonical envelopes and deterministic retry/replay. The public ceiling is protocol `partial` backed by repository-owned loopback TLS; third-party service availability, semantics, deletion, jurisdiction and provider-side sandboxing remain non-claims. ACX-27 remains `pending`.

ACX-26 delivery authority correction: the repository owner confirmed GitHub, not OneDev, is the delivery authority for this project. The configured `origin` and authenticated `gh` account are admissible. GitHub reports no branch protection and no repository rulesets for `main`, so the enforceable review requirement is zero external approvals; closure still requires a non-draft PR, explicit diff/check review, successful required CI and squash merge. ACX-26 remains `in_progress`, its claim remains `target`, and ACX-27 remains `pending` until that GitHub delivery is verifiably complete.
