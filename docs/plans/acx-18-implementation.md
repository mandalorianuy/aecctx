# ACX-18 DWG Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` and `superpowers:test-driven-development` task-by-task. Subagent dispatch is prohibited for this repository task.

**Goal:** Implement the bounded R2000/AC1015 DWG evidence profile through a reviewed LibreDWG 0.13.4 OCI provider, with portable replay and no GPL dependency in the core distribution.

**Status:** Completed on 2026-07-12. Tasks 1 through 5 passed their narrow, live, portable and repository gates; ACX-19 was promoted but not executed. The unchecked step boxes below are the immutable execution checklist retained for audit; completion authority is `docs/implementation-plan.md` plus `docs/evidence/ACX-18.md`.

**Architecture:** ACX-12 `oci-docker-v1` owns all LibreDWG execution. The provider verifies the DWG header, invokes only fixed `dwgread` JSON/DXF conversions, emits validated source-object events plus content-addressed artifacts, and records conversion loss. The core validates those events, maps observed DWG objects separately from converted DXF geometry, and preserves v0.1 opaque behavior. CLI supports replay only; live Docker execution is an explicit SDK operation.

**Tech Stack:** Python 3.12+, existing ACX-12 provider protocol, Docker Linux arm64, GNU LibreDWG 0.13.4 API/ABI 1, JSON Schema 2020-12, existing ezdxf 1.4.4 and package/record APIs, pytest.

## Global Constraints

- Execute only ACX-18; ACX-19 remains pending.
- Normative authority is `docs/specs/dwg-v02-profile.md` and ACXD-029.
- LibreDWG is GPL-3.0-or-later and never enters `pyproject.toml`, the core wheel/sdist, an in-process extra or the host process.
- The only live profile is an explicitly built, immutable-ID-pinned Linux arm64 `oci-docker-v1` image.
- The shared OCI registration primitive defaults to one PID and admits the exact reviewed value two for ACX-18's mounted worker plus one sequential fixed `dwgread` child; larger or caller-controlled process trees are rejected.
- The only claimed source version is self-contained R2000 with exact `AC1015` header.
- LibreDWG JSON is direct decoder evidence. DXF and all geometry derived from it are converted evidence with input/output hashes and conversion loss.
- Runtime requests expose only fixed `dwgread`; `dxf2dwg` is restricted to explicit project-fixture generation.
- External references, embedded scripts/macros/OLE, proxy/custom objects and source commands are inert data and never executed or opened.
- Missing, unsupported, conflicted and failed facts remain explicit; no units, CRS, geometry, hierarchy or labels are guessed.
- Default and explicit v0.1 behavior remain byte-identical opaque ingest.
- Every behavior change starts with a failing test; every task ends with a narrow green gate and coherent commit.

---

### Task 1: Reviewed image, descriptor and registration

**Files:**
- Create: `providers/libredwg/Dockerfile`
- Create: `providers/libredwg/README.md`
- Create: `src/aecctx/providers/dwg.py`
- Modify: `src/aecctx/providers/__init__.py`
- Create: `tests/test_dwg_provider.py`
- Create: `scripts/build_dwg_provider.sh`
- Create: `scripts/verify_dwg_provider.sh`

**Interfaces:**
- Produces constants `DWG_PROVIDER_ID`, `DWG_IMAGE`, `DWG_IMAGE_ID`, `DWG_CONFIGURATION`, and `DWG_WORKER_MODULE`.
- Produces `dwg_descriptor() -> ProviderDescriptor`.
- Produces `dwg_registry(repository_root: str | Path | None = None) -> ProviderRegistry`.
- Registration launches only `python3 /provider/worker.py`; callers never supply a command.

