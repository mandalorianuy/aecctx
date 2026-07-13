# ACX-21 Delivery Quality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` and `superpowers:test-driven-development` task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not dispatch subagents unless the user explicitly authorizes delegation.

**Goal:** Implement a deterministic, local-first AEC delivery policy gate over validated AECCTX evidence, optional semantic baseline diff and a bounded buildingSMART IDS 1.0 subset without implying engineering or consumer approval.

**Architecture:** `src/aecctx/gate/` owns closed policy/result models, strict canonical parsing, deterministic evaluation, diff/IDS adapters and derived projections. Core checks consume existing validation, `RecordStore` and `PackageDiff` APIs; IDS runs only when explicitly requested through a fixed bounded local worker using optional pinned IfcTester/IfcOpenShell dependencies. Canonical JSON is authoritative and Markdown/CI annotations are pure projections.

**Tech Stack:** Python 3.12+, JSON Schema 2020-12, existing AECCTX v0.1/v0.2 validation/records/diff APIs, optional `ifctester==0.8.5` plus `ifcopenshell==0.8.5`, pytest, hatchling, buildingSMART IDS 1.0 unchanged conformance fixtures.

**Execution status:** Tasks 1-9 completed on 2026-07-13. ACX-21 is accepted, published and public `partial` for the exact governed profile. ACX-22 is `pending-next` but has not executed.

## Global Constraints

- Execute only ACX-21. ACX-22 remains `pending` and is only promoted, never executed, by this plan.
- Normative authorities are `docs/specs/quality-gate-v02-profile.md`, expansion-spec section 13, ACXD-021, ACXD-023 and the ACX-21 section of `docs/implementation-plan.md`.
- A gate result expresses policy conformance only. It never expresses engineering approval, regulatory acceptance, construction readiness, source authorship or consumer canonical acceptance.
- Candidate and optional baseline packages must pass existing structural/integrity validation before policy evaluation. Invalid packages produce `error`.
- Canonical result JSON is authoritative. Markdown and CI annotations are deterministic projections with no unique semantics.
- Policies, IDS, IFC sources, packages, dependency output and projection text are untrusted data.
- No expression language, regex, template, callback, import, URL fetch, schema-location fetch, XInclude, macro, shell or caller-selected command is accepted.
- `unknown`, `unsupported`, `conflicted`, `explicit_null` and `not_applicable` remain explicit. Every value-state policy maps all five states to `allow`, `requires_review` or `fail`.
- Active waivers target one exact finding fingerprint and force at least `requires_review`; no waiver creates `pass` or targets a system check.
- IDS support is limited to buildingSMART IDS v1.0.0 simple-value cases, IFC2X3/IFC4, and the exact facet/cardinality combinations proven by unchanged official plus project-authored fixtures.
- `partOf`, XSD restrictions, URI dereference, bSDD lookup, unlisted IFC/IDS versions and unproven official cases remain explicit unsupported findings.
- `ifctester==0.8.5` and `ifcopenshell==0.8.5` are optional under a new `gate-ids` extra. Core install and non-IDS gate checks remain usable without them.
- The IDS worker is fixed by AECCTX, runs without a shell, receives content-addressed bounded inputs, uses no network and emits schema-validated bounded JSON.
- Existing packages, package digests, source bytes and baselines are read-only. Gate outputs are detached new files.
- Every behavior change starts with a failing test, ends with a narrow green gate and receives a coherent commit.
- No task adds WoodFraming, `WFDomain`, `WFImport`, consumer mapping, source write-back, network or LLM requirements.

## File and responsibility map

| File | Responsibility |
|---|---|
| `src/aecctx/gate/__init__.py` | Public `evaluate_gate`, models, limits and stable error exports |
| `src/aecctx/gate/models.py` | Immutable policy/check/waiver/finding/result dataclasses and enums |
| `src/aecctx/gate/policy.py` | Strict bounded JSON, canonicalization, schema registry, semantic validation and digest |
| `src/aecctx/gate/evaluator.py` | Preflight, core check dispatch, waiver application and aggregate outcome |
| `src/aecctx/gate/diff_checks.py` | `PackageDiff` regression policy mapping and exact evidence citations |
| `src/aecctx/gate/ids.py` | IDS/IFC source binding, worker invocation and normalized result mapping |
| `src/aecctx/gate/_ids_worker.py` | Fixed optional IfcTester/IfcOpenShell worker with closed JSON protocol |
| `src/aecctx/gate/projection.py` | Markdown and CI-annotation projections from `GateResult` only |
| `schemas/v0.2/gate-*.schema.json` | Public policy/check/waiver/result contracts |
| `src/aecctx/schemas/v0_2/gate-*.schema.json` | Byte-identical packaged schema mirrors |
| `tests/test_gate_contract.py` | Public types, schemas, IDs, enums, package data and closed documents |
| `tests/test_gate_policy.py` | Strict parsing, canonical digest, limits and malicious policy inputs |
| `tests/test_gate_checks.py` | Preflight, capability, loss, value-state, diagnostic, waiver and aggregation behavior |
| `tests/test_gate_diff.py` | Baseline validation and every stable semantic diff category |
| `tests/test_gate_ids.py` | IDS profile, source binding, worker safety, optional dependency and official cases |
| `tests/test_gate_cli.py` | CLI/SDK parity, output safety, exits and projections |
| `tests/test_gate_conformance.py` | Corpus replay, determinism, packaging, clean install and claim mapping |
| `fixtures/v0.2/gate/` | Project-authored policies/packages/IDS/IFC inputs and expected outputs |
| `fixtures/third_party/buildingsmart-ids-1.0/` | Unchanged attributed official IDS 1.0 fixture subset |
| `conformance/v0.2/gate-corpus.json` | Case/input/hash/expected result and claim mapping |
| `scripts/check_gate_conformance.py` | Portable corpus/schema/hash/result verifier |

