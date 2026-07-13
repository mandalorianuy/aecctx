# AECCTX Decision Log

Date: 2026-07-13
Status: Active

## Accepted decisions

### ACXD-001: Separate public repository

- Decision: AECCTX is application-agnostic and lives independently from WoodFraming.
- Consequence: Consumer ontologies, workflows, approvals, and canonical mutations stay outside this repository.

### ACXD-002: Markdown is a projection

- Decision: JSON/JSONL records and referenced binary/vector artifacts are authoritative. Markdown is deterministically generated navigation and context.
- Consequence: No geometry, identity, provenance, confidence, or diagnostic claim may exist only in Markdown.

### ACXD-003: Evidence precedes interpretation

- Decision: Source evidence, normalized interpretation, and consumer mapping are distinct layers.
- Consequence: An adapter may extract a DXF line or IFC class but cannot claim it is a consumer-domain wall without a separate mapping authority.

### ACXD-004: Honest universal ingestion

- Decision: Every file may be registered, fingerprinted, and diagnosed, but adapters declare `full`, `partial`, `opaque`, or `unsupported` support per capability.
- Consequence: “Any file” means no silent rejection or loss, not perfect semantic conversion of every proprietary format.

### ACXD-005: Deterministic local-first core

- Decision: Core ingest, validation, query, diff, and context generation require neither network access nor an LLM.
- Consequence: Network and inference providers are optional, explicit plugins whose outputs carry provider provenance.

### ACXD-006: Python reference implementation

- Decision: The initial CLI and SDK target Python 3.12+, with JSON Schema as the cross-language contract.
- Consequence: Swift and TypeScript consumers may generate or implement bindings without making Python runtime authority part of the format.

### ACXD-007: Adapter licensing boundary

- Decision: The core is Apache-2.0. GPL and commercial decoders run behind optional process/plugin boundaries and are not bundled by default.
- Consequence: Direct DWG/RVT claims require adapter-specific licensing, execution, version, determinism, and evidence-preservation review.

### ACXD-008: Read-oriented v0.1

- Decision: v0.1 compiles and reads source context; it does not promise write-back to authoring formats.
- Consequence: Agent modifications target future reviewed patch contracts, not source files or generated Markdown in v0.1.

### ACXD-009: Builder baseline posture

- Decision: The repository consumes `baseline-shared-v1` using the `builder` specialization profile.
- Consequence: Shared shell governance remains baseline-owned and repository policy extends it only through the managed overlay and project instructions.

### ACXD-010: Open project vocabulary with external classifications

- Decision: v0.1 uses a small, versioned project registry for compact `aecctx:` neutral kinds and relation types, while allowing optional stable external classification URIs and explicit unregistered extension terms.
- Consequence: The registry improves deterministic query/context behavior without becoming a universal or consumer ontology. `original_class` remains mandatory evidence and registry membership never implies downstream acceptance.
- Evidence: `schemas/v0.1/neutral-vocabulary.json` and ACX-03 record/query conformance tests.

### ACXD-012: Source embedding policy defaults

- Decision: Generated packages default to `external`; `embedded` and `redacted` retention require an explicit caller policy.
- Consequence: Opaque ingest never copies untrusted source bytes into a package implicitly. Every policy remains recorded with the exact source hash, and embedded content is inventoried as authoritative source evidence.
- Evidence: ACX-02 conformance tests cover all policies, streaming hashing, deterministic package identity, and explicit embedding.

### ACXD-011: Package signing deferred beyond v0.1

- Decision: v0.1 standardizes SHA-256 artifact integrity and the logical package digest, but does not standardize or claim package authenticity.
- Consequence: Detached signatures may be carried only as optional namespaced extensions that do not alter v0.1 conformance. A future signing contract must decide canonical signed bytes, algorithm agility, key identity/distribution, revocation and trust policy before authenticity claims are allowed.
- Evidence: ACX-02/ACX-07 deterministic digest tests and ACX-08 security review show stable integrity inputs but no governed trust/key lifecycle.

### ACXD-013: Capability expansion does not revise v0.1 claims

- Decision: Post-v0.1 gaps are governed by `docs/specs/aecctx-capability-expansion-spec.md` as targets. They remain partial or unsupported until their owning task publishes conformance evidence and updates the capability matrix.
- Consequence: Planning, experimental code, or an optional dependency cannot silently promote a public support claim.

