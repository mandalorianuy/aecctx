# AECCTX v0.2 Delivery Quality Gate Profile

Version: `1.0.0-draft.3`
Date: 2026-07-13
Status: ACX-21 normative design; implementation and public quality-gate claims remain pending conformance
Decision authority: ACXD-021 and ACXD-023

## 1. Purpose and claim boundary

This profile defines a deterministic, local-first policy-conformance evaluator over validated AECCTX packages, an optional validated baseline package and an optional bounded buildingSMART Information Delivery Specification (IDS) 1.0 check.

The gate reports only whether the supplied evidence conforms to the supplied policy. `pass` does not mean engineering approval, regulatory acceptance, construction readiness, design correctness, source authorship, consumer canonical acceptance or permission to mutate a source or downstream model.

The machine-readable JSON result is authoritative. Markdown summaries and CI annotations are derived projections and MUST NOT change, omit or elevate the result.

## 2. Options considered and selected architecture

Three IDS implementation paths were reviewed:

1. A new AECCTX IDS parser/checker would minimize dependencies but duplicate a domain standard, increase semantic drift and violate the preference for existing official implementations.
2. A remote or restricted-provider checker would isolate execution but add credentials, egress, retention, replay and platform claims that are unnecessary for IDS 1.0.
3. The selected profile uses optional `ifctester==0.8.5` with `ifcopenshell==0.8.5`, matching the existing bounded IFC runtime. It is LGPL-3.0-or-later, remains outside the Apache-2.0 core dependency set and runs through a fixed local worker with bounded inputs and output.

AECCTX does not use `ifctester.reporter.Json` as result authority because that reporter inserts the host time. AECCTX maps validated `ifctester.ids` evaluation state into its own canonical result model and records the exact runtime versions.

## 3. Invocation inputs

A gate invocation contains:

- one candidate AECCTX v0.1 or v0.2 directory/ZIP package;
- zero or one baseline AECCTX v0.1 or v0.2 directory/ZIP package;
- one closed, versioned JSON policy document;
- zero or one IDS 1.0 document and, when IDS is enabled, one explicit IFC source file;
- evaluator limits and no implicit environment, clock, network, trust or consumer context.

The candidate and baseline MUST pass ordinary AECCTX structural and integrity validation before policy checks run. Invalid packages produce gate outcome `error`, not `fail`, because evaluation did not complete safely.

The policy, IDS and explicit IFC source are caller-selected paths. AECCTX MUST NOT follow source storage references, external links, schema locations, XIncludes, catalog references or URLs from a package or IDS file.

## 4. Policy identity and canonicalization

The policy profile identifier is `https://aecctx.dev/gate/v1`. The policy root contains exactly:

- `profile`, fixed to that identifier;
- `policy_id`, a stable non-empty caller-owned identifier;
- `policy_version`, a semantic version;
- `evaluation_time`, an explicit UTC instant used only for waiver lifecycle evaluation;
- `checks`, an ordered JSON array with unique check IDs;
- `waivers`, an ordered JSON array with unique waiver IDs.

Strict parsing rejects duplicate JSON names, invalid UTF-8, non-finite numbers, unknown fields, Unicode-normalized key collisions and excessive nesting. JSON depth is counted after parsing and NFC normalization: a scalar has depth 0 and the root object has depth 1; no value may exceed depth 32. Canonical policy bytes use UTF-8, Unicode NFC strings, sorted object keys, no insignificant whitespace and one terminal LF. `policy_digest` is SHA-256 of those exact bytes. Array order is significant and is never silently reordered; stable result ordering is defined separately.

`policy_version` conforms to SemVer 2.0.0: core numeric identifiers do not contain leading zeroes, prerelease identifiers are non-empty and numeric prerelease identifiers do not contain leading zeroes, and build identifiers are non-empty. Parser recursion exhaustion is mapped to `AECCTX_GATE_JSON_DEPTH_EXCEEDED`; it is never exposed as a host exception.