---

### Task 1: Closed schemas and public result types

**Files:**
- Create: `schemas/v0.2/gate-check.schema.json`
- Create: `schemas/v0.2/gate-waiver.schema.json`
- Create: `schemas/v0.2/gate-policy.schema.json`
- Create: `schemas/v0.2/gate-result.schema.json`
- Create identical mirrors under `src/aecctx/schemas/v0_2/`
- Create: `src/aecctx/gate/__init__.py`
- Create: `src/aecctx/gate/models.py`
- Create: `tests/test_gate_contract.py`
- Modify: `tests/test_package_data.py`

**Interfaces:**
- Produce `GateLimits(max_policy_bytes=1_048_576, max_ids_bytes=1_048_576, max_checks=256, max_waivers=1024, max_ifc_bytes=268_435_456, max_findings=100_000, max_result_bytes=16_777_216, ids_timeout_seconds=60.0)`.
- Produce immutable `GateCheckPolicy`, `GateWaiver`, `GatePolicy`, `GateFinding`, `GateCheckResult`, `GateDiagnostic`, `GateResult`.
- Produce `GateError(code: str, message: str)` with no raw input or traceback leakage.
- Define exact outcome/status/severity/check-kind/value-action enums from the normative profile.
- `GateResult.to_dict() -> dict[str, Any]` is the only source for serialization/projections.

- [x] **Step 1: Write failing schema-mirror and public-type tests.**

```python
from importlib.resources import files

from aecctx.gate import GateFinding, GateLimits


def test_gate_limits_match_the_profile() -> None:
    limits = GateLimits()
    assert limits.max_checks == 256
    assert limits.max_waivers == 1_024
    assert limits.ids_timeout_seconds == 60.0


def test_gate_finding_keeps_state_and_evidence_explicit() -> None:
    finding = GateFinding(
        code="AECCTX_GATE_VALUE_STATE_UNSUPPORTED",
        check_id="aecctx.policy.required-values",
        severity="error",
        subject_id="assertion:door-fire-rating",
        observed_state="unsupported",
        evidence_refs=("assertion:door-fire-rating",),
        fingerprint="0" * 64,
        message="required value is unsupported",
    )
    assert finding.observed_state == "unsupported"
    assert finding.evidence_refs == ("assertion:door-fire-rating",)


def test_public_and_packaged_gate_schemas_are_identical() -> None:
    public = open("schemas/v0.2/gate-result.schema.json", "rb").read()
    packaged = files("aecctx.schemas.v0_2").joinpath("gate-result.schema.json").read_bytes()
    assert public == packaged
```

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_gate_contract.py tests/test_package_data.py -q`; expect import/file failures for the new gate contract.

- [x] **Step 3: Add four closed Draft 2020-12 schemas.** Use `additionalProperties: false`, exact enum sets, bounded arrays/strings, lowercase SHA-256 patterns, unique IDs and conditional check configuration by `kind`. `gate-policy` references the fixed public `$id` values for check/waiver; `gate-result` requires candidate/policy identity, outcome, exit code, evaluator versions, checks, findings and diagnostics.

```json
{
  "$id": "https://aecctx.dev/schemas/v0.2/gate-waiver.schema.json",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["waiver_id", "check_id", "finding_fingerprint", "reason", "approved_by", "issued_at", "expires_at"],
  "properties": {
    "waiver_id": {"type": "string", "pattern": "^[a-z][a-z0-9._-]{0,63}$"},
    "check_id": {"type": "string", "pattern": "^[a-z][a-z0-9._-]{0,63}$"},
    "finding_fingerprint": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    "reason": {"type": "string", "minLength": 1, "maxLength": 4096},
    "approved_by": {"type": "string", "minLength": 1, "maxLength": 4096},
    "issued_at": {"type": "string", "format": "date-time"},
    "expires_at": {"type": "string", "format": "date-time"}
  }
}
```

- [x] **Step 4: Add immutable exact-state dataclasses.** Validate enum membership and normalized tuple ordering at construction; reject mutable/raw mappings as public result state.

```python
CHECK_KINDS = frozenset({
    "capability.minimum", "loss.maximum", "value_state.action",
    "diagnostic.maximum", "diff.regression", "ids.specification",
})
CHECK_STATUSES = frozenset({"pass", "fail", "requires_review", "waived", "error"})
OUTCOMES = frozenset({"pass", "fail", "requires_review", "error"})
SEVERITIES = ("info", "warning", "error", "blocking")
VALUE_ACTIONS = frozenset({"allow", "requires_review", "fail"})


class GateError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
```

- [x] **Step 5: Export only the governed public facade.** `gate/__init__.py` exports models/limits/error now and reserves `evaluate_gate` for Task 4; no implementation stub returns a false result.

- [x] **Step 6: Verify GREEN and package data.** Run `.venv/bin/python -m pytest tests/test_gate_contract.py tests/test_package_data.py -q`; run `.venv/bin/python -m json.tool` over all eight public/mirrored schema files.

- [x] **Step 7: Commit.**

```bash
git add schemas/v0.2/gate-*.schema.json src/aecctx/schemas/v0_2/gate-*.schema.json \
  src/aecctx/gate/__init__.py src/aecctx/gate/models.py \
  tests/test_gate_contract.py tests/test_package_data.py