### ACXD-014: External sandbox precedes restricted decoders

- Decision: Native, GPL, commercial, and network-backed decoders require a separately reviewed external sandbox provider contract before adapter implementation. The built-in Python worker is not sufficient merely because it is process-isolated.
- Consequence: ACX-12 is a prerequisite for STEP/IGES kernels that cannot use the permissive path and for all DWG/RVT provider work. Caller-provided commands remain prohibited.

### ACXD-015: Hidden geometry is not extractable evidence

- Decision: Geometry absent from observable source bytes or pixels remains `unsupported` as source geometry. Optional reconstruction may exist only as an inference hypothesis with provider provenance, confidence, visible-evidence citations, and no measurement or completeness authority.
- Consequence: OCR/vision work cannot turn plausible reconstruction into a `full` geometry claim.

### ACXD-016: Calibration augments but never rewrites source coordinates

- Decision: Caller-supplied mesh units, control points, transforms, or CRS are manual/derived assertions. Original coordinates and unknown/conflicted states remain preserved.
- Consequence: A calibrated artifact may become usable in a declared coordinate frame without falsifying what the source itself declared.

### ACXD-017: v0.2 schema and compatibility boundary

- Decision: Shared observation/inference, coordinate-qualification, representation-fidelity, provider-attestation, and required-extension semantics are versioned in new `schemas/v0.2` package and record schemas. A v0.2 package uses `aecctx_version = "0.2.0"` and `record_version = "0.2"`; v0.1 schemas and packages remain immutable.
- Fidelity extension: `representation_fidelity.class = "converted"` is a shared v0.2 derived class for a format conversion that preserves evidence lineage but is neither source-exact nor necessarily a projection, tessellation, rasterization, preview or inference. It requires `derived = true` and explicit source representation parents. ACX-18 is its first governed use for DWG-to-DXF evidence.
- Compatibility: The v0.2 reference reader validates both v0.1 and v0.2 packages. A v0.1 reader is not required to accept v0.2. Optional namespaced extensions may be ignored while reading but remain part of package bytes; every declared required extension must be supported or validation fails with a stable diagnostic. Records within one package use the record version selected by its manifest.
- Query/diff/context: Shared v0.2 fields are authoritative structured record fields and remain queryable and diffable as normal JSON. Diff reports a record change when those fields change; context may project them but never becomes their authority. Cross-version comparison is allowed after both packages validate and reports the manifest version change explicitly.
- Consequence: Later capabilities share one typed v0.2 substrate instead of encoding normative semantics as loosely governed v0.1 extensions. Existing v0.1 package identity, query, diff, context, validation and conformance behavior remain stable.
- Evidence: `schemas/v0.2/`, `fixtures/v0.2/shared/minimal-v02`, `conformance/v0.2/claims.json`, `docs/compatibility-v0.2.md`, and `docs/evidence/ACX-11.md`.

### ACXD-018: Detached JWS Ed25519 signing and offline verifier trust

- Statement decision: Sign a canonical `https://aecctx.dev/signing/v1` JSON statement containing package/version identity, logical digest, required extensions and SHA-256 of the canonical semantic manifest. The semantic manifest removes only `package_form`; every other manifest field remains bound so directory/ZIP repackaging is neutral without making semantic mutation invisible.
- Envelope decision: Use detached JWS General JSON Serialization in an explicit sidecar. The payload is omitted and reconstructed from the validated package. Each protected header carries the collision-resistant `https://aecctx.dev/jws/statement-sha256` value so a foreign-package binding mismatch remains distinct from a corrupt signature. Signatures are independent and deterministically ordered; unprotected/unknown headers, embedded/remote keys and duplicate `kid` values are rejected. Countersignatures remain unsupported.
- Algorithm decision: Profile v1 permits only the fully specified JOSE `Ed25519` identifier. Algorithm agility requires a profile revision and conformance; the older polymorphic `EdDSA` and all unreviewed algorithms are rejected. PyCA `cryptography>=45,<50` is an optional signing extra, not a core dependency.
- Identity/trust decision: The verifier explicitly supplies an offline candidate-key registry and a separate trust policy with verification time, trust allowlists, required scopes and signature threshold. Cryptographic validity, identity resolution, key lifecycle (`valid`, `not_yet_valid`, `expired`, `revoked`, `unknown_status`, `not_evaluated`), administrator trust and authorization are independent machine fields. `not_evaluated` is limited to a missing resolved key or policy time and cannot replace an evaluated unknown revocation state. No key generation, discovery, network, host clock or trust selection is implicit.
- Compatibility and claim decision: Unsigned v0.1/v0.2 packages remain valid. Signing never mutates package bytes or logical identity. Acceptance of this design authorizes ACX-20 implementation but does not promote authenticity from `unsupported` until conformance and all gates pass.
- Evidence owner: `docs/specs/signing-v1-profile.md`, `docs/security/signing-threat-model.md`, ACX-20 schemas/corpus/tests and `docs/evidence/ACX-20.md`.

