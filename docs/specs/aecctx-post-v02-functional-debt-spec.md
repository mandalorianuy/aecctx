# AECCTX Post-v0.2 Functional Debt Specification

Version: `0.3.0-draft.1`
Date: 2026-07-13
Status: Approved design; normative planning authority; no implementation claim
Decision authority: ACXD-031

## 1. Purpose

This specification converts every material residual published with AECCTX `0.2.0` into a bounded functional outcome, executable non-claim or explicit external blocker. It governs the future ACX-24 through ACX-38 line without changing the immutable `v0.2.0` release or its claim registry.

The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT and MAY are normative for subordinate plans and implementation work.

## 2. Fixed boundaries

- AECCTX remains application-agnostic and MUST NOT depend on WoodFraming, `WFDomain`, `WFImport` or another consumer ontology.
- Extraction, neutral interpretation, provider inference, derived projections and consumer mapping remain separate layers.
- JSON, JSONL, source bytes and content-addressed artifacts remain authoritative. Markdown and plugin prose remain projections.
- `unknown`, `unsupported`, `conflicted`, `explicit_null` and `not_applicable` MUST remain explicit. No task may create a plausible default to improve apparent coverage.
- Core validation, package I/O, query, diff and context generation remain offline and usable without an LLM.
- Every source, archive, parser output, provider response, policy, trust document and generated artifact is untrusted data.
- Native, GPL, commercial and network-backed decoders remain outside the Apache-2.0 core dependency graph and require an accepted provider profile.
- Source write-back, engineering approval, regulatory certification and consumer canonical acceptance remain outside this line.
- ACX-10 remains deferred. Nothing in ACX-24 through ACX-38 authorizes WoodFraming integration.

## 3. Program strategy and prioritization

The program is dependency-first. Priority uses three ordinal scores from 1 through 5:

- `dependency`: how many later outcomes require the task;
- `risk`: combined security, licensing, provider and semantic risk;
- `value`: expected functional value to public AECCTX users.

Sequence is determined first by dependency, then risk reduction, then value. A lower-scoring task may not borrow scope from a later task.

| Task | Functional outcome | Dependency | Risk | Value | Claim ceiling |
|---|---|---:|---:|---:|---|
| ACX-24 | live OCI providers on Linux arm64 and amd64 | 5 | 4 | 5 | exact-profile `partial` |
| ACX-25 | additional reviewed local enforcement profiles | 5 | 5 | 4 | per-platform `partial` or executable `unsupported` |
| ACX-26 | optional remote/customer-managed provider protocol | 5 | 5 | 4 | protocol `partial`; no service availability claim |
| ACX-27 | expanded IFC 2D and georeferencing | 3 | 3 | 5 | per-schema/item/operation `partial` |
| ACX-28 | expanded DXF semantics and geometry | 3 | 4 | 5 | per-release/entity `partial` |
| ACX-29 | multilingual and layout-aware OCR | 3 | 3 | 4 | exact-runtime `partial` or `experimental partial` |
| ACX-30 | bounded vision and reconstruction hypotheses | 4 | 5 | 4 | inference `experimental partial`; hidden source geometry `unsupported` |
| ACX-31 | mesh CRS and coordinate qualification | 2 | 4 | 4 | per-format/registry `partial` |
| ACX-32 | STEP/IGES XDE and fidelity expansion | 4 | 4 | 4 | per-schema/kernel/runtime `partial` |
| ACX-33 | DWG version and geometry expansion | 5 | 5 | 4 | per-version/provider `partial` |
| ACX-34 | RVT reopening through one admissible provider | 5 | 5 | 5 | exact `partial` or documented `blocked`/`unsupported` |
| ACX-35 | advanced signing and trust profiles | 2 | 5 | 3 | separate-profile `partial` |
| ACX-36 | expanded IDS and delivery gate | 2 | 4 | 4 | bounded IDS `partial` |
| ACX-37 | inspector distribution and host portability | 2 | 3 | 3 | per-host/distribution `partial` |
| ACX-38 | aggregate conformance and release | 5 | 4 | 5 | only previously accepted claims |