git commit -m "feat: define ACX-21 gate contracts"
```

### Task 2: Strict policy parsing, canonical digest and limits

**Files:**
- Create: `src/aecctx/gate/policy.py`
- Modify: `src/aecctx/gate/__init__.py`
- Modify: `src/aecctx/gate/models.py`
- Modify: `src/aecctx/schemas/v0_2/gate-waiver.schema.json`
- Modify: `schemas/v0.2/gate-waiver.schema.json`
- Modify: `src/aecctx/schemas/v0_2/gate-policy.schema.json`
- Modify: `schemas/v0.2/gate-policy.schema.json`
- Modify: `docs/HANDOFF.md`
- Create: `tests/test_gate_policy.py`
- Modify: `tests/test_gate_contract.py`

**Interfaces:**
- Produce `load_gate_policy(data: bytes, *, limits=GateLimits()) -> GatePolicy`.
- Produce `read_gate_document(path, *, maximum_bytes: int, label: str) -> bytes` rejecting symlinks/non-regular files.
- Produce `canonical_gate_json(value: Any) -> bytes` with strict duplicate rejection, NFC normalization and one LF.
- Produce `validate_gate_document(value, schema_name) -> None` with an offline `referencing.Registry` containing all four packaged schemas.
- `GatePolicy.digest` is SHA-256 of canonical parsed policy bytes.
- Section 13 defaults are v1 hard maxima. JSON depth uses scalar depth 0/root-container depth 1. Waivers use the full `aecctx.policy.<check-id>` result ID and reference a declared policy check.

- [x] **Step 1: Write failing strict-input and canonicalization tests.** Cover duplicate keys, normalized-key collisions, invalid UTF-8, NaN/Infinity, booleans in integer slots, unknown fields, full SemVer 2.0.0/time validation, duplicate IDs, check/waiver overflow, nesting depth including parser recursion exhaustion, symlink inputs, non-expandable hard maxima and exact declared waiver targets.

```python
def test_policy_digest_is_independent_of_json_whitespace_and_key_order() -> None:
    left = load_gate_policy(b'{"profile":"https://aecctx.dev/gate/v1","policy_id":"p","policy_version":"1.0.0","evaluation_time":"2026-01-01T00:00:00Z","checks":[],"waivers":[]}')
    right = load_gate_policy(b'{ "waivers": [], "checks": [], "evaluation_time": "2026-01-01T00:00:00Z", "policy_version": "1.0.0", "policy_id": "p", "profile": "https://aecctx.dev/gate/v1" }')
    assert left.digest == right.digest
    assert left.canonical_bytes == right.canonical_bytes


def test_policy_rejects_duplicate_check_ids() -> None:
    with pytest.raises(GateError) as caught:
        load_gate_policy(policy_bytes(checks=[capability_check("same"), capability_check("same")]))
    assert caught.value.code == "AECCTX_GATE_CHECK_ID_DUPLICATE"
```

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_gate_policy.py -q`; expect missing `aecctx.gate.policy` and facade functions.

- [x] **Step 3: Implement strict JSON/NFC primitives.** Adapt the proven signing strict-JSON pattern without importing private signing semantics. Reject normalized key collisions, finite-number violations and recursion deeper than 32 before schema validation.

- [x] **Step 4: Build the fixed offline schema registry.** Load only `gate-check.schema.json`, `gate-waiver.schema.json`, `gate-policy.schema.json` and `gate-result.schema.json` via `importlib.resources`; no input `$schema` or URI causes a fetch.

```python
resources = {
    schema["$id"]: Resource.from_contents(schema)
    for schema in packaged_gate_schemas()
}
registry = Registry().with_resources(resources.items())
validator = Draft202012Validator(policy_schema, registry=registry, format_checker=FormatChecker())
```

- [x] **Step 5: Implement semantic validation.** Require exact profile, semver, UTC `Z` instant, unique check/waiver IDs, no `aecctx.system.*` policy ID, all five value-state actions, baseline/IDS configuration only on matching kinds, exact full waiver result IDs referencing declared policy checks, and waiver interval `issued_at < expires_at`. Correct the Task 1 waiver schema/model to enforce the same full-ID contract before parsing can rely on it.

- [x] **Step 6: Verify GREEN and deterministic digest.** Run `.venv/bin/python -m pytest tests/test_gate_policy.py tests/test_gate_contract.py -q` twice and assert the golden digest stays identical.

- [x] **Step 7: Commit.**

```bash
git add docs/specs/quality-gate-v02-profile.md docs/decisions/decision-log.md \
  docs/plans/acx-21-implementation.md schemas/v0.2/gate-policy.schema.json \
  schemas/v0.2/gate-waiver.schema.json src/aecctx/schemas/v0_2/gate-policy.schema.json \
  src/aecctx/schemas/v0_2/gate-waiver.schema.json src/aecctx/gate/models.py \
  src/aecctx/gate/policy.py src/aecctx/gate/__init__.py \
  tests/test_gate_contract.py tests/test_gate_policy.py
git commit -m "feat: parse deterministic gate policies"
```

### Task 3: Finding identity, waivers and aggregate outcomes

**Files:**
- Create: `src/aecctx/gate/evaluator.py`
- Create: `tests/test_gate_checks.py`
- Modify: `src/aecctx/gate/__init__.py`
- Modify: `src/aecctx/gate/models.py`
- Modify: `schemas/v0.2/gate-result.schema.json`
- Modify: `src/aecctx/schemas/v0_2/gate-result.schema.json`
- Modify: `tests/test_gate_contract.py`
- Modify: `docs/specs/quality-gate-v02-profile.md`
- Modify: `docs/decisions/decision-log.md`
- Modify: `docs/implementation-plan.md`
- Modify: `docs/HANDOFF.md`

**Interfaces:**
- Produce `finding_fingerprint(*, check_id, code, subject_id, observed_state, evidence_refs) -> str`.
- Produce `apply_waivers(checks, policy) -> tuple[tuple[GateCheckResult, ...], tuple[GateDiagnostic, ...]]`.
- Produce `aggregate_gate_outcome(checks) -> tuple[str, int]`.
- Finding fingerprints exclude message text and include sorted unique evidence refs.
- `GateFinding.disposition` is one of `error`, `fail`, `requires_review` or `waived`; `waived` requires `waiver_id` and other dispositions require null. Fingerprints are unique per check and non-empty check results equal their highest finding disposition except for the governed active-mismatch review floor. Waiver application classifies against the original set, applies exact mutations collectively, recomputes mixed-finding status, applies the floor once and never infers disposition from severity.