### ACXD-021: Quality gates express policy conformance only

- Decision: The AEC Delivery Quality Gate evaluates versioned policies over authoritative AECCTX records, capabilities, loss, diagnostics, diffs, and bounded IDS requirements. Its `pass` result is not engineering approval, regulatory acceptance, construction readiness, or consumer canonical acceptance.
- Consequence: Gate results remain reproducible evidence with explicit `pass`, `fail`, `requires_review`, and `error` outcomes; unresolved states cannot be silently defaulted into success.

### ACXD-022: Codex plugin is an optional orchestration surface

- Decision: `aecctx-inspector` packages focused skills and allowlisted MCP access over stable AECCTX library/CLI behavior. It introduces no unique package semantics and keeps v0.2 MCP inspection read-only.
- Consequence: AECCTX remains usable without Codex or an LLM, source content remains untrusted data, and plugin responses cannot elevate Markdown, inference, or presentation above structured evidence and policy results.

### ACXD-023: Deterministic quality-gate policy and bounded IDS 1.0 profile

- Policy decision: ACX-21 uses the closed `https://aecctx.dev/gate/v1` canonical JSON policy, check, waiver and result model in `docs/specs/quality-gate-v02-profile.md`. Stable system checks cannot be disabled or waived. Policy checks use exact IDs, kinds, severities and explicit failure modes; every non-known value state has an explicit `allow`, `requires_review` or `fail` action.
- Outcome decision: check states are `pass`, `fail`, `requires_review`, `waived` and `error`; aggregate precedence is error, fail, review/waived, pass. CLI exits are 0 for pass, 1 for completed fail/review and 2 for error. JSON remains authority; Markdown and CI annotations are projections.
- Waiver decision: a waiver binds one canonical finding fingerprint and explicit lifecycle at policy-owned `evaluation_time`. An active waiver preserves evidence and forces at least `requires_review`; it cannot create pass, target a system check or imply engineering/consumer approval.
- IDS implementation decision: select optional `ifctester==0.8.5` with `ifcopenshell==0.8.5`, both LGPL-3.0-or-later and outside core dependencies. A fixed bounded local worker maps deterministic library state directly and does not use the host-time-bearing IfcTester JSON reporter.
- IDS scope: buildingSMART IDS v1.0.0 final commit `1effec6`, IFC2X3/IFC4 and only exact simple-value entity, attribute, classification, property and material facet/cardinality cases proven by unchanged official plus project-authored fixtures. `partOf`, restrictions/patterns/ranges/enumerations, URI/bSDD lookup, later/earlier IDS and unlisted IFC schemas remain unsupported.
- Source/evidence decision: IDS evaluation requires caller-supplied IDS and IFC files whose hashes match the policy and an authoritative candidate-package source record. Package storage references and IDS links are never followed. IDS results remain distinct from validation, integrity, geometry, provenance and baseline-diff checks.
- Compatibility and claim decision: acceptance of the design authorizes only `docs/plans/acx-21-implementation.md`. It does not implement the capability or promote its public `unsupported` state. ACX-21 remains `in_progress` until implementation, corpus, evidence, local/remote gates and exact claim mapping pass.
- Evidence owner: `docs/specs/quality-gate-v02-profile.md`, `docs/plans/acx-21-implementation.md`, future ACX-21 schemas/corpus/tests and `docs/evidence/ACX-21.md`.

