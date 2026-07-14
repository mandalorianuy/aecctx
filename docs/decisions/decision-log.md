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
- Task 2 parsing clarification: the section 13 defaults are the non-expandable v1 hard maxima; JSON depth counts a scalar as 0 and the root container as 1, with parser recursion exhaustion mapped to the same stable depth error. `policy_version` follows SemVer 2.0.0 including prerelease/build identifier rules. A waiver stores the exact full `aecctx.policy.<check-id>` result ID and MUST reference a check declared by the same policy; short IDs, system IDs, wildcards and undeclared targets are invalid. The stable policy-loader error-code family is normative in profile section 14.
- Task 3 disposition/diagnostic clarification: each finding owns an explicit `error`, `fail`, `requires_review` or `waived` disposition so exact waivers can recompute mixed-finding check status without using severity as policy state. `waived` requires a waiver ID and all other dispositions require it to be null; finding fingerprints are unique per check and a non-empty check result equals the highest finding disposition except for an explicit active-mismatch review floor. `apply_waivers` returns `(ordered_checks, ordered_diagnostics)`; expired/not-yet-valid waivers diagnose without changing status, while an active unmatched waiver forces at least review. All waiver lifecycle states are classified against the original check set, exact mutations are collected, and the mismatch floor is applied once after recomputation so waiver-array order cannot change results. Duplicate targets/identities, missing/system checks, invalid lifecycle and error/already-waived dispositions are invalid control state with stable codes. Fingerprints exclude message, disposition and waiver ID so applying a waiver preserves finding identity.
- Task 4 package-check clarification: invalid preflight never invents package identity; `candidate` is null only for an error whose validation could not establish trusted identity. Valid callers are evaluated only from a bounded private snapshot that is revalidated against the initial complete manifest, with symlink roots and mutation rejected. Validation/integrity diagnostics use a fixed code partition. Loss counts sum diagnostic `affected_count` by exact manifest reason; diagnostic budgets count records; value field paths use a closed dot-segment grammar and malformed evidence is explicit error. Finding/result overflow raises stable operational `GateError`; Task 5 diff and Task 6 IDS remain fail-closed and unimplemented rather than silently ignored.
- Task 5 baseline-diff clarification: `aecctx.system.baseline` is fixed and non-waivable whenever a baseline is supplied or required. Baselines use the candidate private-snapshot/revalidation boundary; missing/invalid identity is never synthesized. The stable `PackageDiff` primitive is extended additively with authoritative non-record artifact changes and exact identity/producer/loss field changes because all-artifact hashes cannot make generated Markdown authoritative, normalized record semantics cannot depend on JSONL byte serialization, and boolean-only fields cannot satisfy exact evidence citations. Diff evidence uses role-qualified `baseline-package:<digest>` and `candidate-package:<digest>` refs because manifest-only changes may retain equal artifact-derived logical digests and unqualified refs would collapse. Gate actions map the nine closed categories; capability disappearance/downgrade is regression while addition/upgrade remains visible non-regression evidence, preserving `missing` distinctly from `unsupported`. Any future semantic category not explicitly mapped is error. Task 6 IDS remains fail-closed and unimplemented.
- Task 6 IDS clarification: IDS v1.0 has no root version field, so the fixed namespace, closed AECCTX profile and exact release provenance establish version. `xsi:schemaLocation` is inert and never fetched or treated as version authority, including the historical `0.9.7` hint preserved in unchanged v1.0-tag cases. `ORIGIN.json` selects exactly one positive and one negative paired case for each simple-value entity/attribute/classification/property/material family at full commit `1effec6f419798ce09617416d258a35bdc58320a`. Input-pair, binding, XML-safety, dependency and worker-protocol failures are non-waivable `aecctx.system.ids-input` errors; safely detected unsupported facets/restrictions and completed IDS nonconformance are policy findings with the declared failure mode. `GateLimits` exposes the already normative 256 specification, 4,096 facet and 250,000 entity maxima additively so callers can only reduce them through the existing hard-limit contract. The stable Task 6 code family is normative in profile section 14.
- Task 7 CLI/projection clarification: a valid `GateResult`, including outcome `error`, yields canonical JSON envelope `ok: true`; failures that prevent result construction yield `ok: false` and exit 2. `--output` is the raw canonical result. Markdown keeps untrusted presentation text inside indented canonical JSON records, while portable CI annotations are deterministic `aecctx-ci-annotations-v1` JSONL rather than GitHub/provider workflow commands. A neutral invocation-level atomic-create primitive preflights all input/output path collisions, uses no-overwrite publication, rolls back only outputs created by the current invocation on failure and is reused by signing through its existing error codes. Task 7 stable gate output codes are normative in profile section 14.
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

