# Post-v0.2 Functional Debt Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the bounded ACX-24 through ACX-38 functional outcomes from `docs/specs/aecctx-post-v02-functional-debt-spec.md`, culminating in a claim-complete AECCTX `0.3.0` reference release without weakening v0.1/v0.2 compatibility or application neutrality.

**Architecture:** Reuse the v0.2 package schemas and shared inference, coordinate, fidelity and provider-attestation records. Expand execution infrastructure before adapters, keep optional and restricted runtimes behind provider profiles, and publish each capability only through an exact profile/fixture/test/evidence mapping. If a task requires changing a standard v0.2 field rather than adding a namespaced extension or sidecar contract, stop that task and govern a compatibility decision before code.

**Tech Stack:** Python 3.12+, pytest, JSON Schema, existing AECCTX package/provider APIs, Docker OCI profiles, optional official parser/kernel dependencies, canonical JSON/JSONL, deterministic ZIP/SVG/GLB, GitHub Actions.

## Global Constraints

- Execute only the first `pending-next` or `in_progress` task in `docs/implementation-plan.md`.
- AECCTX remains application-agnostic; no WoodFraming, `WFDomain`, `WFImport` or consumer ontology enters core, adapters, fixtures or plugins.
- The `0.3.0` reference implementation continues to read v0.1/v0.2 packages; default writer/adapter behavior remains v0.1 unless an existing explicit v0.2 profile is selected.
- New evidence uses the existing v0.2 shared schemas and namespaced extensions. A standard-field change requires a new decision, migration policy, schema line and user review before implementation.
- Markdown and plugin prose remain derived projections; authoritative JSON/JSONL and content-addressed artifacts decide identity, evidence, geometry, diagnostics, gates and trust.
- Unknown, unsupported, conflicted, explicit-null and not-applicable states remain explicit; never synthesize units, CRS, geometry, identity, trust or approval.
- Core validation, package I/O, query, diff and context remain offline and LLM-independent.
- Native, GPL, commercial and network-backed dependencies remain optional and outside the Apache-2.0 core wheel.
- Replay proves mapping only. Every live platform/provider claim needs a live enforcement gate on the exact runtime.
- Every milestone closes with focused tests, `python3 scripts/check_spec_contract.py`, `./scripts/verify_portable.sh`, `./scripts/verify.sh`, exact-SHA CI, evidence and explicit next-task promotion.
- ACX-10 remains deferred.

---

## File and ownership map

| Surface | Responsibility |
|---|---|
| `docs/specs/*-v03-profile.md` | exact normative capability profiles and non-claims |
| `docs/decisions/decision-log.md` | accepted provider/version/license/compatibility decisions |
| `src/aecctx/providers/` | provider registration, local/OCI/remote execution and response validation |
| `providers/` | reviewed optional worker code and reproducible provider build inputs |
| `src/aecctx/adapters/` | source evidence mapping only; no provider launch or consumer mapping |
| `src/aecctx/signing.py`, `src/aecctx/trust/` | detached signing plus optional advanced trust profiles |
| `src/aecctx/gate/` | deterministic policy and IDS evaluation |
| `plugins/aecctx-inspector/` | optional orchestration/distribution with no unique semantics |
| `fixtures/v0.3/` | legally publishable positive/degraded/negative/adversarial inputs |
| `conformance/v0.3/` | claim registry and digest-bound corpus manifests |
| `scripts/check_*_v03_conformance.py` | strict claim/fixture/test/evidence checkers |
| `docs/evidence/ACX-NN.md` | immutable milestone evidence and residuals |

The first implementation milestone creates `conformance/v0.3/claims.json`. It starts with ACX-24 as `target` and may list later targets, but only the owning milestone can promote its own entries.

## Shared interfaces

Provider runtime selection introduced by ACX-24:

```python
@dataclass(frozen=True, slots=True)
class OCIRuntimeTarget:
    platform: str               # "linux"
    architecture: str           # "arm64" or "amd64"
    image: str                  # immutable name or local tag
    image_id: str               # sha256:<64 lowercase hex>

def resolve_oci_target(
    registration: ProviderRegistration,
    *,
    platform: str,
    architecture: str,
) -> OCIRuntimeTarget: ...
```

Provider calls continue to return the existing validated `ProviderResult`. Later local/remote profiles implement the same launcher protocol:

```python
class ProviderExecutionProfile(Protocol):
    profile_id: str
    def preflight(self, registration: ProviderRegistration) -> None: ...
    def launch(self, registration, workspace, limits, environment, stdout, stderr) -> subprocess.Popen[bytes]: ...
    def terminate(self, process: subprocess.Popen[bytes]) -> None: ...
    def memory_bytes(self, pid: int) -> int: ...
```