### ACXD-024: External provider protocol and first enforcement profile

- Decision: ACX-12 uses a versioned JSON file protocol over a private content-addressed workspace. Callers select only an allowlisted `provider_id`; registrations own immutable launch targets, runtime roots, license/network posture, supported actions and enforcement claims. Provider output is schema-validated and hash-checked before it reaches package construction.
- Reference profile: The first executable enforcement profile is `oci-docker-v1`. It requires an allowlisted, digest-pinned image already present in a reviewed Docker-compatible runtime and launches with no network, read-only root filesystem, non-root user, dropped capabilities, `no-new-privileges`, bounded memory/CPU/PIDs/files, private tmpfs, read-only content-addressed input and a single bounded output mount. The runner never pulls an image implicitly.
- Rejected alternative: `macos-seatbelt-v1` remains unavailable for restricted decoders. Conformance showed that the Python runtime requires host-wide reads under Seatbelt and macOS does not provide a usable per-process address-space rlimit for this profile. Allowing broad host reads or silently omitting the memory axis would violate the contract.
- Portability: Protocol/schema/registry validation is portable. A host without a reviewed complete enforcement profile rejects execution with `AECCTX_PROVIDER_PROFILE_UNAVAILABLE`; it does not fall back to the in-process worker or an unconfined subprocess.
- Consequence: ACX-12 claims the digest-pinned Linux-container provider environment wherever the reviewed Docker runtime passes preflight. Native host profiles and Windows-container execution remain blocked by ACXB-001.
- Evidence owner: ACX-12 protocol schemas, Linux-container reference provider corpus, threat model, tests and acceptance evidence.

### ACXD-025: Bounded IFC v0.2 profile and opt-in emission

- Decision: ACX-13 implements only the source-native 2D and coordinate profiles enumerated in `docs/specs/ifc-v02-profile.md`, using optional `ifcopenshell==0.8.5`. Public fixtures/claims are limited to IFC2X3 TC1 and IFC4 Add2 TC1. A different IfcOpenShell version or later IFC family remains unclaimed until separately proven.
- 2D boundary: Only explicitly 2D contexts/views/identifiers and the listed polyline/indexed-line/geometric-curve-set/mapped-item profiles are normalized. Unsupported curves, text, hatch, styling and other items remain source evidence and structured loss; 3D projection can never be relabeled source-native.
- IfcOpenShell 0.8.5 mapped-2D limitation: `resolve_items()` does not yield a usable matrix for `IfcCartesianTransformationOperator2D`; ACX-13 therefore performs bounded structural extraction of the explicit mapping source/origin/target attributes for that operator only. Other mapped operators remain unsupported rather than falling back to 3D projection.
- Coordinate boundary: A complete global link requires one explicit IFC4 `IfcMapConversion` to one `IfcProjectedCRS`, finite/invertible WCS and operation matrices, explicit non-zero axes/positive scale, compatible declared project/map units and a non-empty source CRS name. IFC defaults, EPSG IDs or missing parameters are not synthesized for a public complete claim.
- Compatibility: `ingest_ifc()` remains v0.1 by default. ACX-13 behavior is explicitly selected with `aecctx_version="0.2.0"`; v0.1 fixture/package identity stays unchanged.
- Consequence: both IFC 2D and georeferencing remain public `partial` claims with exact schema/item/operation scope and explicit absent/empty/unsupported/failure/conflict states.
- Evidence owner: ACX-13 fixtures, claim mappings, deterministic SVG/replay tests and acceptance evidence.

### ACXD-026: Bounded DXF v0.2 profiles and opt-in emission

- Decision: ACX-14 implements only the source-semantic and bounded-3D profiles enumerated in `docs/specs/dxf-v02-profile.md`, using optional `ezdxf==1.4.4`. Public fixtures are limited to project-authored `AC1015` and `AC1032` ASCII/binary inputs; other releases or ezdxf versions remain unclaimed.
- Semantic boundary: source handles/owners, dictionaries, extension dictionaries, XDATA/application IDs, groups, attributes, materials, layouts/layers and block/insert structure remain source evidence. Normalization cites those records and never infers construction families from names or geometry.
- Geometry boundary: only the listed point/line/face/mesh/polyline and insert/OCS profiles are source-normalized. GLB/triangles are derived tessellation with explicit fidelity, transforms and loss. ACIS solids/surfaces, proxy/custom objects, xref traversal and encrypted/protected content remain raw/opaque/unsupported.
- Compatibility: `ingest_dxf()` remains v0.1 by default. ACX-14 behavior is explicitly selected with `aecctx_version="0.2.0"`; v0.1 fixture/package identity remains unchanged.
- Consequence: both DXF claims remain public `partial` claims bounded by exact releases, entities, dependency version and corpus evidence.
- Evidence owner: ACX-14 fixtures, claim mappings, deterministic replay, security/loss tests and acceptance evidence.