The policy contains no executable expressions, templating, regular expressions, imports, callbacks, paths, commands, macros or active links.

## 5. Check identifiers, types and severities

System checks are always enabled and cannot be waived:

- `aecctx.system.validation` verifies structural conformance;
- `aecctx.system.integrity` verifies artifact hashes, byte sizes, logical digest and required references;
- `aecctx.system.policy` verifies policy schema, semantics and digest;
- `aecctx.system.ids-input` verifies the optional IDS/IFC binding before IDS evaluation.

Policy check IDs match `^[a-z][a-z0-9._-]{0,63}$`. Their result IDs are `aecctx.policy.<check-id>`. Duplicate IDs are invalid. Check kinds are exactly:

- `capability.minimum`;
- `loss.maximum`;
- `value_state.action`;
- `diagnostic.maximum`;
- `diff.regression`;
- `ids.specification`.

Stable severities are `info`, `warning`, `error` and `blocking` in that order. Severity is presentation and triage metadata; it MUST NOT silently override a check's explicit `failure_mode`, which is either `fail` or `requires_review`.

Every check result is one of `pass`, `fail`, `requires_review`, `waived` or `error`. A check that emits multiple findings takes the highest outcome in the order `error`, `fail`, `requires_review`, `waived`, `pass`.

Every finding carries an authoritative `disposition` of `error`, `fail`, `requires_review` or `waived`. A `waived` finding MUST name its `waiver_id`; every other disposition MUST keep `waiver_id` null. Finding fingerprints MUST be unique within one check so a waiver identifies exactly one finding. A check with findings MUST have the highest disposition of those findings, except that an explicit active-waiver mismatch diagnostic floors the final check status at `requires_review`; a finding-free check retains its explicit check status subject to the same floor. Check status is recomputed from all per-finding dispositions after every waiver has been classified, then the lifecycle review floor is applied once. `severity` remains presentation/triage metadata and does not substitute for disposition.

## 6. Built-in check contracts

### 6.1 Capability minimum

`capability.minimum` compares exact manifest capability keys using the ordered support levels `unsupported < opaque < partial < full`. The policy lists each capability and its minimum level. Missing keys are explicit findings and never inherit a default capability.

### 6.2 Loss maximum

`loss.maximum` evaluates authoritative manifest loss summary and cited diagnostics. It supports an overall maximum and per-reason-code maxima. Missing detailed evidence, inconsistent counts or a reason code absent from the policy is reported according to the check's explicit `failure_mode`; counts are never guessed from prose.

### 6.3 Value-state action

`value_state.action` scans authoritative records selected by record type and optional exact field path. The policy MUST provide an action for each non-known state: `unknown`, `unsupported`, `conflicted`, `explicit_null` and `not_applicable`. Each action is exactly `allow`, `requires_review` or `fail`.

An `allow` action is explicit policy, remains visible in check details and does not rewrite the value. Missing state actions make the policy invalid. `known` values pass this check but are not thereby validated as correct.

### 6.4 Diagnostic maximum

`diagnostic.maximum` counts authoritative diagnostics at or above an exact severity threshold and MAY define per-code maxima. It never treats a successful adapter/process exit as evidence that diagnostics are absent.

### 6.5 Baseline regression

`diff.regression` requires an explicit validated baseline. It consumes the stable AECCTX semantic diff and can independently allow, review or fail added, removed and changed records, artifact changes, capability regressions, loss changes, identity changes, producer changes and version changes. It cites both package digests and exact changed IDs/paths.

A missing baseline when this check is enabled is gate `error`. Archive metadata or record ordering alone remains non-semantic.

### 6.6 IDS specification

`ids.specification` requires the policy to contain the expected IDS SHA-256 and candidate `source_id`. The caller supplies the IDS and IFC source explicitly. The IFC bytes MUST hash to the exact registered source record and the IDS bytes MUST hash to the policy value before parsing begins.

IDS results are labeled `ids` and never replace package validation, integrity, geometry, provenance, capability or diff checks.

