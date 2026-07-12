# ACX-17 STEP/IGES Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` and `superpowers:test-driven-development` task-by-task. Subagent dispatch is prohibited for this repository task.

**Goal:** Implement the bounded v0.2 STEP/IGES source-structure and B-Rep profiles through the reviewed external OCP/OCCT provider without adding the native kernel to the core distribution.

**Architecture:** An ACX-12 `oci-docker-v1` provider owns all OCP/OCCT parsing, XDE traversal, B-Rep serialization and tessellation. A small core `step_iges` boundary validates the already-validated provider event vocabulary and maps observed source/XDE evidence separately from translator-derived B-Rep/GLB. CLI supports portable replay only; live execution remains an explicit SDK operation with a caller-constructed reviewed `ProviderRunner`.

**Tech Stack:** Python 3.12+, existing ACX-12 provider protocol, Docker Linux arm64, `cadquery-ocp==7.9.3.1.1`/OCCT 7.9.3, JSON Schema 2020-12, existing package/record/GLB APIs, pytest.

**Execution resolution:** Tasks 1-6 are complete. Live conformance showed that the reviewed low-level OCCT reader proves deterministic transfer/BREP/tessellation but does not prove XDE-to-source correlation, normalized styles/units/placements, per-root tolerances or partial-root recovery. The normative profile and ACXD-028 therefore retain those outcomes as explicit unsupported residuals; the experimental claims are narrowed to the lexical source graph, direct STEP product/assembly records and translator-derived geometry. All repository and live-provider gates passed before promotion.

## Global Constraints

- Execute only ACX-17; ACX-18 remains pending.
- Normative authority is `docs/specs/step-iges-v02-profile.md` and ACXD-028.
- OCP/OCCT never enters `pyproject.toml`, the core wheel, an in-process extra or a host import path.
- Only the exact operator-built Linux arm64 image may execute live; portable replay is not live-runtime evidence.
- STEP profiles are `CONFIG_CONTROL_DESIGN`, AP214 IS tuple `{ 1 0 10303 214 1 1 1 1 }` and AP242 edition-1 tuple `{ 1 0 10303 442 1 1 4 }`; IGES is 5.3 with only the enumerated type/form list. Profile matching normalizes tuple whitespace but retains the source string.
- Source entities/XDE-backed facts are observed. OCCT BREP and GLB are translator-derived and tessellated evidence respectively.
- External references are preserved but never opened. Runtime network, commands, callbacks and caller resource paths are forbidden.
- Translator-default processing is reported. No source-exact B-Rep, implicit healing, CRS/survey authority or consumer classification is claimed.
- Every partial/unsupported/conflicted outcome emits stable diagnostics and machine-readable loss.
- Default and explicit v0.1 behavior remain opaque and byte-identical.

---

### Task 1: Provider image, descriptor and registration

**Files:**
- Create: `providers/step-iges-ocp/Dockerfile`
- Create: `providers/step-iges-ocp/README.md`
- Create: `providers/step-iges-ocp/requirements.txt`
- Create: `src/aecctx/providers/step_iges.py`
- Modify: `src/aecctx/providers/__init__.py`
- Create: `tests/test_step_iges_provider.py`
- Create: `scripts/build_step_iges_provider.sh`
- Create: `scripts/verify_step_iges_provider.sh`

**Interfaces:**
- Produces constants `STEP_IGES_PROVIDER_ID`, `STEP_IGES_IMAGE`, `STEP_IGES_IMAGE_ID`, `STEP_IGES_CONFIGURATION`.
- Produces `step_iges_descriptor() -> ProviderDescriptor`.
- Produces `step_iges_registry(repository_root: str | Path | None = None) -> ProviderRegistry`.
- Registration launches only `python3 /provider/worker.py` in the exact reviewed image.