- [ ] **Step 1: Write failing descriptor and distribution-boundary tests.** Assert provider ID `org.aecctx.dwg.libredwg`, version `0.2.0`, runtime `python-3.12+libredwg-0.13.4-api1`, license `GPL-3.0-or-later`, `linux-container`, every enforcement axis, exact configuration, allowlisted worker path/command, and absence of `libredwg`/GPL dependencies from `pyproject.toml`.
- [ ] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_dwg_provider.py -k 'registration or core_distribution' -q`; expect import failure for `aecctx.providers.dwg`.
- [ ] **Step 3: Add the deterministic image recipe.** Use the reviewed Ubuntu Noble arm64 base digest already accepted by ACX-17. Download the official 0.13.4 tar.xz, verify SHA-256 `7e153ea4dac4cbf3dc9c50b9ef7a5604e09cdd4c5520bcf8017877bbe1422cd5`, build with `./configure --enable-release`, run exact upstream `programs/dxf.test` (the governed aggregate `alive.test` failure remains recorded), install, remove compiler/source/cache packages in the final stage, and run as UID/GID 65532 with fixed locale/hash settings.
- [ ] **Step 4: Build explicitly and capture immutable evidence.** Run `./scripts/build_dwg_provider.sh` twice with volatile BuildKit provenance disabled; require the same inspected ID both times and record it in `DWG_IMAGE_ID`, worker constants and license/security records. An ID change requires review and cannot auto-update.
- [ ] **Step 5: Implement descriptor/registry and public exports.** Follow the ACX-17 registration pattern, using image tag plus immutable local ID and allowlisted worker module `aecctx.external.libredwg_worker`.
- [ ] **Step 6: Verify GREEN.** Run the focused tests and `docker run --rm --network=none --read-only --user=65532:65532 aecctx-dwg-libredwg:0.2.0 dwgread --version`; assert exact 0.13.4 runtime and no network/write need.
- [ ] **Step 7: Commit.** Commit as `feat: register reviewed ACX-18 LibreDWG provider`.

### Task 2: Project-authored fixture and bounded provider worker

**Files:**
- Create: `providers/libredwg/worker.py`
- Create: `fixtures/v0.2/dwg/generate_fixture.py`
- Create: `fixtures/v0.2/dwg/generate_fixture.sh`
- Generate: `fixtures/v0.2/dwg/r2000-profile.dxf`
- Generate: `fixtures/v0.2/dwg/r2000-profile.dwg`
- Create: `fixtures/v0.2/dwg/wrong-version.dwg`
- Create: `fixtures/v0.2/dwg/truncated.dwg`
- Modify: `tests/test_dwg_provider.py`
- Create: `docs/licenses/libredwg-provider.md`
- Create: `docs/security/dwg-provider-review.md`

**Interfaces:**
- Pure worker helpers remain importable without LibreDWG: `_configuration(request)`, `_probe(data)`, `_validate_source_json(value, limits)`, `_canonical(value)`.
- Worker entrypoint reads `request.json`, invokes fixed absolute `/opt/libredwg/bin/dwgread` argument arrays, and writes `output/response.json`, `output/artifacts/source.json`, and `output/artifacts/converted-r2000.dxf`.
- Source event schema is `aecctx.dwg.source.v1`; conversion event schema is `aecctx.dwg.conversion.v1`.

- [ ] **Step 1: Write failing pure boundary tests.** Cover exact configuration, `AC1015` content probe, wrong/truncated headers, recursive/excessive JSON, conflicted/malformed handles, host paths, non-finite values, external-reference strings retained as inert data, and deterministic canonicalization.
- [ ] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_dwg_provider.py -k 'configuration or probe or source_json' -q`; expect missing worker/helpers.
- [ ] **Step 3: Implement pure validation.** Accept only the canonical configuration. Require exact `AC1015`; reject other headers with `AECCTX_DWG_VERSION_UNCLAIMED`. Validate top-level LibreDWG `FILEHEADER`, `HEADER`, `CLASSES` and `OBJECTS` containers, bounded recursion/records/strings, finite JSON numbers and normalized uppercase handle locators. Preserve duplicates with occurrence locators and explicit conflict; never resolve ambiguous references. Do not reinterpret unknown objects.
- [ ] **Step 4: Generate the positive fixture.** `generate_fixture.py` uses ezdxf 1.4.4 to create an R2000 DXF containing two layers, model/paper layouts, a named block with ATTDEF, two INSERT/ATTRIB instances, LINE, CIRCLE, ARC, LWPOLYLINE, POINT, 3DFACE, TEXT and MTEXT plus one inert xref path string. `generate_fixture.sh` invokes only `dxf2dwg --as r2000` inside the exact reviewed image and copies the resulting `AC1015` DWG. Negative fixtures mutate project-authored bytes only.
- [ ] **Step 5: Verify fixture rights and determinism.** Regenerate twice, compare source hashes, assert `AC1015`, and parse with `dwgread -O JSON` and `dwgread -O DXF`. Document why writer limitations restrict the public corpus to R2000.
- [ ] **Step 6: Write failing live extraction tests.** Through `ProviderRunner`, assert exact attestation, source JSON object/handle evidence, converted DXF artifact, conversion hashes, xref non-resolution, partial capability/loss, deterministic repeated output, wrong-version rejection and runtime/resource failures.
- [ ] **Step 7: Implement the worker.** Use `subprocess.run` with fixed arrays, no shell, minimal environment, output byte checks and stable return-code mapping. Canonicalize JSON only after strict parse/limits. Hash exact input, canonical JSON and DXF. Emit sequential events and full ACX-12 attestation; retain LibreDWG warnings as stable diagnostic codes without raw host paths.
- [ ] **Step 8: Complete license/security review.** Record source/archive/image hashes, GPL obligations, no image redistribution by default, no entitlement/network/telemetry/retention, upstream beta/advanced-object limits, the February 2026 heap-overflow report and whether 0.13.4 contains the fix. Keep the sandbox mandatory regardless.
- [ ] **Step 9: Verify live GREEN.** Run `./scripts/verify_dwg_provider.sh`; require exact image ID, positive extraction, deterministic parity and rejection tests.
- [ ] **Step 10: Commit.** Commit as `feat: extract bounded R2000 evidence through LibreDWG sandbox`.