Adapter expansion continues through explicit v0.2 opt-in and validated provider results:

```python
def ingest_<format>(
    source_path: str | Path,
    output_path: str | Path,
    *,
    aecctx_version: str = "0.1.0",
    provider_result: ProviderResult | None = None,
    **bounded_profile_inputs: object,
) -> IngestResult: ...
```

No adapter may create or select a provider implicitly.

---

### Task 1: ACX-24 Multi-architecture OCI provider execution

**Files:**
- Create: `docs/specs/provider-oci-multiarch-v03-profile.md`
- Create: `conformance/v0.3/claims.json`
- Create: `conformance/v0.3/provider-multiarch-corpus.json`
- Create: `fixtures/v0.3/provider-multiarch/README.md`
- Create: `scripts/check_provider_multiarch_conformance.py`
- Create: `scripts/build_provider_matrix.sh`
- Create: `scripts/verify_provider_matrix.sh`
- Create: `tests/test_provider_multiarch.py`
- Create: `tests/test_v03_claim_registry.py`
- Modify: `src/aecctx/providers/models.py`
- Modify: `src/aecctx/providers/oci.py`
- Modify: `src/aecctx/providers/{tesseract,step_iges,dwg}.py`
- Modify: `providers/{tesseract-ocr,step-iges-ocp,libredwg}/Dockerfile`
- Modify: `docs/licenses/{tesseract-ocr-provider,step-iges-ocp-provider,libredwg-provider}.md`
- Modify: `docs/security/{external-provider-threat-model,step-iges-provider-review,dwg-provider-review}.md`
- Modify: `scripts/verify_portable.sh`, `scripts/verify.sh`, `.github/workflows/ci.yml`
- Test: `tests/test_provider_multiarch.py`, existing provider/adapter suites

**Interfaces:**
- Consumes: `ProviderRegistration`, `OCIDockerProfile`, `ProviderRunner`, existing replay corpora and worker protocols.
- Produces: `OCIRuntimeTarget`, `resolve_oci_target(...)`, architecture-bound attestations and claim `sandbox.oci-multiarch`.

- [x] **Step 1: Lock the normative profile and decision before runtime changes**

  Add ACXD-032 with exact platforms (`linux/arm64`, `linux/amd64`), provider/version matrix, normalized attestation fields, semantic-equivalence rules, build provenance and explicit macOS/Windows non-claims. Run `python3 scripts/check_spec_contract.py`; expected: PASS. Stop for human review if any worker dependency has no legally reproducible amd64 build.

- [x] **Step 2: Write failing runtime-selection tests**

  Tests must instantiate registrations with two targets and assert exact architecture selection, unknown architecture rejection, digest drift rejection and no implicit pull/build. Run `python -m pytest tests/test_provider_multiarch.py -q`; expected: FAIL because `OCIRuntimeTarget` and `resolve_oci_target` do not exist.

- [x] **Step 3: Implement the minimal architecture-bound registration contract**

  Add `OCIRuntimeTarget` and an immutable `oci_targets: tuple[OCIRuntimeTarget, ...]` to `ProviderRegistration`. Keep legacy single-image registration readable only for the existing v0.2 profiles. `OCIDockerProfile.preflight()` must inspect both `.Os` and `.Architecture`, select one exact target and reject mismatch with `AECCTX_PROVIDER_ARCHITECTURE_UNSUPPORTED` or `AECCTX_PROVIDER_IMAGE_DIGEST_MISMATCH`.

- [x] **Step 4: Build reproducible provider targets and bind fixtures**

  `scripts/build_provider_matrix.sh --provider NAME --platform linux --architecture ARCH` builds only reviewed Dockerfiles, records package locks and emits a machine-readable build receipt. It must never push. Generate arm64/amd64 output for the existing OCR, STEP/IGES and DWG positive fixtures; compare canonical response/events/artifacts after removing only governed attestation architecture fields.

- [x] **Step 5: Add adversarial live gates**

  Run timeout, PID tree, memory, filesystem, network, output, malformed-response and wrong-architecture cases against both architectures. `scripts/verify_provider_matrix.sh` must fail if Docker/emulation/runtime/image is unavailable; a skip cannot promote the claim.

- [x] **Step 6: Create claim and corpus mapping**

  `conformance/v0.3/provider-multiarch-corpus.json` binds source, request, response, artifact, descriptor, image and build-receipt digests. `sandbox.oci-multiarch` stays `experimental partial` until exact live evidence exists for all six provider/architecture combinations.