- [x] **Step 1: Write failing aggregation tests for all precedence combinations.** Include pass, review, fail, error, mixed order, message-independent fingerprint, evidence normalization, mixed finding dispositions, active waiver, expired waiver, not-yet-valid waiver, mismatched fingerprint, duplicate target, invalid lifecycle and attempted system-check waiver.

```python
@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        (("pass",), ("pass", 0)),
        (("pass", "requires_review"), ("requires_review", 1)),
        (("waived",), ("requires_review", 1)),
        (("requires_review", "fail"), ("fail", 1)),
        (("fail", "error"), ("error", 2)),
    ],
)
def test_aggregate_precedence(statuses: tuple[str, ...], expected: tuple[str, int]) -> None:
    assert aggregate_gate_outcome(tuple(check_result(status) for status in statuses)) == expected
```

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_gate_checks.py -q`; expect missing evaluator functions.

- [x] **Step 3: Implement canonical finding fingerprints.** Normalize the exact identity object, reject empty check/code/subject, sort unique evidence refs and hash canonical bytes.

- [x] **Step 4: Implement waiver lifecycle against policy `evaluation_time`.** Active is `issued_at <= evaluation_time < expires_at`; expired/not-yet-valid waivers retain the original finding/check and add stable warning diagnostics. An active exact waiver preserves finding identity/evidence/message, sets `waiver_id`, changes only `fail`/`requires_review` disposition to `waived` and recomputes the check from all finding dispositions. An active mismatch adds a review diagnostic and floors its check at `requires_review`. Classify against the original check set and apply exact mutations plus the final floor as a batch so policy order is immaterial.

- [x] **Step 5: Reject unsafe waiver behavior.** No wildcard, no system/missing check, no duplicate target, no invalid policy clock/interval, no error/already-waived target and no policy clock fallback. Invalid control state raises a stable `GateError`; lifecycle evidence remains in the separately returned diagnostics.

- [x] **Step 6: Verify GREEN and order independence.** Run `.venv/bin/python -m pytest tests/test_gate_checks.py -q`; shuffle input check/finding order and prove canonical output order/outcome unchanged.

- [x] **Step 7: Commit.**

```bash
git add docs/specs/quality-gate-v02-profile.md docs/decisions/decision-log.md \
  docs/implementation-plan.md docs/plans/acx-21-implementation.md docs/HANDOFF.md \
  schemas/v0.2/gate-result.schema.json src/aecctx/schemas/v0_2/gate-result.schema.json \
  src/aecctx/gate/evaluator.py src/aecctx/gate/models.py src/aecctx/gate/__init__.py \
  tests/test_gate_contract.py tests/test_gate_checks.py
git commit -m "feat: aggregate gate outcomes and waivers"
```

### Task 4: Candidate preflight and authoritative package checks

**Files:**
- Modify: `src/aecctx/gate/evaluator.py`
- Modify: `src/aecctx/gate/__init__.py`
- Modify: `src/aecctx/gate/models.py`
- Modify: `schemas/v0.2/gate-result.schema.json`
- Modify: `src/aecctx/schemas/v0_2/gate-result.schema.json`
- Modify: `schemas/v0.2/gate-check.schema.json`
- Modify: `src/aecctx/schemas/v0_2/gate-check.schema.json`
- Modify: `tests/test_gate_contract.py`
- Modify: `tests/test_gate_checks.py`
- Modify: `src/aecctx/records.py` only if a read-only iterator is required; do not change record authority
- Modify: this profile/decision/plan/HANDOFF governance when Task 4 changes behavior or status

**Interfaces:**
- Produce `evaluate_gate(candidate_package, policy, *, baseline_package=None, ids_document=None, ifc_source=None, limits=GateLimits()) -> GateResult`.
- Produce internal `evaluate_capability_check`, `evaluate_loss_check`, `evaluate_value_state_check`, `evaluate_diagnostic_check`.
- System preflight check IDs are fixed and non-waivable.
- Invalid preflight returns a valid error result with `candidate: null`; non-error results require exact candidate identity.
- Evaluate records only from a revalidated private snapshot; reject candidate mutation and symlink roots.
- Task 5/6 checks or optional inputs fail closed with the governed not-implemented error until those tasks land.

- [x] **Step 1: Write failing preflight/core-check tests.** Cover invalid hash/digest/schema, missing capability, support-level ordering, loss totals/reason budgets, all five value states/actions, field-path selection, diagnostic severity/code budgets and missing evidence.

```python
def test_unknown_state_fails_only_by_explicit_policy_action(tmp_path: Path) -> None:
    package = package_with_assertion(tmp_path, {"state": "unknown", "reason_code": "NOT_OBSERVED"})
    result = evaluate_gate(package, value_state_policy(unknown="fail"))
    assert result.outcome == "fail"
    assert result.findings[0].observed_state == "unknown"
    assert result.findings[0].evidence_refs == ("assertion:test",)


def test_invalid_candidate_is_error_not_policy_failure(mutated_fixture: Path) -> None:
    result = evaluate_gate(mutated_fixture, empty_policy())
    assert result.outcome == "error"
    assert result.exit_code == 2
    assert result.checks[0].check_id == "aecctx.system.validation"
```

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_gate_checks.py -q`; expect missing `evaluate_gate` and check dispatch.

- [x] **Step 3: Implement validation/integrity preflight.** Call `validate_package` first, never open `RecordStore` on invalid input, bind package ID/version/logical digest and map existing diagnostics without copying unsafe source text. Copy accepted members to a private snapshot, revalidate the complete manifest and read only that snapshot.

- [x] **Step 4: Implement capability and loss checks.** Compare exact manifest fields, cite `manifest.json#/capabilities/<name>` or loss diagnostics, use no prose inference and emit stable missing/inconsistent diagnostics.