Only ACX-24 may become `pending-next` when the subordinate implementation plan is accepted. All later tasks remain `pending` until promoted by the preceding closure.

## 4. Common claim lifecycle

The release-governance states remain `target`, `experimental`, `public` and `blocked`. Emitted package support remains `full`, `partial`, `opaque` or `unsupported`.

Every positive public claim MUST bind:

- one stable claim ID and exact profile ID;
- source/profile versions and configuration digest;
- dependency, provider and runtime versions;
- platform and architecture scope;
- fixture IDs and hashes;
- conformance test IDs;
- evidence document;
- support ceiling and structured exclusions.

Replay proves deterministic mapping for recorded provider bytes. It MUST NOT prove live provider availability, isolation, architecture portability, network behavior, entitlement or semantic correctness beyond the recorded corpus.

## 5. Common Definition of Ready

An owning task MUST NOT move to `in_progress` until:

1. all earlier non-deferred tasks are `completed` or documented `blocked`;
2. normative sections, decision owners and exact non-scope are named;
3. official APIs, versions, licenses, distribution posture and security history are reviewed;
4. claimed providers and enforcement axes are available, or the task is explicitly a provider-selection gate;
5. positive, degraded, negative and adversarial fixtures are identified with publication rights;
6. target claim IDs, profile IDs, platform scope and ceilings are written;
7. focused tests, corpus checker and final repository gates are named;
8. no open decision can silently change the result.

## 6. Common Definition of Done

Completion requires:

1. a usable SDK/CLI or provider result, not documentation or scaffolding alone;
2. failing conformance tests written before claim-producing implementation;
3. legally publishable positive, degraded, negative and adversarial fixtures;
4. deterministic bytes or an explicit reproducibility class with request/response hashes;
5. structured capability/loss reports and stable diagnostics for every non-full path;
6. resource, path, process-tree, archive, malformed-output and hostile-metadata tests appropriate to the boundary;
7. dependency, license, redistribution, privacy, telemetry, retention and platform evidence;
8. clean-core installation without optional or restricted dependencies;
9. one-to-one claim, fixture, test and evidence mapping;
10. `python3 scripts/check_spec_contract.py`, focused tests, `./scripts/verify_portable.sh` and `./scripts/verify.sh` passing;
11. exact-SHA CI on every claimed platform before publication;
12. evidence that WoodFraming and consumer mappings were not modified or introduced.

## 7. ACX-24: Multi-architecture OCI provider execution

### Functional result

The existing OCR, STEP/IGES and DWG providers execute live under `oci-docker-v1` on Linux arm64 and Linux amd64. For identical source/configuration/provider versions, both architectures emit semantically identical ordered events, capability/loss reports and derived artifact content, except for explicitly normalized runtime-attestation architecture fields.

### Required fixtures

- the existing ACX-15 English OCR image/PDF inputs;
- the four ACX-17 STEP/IGES inputs;
- the ACX-18 AC1015 DWG input;
- wrong-architecture manifest, missing image, digest drift and runtime-unavailable cases;
- timeout, process-tree, memory, output-limit and hostile-response cases on both architectures.

### Gates and non-claims

- Each architecture uses a separately digest-pinned image and records build inputs, package locks, licenses and reproducibility evidence.
- Live execution MUST pass the complete ACX-12 enforcement-axis suite; replay alone cannot close ACX-24.
- ARM/AMD output differences that alter evidence semantics or artifact hashes block promotion until governed.
- This task adds no format vocabulary and does not claim native Windows/macOS execution.

## 8. ACX-25: Additional local enforcement profiles

### Functional result

Restricted providers can execute through additional local profiles only where filesystem, user, process, network, CPU, memory, wall-time, child-process, output and cleanup limits are enforced and tested. Every evaluated but inadmissible platform has a deterministic executable rejection and a machine-readable enforcement report.