- [x] **Step 7: Run acceptance gates**

  Run:

  ```bash
  python -m pytest tests/test_provider_multiarch.py tests/test_external_providers.py tests/test_tesseract_provider.py tests/test_step_iges_provider.py tests/test_dwg_provider.py -q
  python scripts/check_provider_multiarch_conformance.py
  python scripts/check_spec_contract.py
  ./scripts/verify_portable.sh
  ./scripts/verify.sh
  ```

  Expected: all pass; live matrix receipts exist for arm64 and amd64; portable mode validates replay without claiming live availability.

- [x] **Step 8: Close and promote**

  Write `docs/evidence/ACX-24.md`, update claims/capability matrix/HANDOFF, set ACX-24 `completed`, promote only ACX-25, and commit `feat: add multi-architecture OCI provider execution`.

---

### Task 2: ACX-25 Additional local enforcement profiles

**Files:**
- Create: `docs/specs/provider-local-enforcement-v03-profile.md`
- Create: `src/aecctx/providers/local.py`
- Create: `conformance/v0.3/local-enforcement-corpus.json`
- Create: `fixtures/v0.3/local-providers/`
- Create: `scripts/check_local_enforcement_conformance.py`
- Create: `tests/test_local_provider_profiles.py`
- Modify: `src/aecctx/providers/__init__.py`, `models.py`, `runner.py`
- Modify: `docs/security/external-provider-threat-model.md`
- Modify: `docs/implementation-plan.md`, `docs/capability-matrix.md`

**Interfaces:**
- Consumes: `ProviderExecutionProfile`, ACX-12 enforcement axes, ACX-24 runtime-attestation normalization.
- Produces: one profile class per accepted platform and claim `sandbox.local-enforcement`; rejected platforms emit `LocalEnforcementReport` with every axis.

```python
@dataclass(frozen=True, slots=True)
class LocalEnforcementReport:
    profile_id: str
    platform: str
    axes: Mapping[str, Literal["enforced", "unavailable"]]
    executable: bool
    diagnostics: tuple[str, ...]
```

- [x] Govern ACXD-033 with official OS/runtime APIs, CI availability and per-axis proof. Do not combine Linux, macOS and Windows into one claim.
- [x] Write RED tests for complete isolation plus deterministic rejection of every missing axis.
- [x] Implement only profiles whose full axis suite is enforceable; keep `MacOSSeatbeltProfile` fail-closed unless the memory and host-read gaps are solved.
- [x] Execute the reference provider success and adversarial process/filesystem/network/resource corpus on each claimed platform.
- [x] Scan wheel/sdist to prove no native or restricted provider binary is bundled.
- [x] Run `pytest tests/test_local_provider_profiles.py tests/test_external_providers.py -q`, checker, portable/full gates and exact-platform CI.
- [x] Record accepted and rejected platforms in `docs/evidence/ACX-25.md`; promote only ACX-26; commit `feat: add reviewed local provider enforcement profiles`.

---

### Task 3: ACX-26 Optional remote/customer-managed provider protocol

**Files:**
- Create: `docs/specs/provider-remote-v03-profile.md`
- Create: `schemas/v0.2/remote-provider-policy.schema.json` and packaged mirror
- Create: `src/aecctx/providers/remote.py`
- Create: `providers/reference-remote/worker.py`
- Create: `fixtures/v0.3/remote-providers/`
- Create: `conformance/v0.3/remote-provider-corpus.json`
- Create: `scripts/check_remote_provider_conformance.py`
- Create: `tests/test_remote_providers.py`
- Modify: `src/aecctx/providers/{models,protocol,registry,runner,__init__}.py`
- Modify: `docs/security/external-provider-threat-model.md`

**Interfaces:**
- Consumes: content-addressed request/response protocol and `ProviderResult` validation.
- Produces: explicit `RemoteProviderPolicy`, `RemoteProviderProfile`, deterministic replay and claim `sandbox.remote-provider`.

```python
@dataclass(frozen=True, slots=True)
class RemoteProviderPolicy:
    endpoint_origin: str
    endpoint_spki_sha256: str
    upload_consent: bool
    allowed_regions: tuple[str, ...]
    retention_max_seconds: int
    timeout_seconds: float
    max_attempts: int

def run_remote_provider(
    registration: ProviderRegistration,
    request: Mapping[str, object],
    policy: RemoteProviderPolicy,
    *,
    credential: bytes,
) -> ProviderResult: ...
```