- [x] **Step 5: Implement value-state checks.** Traverse only validated record dictionaries using exact dot-separated field paths with no expression syntax; preserve state/reason/evidence and apply the policy's explicit action. An absent field is a separate `AECCTX_GATE_VALUE_FIELD_MISSING` finding.

- [x] **Step 6: Implement diagnostic budgets and deterministic result serialization.** Reuse authoritative diagnostic records, enforce exact severity order, cap findings before serialization and raise stable bounded operational errors on finding/result overflow. Update mirrored result/check schemas for nullable invalid-candidate identity and the closed field-path grammar.

- [x] **Step 7: Verify GREEN and regressions.** Run `.venv/bin/python -m pytest tests/test_gate_checks.py tests/test_validation.py tests/test_records.py -q`; run the gate twice over directory and ZIP equivalents and compare canonical result bytes.

- [x] **Step 8: Commit.**

```bash
git add docs/specs/quality-gate-v02-profile.md docs/decisions/decision-log.md \
  docs/implementation-plan.md docs/plans/acx-21-implementation.md docs/HANDOFF.md \
  schemas/v0.2/gate-result.schema.json src/aecctx/schemas/v0_2/gate-result.schema.json \
  schemas/v0.2/gate-check.schema.json src/aecctx/schemas/v0_2/gate-check.schema.json \
  src/aecctx/gate tests/test_gate_contract.py tests/test_gate_checks.py
git commit -m "feat: evaluate authoritative package gate checks"
```

### Task 5: Baseline semantic regression checks

**Files:**
- Create: `src/aecctx/gate/diff_checks.py`
- Create: `tests/test_gate_diff.py`
- Modify: `src/aecctx/gate/evaluator.py`
- Modify: `src/aecctx/diff.py` additively to expose authoritative artifacts and exact identity/producer/loss field changes
- Modify: `tests/test_query_diff_context.py` to preserve existing diff compatibility and prove Markdown non-authority
- Modify: `tests/test_gate_checks.py` to replace Task 4's diff fail-closed checkpoint while retaining IDS fail-closed coverage
- Modify: normative profile, ACXD-023, implementation plan and HANDOFF when Task 5 changes behavior/status

**Interfaces:**
- Produce `evaluate_diff_policy(check: GateCheckPolicy, diff: PackageDiff) -> GateCheckResult`.
- Consume only `diff_packages(before_path, after_path) -> PackageDiff`.
- Each diff category has exact policy action `allow`, `requires_review` or `fail`; missing categories make the diff-check policy invalid.
- `aecctx.system.baseline` validates every supplied/required baseline through a revalidated private snapshot; a supplied unused baseline records identity without inventing a policy check.
- Gate artifact regressions consume only additive `PackageDiff.authoritative_artifact_changes` for authoritative non-record artifacts; normalized JSONL streams are governed by record IDs/dictionaries, existing all-artifact observations remain compatibility data and generated Markdown is never gate authority.
- Exact identity/producer/loss field-change maps provide the evidence paths required by the normative profile. Capability upgrades/additions are visible non-regressions; downgrades/disappearance follow `capability_regressions` without synthesizing a missing support level.
- Every diff observation cites role-qualified `baseline-package:<digest>` and `candidate-package:<digest>` refs so equal artifact-derived logical digests cannot collapse the two package roles.

- [x] **Step 1: Write failing tests for every `PackageDiff` category.** Cover added/removed/changed records, artifacts, capability downgrade/upgrade, loss, identity, producer and version; prove archive metadata/reordering is not a regression.

```python
def test_capability_downgrade_cites_both_package_digests(tmp_path: Path) -> None:
    before, after = capability_revision_pair(tmp_path, before="full", after="partial")
    result = evaluate_gate(after, diff_policy(capability_regression="fail"), baseline_package=before)
    finding = next(item for item in result.findings if item.code == "AECCTX_GATE_CAPABILITY_REGRESSION")
    assert result.outcome == "fail"
    assert finding.evidence_refs == (
        f"baseline-package:{result.baseline_logical_digest}",
        f"candidate-package:{result.candidate_logical_digest}",
        "manifest.json#/capabilities/identity",
    )
```

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_gate_diff.py -q`; expect missing diff-check module/dispatch.

- [x] **Step 3: Validate the baseline independently.** Missing/invalid baseline with enabled diff check is `aecctx.system.baseline` error; every supplied baseline is copied to a private snapshot, revalidated and recorded, while a supplied unused baseline does not invent a policy check.

- [x] **Step 4: Map every stable diff field.** Extend `PackageDiff` additively where boolean/all-artifact data cannot support exact citations, preserving existing fields. Use exact IDs/JSON pointers; compare capability support levels to distinguish regression/disappearance from improvement/addition; never compare Markdown, non-authoritative projections or `created_at`.

- [x] **Step 5: Apply exact category actions.** `allow` stays visible in check details, review/fail emit findings, and an unhandled semantic category is `AECCTX_GATE_DIFF_CATEGORY_UNHANDLED` error.

- [x] **Step 6: Verify GREEN and compatibility.** Run `.venv/bin/python -m pytest tests/test_gate_diff.py tests/test_query_diff_context.py tests/test_v02_compatibility.py -q`.

- [x] **Step 7: Commit.**

```bash
git add docs/specs/quality-gate-v02-profile.md docs/decisions/decision-log.md \
  docs/implementation-plan.md docs/plans/acx-21-implementation.md docs/HANDOFF.md \
  src/aecctx/diff.py src/aecctx/gate/diff_checks.py src/aecctx/gate/evaluator.py \
  tests/test_gate_checks.py tests/test_gate_diff.py tests/test_query_diff_context.py