### ACXD-036: Bounded DXF v0.3 release, curve and source-bundle profiles

- Runtime and release decision: ACX-28 retains optional `ezdxf==1.4.4` and adds exact project-corpus coverage for `AC1009` (R12), `AC1018` (R2004) and `AC1021` (R2007), alongside the already-public `AC1015` and `AC1032` profiles. Intermediate releases not represented by the committed corpus remain unclaimed even when ezdxf can parse them.
- Geometry decision: source-exact evidence is added for `ELLIPSE`, `SPLINE`, `HELIX`, `RAY`, `XLINE` and `MLINE` attributes, plus `MESH` topology on the newly covered R2007 corpus. Deterministic sampled paths use a fixed profile tolerance and segment ceiling and remain derived tessellation; they are never exact B-Rep or construction-domain classifications. Existing face/polyline geometry remains governed by ACXD-026.
- Source-bundle decision: an optional directory bundle is admitted only through a schema-validated `source-bundle.json` whose root and xref members are safe bundle-root-relative POSIX logical paths with exact byte counts and SHA-256 digests. All members are regular non-symlink files below the bundle root. Traversal is depth-first in logical-path order with fixed file, depth, per-file and aggregate-byte limits; missing members, cycles, escapes, duplicate paths and digest drift fail before any xref is opened. Host-relative and network paths are never resolved.
- Xref evidence decision: bundle members remain distinct source records and every traversed entity cites its member source. The root block's declared xref path is preserved separately from the resolved content-addressed bundle member. No source bundle is synthesized from ambient filesystem paths.
- ACIS and protected-content decision: no accepted ACIS/SAT/SAB kernel provider exists for this task. `3DSOLID`, `BODY`, `REGION`, `SURFACE` and derived ACIS surface families remain raw with `AECCTX_DXF_ACIS_KERNEL_UNSUPPORTED`; proxy/custom and encrypted/protected inputs remain opaque or rejected with stable diagnostics. The ezdxf xref import API is not used because it can omit unsupported entities and would collapse source separation.
- Compatibility and claims: v0.1 remains the default and byte-compatible. The v0.3 behavior is an additive explicit profile under `aecctx_version="0.2.0"` plus an optional source bundle. Public claims `dxf.source-semantics.v03` and `dxf.geometry.v03` have ceiling `partial` and require the exact fixture/corpus/test/evidence mapping.
- Evidence owner: `docs/specs/dxf-v03-profile.md`, ACX-28 source-bundle schema, project-authored corpus, tests and `docs/evidence/ACX-28.md`.

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

## Post-v0.2 program decisions

### ACXD-031: Dependency-first functional debt program

- Date: 2026-07-13.
- Status: Accepted for specification and planning; it creates no implementation or release claim.
- Decision: post-`0.2.0` work follows the dependency-first sequence in `docs/specs/aecctx-post-v02-functional-debt-spec.md`. Multi-architecture execution of the existing OCI providers precedes new format or inference claims; additional local and remote provider profiles precede capabilities that depend on them.
- Functional rule: every residual maps to an executable outcome, a bounded anti-claim or a documented external blocker. A document, mock, replay-only mapping or unavailable provider is not sufficient evidence for a live capability.
- Claim rule: public support may advance only for exact profile, dependency, provider and platform combinations with legally publishable fixtures and mapped conformance. Existing `0.2.0` claims remain unchanged until a future owning task completes.
- Sequencing consequence: the subordinate implementation plan may promote only ACX-24 to `pending-next`; ACX-25 through ACX-38 remain `pending`, ACX-10 remains `deferred`, and no implementation begins from this decision alone.
- Boundary: WoodFraming and all consumer mappings remain outside AECCTX.

### ACXD-032: Architecture-bound OCI provider targets