- [x] Govern ACXD-034: HTTPS origin/SPKI binding, redirect denial, credential handling, egress/region/retention/telemetry requirements and retry semantics.
- [x] RED-test consent denial, endpoint mismatch, auth failure, redirect, timeout, retry exhaustion, oversized/malformed response and secret redaction.
- [x] Implement a closed client with no ambient proxies, credentials, trust store, clock or endpoint discovery; reference tests use only a repository-owned loopback TLS server.
- [x] Prove core install and every non-provider command remain network-free.
- [x] Bind loopback success/degraded/error responses and replay to the corpus; do not claim third-party service availability.
- [x] Run focused tests, `check_remote_provider_conformance.py`, portable/full gates and exact-SHA CI.
- [x] Write `docs/evidence/ACX-26.md`; promote only ACX-27; commit `feat: add optional remote provider protocol`.

---

### Task 4: ACX-27 Expanded IFC 2D and georeferencing

**Files:**
- Create: `docs/specs/ifc-v03-profile.md`
- Create: `fixtures/v0.3/ifc/` and generator
- Create: `conformance/v0.3/ifc-corpus.json`
- Create: `scripts/check_ifc_v03_conformance.py`
- Create: `tests/test_ifc_v03.py`
- Modify: `src/aecctx/adapters/ifc.py`
- Modify: `docs/licenses/ifcopenshell.md`, `docs/capability-matrix.md`

**Interfaces:**
- Consumes: `ingest_ifc(..., aecctx_version="0.2.0")`, v0.2 coordinate/fidelity records.
- Produces: claims `ifc.native-2d.v03` and `ifc.georeferencing.v03`; no change to default v0.1 output.

- [x] Govern ACXD-035 with exact IfcOpenShell version, IFC schemas, item classes and coordinate operations after official API review.
- [x] RED-test every selected curve/annotation/style/operation plus absent, empty, unsupported, multiple, conflicted and non-invertible cases.
- [x] Generate legally publishable IFC fixtures and bind source hashes before adapter changes.
- [x] Implement evidence-first helpers that return source primitives before neutral records; use namespaced extensions for new source structures.
- [x] Prove SVG remains derived, transform chains are reversible and no EPSG/unit/operation is guessed.
- [x] Run `pytest tests/test_ifc_adapter.py tests/test_ifc_v02.py tests/test_ifc_v03.py -q`, checker and repository gates.
- [x] Write evidence, promote only ACX-28 and commit `feat: expand bounded IFC evidence profiles`.

---

### Task 5: ACX-28 Expanded DXF semantics and geometry

**Files:**
- Create: `docs/specs/dxf-v03-profile.md`
- Create: `schemas/v0.2/source-bundle.schema.json` and packaged mirror
- Create: `fixtures/v0.3/dxf/` and generator
- Create: `conformance/v0.3/dxf-corpus.json`
- Create: `scripts/check_dxf_v03_conformance.py`
- Create: `tests/test_dxf_v03.py`
- Modify: `src/aecctx/adapters/dxf.py`, `src/aecctx/cli.py`
- Modify: `docs/licenses/ezdxf.md`, `docs/capability-matrix.md`

**Interfaces:**
- Consumes: v0.2 DXF raw tags/ownership/geometry and package safety primitives.
- Produces: `load_source_bundle(path) -> SourceBundle`, claims `dxf.source-semantics.v03` and `dxf.geometry.v03`.

- [x] Govern ACXD-036 with exact releases/entities, xref bundle rules and the selected ACIS decision; ACIS remains unsupported unless an accepted kernel provider exists.
- [x] RED-test selected curves/surfaces/releases, bounded xrefs, cycles, escapes, hashes, proxy/custom/encrypted/ACIS and resource limits.
- [x] Generate ASCII/binary fixtures and content-addressed xref bundles; no test may depend on host-relative paths.
- [x] Implement source-bundle validation before opening any xref and evidence mapping before tessellation.
- [x] Preserve raw tags and fidelity; prove no entity becomes a consumer wall/beam/panel classification.
- [x] Run DXF v0.1/v0.2/v0.3, CLI, bundle-safety, determinism and full gates.
- [x] Write evidence, promote only ACX-29 and commit `feat: expand bounded DXF profiles`.

---

### Task 6: ACX-29 Multilingual and layout-aware OCR

**Files:**
- Create: `docs/specs/ocr-v03-profile.md`
- Create: `schemas/v0.2/ocr-layout.schema.json` and packaged mirror
- Create: `fixtures/v0.3/ocr/`
- Create: `conformance/v0.3/ocr-corpus.json`
- Create: `scripts/check_ocr_v03_conformance.py`
- Create: `tests/test_ocr_v03.py`
- Modify: `providers/tesseract-ocr/worker.py`, `src/aecctx/providers/tesseract.py`
- Modify: `src/aecctx/adapters/{image,pdf}.py`, `src/aecctx/cli.py`