## 7. IDS 1.0 bounded profile

The selected standard is buildingSMART IDS `v1.0.0`, final release commit `1effec6`, namespace `http://standards.buildingsmart.org/IDS`. Earlier drafts and later versions are unsupported by this profile.

The selected implementation is exactly `ifctester==0.8.5` with `ifcopenshell==0.8.5`. The supported IFC schema identifiers are `IFC2X3` and `IFC4`, matching the existing AECCTX bounded IFC corpus. IFC4X1, IFC4X2, IFC4X3 and custom schemas remain unsupported here even if the dependency can parse them.

The initial public target is a partial simple-value subset of these IDS facet families in applicability and requirements:

- `entity` with exact `name` and optional exact `predefinedType`;
- `attribute` with exact `name` and absent-or-exact simple value;
- `classification` with absent-or-exact `system` and `value`;
- `property` with exact `propertySet`, `baseName`, optional exact `dataType` and absent-or-exact simple value;
- `material` with absent-or-exact simple value.

Required, optional and prohibited cardinalities are supported only where an unchanged buildingSMART v1.0 conformance case and an AECCTX project fixture both pass. `partOf`, XSD restrictions/patterns/ranges/enumerations, URI dereference, bSDD lookup, geometry, quantities not represented by the selected property subset and every unlisted facet/profile remain explicit `unsupported` findings. Passing an unsupported facet as though it were evaluated is prohibited.

Official buildingSMART fixtures MAY be vendored only unchanged from the tagged release, with exact hashes and the upstream CC BY-ND 4.0 license/attribution. Project-authored fixtures remain Apache-2.0 and are kept separate. No official fixture may be edited and still described as an official conformance case.

## 8. IDS worker boundary

The IDS evaluator runs in a fixed local Python worker selected by AECCTX, never through a caller command. The parent passes content-addressed input paths and closed JSON configuration without a shell. The worker has a normalized locale/timezone/environment, network APIs are denied by the test harness, output is bounded and schema-validated, and timeout terminates the complete worker process.

The worker MUST reject XML `DOCTYPE`, entities, XInclude, unknown namespaces/versions, unsupported facets or restrictions before evaluation. It loads only the XSD bundled by the pinned `ifctester` distribution. IDS `uri`, instructions and descriptions are inert data and are never fetched or executed.

Worker output contains stable specification/facet identifiers, pass/fail state, IFC GUID/STEP identifiers where available and bounded failure reasons. Host paths, wall-clock time and dependency-internal object representations are excluded.

## 9. Waivers

Waivers target one exact finding fingerprint. A finding fingerprint is SHA-256 of canonical JSON containing the check result ID, stable finding code, subject identifier, evidence references and observed state, excluding presentation text.

Each waiver contains exactly:

- unique `waiver_id`;
- `check_id`, which is the exact result ID `aecctx.policy.<check-id>` of one check declared by the same policy, and exact `finding_fingerprint`;
- non-empty `reason` and `approved_by` strings;
- `issued_at` inclusive and `expires_at` exclusive UTC instants.

The policy's explicit `evaluation_time` decides lifecycle. Invalid intervals make policy evaluation `error`. Expired or not-yet-valid waivers do not suppress the finding, do not change check status and emit `AECCTX_GATE_WAIVER_EXPIRED` or `AECCTX_GATE_WAIVER_NOT_YET_VALID`. An active exact match changes only a `fail` or `requires_review` finding disposition to `waived`, preserves identity/evidence/message and records `waiver_id`; the check is then recomputed from all finding dispositions. `error` and already-`waived` findings are not waivable. An active waiver with no matching fingerprint emits `AECCTX_GATE_WAIVER_FINDING_MISMATCH` and forces its target check to at least `requires_review`, preventing silent success. Classification and mutation MUST use the original check/finding set, and the mismatch floor MUST be applied after all exact matches, so waiver-array order cannot change results.