- Date: 2026-07-13.
- Status: Accepted for ACX-24 implementation; it creates no capability claim until the live matrix passes.
- Platform decision: the reviewed target set is exactly `linux/arm64` and `linux/amd64`. The host operating system is not a claim axis; native macOS and Windows provider execution remain unsupported. Emulation is admissible only when Docker reports the executed image itself as the requested Linux architecture.
- Provider decision: ACX-24 covers only `org.aecctx.ocr.tesseract-tsv@0.2.0`, `org.aecctx.step-iges.ocp@0.2.0` and `org.aecctx.dwg.libredwg@0.2.0`, using respectively Tesseract 5.3.4 with English data, cadquery-ocp 7.9.3.1.1 with OCCT 7.9.3, and LibreDWG 0.13.4. No new format, extraction or inference semantics are introduced.
- Identity decision: each registration binds an exact `(os, architecture, image tag, local image ID)` target. Runtime selection is explicit and exact; unknown targets, target/image architecture mismatch and image-ID drift fail closed. AECCTX never pulls, builds or chooses another architecture implicitly.
- Attestation decision: normalized live evidence records provider ID/version, platform, architecture, immutable local image ID, base manifest digest, dependency versions, build-recipe digest, source/archive or package-lock digests, request/response/artifact digests and enforced sandbox axes. Host paths, timestamps, builder names and other machine-local values are excluded.
- Equivalence decision: the same governed positive fixture and configuration must produce byte-identical canonical response, ordered events and artifacts across both architectures after removing only the normalized attestation fields `architecture` and `image_id`. Diagnostics, value states, evidence lineage and loss reports are never normalized away.
- Build and distribution decision: the repository publishes reviewed recipes and deterministic receipts but does not push provider images. Tesseract remains Apache-2.0 plus HPND dependencies, OCP/OCCT remains behind the Apache/LGPL-with-exception external boundary, and LibreDWG remains GPL-3.0-or-later behind the process boundary. Image distributors remain responsible for SBOM, notices, corresponding source and replacement obligations applicable to their distribution.
- Claim decision: replay validates portability of evidence only. `sandbox.oci-multiarch` may become public partial solely after all six provider/architecture combinations pass live positive, equivalence and adversarial gates with publishable fixtures and bound receipts.
- Evidence owner: `docs/specs/provider-oci-multiarch-v03-profile.md`, `conformance/v0.3/provider-multiarch-corpus.json`, `scripts/verify_provider_matrix.sh` and `docs/evidence/ACX-24.md`.

### ACXD-033: No admissible native local enforcement profile in ACX-25 draft 1

- Date: 2026-07-13.
- Status: Accepted for ACX-25 implementation; it creates no positive sandbox claim.
- Contract decision: ACX-25 evaluates `linux-native-v1`, `macos-app-sandbox-v1` and `windows-appcontainer-job-v1` independently against the complete 16-axis ACX-12 contract. A machine-readable `LocalEnforcementReport` is authoritative for profile admission; provider descriptors and host feature names are not enforcement evidence.
- Linux decision: Landlock and cgroup v2 are useful official primitives but no reviewed, pinned, unprivileged supervisor/delegation contract in this repository jointly proves filesystem, user, process, network, CPU, memory, child-tree, open-file, environment, temporary-storage and cleanup enforcement. `linux-native-v1` remains executable `unsupported`.
- macOS decision: App Sandbox requires a signed entitlement-bearing containing application/helper and the legacy `sandbox-exec` path is deprecated; the current distribution has no complete aggregate CPU/memory/process-tree supervisor. `macos-app-sandbox-v1` and legacy `macos-seatbelt-v1` remain executable `unsupported`.
- Windows decision: AppContainer/LPAC and Job Objects together expose the necessary classes of controls, but the repository has no reviewed native broker that safely creates profiles/DACLs, launches and assigns non-breakaway jobs before execution, monitors the full resource contract and cleans persistent state. `windows-appcontainer-job-v1` remains executable `unsupported`.
- Functional outcome: all three profiles return deterministic complete reports and reject before workspace creation or process launch. A future positive profile requires a new accepted decision plus exact-platform live success and adversarial evidence; rejection cannot be counted as successful sandbox execution.
- Packaging/license decision: ACX-25 adds no OS helper, native broker, restricted binary or dependency. GPL/commercial decoder entitlement remains separately required.
- Claim decision: `sandbox.local-enforcement` may close as public `unsupported` for the three exact native profiles if the report/rejection/corpus/packaging matrix passes on Ubuntu, macOS and Windows. Existing OCI claims remain unchanged.
- Evidence owner: `docs/specs/provider-local-enforcement-v03-profile.md`, `conformance/v0.3/local-enforcement-corpus.json`, `scripts/check_local_enforcement_conformance.py` and `docs/evidence/ACX-25.md`.