**Interfaces:**
- Consumes: ACX-24 live matrix, existing `ProviderResult` inference mapping.
- Produces: closed `aecctx.ocr.layout.v1` event payload and claim `pdf-image.ocr-layout`.

- [x] Govern ACXD-037 with exact languages, data packages, orientations, PSM/layout profiles and licensing.
- [x] RED-test multilingual, rotated, multi-column/table, blank, mixed-script, corrupt, low-confidence and native-text conflict fixtures.
- [x] Extend the fixed worker configuration allowlist; no caller-selected executable/model path.
- [x] Map words/lines/blocks/tables as inferred evidence with exact region/request/response/runtime hashes; unknown order/topology stays unknown.
- [x] Prove live arm64/amd64 and replay equivalence for every claimed language/layout profile.
- [x] Run provider, PDF/image, CLI, conformance and full repository gates.
- [x] Write evidence, promote only ACX-30 and commit `feat: add bounded multilingual OCR profiles`.

---

### Task 7: ACX-30 Vision and reconstruction hypotheses

**Files:**
- Create: `docs/specs/vision-v03-profile.md`
- Create: `schemas/v0.2/vision-candidate.schema.json` and packaged mirror
- Create: `src/aecctx/vision.py` (ACXD-039 compatibility-preserving owner path)
- Create: `fixtures/v0.3/vision/`
- Create: `conformance/v0.3/vision-corpus.json`
- Create: `scripts/check_vision_v03_conformance.py`
- Create: `tests/test_vision_v03.py`
- Modify: `src/aecctx/adapters/{image,pdf}.py`, `src/aecctx/cli.py`
- Modify: `docs/capability-matrix.md`

**Interfaces:**
- Consumes: ACX-26 for network providers or ACX-24/25 for local providers, v0.2 inference envelope.
- Produces: `map_vision_result(result: ProviderResult) -> tuple[dict[str, object], ...]`, claims `pdf-image.vision-inference` and `pdf-image.reconstruction-hypothesis`.

- [x] Govern ACXD-039 by selecting one exact provider, vocabulary, thresholds, confidence calibration, privacy/network profile and reproducibility class. ACXD-038 is already owned by the ACX-29 DXF gate correction.
- [x] RED-test symbols/regions/dimensions/tables, ambiguity/conflict/absence, prompt text, crop/occlusion/redaction and calibration conflict.
- [x] Implement schema validation and mapping only after provider output passes the existing provider boundary.
- [x] Keep every output `inferred`; add tests that source identity, measurement, CRS, validation completeness and geometry support cannot consume hypotheses.
- [x] Run privacy-denied, provider-unavailable, replay-drift and nondeterminism-bound tests.
- [x] Complete positive claim evidence; promote only ACX-31; commit `feat: add bounded vision inference`.

---

### Task 8: ACX-31 Mesh CRS and coordinate qualification

**Files:**
- Create: `docs/specs/mesh-coordinate-v03-profile.md`
- Create: `schemas/v0.2/crs-registry.schema.json` and packaged mirror
- Create: `src/aecctx/crs.py`
- Create: `fixtures/v0.3/mesh/`
- Create: `conformance/v0.3/mesh-crs-corpus.json`
- Create: `scripts/check_mesh_crs_v03_conformance.py`
- Create: `tests/test_mesh_v03.py`
- Modify: `src/aecctx/adapters/geometry.py`, `src/aecctx/coordinates.py`, `src/aecctx/cli.py`
- Modify: `pyproject.toml`, `docs/licenses/trimesh.md`

**Interfaces:**
- Consumes: `CoordinateSolution`, v0.2 manual/source/derived qualification.
- Produces: `CRSRegistry`, `validate_crs_identifier(...)`, `apply_datum_operation(...)`, claims `mesh.crs-registry` and `mesh.datum-transform`.

```python
def validate_crs_identifier(registry: CRSRegistry, identifier: str) -> CRSRecord: ...
def apply_datum_operation(
    points: Sequence[Sequence[float]],
    operation: DatumOperation,
) -> CoordinateSolution: ...
```

- [x] Govern ACXD-040 with the exact offline registry/library/grid versions, licenses and authority/non-authority language. ACXD-039 remains immutable ACX-30 authority.
- [x] RED-test valid/unknown/deprecated/compound/conflicting CRS, axes, vertical CRS, large coordinates, grids, singular/reflected/tolerance failures.
- [x] Add an optional extra only if the selected official library is permissively distributable; keep core import clean and network disabled.
- [x] Preserve source vertices and emit manual/derived records with registry digest, operation, residual and accuracy.
- [x] Prove that a valid CRS identifier does not establish survey truth and unit guessing remains impossible.
- [x] Run mesh v0.1/v0.2/v0.3, clean-core/extra installs, determinism and repository gates.
- [x] Write evidence, promote only ACX-32 and commit `feat: add offline mesh CRS qualification`.