### Required fixtures

- reference provider success for each claimed platform/profile;
- filesystem escape, environment leak, network attempt, child-process tree, memory/CPU exhaustion, timeout and cleanup attacks;
- unavailable or unenforceable axis cases;
- core wheel and sdist scans proving provider separation.

### Gates and non-claims

- Native Linux, macOS and Windows are independent claim profiles; success on one does not imply another.
- A descriptor declaration is not enforcement evidence.
- GPL/commercial provider execution additionally requires the owning decoder's entitlement and redistribution evidence.
- A platform with an unenforceable required axis remains `unsupported`; best-effort subprocess isolation is prohibited.

## 9. ACX-26: Optional remote and customer-managed providers

### Functional result

AECCTX can invoke an explicitly registered remote/customer-managed provider through a closed, content-addressed protocol with caller consent, allowlisted endpoint identity, bounded request/response bytes, timeout/retry/rate limits, response attestation and deterministic replay. Core operations remain network-free.

### Required fixtures

- repository-owned loopback reference provider with success, degraded and unavailable outcomes;
- endpoint mismatch, TLS/auth failure, redirect, retry exhaustion, timeout, oversized output, malformed attestation and replay drift;
- redaction, upload-denied, retention-disclosure and jurisdiction-policy failures;
- network-disabled core-install tests.

### Gates and non-claims

- Endpoint, credentials, billing consent, upload consent, retention, region/jurisdiction and telemetry policy are explicit caller inputs or governed deployment configuration.
- No credential may enter a package, diagnostic or fixture.
- The reference provider proves protocol behavior, not availability or fitness of a third-party service.
- No remote provider is required for validation, query, diff, context or opaque ingest.

## 10. ACX-27: IFC expansion

### Functional result

The IFC adapter preserves additional source-native 2D curves, annotations, text, hatches/styles and selected later schema profiles, plus selected georeferencing operations not covered by ACX-13. Every supported item retains source representation/context identity and every complete transform is reversible.

### Required fixtures

- project-authored files for each claimed schema/item/operation combination;
- absent, empty, unsupported, failed, multiple, non-invertible and conflicted operations;
- arcs, conics, trimmed/composite curves, text/style and mapped-item adversarial cases;
- unit conflict, missing CRS, false EPSG cue and large-coordinate cases.

### Gates and non-claims

- A 3D projection never becomes source-native 2D.
- IFC2X3 property-set georeferencing is claimed only for explicitly tested property paths.
- Later schemas remain unclaimed unless both parsing and semantic conformance pass.
- No EPSG, scale, rotation, elevation or operation is inferred from convention.

## 11. ACX-28: DXF expansion

### Functional result

The DXF adapter preserves selected additional releases, curves, surfaces and semantic objects. Optional external references are traversed only from an explicit content-addressed source bundle with cycle/depth/size controls. ACIS/SAT/SAB content is interpreted only through a separately reviewed kernel provider.

### Required fixtures

- project-authored ASCII/binary fixtures for each release/entity family;
- curved and surface geometry with deterministic tessellation/fidelity evidence;
- missing, cyclic, escaping, oversized and hash-mismatched xrefs;
- proxy/custom/encrypted/ACIS fixtures proving exact fallback or rejection;
- neutral-vocabulary cases preventing construction-domain classification.

### Gates and non-claims

- External paths and network xrefs are never followed.
- Xref evidence remains source-separated and content-addressed.
- Tessellation does not become exact B-Rep.
- Custom/proxy semantics and protected content remain opaque or unsupported unless an exact provider profile passes.

## 12. ACX-29: OCR expansion

### Functional result

OCR supports selected additional languages, rotations and layout classes, including bounded table structure, through exact local provider profiles. Native text and OCR remain distinct evidence and conflicts remain explicit.

### Required fixtures