git commit -m "feat: gate semantic baseline regressions"
```

### Task 6: Bounded buildingSMART IDS 1.0 evaluation

**Files:**
- Create: `src/aecctx/gate/ids.py`
- Create: `src/aecctx/gate/_ids_worker.py`
- Create: `tests/test_gate_ids.py`
- Modify: `tests/test_gate_diff.py` to replace Task 5's IDS-not-implemented checkpoint with the Task 6 paired-input system error
- Modify: `src/aecctx/gate/evaluator.py`
- Modify: `src/aecctx/gate/models.py` to expose the already normative IDS specification/facet/entity maxima through `GateLimits`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Create unchanged attributed subset under `fixtures/third_party/buildingsmart-ids-1.0/`
- Create project fixtures under `fixtures/v0.2/gate/ids/`

**Interfaces:**
- Add optional extra `gate-ids = ["ifctester==0.8.5", "ifcopenshell==0.8.5"]`; add both exact pins to `all` and `test`.
- Produce `evaluate_ids_check(candidate_store, check, ids_path, ifc_source_path, limits) -> GateCheckResult`.
- Produce worker command only as `[sys.executable, "-I", "-m", "aecctx.gate._ids_worker"]` with no shell/caller executable.
- Worker stdin request contains exact content-addressed paths/digests, allowed profile and hard limits; stdout is one closed JSON result.
- `GateLimits` adds non-expandable `max_ids_specifications=256`, `max_ids_facets=4096` and `max_ids_entities=250000`; callers may only reduce them under the existing hard-limit comparison.

- [x] **Step 1: Vendor only unchanged official cases selected by a manifest.** Copy exact IDS v1.0.0 tag files without editing; add `LICENSE-CC-BY-ND-4.0.txt`, `ORIGIN.json` with tag/commit/path/SHA-256 and a test that byte hashes match. Keep project-authored IFC/IDS fixtures in a separate Apache-2.0 directory.

  The selected upstream manifest contains paired positive/negative cases for `entity/pass-a_matching_entity_should_pass`, `entity/fail-an_entity_not_matching_a_specified_predefined_type_will_fail`, `attribute/pass-a_required_facet_checks_all_parameters_as_normal`, `attribute/fail-attributes_should_check_strings_case_sensitively_2_2`, `classification/pass-both_system_and_value_must_match__all__not_any__if_specified_1_2`, `classification/fail-both_system_and_value_must_match__all__not_any__if_specified_2_2`, `property/pass-a_required_facet_checks_all_parameters_as_normal`, `property/fail-elements_with_no_properties_always_fail`, `material/pass-a_required_facet_checks_all_parameters_as_normal` and `material/fail-elements_without_a_material_always_fail`, each with `.ids` and `.ifc` bytes from commit `1effec6f419798ce09617416d258a35bdc58320a`.

- [x] **Step 2: Write failing IDS contract/safety tests before adding dependencies.** Cover dependency absence, exact version mismatch, IDS/source missing pair, source ID/hash mismatch, IFC2X3/IFC4 success, IFC4X3 rejection, each selected simple facet, `partOf`/restriction rejection, invalid XML, DTD/entity/XInclude, oversize, timeout/crash/output overflow and prompt/command-like inert text.

```python
def test_ids_source_must_match_registered_candidate_source(tmp_path: Path) -> None:
    package, registered_ifc = build_ifc_gate_fixture(tmp_path)
    other_ifc = tmp_path / "other.ifc"
    other_ifc.write_bytes(registered_ifc.read_bytes() + b"\n")
    result = evaluate_gate(package, ids_policy(), ids_document=IDS, ifc_source=other_ifc)
    assert result.outcome == "error"
    assert "AECCTX_GATE_IDS_SOURCE_HASH_MISMATCH" in result.diagnostic_codes


def test_unsupported_ids_restriction_is_not_reported_as_pass(ids_fixture_with_pattern: Path) -> None:
    result = evaluate_gate(PACKAGE, ids_policy(), ids_document=ids_fixture_with_pattern, ifc_source=IFC)
    assert result.outcome == "fail"
    assert result.findings[0].code == "AECCTX_GATE_IDS_RESTRICTION_UNSUPPORTED"
```

- [x] **Step 3: Verify RED.** Run `.venv/bin/python -m pytest tests/test_gate_ids.py -q`; expect missing modules/extra and explicit dependency-unavailable behavior.

- [x] **Step 4: Add the optional pinned dependency boundary.** Update `pyproject.toml` and `uv.lock`; verify `ifctester==0.8.5`/`ifcopenshell==0.8.5`, LGPL-3.0-or-later metadata, transitive dependency list and that a core-only wheel install imports/runs non-IDS checks without them.

- [x] **Step 5: Implement parent input binding and XML preflight.** Reject symlinks/non-regular/oversize files, hash before parse, match exact source record, reject active XML markers/unknown namespace/version/facets/restrictions and count specifications/facets before worker launch.

- [x] **Step 6: Implement the fixed worker.** Import exact dependency versions, use `ifctester.ids.open(path, validate=True)`, open the bound IFC with IfcOpenShell, validate only allowed schema/facet/simple-value subset and map `Ids`/`Specification`/facet state directly. Do not call `reporter.Json`, do not include host time and cap entities/findings.

```python
ids_file = ids.open(request.ids_path, validate=True)
ifc_file = ifcopenshell.open(request.ifc_path)
ids_file.validate(ifc_file, should_filter_version=True)
response = normalize_ids_state(ids_file, limits=request.limits)
sys.stdout.buffer.write(canonical_json(response))
```

- [x] **Step 7: Enforce worker timeout/output/version protocol.** Start a new process group/session where supported, terminate then kill the complete worker on timeout, validate one JSON response and map crash/timeout/malformed/oversize output to stable gate `error` diagnostics.

- [x] **Step 8: Run official and project conformance subsets.** Run `.venv/bin/python -m pytest tests/test_gate_ids.py -q`; require every claimed official case to match its `pass-`/`fail-` expectation. If any target combination fails, stop IDS claim work, amend the normative profile, ACXD-023/decision log, this plan and the claim registry to register it as unsupported before proceeding; never weaken expected results.

- [x] **Step 9: Commit.**

```bash
git add src/aecctx/gate/ids.py src/aecctx/gate/_ids_worker.py src/aecctx/gate/evaluator.py \
  tests/test_gate_ids.py fixtures/third_party/buildingsmart-ids-1.0 \
  fixtures/v0.2/gate/ids pyproject.toml uv.lock