### ACXD-034: Closed HTTPS/SPKI remote provider protocol

- Date: 2026-07-13.
- Status: Accepted and conformance-complete for ACX-26; it creates no service-availability or third-party capability claim.
- Endpoint decision: `remote-https-spki-v1` binds one normalized HTTPS origin and one SHA-256 SPKI pin in both registration and invocation policy. The route is fixed; redirects, discovery, proxies, URL credentials, ambient CA roots and wall-clock trust decisions are forbidden. The repository-owned conformance endpoint is loopback TLS, not plain HTTP.
- Consent/privacy decision: upload and billing consent, region allowlist, retention ceiling and telemetry consent are explicit per invocation and checked before network access. Credentials are caller bytes used only after pin verification and are forbidden from bodies, digests, diagnostics, details, fixtures and replay.
- Protocol decision: canonical request/response envelopes bind source, existing v0.2 request/response, artifacts, policy projection and transport body hashes. Existing response validation remains authoritative after confined artifact materialization. Core commands never invoke this client.
- Retry decision: only transport failures and HTTP 429/502/503/504 retry, with one through three byte-identical attempts and policy-fixed monotonic delay. Redirect, authentication, identity, consent, malformed/digest-invalid and semantic failures are terminal.
- Dependency/license decision: optional `cryptography>=45,<50` supplies certificate/SPKI parsing under Apache-2.0 OR BSD-3-Clause and remains outside core. No remote SDK, commercial/GPL decoder, credential or service dependency is distributed.
- Claim decision: `sandbox.remote-provider` may become public `partial` only for this exact protocol after loopback live/adversarial, deterministic replay, packaging and offline-core gates pass. No provider SLA, deletion, jurisdiction, billing, semantic, entitlement or provider-side sandbox guarantee is claimed.
- Evidence owner: `docs/specs/provider-remote-v03-profile.md`, `conformance/v0.3/remote-provider-corpus.json`, `scripts/check_remote_provider_conformance.py` and `docs/evidence/ACX-26.md`.
- Completion result: all governed live loopback, adversarial, replay, packaging, offline-core and cross-platform CI gates passed; only the exact protocol is public `partial`. GitHub is the repository delivery authority, with zero externally required approvals under the current unprotected/no-ruleset configuration and mandatory PR/check/squash evidence.

### ACXD-035: Bounded IFC4X3 2D and scaled-map expansion

- Date: 2026-07-13.
- Status: Accepted for ACX-27 implementation; it creates no survey, rendering or consumer-semantic authority.
- Runtime/schema decision: positive v0.3 claims use only optional `ifcopenshell==0.8.5` and project-authored `IFC4X3_ADD2` STEP fixtures. Existing ACX-13 IFC2X3/IFC4 claims and default v0.1 output remain unchanged.
- 2D decision: the exact additional structural profiles are finite 2D `IfcCircle`, `IfcEllipse`, parameter-trimmed supported conics, bounded `IfcCompositeCurve`, explicit line/arc indexed polycurves, bounded `IfcTextLiteral`, supported-boundary `IfcAnnotationFillArea` and directly associated bounded text/curve/fill/hatching style evidence. SVG stays derived and cannot create source geometry.
- Coordinate decision: only explicit `IfcMapConversionScaled` with one projected CRS, complete ACX-13 parameters and finite positive explicit X/Y/Z factors may become a reversible known transform. Factors scale coordinates, not units. IFC2X3 property sets, defaulted parameters, multiple operations, false EPSG cues and unlisted operations remain observed loss/unknown/unsupported/conflicted.
- Safety decision: exact text/point/segment/member/depth limits, finite-value validation, cycle rejection and stable diagnostics precede public claims.
- Claim decision: `ifc.native-2d.v03` and `ifc.georeferencing.v03` may become public `partial` only after their digest-bound fixture/corpus, RED/GREEN, reversibility, derived-preview, packaging and cross-platform gates pass.
- Evidence owner: `docs/specs/ifc-v03-profile.md`, `fixtures/v0.3/ifc/`, `conformance/v0.3/ifc-corpus.json`, `scripts/check_ifc_v03_conformance.py` and `docs/evidence/ACX-27.md`.
- Completion result: both exact claims are public `partial` after source-structure, degradation, limit, reversibility, derived-preview, package and repository gates passed. The non-claims above remain unchanged.