---

### Task 9: ACX-32 STEP/IGES XDE and fidelity expansion

**Files:**
- Create: `docs/specs/step-iges-v03-profile.md`
- Create: `schemas/v0.2/step-iges-xde-event.schema.json` and packaged mirror
- Create: `fixtures/v0.3/step-iges/`
- Create: `conformance/v0.3/step-iges-corpus.json`
- Create: `scripts/check_step_iges_v03_conformance.py`
- Create: `tests/test_step_iges_v03.py`
- Modify: `providers/step-iges-ocp/worker.py`
- Modify: `src/aecctx/providers/step_iges.py`, `src/aecctx/adapters/step_iges.py`

**Interfaces:**
- Consumes: ACX-24 multiarch OCP provider and existing lexical/BREP evidence.
- Produces: XDE event payloads, distinct raw/translated/healed artifacts, claims `step-iges.xde-structure` and `step-iges.partial-recovery`.

- [x] Govern ACXD-041 with exact OCP/OCCT version, XDE API calls, schemas and healing policy.
- [x] RED-test names/colors/layers/materials/units/placements, multi-root partial success, invalid topology, tolerance and healing pairs.
- [x] Extend provider schema and worker with closed actions/configuration; healing is opt-in and creates a new artifact.
- [x] Map XDE/source correlation and per-root results without replacing lexical source evidence or claiming source-exact BREP.
- [x] Prove arm64/amd64/replay equality and structured partial completion.
- [x] Run existing plus v0.3 provider/adapter suites and all gates.
- [x] Write evidence, promote only ACX-33 and commit `feat: expand STEP IGES XDE evidence`.

---

### Task 10: ACX-33 DWG version and geometry expansion

**Files:**
- Create: `docs/specs/dwg-v03-profile.md`
- Create: `schemas/v0.2/dwg-v03-event.schema.json` and packaged mirror
- Create: `fixtures/v0.3/dwg/`
- Create: `conformance/v0.3/dwg-corpus.json`
- Create: `scripts/check_dwg_v03_conformance.py`
- Create: `tests/test_dwg_v03.py`
- Modify: `providers/libredwg/worker.py`
- Modify: `src/aecctx/providers/dwg.py`, `src/aecctx/adapters/dwg.py`, `src/aecctx/cli.py`

**Interfaces:**
- Consumes: ACX-24 multiarch and ACX-28 source-bundle contract.
- Produces: exact version profiles and claim `dwg.external-provider.v03`.

- [x] Govern ACXD-042 with exact LibreDWG/alternative provider version, supported DWG releases, xref and geometry ceiling, GPL/commercial posture and known upstream failures.
- [x] RED-test every selected version, units, 3D, xref, duplicate handle, conversion loss, encrypted/protected, ACIS/proxy/custom and writer denial.
- [x] Generate project-authored DWG inputs through a documented legal toolchain; bind generator and output hashes.
- [x] Extend worker actions without exposing writer operations or caller commands.
- [x] Keep direct decoder JSON observed and DXF/geometry converted/derived with complete lineage.
- [x] Run live arm64/amd64, replay, adversarial, packaging and full gates.
- [x] Write evidence, promote only ACX-34 and commit `feat: expand bounded DWG provider profiles`.

---

### Task 11: ACX-34 RVT provider reopening

**Files:**
- Create: `docs/specs/rvt-v03-profile.md` only after provider acceptance, otherwise update blocked profile
- Create: `docs/plans/acx-34-rvt-provider-implementation.md` only after provider acceptance
- Create: `fixtures/v0.3/rvt/` only with publishable real fixtures
- Create: `conformance/v0.3/rvt-corpus.json` only for accepted route
- Create: `tests/test_rvt_v03.py` or extend blocked tests
- Create: `conformance/v0.3/rvt-provider-decision.json`
- Modify: `docs/decisions/decision-log.md`, `docs/capability-matrix.md`

**Interfaces:**
- Consumes: ACX-25 local profile or ACX-26 remote profile; ACXD-030 reopening requirements.
- Produces: one accepted provider descriptor/adapter and promoted `rvt.external-provider`, or renewed executable `unsupported`/`blocked` outcome.

The published `conformance/v0.2/rvt-provider-decision.json`, ACX-19 evidence and `v0.2.0` claim remain immutable inputs. ACX-34 records its new decision only under `conformance/v0.3/`.