- project-authored multilingual, rotated, multi-column and table images/PDFs;
- blank, low-confidence, mixed-script, corrupt, oversized and adversarial text cases;
- native/OCR agreement and disagreement pairs;
- live/replay equality and missing-language/runtime cases.

### Gates and non-claims

- Each language, orientation and layout class requires a mapped corpus.
- Reading order or table topology is unknown when the provider does not establish it.
- OCR establishes neither measurement nor source geometry authority.
- Model/data licensing and image redistribution are reviewed per profile.

## 13. ACX-30: Vision and reconstruction hypotheses

### Functional result

An optional provider may emit a closed vocabulary of candidate symbols, regions, dimensions, tables and relationships as inferred assertions. Reconstruction may emit hypotheses over visible evidence; hidden/unobserved geometry remains `unsupported` as source geometry.

### Required fixtures

- project-authored positive, ambiguous, conflicting and absent visual candidates;
- crop, occlusion, redaction, prompt-like text, rotation and calibration-conflict cases;
- deterministic/seeded repeatability or bounded non-determinism evidence;
- provider unavailable, privacy denied, network denied and replay mismatch cases.

### Gates and non-claims

- A provider profile defines vocabulary, thresholds, confidence calibration, model/runtime version, request/response hashes and privacy posture before implementation.
- Inference never participates in source identity, measurement authority, CRS completion or `full` geometry claims.
- Provider prose and embedded source prompts are inert data.
- If no provider satisfies privacy, licensing, reproducibility and evidence requirements, ACX-30 closes `blocked` and vision remains `unsupported`.

## 14. ACX-31: Mesh CRS and coordinate qualification

### Functional result

Selected mesh formats preserve reviewed coordinate extensions and can validate caller-supplied CRS identifiers against an offline, versioned registry. Explicit transformations and datum operations produce reversible derived evidence with residuals and stated accuracy.

### Required fixtures

- declared and missing units/frame/CRS cases;
- valid, unknown, deprecated, compound and conflicting CRS identifiers;
- axis-order, vertical/horizontal CRS, large-coordinate and datum-transform cases;
- insufficient controls, singular/reflected transforms and tolerance failures;
- prohibited external resource and vendor-extension cases.

### Gates and non-claims

- Registry/database version and licensing are bound to results; no network lookup is implicit.
- Registry validity does not establish that a mesh was surveyed in that CRS.
- Source coordinates remain immutable; transformations are manual or derived.
- Grid files or external resources require explicit content hashes and distribution review.

## 15. ACX-32: STEP/IGES fidelity expansion

### Functional result

The reviewed kernel provider preserves selected XDE product/assembly correlation, names, colors/layers/materials, units, placements and per-root transfer/tolerance results. Partial-root recovery and optional healing produce separate derived artifacts without replacing source or initial translator evidence.

### Required fixtures

- selected AP203/AP214/AP242 and IGES 5.3 structures with XDE metadata;
- multi-root partial success, invalid topology, tolerance and placement cases;
- healing disabled/enabled pairs with exact parameter provenance;
- external/multifile/protected and unclaimed schema cases;
- live arm64/amd64 and replay equivalence.

### Gates and non-claims

- Source lexical graph, translator BREP, healed BREP and tessellation remain distinct.
- Source-exact BREP is not claimed from kernel translation.
- Every schema/kernel/runtime/platform combination is independently bounded.
- Partial recovery cannot silently turn session completeness into `full`.

## 16. ACX-33: DWG expansion

### Functional result

The external DWG provider supports selected additional DWG versions, qualified units, bounded 3D geometry and explicit content-addressed xrefs. Direct decoder evidence and converted DXF/geometry remain separate.

### Required fixtures

- project-authored DWG files for each claimed version/profile;
- units, 3D, xref, duplicate-handle and conversion-loss cases;
- encrypted/protected, proxy/custom, ACIS, corrupt and wrong-version cases;
- live arm64/amd64 and replay equality;
- malicious decoder-output and writer-disable tests.