git commit -m "feat: evaluate bounded IDS 1.0 requirements"
```

### Task 7: CLI, canonical output and derived projections

**Files:**
- Create: `src/aecctx/_atomic.py`
- Create: `src/aecctx/gate/projection.py`
- Modify: `src/aecctx/cli.py`
- Modify: `src/aecctx/gate/models.py`
- Create: `tests/test_gate_cli.py`
- Modify: `tests/test_signing_cli.py` only to prove the generalized atomic primitive preserves signing behavior
- Modify: `README.md`

**Interfaces:**
- CLI arguments match the normative contract exactly.
- Produce `GateResult.canonical_bytes() -> bytes`.
- Produce `render_gate_markdown(result: GateResult) -> bytes` and `render_ci_annotations(result: GateResult) -> bytes`.
- Atomic detached output creation rejects existing/symlink/directory targets and never overwrites.
- `--output` contains raw canonical `GateResult` JSON; `--json` uses the canonical result-producing envelope contract from profile section 12.
- CI annotations use provider-neutral canonical JSONL profile `aecctx-ci-annotations-v1`; provider workflow commands remain downstream adapters.
- All requested outputs are collision-preflighted and published through one neutral rollback-capable atomic-create primitive.

- [x] **Step 1: Write failing parser, exit and parity tests.** Cover pass/fail/review/error exits, JSON envelope semantics, required IDS/IFC pairing, baseline missing, output collisions, Markdown/result parity and hostile messages rendered as escaped data.

```python
@pytest.mark.parametrize(
    ("outcome", "exit_code"),
    [("pass", 0), ("fail", 1), ("requires_review", 1), ("error", 2)],
)
def test_gate_cli_exit_matches_authoritative_result(outcome: str, exit_code: int, gate_case: GateCase) -> None:
    completed = run_cli(gate_case.arguments_for(outcome) + ["--json"])
    assert completed.returncode == exit_code
    assert json.loads(completed.stdout)["data"]["outcome"] == outcome
```

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_gate_cli.py -q`; expect no `gate` parser/handler/projection.

- [x] **Step 3: Add exact CLI parser and handler.** Parse policy/optional inputs, call only public `evaluate_gate`, print canonical envelope for `--json`, concise non-authoritative text otherwise and return the result exit code.

- [x] **Step 4: Implement safe detached output creation.** Generalize the existing signing sidecar atomic-create pattern into a neutral internal helper or duplicate the bounded primitive without importing signing semantics. Never partially publish output.

- [x] **Step 5: Implement Markdown and CI projections.** Render only `GateResult.to_dict()`, include policy/package digests, outcome, check IDs, finding fingerprints/evidence refs and the explicit non-approval disclaimer. Escape source/policy text and never follow links.

- [x] **Step 6: Prove projection parity.** Parse IDs/outcome/evidence refs from both projections in tests and compare to JSON; mutate projection text and prove it cannot affect reevaluation/result.

- [x] **Step 7: Document installation/usage.** Add core gate and optional `aecctx[gate-ids]` examples, exact exits and non-approval language; do not claim implementation publicly until Task 9.

- [x] **Step 8: Verify GREEN.** Run `.venv/bin/python -m pytest tests/test_gate_cli.py tests/test_cli.py -q` and direct CLI smoke for all four outcomes.

- [x] **Step 9: Commit.**

```bash
git add src/aecctx/cli.py src/aecctx/gate/projection.py tests/test_gate_cli.py README.md
git commit -m "feat: expose deterministic delivery gate CLI"
```

### Task 8: Conformance corpus, portable gate and packaging boundaries

**Files:**
- Create: `fixtures/v0.2/gate/` remaining package/policy/baseline/malicious fixtures
- Create: `conformance/v0.2/gate-corpus.json`
- Create: `scripts/check_gate_conformance.py`
- Create: `tests/test_gate_conformance.py`
- Modify: `conformance/v0.2/claims.json`
- Modify: `scripts/verify_portable.sh`
- Modify: `pyproject.toml` sdist/package-data lists only where required
- Modify: `docs/capability-matrix.md`
- Create: `docs/evidence/ACX-21.md`

**Interfaces:**
- Corpus maps every case ID to input paths/SHA-256, expected outcome/exit/check IDs/finding codes and exact claim ID.
- `scripts/check_gate_conformance.py` runs offline and emits one canonical JSON summary with `ok` and ordered entries.
- Proposed claim ID is `quality-gate.policy-ids`, profile `aecctx-gate-v1-ids-1.0-simple-v1`, maximum support `partial`.