- [x] Confirm no explicit selection of licensed local runtime or approved remote route was supplied; create no adapter/provider scaffolding.
- [x] Record entitlement, exact runtime/RVT versions, automation rights, CI, fixtures, telemetry, billing, retention, jurisdiction and lifecycle in ACXD-043.
- [x] Do not enter the accepted-provider branch or create its subordinate profile/plan without route authorization.
- [x] RED-test the renewed decision, route-promotion rejection, v0.3 unsupported claim and unchanged opaque fallback; positive RVT cases remain prohibited without a real publishable fixture/provider.
- [x] Add no neutral RVT mapping or converter-derived evidence because no route was accepted.
- [x] Run decision, distribution, anti-claim, consumer-boundary and full gates.
- [x] Update the decision checker and anti-claim evidence; document the exact missing human/external decision.
- [x] Promote only ACX-35 and commit `docs: renew RVT provider blocker`.

---

### Task 12: ACX-35 Advanced signing and trust profiles

**Files:**
- Create: `docs/specs/signing-v2-profile.md`
- Create: `src/aecctx/trust/{__init__,x509,timestamp,status}.py`
- Create: schemas and packaged mirrors for chain/status/timestamp policy and result
- Create: `fixtures/v0.3/signing/`
- Create: `conformance/v0.3/signing-corpus.json`
- Create: `scripts/check_signing_v03_conformance.py`
- Create: `tests/test_signing_v03.py`
- Modify: `src/aecctx/signing.py`, `src/aecctx/cli.py`, `pyproject.toml`

**Interfaces:**
- Consumes: existing canonical `SigningStatement` and detached-bundle model; ACX-26 only for explicitly selected online status.
- Produces: separate X.509, status, timestamp and countersignature result types; claims are separate, never one aggregate authenticity claim.

- [x] Govern ACXD-044 with exact algorithms, libraries, chain rules, offline status/timestamp inputs and countersignature semantics.
- [x] RED-test project test PKI: valid/expired/revoked/unknown/rotated chains, stale CRL/OCSP, timestamps, multisignatures, mutations and algorithm confusion.
- [x] Implement each trust layer as optional pure evaluation over explicit bytes and verification time; no host trust store, clock or discovery.
- [x] Preserve existing Ed25519 profile compatibility and clean install without advanced extras.
- [x] Prove machine-distinct integrity, crypto, identity, lifecycle, trust, authorization and archival-time results.
- [x] Run signing v1/v2, CLI, clean install, no-network and full gates.
- [x] Write evidence, promote only ACX-36 and commit `feat: add advanced optional trust profiles`.

---

### Task 13: ACX-36 Expanded IDS and quality gate

**Files:**
- Create: `docs/specs/quality-gate-v03-profile.md`
- Create: `fixtures/v0.3/gate/`
- Create: `conformance/v0.3/gate-corpus.json`
- Create: `scripts/check_gate_v03_conformance.py`
- Create: `tests/test_gate_v03.py`
- Modify: `src/aecctx/gate/{ids,_ids_worker,evaluator,models,projection}.py`
- Modify: v0.2 gate schemas only through backward-compatible optional fields or new namespaced check kinds

**Interfaces:**
- Consumes: `evaluate_gate(...)`, pinned IfcTester/IfcOpenShell worker.
- Produces: selected additional IDS check observations and claim `quality-gate.ids-expanded`.

- [x] Govern ACXD-045 with exact official IDS cases, facets, restrictions, cardinalities and dependency versions.
- [x] RED-test each selected combination plus unsupported `partOf`, URI/bSDD, geometry/quantity and malicious XML cases.
- [x] Vendor only unchanged official fixtures with hashes/license; generate separate Apache-2.0 project cases.
- [x] Extend preflight and deterministic mapping; unsupported facets fail closed or require review.
- [x] Prove JSON authority, exit/outcome stability and Markdown/CI parity.
- [x] Run gate v0.2/v0.3, missing-extra, worker limits, clean install and repository gates.
- [x] Write evidence, promote only ACX-37 and commit `feat: expand bounded IDS quality gates`.

---

### Task 14: ACX-37 Inspector distribution and host portability

**Files:**
- Create: `docs/specs/inspector-distribution-v03-profile.md`
- Create: `conformance/v0.3/plugin-corpus.json`
- Create: `fixtures/v0.3/plugin/`
- Create: `scripts/build_inspector_distribution.py`
- Create: `scripts/check_inspector_v03_conformance.py`
- Create: `tests/test_codex_plugin_v03.py`
- Modify: `plugins/aecctx-inspector/.codex-plugin/plugin.json`
- Modify: `plugins/aecctx-inspector/assets/compatibility.json`
- Modify: `plugins/aecctx-inspector/scripts/manage.py`
- Modify: existing plugin skills only for compatibility, never new semantics