Waiver application returns separately ordered checks and diagnostics so later result assembly cannot hide lifecycle evidence. Duplicate `(check_id, finding_fingerprint)` targets, missing target checks, invalid clocks/intervals, wildcards, system checks and non-waivable dispositions are invalid control state reported as `GateError`; they are never silently ignored. A waiver can never create `pass`, target a system check, target an undeclared policy check, use a wildcard or authorize consumer/engineering acceptance. The waiver schema therefore accepts only the full `aecctx.policy.` result-ID form; a short check ID or `aecctx.system.*` value is invalid control input.

## 10. Aggregate outcome and exit codes

Aggregate precedence is deterministic:

1. Any system/check `error` produces `error`.
2. Otherwise any `fail` produces `fail`.
3. Otherwise any `requires_review` or `waived` produces `requires_review`.
4. Otherwise the result is `pass`.

Stable CLI exit codes are:

- `0` for `pass`;
- `1` for completed evaluation with `fail` or `requires_review`;
- `2` for `error`, invalid control input, invalid package, missing optional IDS dependency or operational failure.

JSON `ok` means the command produced a valid result document. It does not mean policy `pass`.

## 11. Result authority and ordering

The result binds:

- evaluator/profile/dependency versions;
- candidate and optional baseline package IDs/logical digests;
- canonical policy digest;
- optional IDS and IFC source digests/source ID;
- aggregate outcome and exit code;
- ordered system and policy check results;
- ordered findings, waiver decisions, diagnostics and evidence references.

Checks sort by result ID. Findings sort by check ID, code, subject, fingerprint and evidence reference. Diagnostics sort by code and path. Presentation messages do not participate in finding identity.

Repeated evaluation with identical bytes, versions, limits and platform-normalized settings MUST produce byte-identical canonical JSON. The result contains no host clock, random ID, temporary path or filesystem ordering.

## 12. SDK and CLI contract

The public SDK provides:

```python
evaluate_gate(
    candidate_package,
    policy,
    *,
    baseline_package=None,
    ids_document=None,
    ifc_source=None,
    limits=GateLimits(),
) -> GateResult
```

The CLI provides:

```text
aecctx gate CANDIDATE --policy POLICY [--baseline BASELINE]
            [--ids IDS --ifc-source IFC] [--output RESULT]
            [--markdown MARKDOWN] [--ci-annotations ANNOTATIONS] [--json]
```

`--ids` and `--ifc-source` are a required pair. Outputs are new files created atomically and never overwrite input packages, policies or sources. Library, CLI, Markdown and CI annotation projections MUST agree on aggregate outcome, check IDs, finding fingerprints and evidence references.

## 13. Safety limits

The following defaults are also the v1 hard maxima; callers MAY reduce them but MUST NOT expand them:

- 1 MiB each for policy and IDS;
- 256 policy checks and 1,024 waivers;
- JSON/XML nesting depth 32;
- 128 bytes for IDs, 4,096 bytes for human strings and 8,192 evidence references;
- 256 MiB explicit IFC source;
- 256 IDS specifications, 4,096 total facets and 250,000 evaluated IFC entities;
- 100,000 findings and 16 MiB canonical result;
- 60 seconds IDS worker wall time.

Regular-file inputs only are accepted; symlinks are rejected. Over-limit behavior is a stable `error`, never partial `pass`.

## 14. Stable diagnostic families

The implementation provides stable diagnostics for at least:

- invalid candidate/baseline package, policy schema/semantics or digest;
- duplicate/unknown check, unsupported check kind and invalid state action;
- missing baseline, IDS or IFC source;
- source ID/hash/schema mismatch;
- malformed/oversized/active XML and unsupported IDS version/facet/restriction;
- unavailable or mismatched `ifctester`/`ifcopenshell` dependency;
- worker timeout/crash/oversized/malformed output;
- invalid/not-yet-valid/expired/mismatched waiver;
- capability, loss, value-state, diagnostic and diff nonconformance;
- result/projection parity failure.

Diagnostics MUST NOT embed source text, policy contents, host paths or dependency tracebacks by default.