- [ ] **Step 1: Write failing descriptor/registration tests.** Assert provider ID `org.aecctx.step-iges.ocp`, version `0.2.0`, exact runtime string, `LGPL-2.1-only WITH OCCT-exception AND Apache-2.0`, `linux-container`, all enforcement axes, immutable image ID, exact worker path/command, and absence of `cadquery-ocp`/`OCP` from `pyproject.toml`.
- [ ] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_step_iges_provider.py -k 'registration or core_distribution' -q`; expect import failure for `aecctx.providers.step_iges`.
- [ ] **Step 3: Add the reviewed image recipe.** Base it on the already reviewed Ubuntu Noble arm64 digest, install Python 3.12/pip and exact `cadquery-ocp==7.9.3.1.1`, set `LANG/LC_ALL=C.UTF-8`, `PYTHONHASHSEED=0`, `OMP_NUM_THREADS=1`, `OMP_THREAD_LIMIT=1`, non-root UID/GID `65532`, and remove package/pip caches. `requirements.txt` pins the exact wheel version; the build script uses `docker build --pull=false --network=default -t aecctx-step-iges-ocp:0.2.0 providers/step-iges-ocp` and never runs from core ingest.
- [ ] **Step 4: Build explicitly and capture immutable evidence.** Run `./scripts/build_step_iges_provider.sh`; inspect `docker image inspect --format '{{.Id}}' aecctx-step-iges-ocp:0.2.0`, record the exact `sha256:` ID in `step_iges.py`, the worker constant and the provider license record. A changed ID is a reviewed-profile change, not an auto-update.
- [ ] **Step 5: Implement descriptor/registry and public exports.** Follow `src/aecctx/providers/tesseract.py`: exact constants, `ProviderDescriptor.from_dict`, `ProviderRegistration` with tag plus immutable local ID, and allowlisted worker module `aecctx.external.step_iges_ocp_worker`.
- [ ] **Step 6: Verify GREEN.** Run `.venv/bin/python -m pytest tests/test_step_iges_provider.py -k 'registration or core_distribution' -q` and `docker run --rm --network=none --read-only --user=65532:65532 aecctx-step-iges-ocp:0.2.0 python3 -c 'import OCP; print(OCP.__version__)'`; expect exact runtime and no write/network need.
- [ ] **Step 7: Commit.** `git add providers/step-iges-ocp src/aecctx/providers scripts/build_step_iges_provider.sh scripts/verify_step_iges_provider.sh tests/test_step_iges_provider.py && git commit -m "feat: register reviewed ACX-17 OCP provider"`.

### Task 2: Bounded source scanner and project-authored fixtures

**Files:**
- Create: `providers/step-iges-ocp/worker.py`
- Create: `providers/step-iges-ocp/generate_fixtures.py`
- Create: `fixtures/v0.2/step-iges/generate_fixtures.sh`
- Generate: `fixtures/v0.2/step-iges/ap203-part.step`
- Generate: `fixtures/v0.2/step-iges/ap214-assembly.step`
- Generate: `fixtures/v0.2/step-iges/ap242-part.step`
- Generate: `fixtures/v0.2/step-iges/iges53-part.igs`
- Create: `fixtures/v0.2/step-iges/unknown-schema.step`
- Create: `fixtures/v0.2/step-iges/external-reference.step`
- Create: `fixtures/v0.2/step-iges/malformed.step`
- Modify: `tests/test_step_iges_provider.py`

**Interfaces:**
- Worker pure helpers remain importable without OCP: `_configuration(request)`, `_probe(data)`, `_scan_step(data, limits)`, `_scan_iges(data, limits)`.
- `_scan_step` returns exact header fields plus sorted entity records `{id, original_class, component_classes, raw, references}`; `component_classes` is populated only for ISO 10303-21 complex instances.
- `_scan_iges` returns exact global fields plus sorted directory records `{sequence, entity_type, form, parameter_pointer, transform_pointer, level, label, subscript}`.
- OCP imports occur only inside native transfer functions.

- [ ] **Step 1: Write failing pure worker tests.** Cover STEP/IGES probes, exact/multiple/unknown STEP schema, duplicate/broken IDs, multiline strings/comments, IGES 80-column sections, type/form extraction, malformed/truncated data, entity/record/recursion limits and external-reference detection.
- [ ] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_step_iges_provider.py -k 'probe or scanner or configuration' -q`; expect missing worker/helpers.
- [ ] **Step 3: Implement only the bounded lexical/source layer.** Parse ISO-10303-21 record boundaries with string/comment awareness, positive `#id=CLASS(...)` envelopes and complex `#id=(CLASS(...) CLASS(...))` instances; retain raw record bytes decoded as strict ASCII, ordered component classes and direct `#id` references. Parse IGES fixed 80-column section markers/directory pairs and Global delimiters. Do not implement EXPRESS, geometry or schema semantics. Reject recovery that would invent a record.
- [ ] **Step 4: Implement exact configuration validation.** Accept only the canonical `STEP_IGES_CONFIGURATION`; reject extra keys, changed deflections, resource paths, commands or environment fields with `AECCTX_STEP_IGES_CONFIGURATION_INVALID`.
- [ ] **Step 5: Verify scanner GREEN.** Run the targeted tests; assert stable error codes and deterministic sort order.
- [ ] **Step 6: Generate legal fixtures through the reviewed kernel.** In `generate_fixtures.py`, use `BRepPrimAPI_MakeBox`, XDE labels, two placed component instances, names/colors/layers and `STEPCAFControl_Writer`/`IGESCAFControl_Writer`. Set exact STEP schema modes for AP203/AP214/AP242 and emit IGES 5.3. The shell script mounts only the generator/output into the reviewed image. Hand-authored negative fixtures contain no third-party geometry.
- [ ] **Step 7: Verify fixtures independently.** Hash every fixture, run the pure scanners, and use a one-off provider-container read to assert non-empty OCCT transfer, assembly placements and IGES shape. Regeneration must produce identical fixture bytes; if OCCT headers contain timestamps, normalize only the project-authored generation timestamp in the generator before committing.
- [ ] **Step 8: Commit.** `git add providers/step-iges-ocp/worker.py providers/step-iges-ocp/generate_fixtures.py fixtures/v0.2/step-iges tests/test_step_iges_provider.py && git commit -m "test: add ACX-17 STEP IGES source corpus"`.