- [x] **Step 1: Write failing corpus/claim tests.** Require positive, fail, review, error, malicious-policy, baseline-regression, IDS and missing-extra cases; fail for unmapped claim/case, stale hash, duplicate case and expected/public claim mismatch.

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_gate_conformance.py tests/test_claim_registry.py -q`; expect missing corpus/checker and target claim evidence.

- [x] **Step 3: Build deterministic project-authored fixtures.** Generate directory/ZIP equivalents, capability/loss/value-state/diagnostic packages, baseline pairs, malicious JSON/XML, policies/waivers and expected canonical results. Record origin/license/hash in the corpus.

- [x] **Step 4: Implement the portable corpus checker.** Validate schemas/hashes, run non-IDS cases in core mode, run IDS cases only in the test/IDS environment, compare exact outcome/exit/check/finding sets and run each deterministic case twice for byte equality.

- [x] **Step 5: Add packaging and dependency isolation tests.** Build wheel/sdist, inspect that public/packaged schemas and intended project fixtures/corpus exist, ensure no third-party fixture is accidentally relicensed, and prove core-only install has no `ifctester`, Flask, BCF client or IfcOpenShell requirement.

- [x] **Step 6: Add portable verification hooks.** Add JSON syntax, schema mirror, corpus checker and gate tests to `verify_portable.sh`; preserve GitHub Actions on Ubuntu/macOS/Windows with missing optional IDS behavior deterministic. IDS-extra platform jobs must use the exact pins before claim promotion.

- [x] **Step 7: Draft acceptance evidence without promoting the claim.** Fill all 12 evidence sections with spec/decision coverage, fixture hashes/licenses, commands, determinism, diagnostics, dependency/security/platform review, residuals, WoodFraming proof and promotion conditions. Keep claim `target` and capability matrix `unsupported` until Task 9 gates pass.

- [x] **Step 8: Verify GREEN narrowly.** Run `.venv/bin/python -m pytest tests/test_gate_*.py tests/test_claim_registry.py tests/test_package_data.py -q`, `.venv/bin/python scripts/check_gate_conformance.py` and `python3 scripts/check_spec_contract.py`.

- [x] **Step 9: Commit implementation candidate.**

```bash
git add fixtures/v0.2/gate fixtures/third_party/buildingsmart-ids-1.0 \
  conformance/v0.2/gate-corpus.json conformance/v0.2/claims.json \
  scripts/check_gate_conformance.py scripts/verify_portable.sh tests/test_gate_conformance.py \
  pyproject.toml docs/capability-matrix.md docs/evidence/ACX-21.md
git commit -m "test: publish ACX-21 gate conformance candidate"
```

### Task 9: Acceptance, publication and exact next-task promotion

**Files:**
- Modify: `docs/evidence/ACX-21.md`
- Modify: `docs/capability-matrix.md`
- Modify: `conformance/v0.2/claims.json`
- Modify: `conformance/v0.2/gate-corpus.json`
- Modify: `fixtures/v0.2/gate/generate_fixtures.py`
- Modify: `scripts/check_gate_conformance.py`
- Modify: `tests/test_gate_conformance.py`
- Modify: `docs/implementation-plan.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/plans/acx-21-implementation.md` checkpoints only
- Modify: `README.md` final claim wording

**Interfaces:**
- No new runtime interface; this task verifies and truthfully publishes only the proven subset.
- ACX-22 is promoted only after candidate, closure and merged-main gates pass.
- Claim promotion is one atomic contract transition across the registry, corpus, deterministic generator, checker and conformance tests; mixed `target`/`public` state is invalid.

- [x] **Step 1: Run the full local acceptance matrix.** Run task tests, spec/claim/corpus checkers, `./scripts/verify_portable.sh`, clean core/IDS-extra wheel installs and `./scripts/verify.sh`. Record exact counts, skips, artifact hashes and dependency versions/licenses in evidence.

- [x] **Step 2: Audit every claim against evidence.** Promote `quality-gate.policy-ids` from `target` to public `partial` only if each advertised policy/IDS combination has unique fixture/test/evidence mapping. Remove any unproven combination from the profile and retain it as unsupported; no scaffolding counts.

- [x] **Step 3: Prove the non-claims.** Scan source/docs/artifacts for WoodFraming, `WFDomain`, `WFImport`, approval/certification language, network/LLM requirements and third-party dependency leakage. Record that Markdown/CI projections are not authority and `requires_review`/waived cannot become pass.

- [x] **Step 4: Publish and verify the implementation candidate.** Push the feature branch, require exact-SHA green Ubuntu/macOS/Windows CI, and record run/job URLs/status. Do not change task status or promote ACX-22 before green CI.

- [x] **Step 5: Close ACX-21.** Set ACX-21 `completed`, promote only ACX-22 to `pending-next`, finalize claim/evidence/capability/HANDOFF and check all plan tasks. Run `python3 scripts/check_spec_contract.py` and `./scripts/verify.sh`; commit `docs: close ACX-21 quality gate milestone`.

- [x] **Step 6: Publish and validate closure.** Push closure commit, require exact-SHA green Ubuntu/macOS/Windows CI, merge with `--no-ff` to `main`, rerun `./scripts/verify.sh`, push `main` and require green merged-main CI.

- [x] **Step 7: Record publication evidence only.** Add exact candidate/closure/merge SHAs and CI URLs/status in evidence, commit/push the documentation-only update, require green CI and stop. Do not execute ACX-22 and do not create a release/tag; ACX-23 owns release authority.

## Required execution order

Tasks 1 through 9 are sequential. Each task begins only after the preceding task's narrow gate and commit. A newly discovered semantic, security, licensing or portability decision updates the normative profile, decision log and this plan before affected implementation continues.

## Planning checkpoint

Tasks 1-8 materialize the closed public schemas/models, strict bounded policy input, deterministic finding/waiver aggregation, authoritative package checks, semantic baseline regression checks, bounded IDS 1.0 evaluation, deterministic CLI/projections and a 27-case hash-bound offline corpus with clean-install packaging boundaries. Task 9 acceptance began with three expected claim-state failures; the minimal registry/corpus/generator/checker/test transition then passed 14 focused tests, the 205-test gate/claim/package suite and the 604-test repository gate with 9 intentional skips. Closure and merged-main SHAs passed Ubuntu/macOS/Windows CI. ACX-21 is completed at 9/9 detailed tasks (100%) and `quality-gate.policy-ids` is public `partial` only for `aecctx-gate-v1-ids-1.0-simple-v1` on Python 3.12 Linux/macOS/Windows. ACX-22 is `pending-next` but MUST NOT execute until a new continuation request.