### ACXD-020: Optional inference provider profiles

- OCR decision: ACX-15 selects experimental `org.aecctx.ocr.tesseract-tsv@0.2.0`, bounded to Ubuntu Noble `tesseract-ocr=5.3.4-1build5`, its official C API loaded through Python `ctypes`, English data `1:4.1.0-2`, LSTM and PSM 6 under ACX-12 `oci-docker-v1`. OpenMP is fixed to one thread so the existing `pids=1` sandbox is preserved. It is local, deterministic for fixed bytes/config/runtime, network-disabled and emits `aecctx.ocr.words.v1` word evidence.
- Canonical raster decision: PDF/image adapters feed the provider a deterministic grayscale PGM made from decoded pixels. Provider input/region hashes bind that representation and provenance cites the observed parent raster. Encoded PNG/JPEG/TIFF bytes remain evidence but are not used as cross-platform OCR replay identity because decoder backends may reserialize equivalent pixels differently.
- Image verification: a locally built provider image may be registered by allowlisted tag only when registration also pins its inspected immutable Docker image ID. Preflight rejects an ID mismatch; it never pulls/builds or trusts a mutable tag alone. The original digest-addressed ACX-12 path remains valid.
- Replay/claim boundary: validated offline replay is portable conformance for protocol and mapping but does not prove provider runtime availability. OCR remains release-governance `experimental` until the exact image/provider/platform execution matrix is public and green.
- Vision decision: no vision or reconstruction provider is accepted in ACX-15. Those capabilities remain `unsupported`; hidden/unobserved geometry remains unsupported as source evidence under ACXD-015.
- Privacy/licensing: the selected runtime is local with no egress, telemetry or retention; Tesseract and selected English trained data are Apache-2.0. Pillow remains an isolated provider dependency under its own license. No inference dependency enters the Apache-2.0 core wheel.
- Evidence owner: ACX-15 provider descriptor/worker/build recipe, replay corpus, mapping/adversarial tests and acceptance evidence.

### ACXD-027: Bounded mesh coordinate qualification and similarity registration

- Format boundary: ACX-16 claims exact coordinate metadata only for self-contained OBJ/STL and glTF/GLB 2.0 through `trimesh==4.12.2`. OBJ/STL units, axes and CRS remain unknown. glTF 2.0 contributes meters and its normative right-handed `+Y`-up/`+Z`-forward frame, but no geographic CRS. Unit guessing and external-resource resolution are prohibited.
- Registration decision: explicit profiles support uniform scale, author-supplied invertible affine matrix, and control-point least-squares orientation-preserving similarity. Automatic affine/shear fitting and reflections are rejected. A source/manual unit or frame contradiction remains `conflicted` and emits no calibrated artifact.
- Authority boundary: original source vertices, faces, transforms and hash remain observed and immutable. Profile records are manual; calibrated GLB/records are derived and cite both manual and observed evidence. Target CRS identifiers are preserved as manual strings and do not imply survey, datum or EPSG validation authority.
- Compatibility: `ingest_geometry()` remains byte-identical v0.1 by default. The bounded profile requires explicit v0.2 SDK/CLI selection and an optional schema-validated profile.
- Evidence owner: ACX-16 schema, solver, geometry adapter, project-authored corpus, claim mapping and acceptance evidence.

### ACXD-028: Bounded STEP/IGES external OCP provider