### Task 3: Native XDE/B-Rep extraction and OCI conformance

**Files:**
- Modify: `providers/step-iges-ocp/worker.py`
- Modify: `tests/test_step_iges_provider.py`
- Create: `docs/licenses/step-iges-ocp-provider.md`
- Create: `docs/security/step-iges-provider-review.md`

**Interfaces:**
- Worker `_transfer_step(path, scanned) -> NativeExtraction` uses `STEPCAFControl_Reader`.
- Worker `_transfer_iges(path, scanned) -> NativeExtraction` uses `IGESCAFControl_Reader`.
- `NativeExtraction` serializes only canonical JSON event payloads plus `artifacts/root-<n>.brep` and `artifacts/scene-mesh.json`; core GLB is created later from the validated mesh artifact.
- Event types are `source_entity`, `product`, `assembly_relation`, `instance`, `shape`, `style`, `diagnostic`, `artifact` with contiguous sequences.

- [ ] **Step 1: Write failing native extraction tests.** Through `ProviderRunner(OCIDockerProfile(image=STEP_IGES_IMAGE))`, assert exact descriptor/image attestation, source entities, schemas/IGES version, product/assembly hierarchy, repeated instances, names/colors/layers, units, finite reversible placements, BREP artifacts, topology counts/bounds/tolerances and GLB bytes.
- [ ] **Step 2: Verify RED.** Run `AECCTX_RUN_STEP_IGES_PROVIDER=1 .venv/bin/python -m pytest tests/test_step_iges_provider.py -k live -q`; expect response failure or missing native events.
- [ ] **Step 3: Implement XDE traversal.** Initialize an XCAF document, enable color/name/layer/material modes, read/transfer, traverse free shapes/components/references with stable label-entry ordering, and map labels back to source model entities wherever OCCT exposes the link. Preserve original STEP/IGES classes and XDE label locators separately.
- [ ] **Step 4: Implement placement/unit evidence.** Emit declared units from source scanner/model, kernel target units, scale/inverse, local/assembly matrices and inverse matrices. Reject non-finite/singular transforms; unresolved mappings remain diagnostic events.
- [ ] **Step 5: Implement BREP and mesh artifacts.** Use `BRepTools.Write_s`/equivalent OCCT ASCII BREP 7.9.3 serialization per root. Traverse vertices/edges/wires/faces/shells/solids for counts, bounds and tolerance range. Mesh with fixed `0.1` linear and `0.5` angular deflection and emit canonical finite vertices/triangle indices in `scene-mesh.json`; do not add another GLB exporter to the provider.
- [ ] **Step 6: Report translator processing and loss.** Capture OCCT read/transfer warnings/failures, failed roots, invalid topology and partial transfer. Always emit `AECCTX_STEP_IGES_TRANSLATOR_PROCESSING_APPLIED` when the fixed translator sequence may heal/convert topology; never label BREP observed or exact.
- [ ] **Step 7: Exercise security/resource failures.** Add live tests for no-network, read-only root, `pids=1`, timeout, memory, file/output/entity limits, external references, corrupt files and cleanup. Provider failure emits a validated error response or ACX-12 execution error and cannot leak paths/stdout into package evidence.
- [ ] **Step 8: Complete license/security records.** Record OCP/OCCT versions, wheel/image hashes, LGPL/OCCT exception obligations, no image redistribution by default, runtime egress/telemetry/retention posture, fixture rights and exact supported platform.
- [ ] **Step 9: Verify live GREEN.** Run `./scripts/verify_step_iges_provider.sh`; expect every live fixture and enforcement test green for the exact image ID.
- [ ] **Step 10: Commit.** `git add providers/step-iges-ocp tests/test_step_iges_provider.py docs/licenses docs/security scripts/verify_step_iges_provider.sh && git commit -m "feat: extract STEP IGES evidence through OCP sandbox"`.