### Task 3: Event schema and neutral v0.2 package mapping

**Files:**
- Create: `schemas/v0.2/dwg-provider-event.schema.json`
- Create: `src/aecctx/schemas/v0_2/dwg-provider-event.schema.json`
- Create: `src/aecctx/dwg.py`
- Create: `src/aecctx/adapters/dwg.py`
- Create: `tests/test_dwg_adapter.py`

**Interfaces:**
- Produces `DWGInputError(code, message)`.
- Produces `probe_dwg(prefix: bytes) -> dict[str, float | str]`.
- Produces `validate_dwg_events(result: ProviderResult) -> DWGEvidence`.
- Produces `ingest_dwg(source_path, output_path, *, created_at=None, embedding_policy="external", package_form="directory", aecctx_version="0.1.0", provider_result: ProviderResult | None = None) -> IngestResult`.

- [ ] **Step 1: Write failing event-schema tests.** Mutate event sequence, source schema, duplicate/broken handles, unsafe artifact refs, hash/version mismatch, direct-versus-converted fidelity, host paths, non-finite geometry and excessive nesting. Expect stable rejection before package construction.
- [ ] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_dwg_adapter.py -k validation -q`; expect missing schema/module.
- [ ] **Step 3: Add mirrored schema and semantic validator.** Validate exact source/conversion payload families, artifact media types/hashes, input/output digest chain, `AC1015`, handle grammar/references and conversion fidelity. Failed `ProviderResult` cannot map as successful structured extraction.
- [ ] **Step 4: Write failing mapping tests.** Use a validated provider result to assert observed source-object primitives, neutral layer/block/insert entities/relations backed by handles, explicit unit/CRS states, converted DXF artifact, converted simple geometry primitives, capability/loss, deterministic directory/ZIP packages and queryable evidence links.
- [ ] **Step 5: Implement v0.2 mapping.** Keep every bounded LibreDWG object as observed evidence. Normalize only corpus-proven layers, blocks, inserts and text. Parse the validated converted DXF bytes with ezdxf 1.4.4 and normalize only LINE/POINT/CIRCLE/ARC/LWPOLYLINE/3DFACE/INSERT/TEXT/MTEXT/ATTRIB/ATTDEF as `derived` converted evidence citing the DWG object when handle parity exists. Unmatched handles remain explicit conversion loss.
- [ ] **Step 6: Preserve v0.1 behavior.** Default and explicit v0.1 call `ingest_opaque` and are byte-identical. v0.2 without a validated result fails with `AECCTX_DWG_RUNTIME_UNAVAILABLE`; callers may separately choose opaque ingest.
- [ ] **Step 7: Verify GREEN.** Run `.venv/bin/python -m pytest tests/test_dwg_adapter.py tests/test_opaque_ingest.py tests/test_v02_compatibility.py -q`.
- [ ] **Step 8: Commit.** Commit as `feat: map LibreDWG evidence into v0.2 packages`.

### Task 4: Replay corpus, CLI and experimental claim

**Files:**
- Create: `fixtures/v0.2/dwg/descriptor.json`
- Create: `fixtures/v0.2/dwg/requests/r2000-profile.json`
- Create: `fixtures/v0.2/dwg/outputs/r2000-profile/response.json`
- Create: `fixtures/v0.2/dwg/outputs/r2000-profile/artifacts/*`
- Create: `fixtures/v0.2/dwg/generate_replay.py`
- Create: `conformance/v0.2/dwg-corpus.json`
- Modify: `conformance/v0.2/claims.json`
- Modify: `src/aecctx/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_dwg_provider.py`
- Modify: `scripts/check_spec_contract.py`
- Modify: `scripts/verify_portable.sh`

**Interfaces:**
- CLI adapter choice adds `dwg` and content probe after IFC/STEP discrimination.
- Existing paired `--provider-replay PATH` and `--provider-entry ID` accept the DWG provider only with `--adapter dwg --aecctx-version 0.2.0`.
- Corpus entries reproduce exact request and validate response/artifact hashes through `validate_provider_replay_corpus`.

- [ ] **Step 1: Generate canonical replay.** Run the positive fixture through the exact live provider, retain the validated response/artifacts without altering runtime evidence, and bind descriptor/input/request/output paths in `dwg-corpus.json`.
- [ ] **Step 2: Write failing replay/CLI tests.** Cover portable corpus validation, replay-to-package mapping, auto-probe, explicit adapter, missing/mismatched paired options, v0.1 replay rejection, provider failure, wrong version and deterministic ZIP.
- [ ] **Step 3: Verify RED.** Run focused provider/adapter/CLI replay tests and confirm missing corpus/adapter behavior.
- [ ] **Step 4: Implement CLI replay only.** Load the exact replay entry, verify `org.aecctx.dwg.libredwg`, pass the result to `ingest_dwg`, and never launch Docker from CLI. Preserve IFC precedence, then STEP/IGES, then DWG content probes.
- [ ] **Step 5: Register exact claim and portable gates.** Add fixture `v02-dwg-acx18`; promote `dwg.external-provider` to exact `experimental partial` only with test IDs and `docs/evidence/ACX-18.md`. Validate mirrored schema and replay corpus in portable scripts.
- [ ] **Step 6: Verify GREEN.** Run claim registry validation, replay validation, focused tests and repeated ZIP comparison.
- [ ] **Step 7: Commit.** Commit as `feat: publish ACX-18 DWG replay corpus`.

### Task 5: Documentation, full gates and promotion

**Files:**
- Create: `docs/evidence/ACX-18.md`
- Modify: `README.md`
- Modify: `docs/capability-matrix.md`
- Modify: `docs/compatibility-v0.2.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/implementation-plan.md`
- Modify: `docs/plans/acx-18-implementation.md`

**Interfaces:**
- Evidence binds exact source/archive/image/request/response/artifact hashes, tests, license/security records and CI scope.
- Ledger moves ACX-18 to `completed` and only ACX-19 to `pending-next` after every gate passes.

- [ ] **Step 1: Document exact support and commands.** Include SDK live execution, CLI replay, opaque fallback, direct/converted authority, conversion loss, platform scope and every residual.
- [ ] **Step 2: Run narrow gates.** Run all ACX-18 tests, JSON/schema checks, replay validation, claim registry validation, deterministic package checks and core-distribution scans.
- [ ] **Step 3: Run live gate.** Run `./scripts/verify_dwg_provider.sh` against the exact image and record image ID/runtime/test counts.
- [ ] **Step 4: Run repository gates.** Run `python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues`, `./scripts/verify_portable.sh` and `./scripts/verify.sh`.
- [ ] **Step 5: Promote only after green.** Mark ACX-18 `completed`, promote ACX-19 to `pending-next`, update handoff/evidence, run spec contract and full verify again. Do not execute ACX-19.
- [ ] **Step 6: Commit and publish.** Commit the milestone, push `codex/acx-11-shared-expansion-contracts`, wait for Ubuntu/macOS/Windows CI on the exact HEAD and record the run.

## Plan self-review

- Spec sections map to tasks: provider/license/security (Tasks 1-2), source/conversion evidence (Tasks 2-3), package/CLI/replay/claims (Tasks 3-4), documentation/residuals/promotion (Task 5).
- No production behavior precedes its failing test.
- LibreDWG execution stays exclusively in OCI and no GPL artifact enters the core distribution.
- Direct JSON evidence and converted DXF/geometry remain machine-distinct with complete hash lineage.
- The public target is only R2000/AC1015; all other DWG versions and proprietary content remain explicit residuals.
- No task adds consumer semantics, network, LLM, WoodFraming, RVT, signing or quality-gate scope.
- The immutable image ID is a reviewed build output that must be committed before live tests or claims; it is not guessed in this plan.