### Gates and non-claims

- Exact decoder version, GPL/commercial posture and security history are reviewed.
- Writer operations remain unreachable from provider requests.
- Xrefs use explicit bounded bundles; filesystem/network traversal is prohibited.
- Complete 3D, ACIS and custom semantics remain unsupported unless separately proven.

## 17. ACX-34: RVT reopening

### Functional result

ACX-34 selects exactly one admissible route: licensed local runtime or approved remote service. Only after entitlement, sandbox/network, CI, fixture, privacy, retention, jurisdiction and lifecycle gates pass may neutral RVT extraction be implemented. Otherwise the task renews the executable blocked boundary without adding adapter scaffolding.

### Required fixtures

- at least one legally publishable real RVT positive file for a selected exact version;
- degraded, unsupported-version, linked-document, corrupt and resource-abuse cases;
- classes/properties/relations/views/geometry/units/coordinates appropriate to the selected profile;
- provider unavailable and entitlement/consent failure cases;
- opaque fallback and anti-claim regression fixtures.

### Gates and non-claims

- A human authorizes one route and supplies the evidence required by ACXD-030 before decoder code.
- Trial/customer/proprietary fixtures cannot be the sole public conformance evidence.
- IFC conversion is converter-derived evidence, not native RVT extraction.
- No WoodFraming or consumer classification enters the provider or neutral mapping.

## 18. ACX-35: Advanced signing and trust

### Functional result

X.509 identity, revocation evidence, trusted timestamping and multi-party signing are separate optional profiles over the existing deterministic statement. Each profile produces machine-distinct integrity, cryptographic, lifecycle, trust, authorization and archival-time results.

### Required fixtures

- project-generated test PKI with valid, expired, revoked, unknown and rotated chains;
- offline CRL/OCSP-response and timestamp-token fixtures when selected;
- multiple independent signatures and explicit countersignature semantics;
- mutation, algorithm confusion, chain/path, stale-status and hostile-control cases;
- operation without optional trust dependencies.

### Gates and non-claims

- No network discovery or host trust store is implicit.
- Online status retrieval, if selected, uses ACX-26 and explicit policy/consent.
- Timestamp validity, signer trust and organizational authorization remain separate.
- Core does not generate, store, rotate or select production keys.

## 19. ACX-36: IDS and delivery-gate expansion

### Functional result

The quality gate evaluates selected additional IDS 1.0 facets, restrictions and cardinalities through a pinned official implementation, while preserving deterministic AECCTX policy outcomes and exact evidence references.

### Required fixtures

- unchanged official cases plus project-authored positive/negative pairs for every claimed combination;
- `partOf`, restriction/range/pattern/enumeration and cardinality profiles selected by the owning decision;
- unsupported URI/bSDD, geometry, quantity and remote-lookup cases;
- malicious XML, worker timeout/crash/output and missing-extra cases;
- result/Markdown/CI projection parity.

### Gates and non-claims

- An IDS pass remains information-requirement conformance, not engineering approval.
- URI/bSDD or remote lookup is unsupported unless separately governed through ACX-26.
- Unsupported facets fail closed or require review; they never pass silently.
- Official fixtures remain unchanged and separately licensed.

## 20. ACX-37: Inspector distribution and host portability

### Functional result

The inspector is packaged as a reproducible, integrity-bound optional distribution and verified against enumerated compatible local hosts. Installation, upgrade and uninstall preserve exact inventory and core independence.

### Required fixtures

- compatible/incompatible core, MCP and host version matrices;
- signed/checksummed distribution mutation and downgrade cases;
- install, upgrade, rollback and exact uninstall cases;
- prompt-injection and result-parity corpus across supported hosts;
- offline core behavior without the plugin.

### Gates and non-claims

- The plugin introduces no unique validation, query, diff, gate or claim semantics.
- Marketplace publication requires separate external authorization and registry evidence.
- Universal model or third-party-host behavior is not inferred from one tested host.
- Native/GPL/commercial decoder execution continues through provider contracts, never plugin shell tools.