### Task 4: Provider-event validation and neutral package mapping

**Files:**
- Create: `schemas/v0.2/step-iges-provider-event.schema.json`
- Create: `src/aecctx/schemas/v0_2/step-iges-provider-event.schema.json`
- Create: `src/aecctx/step_iges.py`
- Create: `src/aecctx/adapters/step_iges.py`
- Create: `tests/test_step_iges_adapter.py`

**Interfaces:**
- Produces `StepIgesInputError(code, message)`.
- Produces `probe_step_iges(prefix: bytes) -> {format, confidence}` without extension-only detection.
- Produces `validate_step_iges_events(result: ProviderResult) -> StepIgesEvidence`.
- Produces `ingest_step_iges(source_path, output_path, *, created_at=None, embedding_policy="external", package_form="directory", aecctx_version="0.1.0", provider_result: ProviderResult | None = None) -> IngestResult`.

- [ ] **Step 1: Write failing schema/result tests.** Mutate each event family to contain duplicate IDs/sequences, unsafe artifact refs, non-finite matrices, broken source references, unsupported schema/type/form presented as known, observed BREP, tessellation marked exact, host paths and excessive nesting. Expect stable rejection before package construction.
- [ ] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_step_iges_adapter.py -k validation -q`; expect missing module/schema.
- [ ] **Step 3: Add mirrored event schema and semantic validator.** Validate canonical event families, cross-event references, source locator grammar, matrices/inverses, artifact hashes and evidence/fidelity invariants. A failed `ProviderResult` cannot be mapped as successful structured extraction.
- [ ] **Step 4: Write failing mapping tests.** Load committed replay for each positive fixture and assert observed source primitives, XDE-backed neutral entities/relations, explicit units/placements, derived BREP/GLB, capability/loss reports, deterministic directory/ZIP packages and queryable evidence links.
- [ ] **Step 5: Implement v0.2 mapping.** Keep source entities in `evidence/primitives.jsonl`; XDE structure normalization cites observed parents; validate canonical mesh JSON and use the existing `trimesh==4.12.2` convention for derived GLB; BREP/GLB records carry `representation_fidelity`; all provider/runtime/configuration/transfer digests and diagnostics are retained.
- [ ] **Step 6: Preserve v0.1 behavior.** With no v0.2 provider result call the existing opaque ingest path so default and explicit v0.1 packages are byte-identical. v0.2 without a validated result fails with `AECCTX_STEP_IGES_RUNTIME_UNAVAILABLE`; callers may explicitly select normal opaque ingest instead.
- [ ] **Step 7: Verify GREEN.** Run `.venv/bin/python -m pytest tests/test_step_iges_adapter.py tests/test_opaque_ingest.py tests/test_v02_compatibility.py -q`.
- [ ] **Step 8: Commit.** `git add schemas/v0.2/step-iges-provider-event.schema.json src/aecctx/schemas/v0_2 src/aecctx/step_iges.py src/aecctx/adapters/step_iges.py tests/test_step_iges_adapter.py && git commit -m "feat: map STEP IGES provider evidence into v0.2 packages"`.

### Task 5: Replay corpus, CLI and public claims

**Files:**
- Create: `fixtures/v0.2/step-iges/descriptor.json`
- Create: `fixtures/v0.2/step-iges/requests/*.json`
- Create: `fixtures/v0.2/step-iges/outputs/*/response.json`
- Create: `fixtures/v0.2/step-iges/outputs/*/artifacts/*`
- Create: `fixtures/v0.2/step-iges/generate_replay.py`
- Create: `conformance/v0.2/step-iges-corpus.json`
- Modify: `conformance/v0.2/claims.json`
- Modify: `src/aecctx/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `scripts/check_spec_contract.py`
- Modify: `scripts/verify_portable.sh`

**Interfaces:**
- CLI adapter choice adds `step-iges` and content auto-probe.
- CLI adds paired `--provider-replay PATH` and `--provider-entry ID`, valid only with `--adapter step-iges --aecctx-version 0.2.0`.
- Corpus entries reproduce exact requests and validate response/artifact hashes through `validate_provider_replay_corpus`.

- [ ] **Step 1: Generate canonical replay exchanges.** Run each positive/partial/negative fixture through the exact live provider, copy only validated response/artifacts, normalize no runtime evidence, and bind descriptor/input/request/output hashes in `step-iges-corpus.json`.
- [ ] **Step 2: Write failing replay/CLI tests.** Cover portable corpus validation, replay-to-package mapping, auto-probe, explicit adapter, missing/mismatched paired options, v0.1 rejection of replay, provider failure, unsupported schema and deterministic ZIP.
- [ ] **Step 3: Verify RED.** Run `.venv/bin/python -m pytest tests/test_step_iges_provider.py tests/test_step_iges_adapter.py tests/test_cli.py -k 'replay or step_iges' -q`; expect missing corpus/CLI options.
- [ ] **Step 4: Implement CLI replay only.** Load an exact replay entry, verify provider ID, pass `ProviderResult` to `ingest_step_iges`, and never launch Docker from CLI. Auto-probe uses bounded content, not extension alone.
- [ ] **Step 5: Add claims and portable gates.** Register fixture `v02-step-iges-acx17`; add `step-iges.source-structure` and `step-iges.brep-geometry` as exact `experimental partial` claims with Linux-arm64-live/any-replay scope, test IDs and evidence path `docs/evidence/ACX-17.md` created in Task 6. Validate mirrored schema and corpus JSON in portable scripts.
- [ ] **Step 6: Verify GREEN.** Run claim registry validation, replay corpus validation, focused CLI/adapter/provider tests and repeated ZIP byte comparison.
- [ ] **Step 7: Commit.** `git add fixtures/v0.2/step-iges conformance/v0.2 src/aecctx/cli.py tests scripts && git commit -m "feat: publish ACX-17 STEP IGES replay corpus"`.

### Task 6: Documentation, evidence, gates and promotion

**Files:**
- Create: `docs/evidence/ACX-17.md`
- Modify: `README.md`
- Modify: `docs/capability-matrix.md`
- Modify: `docs/compatibility-v0.2.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/implementation-plan.md`

**Interfaces:**
- Evidence binds exact fixture/request/response/artifact/image hashes, tests, license/security records and CI scope.
- Ledger moves ACX-17 to `completed` and only ACX-18 to `pending-next` after every gate passes.

- [ ] **Step 1: Document exact support and commands.** Include SDK live execution, CLI replay, opaque fallback, observed/derived authority, translator-processing loss, platform scope and every residual from the normative profile.
- [ ] **Step 2: Run narrow gates.** Run all ACX-17 tests, JSON/schema checks, `validate_provider_replay_corpus`, claim registry validation, deterministic package checks and clean-core distribution scan.
- [ ] **Step 3: Run live gate.** Run `./scripts/verify_step_iges_provider.sh` against the exact local image and record image ID, runtime, fixture counts, event/artifact hashes and enforcement results.
- [ ] **Step 4: Run repository gates before promotion.** Run `python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues`, `./scripts/verify_portable.sh` and `./scripts/verify.sh`; record exact test/build results.
- [ ] **Step 5: Promote only after green.** Mark ACX-17 `completed`, promote ACX-18 to `pending-next`, update handoff/evidence, run `python scripts/check_spec_contract.py` and `./scripts/verify.sh` again. Do not execute ACX-18.
- [ ] **Step 6: Commit and publish.** Commit coherent implementation/evidence milestones, push `codex/acx-11-shared-expansion-contracts`, wait for Ubuntu/macOS/Windows CI on the exact HEAD and record the run. The live Linux arm64 provider claim remains bound to the separately recorded local OCI gate.

## Plan self-review

- Every normative spec section maps to a task: runtime/license/security (Tasks 1/3), source profiles/locators (Task 2), XDE/BREP/fidelity (Task 3), package authority/loss (Task 4), corpus/claims/CLI (Task 5), residuals/evidence/promotion (Task 6).
- Production behavior always starts with a failing test; generated fixture/image steps are attached to the behavior they prove.
- Provider, event and adapter interfaces use consistent names across tasks.
- No task adds OCCT to core dependencies, follows external references, claims source-exact B-Rep or borrows ACX-18 scope.
- The plan contains no deferred implementation placeholder; exact runtime image ID is a build output that must be committed before live tests or claims.