Task 2 policy loading uses these stable `GateError.code` values: `AECCTX_GATE_INPUT_TYPE_INVALID`, `AECCTX_GATE_INPUT_LIMIT_EXCEEDED`, `AECCTX_GATE_INPUT_UNREADABLE`, `AECCTX_GATE_JSON_INVALID`, `AECCTX_GATE_JSON_DUPLICATE_KEY`, `AECCTX_GATE_JSON_NORMALIZATION_COLLISION`, `AECCTX_GATE_JSON_NONFINITE`, `AECCTX_GATE_JSON_DEPTH_EXCEEDED`, `AECCTX_GATE_SCHEMA_UNSUPPORTED`, `AECCTX_GATE_SCHEMA_INVALID`, `AECCTX_GATE_LIMIT_INVALID`, `AECCTX_GATE_PROFILE_UNSUPPORTED`, `AECCTX_GATE_POLICY_VERSION_INVALID`, `AECCTX_GATE_EVALUATION_TIME_INVALID`, `AECCTX_GATE_CHECK_ID_DUPLICATE`, `AECCTX_GATE_WAIVER_ID_DUPLICATE`, `AECCTX_GATE_CHECK_ID_RESERVED`, `AECCTX_GATE_WAIVER_TARGET_INVALID`, `AECCTX_GATE_WAIVER_INTERVAL_INVALID`, `AECCTX_GATE_CHECK_LIMIT_EXCEEDED`, `AECCTX_GATE_WAIVER_LIMIT_EXCEEDED` and `AECCTX_GATE_POLICY_INVALID`. Messages are bounded control diagnostics and MUST NOT copy source contents or host paths.

Task 3 adds `AECCTX_GATE_FINDING_IDENTITY_INVALID`, `AECCTX_GATE_WAIVER_DUPLICATE_TARGET`, `AECCTX_GATE_WAIVER_CHECK_INVALID`, `AECCTX_GATE_WAIVER_CHECK_MISSING` and `AECCTX_GATE_WAIVER_DISPOSITION_INVALID` as stable control-error codes. Lifecycle diagnostics are `AECCTX_GATE_WAIVER_EXPIRED`, `AECCTX_GATE_WAIVER_NOT_YET_VALID` and `AECCTX_GATE_WAIVER_FINDING_MISMATCH`, all with diagnostic severity `warning`. The mismatch diagnostic additionally floors its target check at `requires_review`; the first two do not change the original check disposition.

## 15. Conformance and claim promotion

ACX-21 MUST publish project-authored positive, fail, review, error, malicious-policy, baseline-regression and IDS fixtures. It MUST also map the exact unchanged buildingSMART v1.0 cases used for each claimed facet/cardinality combination.

Conformance covers canonical policy/result bytes, all aggregate outcomes and exits, each check kind, every explicit value state, active/expired/invalid waivers, diff categories, invalid packages, malicious JSON/XML, dependency absence, worker limits, CLI/SDK/projection parity, clean core installation and no-network/no-LLM behavior.

The capability remains public `unsupported` until schemas, implementation, fixtures, claim mapping, dependency/license/security review, `docs/evidence/ACX-21.md`, local gates and exact-SHA remote CI pass. Completion may promote only the exact tested profile to `partial`; unlisted IDS versions/facets and engineering/consumer approval remain unsupported.

## 16. Normative and reviewed references

- buildingSMART IDS 1.0 XSD: `https://standards.buildingsmart.org/IDS/1.0/ids.xsd`
- buildingSMART IDS v1.0 final release: `https://github.com/buildingSMART/IDS/releases/tag/v1.0.0`
- buildingSMART IDS repository license: CC BY-ND 4.0
- IfcOpenShell 0.8.5 IfcTester API: `https://docs.ifcopenshell.org/autoapi/ifctester/index.html`
- IfcTester 0.8.5 distribution: `https://pypi.org/project/ifctester/0.8.5/`
- IfcTester license: LGPL-3.0-or-later