**Interfaces:**
- Consumes: stable library/CLI/MCP/gate/signing results through ACX-36.
- Produces: deterministic inventory/checksum/signature metadata and claim `codex.aecctx-inspector-distribution`.

- [x] Govern ACXD-046 with exact host/core/MCP version matrix, package format, integrity/signature rules and marketplace non-claim.
- [x] RED-test compatible/incompatible versions, mutation, downgrade, install/upgrade/rollback/uninstall and adversarial parity.
- [x] Build reproducible create-only artifacts; installation cannot overwrite unknown files and uninstall removes only exact inventory.
- [x] Run parity for validate/info/query/diff/context/gate across every claimed host profile.
- [x] Prove core has no plugin dependency and provider execution never becomes a plugin shell tool.
- [x] Run plugin checker, clean installs, platform CI and full gates.
- [x] Write evidence, promote only ACX-38 and commit `feat: package portable inspector distribution`.

---

### Task 15: ACX-38 Aggregate conformance and AECCTX 0.3.0 release

**Files:**
- Create: `conformance/v0.3/corpus.json`
- Create: `src/aecctx/release_v03_conformance.py`
- Create: `tests/test_v03_release.py`
- Create: `docs/compatibility-v0.3.md`
- Create: `docs/releases/v0.3.0.md`
- Create: `docs/release/v0.3.0-evidence-index.md`
- Create: `docs/release/v0.3.0-supply-chain.md`
- Create: `docs/evidence/ACX-38.md`
- Modify: `pyproject.toml`, `uv.lock`, `src/aecctx/__init__.py`
- Modify: `README.md`, `CHANGELOG.md`, `docs/HANDOFF.md`, `docs/capability-matrix.md`
- Modify: `scripts/verify_release.sh`, `.github/workflows/release.yml`

**Interfaces:**
- Consumes: every ACX-24 through ACX-37 completed or documented-blocked outcome.
- Produces: strict aggregate checker, deterministic artifacts and immutable `v0.3.0` release only after exact gates.

- [ ] Audit the ledger and reject any earlier task lacking evidence, claim mapping or documented blocker.
- [ ] RED-test missing/duplicate/unmapped claim, digest drift, target/blocked promotion, replay-as-live and restricted/consumer artifact leakage.
- [ ] Build `conformance/v0.3/corpus.json` with every component corpus digest and exact task outcome.
- [ ] Verify v0.1/v0.2 package read compatibility, v0.1 default output stability and all optional v0.2 profiles.
- [ ] Build deterministic wheel, sdist and inspector archive; emit SHA256SUMS and SPDX SBOM.
- [ ] Run clean core/all-extras installs and scan artifacts for RVT/proprietary/provider/consumer leakage.
- [ ] Run:

  ```bash
  python -m pytest tests/test_v03_release.py -q
  python -m aecctx.release_v03_conformance
  python scripts/check_spec_contract.py
  ./scripts/verify_portable.sh
  ./scripts/verify.sh
  ./scripts/verify_release.sh
  ```

- [ ] Push a release candidate and require green exact-SHA CI on every claimed platform/provider matrix.
- [ ] Merge through a no-ff reviewed commit, rerun full verification on `main`, create immutable `v0.3.0`, publish only verified assets and verify downloaded checksums.
- [ ] Mark ACX-38 completed with no automatic next task; commit `release: publish AECCTX 0.3.0` plus a later evidence-only commit if remote publication receipts are required.

---

## Promotion and evidence protocol

For every ACX:

1. Set only the current task `in_progress` in the same commit that locks its task profile and fixture/test plan.
2. Do not edit later task claim states, adapters or fixtures.
3. Keep RED evidence in the task evidence document or commit history.
4. Promote a claim only after focused, portable, full and exact-platform/provider gates pass.
5. Attach `docs/evidence/ACX-NN.md` using the repository evidence template.
6. Set the task `completed` or documented `blocked` and promote exactly the following task in one governance change.
7. Do not execute the promoted task until a new user continuation request.

## Plan completion definition

This plan is complete when ACX-24 through ACX-38 are `completed` or documented `blocked`, every public claim is mapped to executable conformance, every retained residual is explicit, and the release gate either publishes verified `v0.3.0` or records the exact external blocker. Completion does not include ACX-10, WoodFraming mapping, source write-back, universal ontology, hidden source geometry, survey authority or engineering approval.