- Kernel/provider: ACX-17 selects `org.aecctx.step-iges.ocp@0.2.0` using Python 3.12 and `cadquery-ocp==7.9.3.1.1` with bundled OCCT 7.9.3. OCP/OCCT is a native decoder and therefore runs only through the ACX-12 `oci-docker-v1` boundary; it never enters the core wheel or in-process extras.
- Format boundary: claims are limited to project-corpus STEP ISO 10303-21 `CONFIG_CONTROL_DESIGN`, `AUTOMOTIVE_DESIGN` with AP214 IS tuple `{ 1 0 10303 214 1 1 1 1 }`, `AP242_MANAGED_MODEL_BASED_3D_ENGINEERING_MIM_LF` with edition-1 tuple `{ 1 0 10303 442 1 1 4 }`, and the exact IGES 5.3 entity/form list in the normative profile. Whitespace is normalized only when matching edition tuples; the original `FILE_SCHEMA` string is retained. Other schemas, versions, external references, protected/compressed sets and proprietary extensions remain unclaimed/unsupported.
- Evidence boundary: source entities and locators remain observed. Kernel B-Rep is translator-derived and records fixed translator-processing loss; the provider emits bounded canonical triangle JSON and the core applies its existing `trimesh==4.12.2` deterministic convention to produce subordinate GLB. The completed experimental cut normalizes only direct STEP product/assembly records. Names, colors, layers, units, placements and IGES subfigure facts remain raw source records; XDE correlation, normalized styles/units/transforms, per-root tolerance summaries and partial-root recovery remain explicitly unsupported until a new governed corpus proves them. No source-exact B-Rep or consumer classification is claimed.
- Runtime/license: the initial live claim is exact Linux arm64 OCI plus portable offline replay. OCP bindings are Apache-2.0 and OCCT is LGPL-2.1 with exception. The image is operator-built, digest-pinned, network-disabled and not distributed by core; any image distribution requires the reviewed LGPL notices/source/relinking record. No entitlement, telemetry or service dependency exists.
- Lifecycle: a base image, architecture, provider, Python, OCP, OCCT, translator parameter or image digest change requires a new reviewed profile and corpus. Replay proves protocol/mapping, not native runtime availability.
- Consequence: ACXD-019 is resolved only for this ACX-17 provider/profile. At ACX-17 completion, DWG and RVT retained separate instances; those are now resolved by ACXD-029 and ACXD-030. ACXB-001 continues to block unreviewed native host and other container enforcement profiles.
- Evidence owner: `docs/specs/step-iges-v02-profile.md`, ACX-17 provider recipe/descriptor, project-authored corpus, license/security review, tests and acceptance evidence.

### ACXD-029: Bounded DWG R2000 external LibreDWG provider