## 21. ACX-38: Aggregate conformance and release

### Functional result

ACX-38 builds a digest-bound aggregate corpus, clean-install matrix, reproducible artifacts, SBOM, checksums, compatibility/migration notes and exact-SHA release candidate for the accepted post-v0.2 claims.

### Required fixtures and gates

- every completed or documented-blocked ACX-24 through ACX-37 outcome;
- all retained v0.1/v0.2 compatibility and anti-claim fixtures;
- clean core and optional-extra installations;
- deterministic wheel, sdist, plugin and provider metadata;
- restricted dependency/artifact and consumer-boundary scans;
- supported platform/provider CI and immutable release verification.

ACX-38 MUST exclude targets, blocked capabilities, replay-only availability and unmapped fixtures from public claims. A `0.3.0` tag is authorized only after all release gates pass; the version number does not itself imply `1.0` stability.

## 22. Residual traceability

| Published residual | Owning outcome |
|---|---|
| OCI providers limited to Linux arm64 | ACX-24 |
| native Linux/macOS/Windows sandbox unsupported | ACX-25 |
| network/commercial/customer-managed provider governance | ACX-26 |
| IFC later schemas, curves, annotations, styles and georeferencing variants | ACX-27 |
| DXF releases, curves/surfaces, xrefs, ACIS/proxy/custom content | ACX-28 |
| OCR languages, rotation, complex layouts and tables | ACX-29 |
| vision vocabulary/provider and reconstruction hypotheses | ACX-30 |
| hidden/unobserved source geometry | ACX-30 executable unsupported boundary |
| mesh coordinate extensions, CRS lookup and datum operations | ACX-31 |
| mesh survey authority and unit guessing | ACX-31 executable non-claim |
| STEP/IGES XDE, styles, units, placements, recovery and healing | ACX-32 |
| DWG versions, xrefs, units, 3D and exact provider limits | ACX-33 |
| RVT provider, entitlement and real semantic extraction | ACX-34 |
| X.509, revocation, timestamps, countersigning and archival trust | ACX-35 |
| additional IDS facets/cardinalities and remote vocabularies | ACX-36 |
| plugin marketplace and third-party-host portability | ACX-37 |
| aggregate compatibility, packaging and release | ACX-38 |

No residual may be removed from the capability matrix merely because its task executed. Removal or narrowing requires a passing claim mapping or an explicit durable non-claim.

## 23. What does not count as progress

The following cannot satisfy an acceptance item or promote a claim:

- documentation, schemas, descriptors or directory scaffolding without executable conformance;
- a mock provider presented as a real decoder or external service;
- replay presented as live provider, platform, sandbox or entitlement proof;
- a locally built image without bound build inputs, dependency/license record and immutable digest;
- an unavailable provider, skipped live test or green portable test used as live evidence;
- proprietary fixtures that cannot be published as the sole support corpus;
- generated Markdown, plugin prose or screenshots used as record authority;
- happy-path tests without degraded, negative and adversarial cases;
- hidden geometry, CRS, units, identity, trust or approval inferred from convention;
- a blocked task counted as implemented capability;
- consumer integration, WoodFraming work or unrelated cleanup.

## 24. Planning and execution handoff

The subordinate implementation plan MUST:

- add ACX-24 through ACX-38 to the single governed ledger;
- promote only ACX-24 to `pending-next`;
- keep ACX-25 through ACX-38 `pending` and ACX-10 `deferred`;
- provide task-specific DoR, DoD, fixtures, claim IDs, tests, security/license/provider gates and evidence paths;
- require explicit promotion after each completed or documented-blocked task;
- forbid implementation of ACX-24 until the plan is reviewed and accepted.

This specification authorizes planning only. It does not authorize provider builds, dependency changes, fixture generation, schema changes, implementation, claims, tags or releases.