- Provider decision: ACX-18 selects `org.aecctx.dwg.libredwg@0.2.0` using GNU LibreDWG 0.13.4 API/ABI 1, built with `--enable-release` from the official release archive with SHA-256 `7e153ea4dac4cbf3dc9c50b9ef7a5604e09cdd4c5520bcf8017877bbe1422cd5`. LibreDWG is GPL-3.0-or-later and therefore runs only through ACX-12 `oci-docker-v1`; it never enters core dependencies, wheels, sdists or in-process extras. Provider requests expose only fixed `dwgread`; `dxf2dwg` is limited to explicit project-fixture generation.
- Format boundary: the initial target is self-contained R2000/`AC1015` only. Other DWG revisions, encrypted/protected content, proxy/custom semantics, ACIS bodies, external-reference traversal and proprietary vertical objects remain unsupported or opaque.
- Evidence boundary: `dwgread` JSON is direct decoder evidence. `dwg2dxf --as r2000` output and all geometry parsed from it are converted/derived evidence with converter/runtime/configuration and input/output hashes. They are never presented as native DWG geometry or source-exact B-Rep.
- Runtime/distribution: the provider is operator-built, digest-pinned, network-disabled and not distributed by core. There is no entitlement, credential, telemetry, retention or service dependency. Any image distribution must satisfy GPL source, notice and replacement obligations. Image ID, exact base image and build results are implementation evidence, not inferred trust.
- Rejected alternatives: ODA Drawings SDK and Autodesk RealDWG lack repository-owned commercial entitlement, redistribution terms and public CI credentials. Network conversion lacks upload consent, retention/jurisdiction and reproducibility governance. They require separate future decisions.
- Fixture decision: conformance DWGs are generated from project-authored DXF/JSON commands by the exact provider. Negative cases mutate only project-authored bytes. Proprietary samples may supplement local diagnosis but cannot support a claim.
- Upstream-test decision: the official 0.13.4 arm64 aggregate `make check` fails `programs/alive.test` on 25 JSON-to-DWG writer round trips; `programs/dxf.test` passes the DWG read/DXF conversion and DXF-to-DWG paths used by this profile. The reviewed build therefore gates the exact `dxf.test` plus AECCTX live/adversarial conformance and records the aggregate failure as residual risk. This does not establish full LibreDWG conformance or authorize writer access from provider requests.
- Duplicate-handle decision: a project-authored R2000 DXF converted by the reviewed LibreDWG 0.13.4 writer reproducibly emits `DICTIONARY` and `VX_CONTROL` objects sharing handle `0x11`. The provider preserves both with source-order occurrence locators, reports `AECCTX_DWG_HANDLE_CONFLICT`, and refuses to resolve any reference through a duplicated handle. Rejecting the complete source would prevent a legally generated public corpus; merging or selecting one object would invent identity.
- Image-identity decision: Docker BuildKit provenance manifests are disabled for this operator-built single-platform image because their volatile metadata changes the locally inspected manifest-list ID across byte-identical cached builds. Review evidence binds the base digest, upstream archive SHA, Dockerfile and targeted test log directly; protocol runtime attestation remains mandatory. Two consecutive builds must inspect to the same image ID.
- Process-ceiling decision: `oci-docker-v1` registration now carries an exact `container_pids_limit` from 1 through 4, defaulting to 1. Existing providers remain at 1. ACX-18 registers 2 because the mounted Python worker launches one fixed sequential `dwgread` child; caller commands, shells and concurrent/unbounded descendants remain prohibited. This resolves the prior mismatch between the one-PID reference profile and the governed external CLI decoder architecture without creating a provider-specific launcher bypass.
- Consequence: the ACX-18 instance of ACXD-019 is resolved for this exact provider/profile. At ACX-18 completion, RVT retained a separate instance; it is now resolved by ACXD-030.
- Evidence owner: `docs/specs/dwg-v02-profile.md`, ACX-18 provider recipe/descriptor, generated corpus, license/security review, tests and acceptance evidence.

### ACXD-019: Restricted decoder distribution and entitlement

- Resolution: ACX-17 and ACX-18 selected bounded providers through ACXD-028 and ACXD-029. ACX-19 selects no provider through ACXD-030 because no candidate satisfies license/entitlement, runtime, sandbox, CI and fixture-rights gates in the current repository.
- Reopening requirement: any future RVT provider must record license compatibility, entitlement, redistribution, CI access, fixture rights, telemetry/network behavior, supported platforms and support lifecycle before implementation.
- Blocking effect: RVT extraction only. ACX-19 may close as documented `blocked` while later independent tasks continue.

### ACXD-030: No admissible RVT provider for ACX-19

- Decision: no RVT provider is selected. Autodesk Revit desktop requires a licensed Windows Revit runtime; APS Automation requires credentials, egress, remote transfer, billing and retention governance; ODA BimRv requires a separately licensed commercial module; Autodesk's open-source IFC exporter still depends on Revit and proprietary assemblies. The repository has none of the required entitlement/runtime/sandbox/CI/fixture-rights combinations.
- Functional outcome: ACX-19 implements only the machine-checked blocked boundary in `docs/specs/rvt-v02-blocked-profile.md`: provider-decision validation, anti-claim registry enforcement, exact opaque fallback for a project-authored non-RVT sentinel, restricted-dependency scans and consumer-boundary scans. It MUST NOT create an RVT adapter, descriptor, replay or extraction event.
- Reopening: a human must authorize and supply either a licensed local runtime plus complete enforcement/CI/fixture evidence, or APS credentials plus billing/upload/retention/jurisdiction approval and a reviewed network-provider profile. The implementation plan must be updated before any decoder code.
- Consequence: ACX-19 may close only as `blocked`; RVT remains public `unsupported` with opaque fallback. This is not an RVT capability claim.
- Evidence owner: `docs/specs/rvt-v02-blocked-profile.md`, the ACX-19 decision record/checker/tests and `docs/evidence/ACX-19.md`.

## Open decisions

None.
