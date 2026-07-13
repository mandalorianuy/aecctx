# AECCTX v0.2 Delivery Quality Gate Profile

Version: `1.0.0-draft.6`
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

Candidate validation is a two-phase bounded preflight. The evaluator validates the caller path, copies only package members accepted by `PackageReader` into a private temporary snapshot, validates that snapshot and requires its complete manifest to equal the initially validated manifest before opening `RecordStore`. A symlink candidate root or a package that changes during this sequence is rejected. Policy checks read only the snapshot, closing the validation/use race without treating the caller path as trusted storage.

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
- `aecctx.system.baseline` verifies an explicitly supplied or policy-required baseline before semantic diff evaluation;
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

Each `loss_summary` entry is one exact reason code. Every reason MUST have at least one authoritative diagnostic with the same `code` and a non-negative integer `affected_count`; that reason's count is the sum of those values and the overall count is the sum of all reason counts. Duplicate summary codes, missing/invalid counts and diagnostics that cite an undeclared loss reason are inconsistent evidence. When `reason_code_maxima` is present, every observed reason absent from that map is a finding; an omitted map does not invent a zero maximum.

### 6.3 Value-state action

`value_state.action` scans authoritative records selected by record type and optional exact field path. The policy MUST provide an action for each non-known state: `unknown`, `unsupported`, `conflicted`, `explicit_null` and `not_applicable`. Each action is exactly `allow`, `requires_review` or `fail`.

An `allow` action is explicit policy, remains visible in check details and does not rewrite the value. Missing state actions make the policy invalid. `known` values pass this check but are not thereby validated as correct.

An exact field path is dot-separated and each segment matches `[A-Za-z_][A-Za-z0-9_-]*`; it is data selection, not an expression language. Without a field path, mappings and arrays are traversed in deterministic key/index order and every object containing `state` is evaluated. A missing selected field emits `AECCTX_GATE_VALUE_FIELD_MISSING`. A malformed or unrecognized state object emits invalid-evidence error rather than being coerced to any value state. Findings cite the authoritative record ID plus a deterministic field path/JSON pointer; an `allow` observation remains in check evidence and message even though it creates no failing finding.

### 6.4 Diagnostic maximum

`diagnostic.maximum` counts authoritative diagnostics at or above an exact severity threshold and MAY define per-code maxima. It never treats a successful adapter/process exit as evidence that diagnostics are absent.

Both the overall and per-code counts count diagnostic records, never `affected_count`. Missing/invalid `code` or `severity` is invalid evidence and cannot be silently excluded from a budget.

### 6.5 Baseline regression

`diff.regression` requires an explicit validated baseline. It consumes the stable AECCTX semantic diff and can independently allow, review or fail added, removed and changed records, artifact changes, capability regressions, loss changes, identity changes, producer changes and version changes. It cites both package roles/digests as `baseline-package:<logical-digest>` and `candidate-package:<logical-digest>` plus exact changed IDs/paths. Role qualification is mandatory because manifest-only semantic changes can legitimately leave the artifact-derived logical digests equal; equal unqualified refs would collapse and lose the two-sided evidence relation.

A missing baseline when this check is enabled is gate `error`. Archive metadata or record ordering alone remains non-semantic.

An explicitly supplied baseline is always validated, recorded in the result and exposed through `aecctx.system.baseline`, even when no `diff.regression` policy check is declared; that condition MUST NOT invent a policy check. Baseline evaluation uses the same private-copy, complete-manifest revalidation and mutation/symlink rejection as the candidate. Missing or invalid required baseline identity remains null and produces gate `error`; no placeholder identity is synthesized.

The stable diff primitive distinguishes all artifact inventory changes from authoritative non-record artifact changes. Gate regression policy consumes only authoritative non-record artifact changes: the six authoritative JSONL record streams are compared by normalized record dictionaries/IDs instead of byte serialization, while generated Markdown and other non-authoritative projections cannot create a regression. It exposes exact field changes for identity (`package_id`, `source_ids`, `source_embedding_policy`), producer fields and loss summary so findings cite exact JSON pointers. Existing all-artifact observations remain available for compatibility but are not gate authority.

Category actions are exact and independent. Added, removed and changed records; authoritative artifacts; loss; identity; producer and version changes use their configured action. `capability_regressions` applies only when an explicit support level decreases or disappears; an added capability or support increase is recorded in check evidence/message but creates no regression finding. Missing support is preserved as `missing`, never rewritten to `unsupported`. An observed semantic diff category not handled by this closed mapping is an `error`, never an implicit pass.

### 6.6 IDS specification

`ids.specification` requires the policy to contain the expected IDS SHA-256 and candidate `source_id`. The caller supplies the IDS and IFC source explicitly. The IFC bytes MUST hash to the exact registered source record and the IDS bytes MUST hash to the policy value before parsing begins.

IDS results are labeled `ids` and never replace package validation, integrity, geometry, provenance, capability or diff checks.

## 7. IDS 1.0 bounded profile

The selected standard is buildingSMART IDS `v1.0.0`, final release commit `1effec6f419798ce09617416d258a35bdc58320a`, namespace `http://standards.buildingsmart.org/IDS`. IDS 1.0 has no root version attribute: the namespace, closed AECCTX profile and byte provenance establish the selected version. `xsi:schemaLocation` is inert metadata and is never dereferenced or treated as version authority; this preserves unchanged official v1.0 tag fixtures whose historical hint names `0.9.7`. Earlier drafts and later namespaces/profiles remain unsupported.

The selected implementation is exactly `ifctester==0.8.5` with `ifcopenshell==0.8.5`. The supported IFC schema identifiers are `IFC2X3` and `IFC4`, matching the existing AECCTX bounded IFC corpus. IFC4X1, IFC4X2, IFC4X3 and custom schemas remain unsupported here even if the dependency can parse them.

The initial public target is a partial simple-value subset of these IDS facet families in applicability and requirements:

- `entity` with exact `name` and optional exact `predefinedType`;
- `attribute` with exact `name` and absent-or-exact simple value;
- `classification` with absent-or-exact `system` and `value`;
- `property` with exact `propertySet`, `baseName`, optional exact `dataType` and absent-or-exact simple value;
- `material` with absent-or-exact simple value.

Required, optional and prohibited cardinalities are supported only where an unchanged buildingSMART v1.0 conformance case and an AECCTX project fixture both pass. `partOf`, XSD restrictions/patterns/ranges/enumerations, URI dereference, bSDD lookup, geometry, quantities not represented by the selected property subset and every unlisted facet/profile remain explicit `unsupported` findings. Passing an unsupported facet as though it were evaluated is prohibited.

Official buildingSMART fixtures MAY be vendored only unchanged from the tagged release, with exact hashes and the upstream CC BY-ND 4.0 license/attribution. Project-authored fixtures remain Apache-2.0 and are kept separate. No official fixture may be edited and still described as an official conformance case.

Task 6 selects exactly the paired `.ids`/`.ifc` cases named in `fixtures/third_party/buildingsmart-ids-1.0/ORIGIN.json`: one positive and one negative simple-value case for each of `entity`, `attribute`, `classification`, `property` and `material`. No restriction, `partOf`, URI, unlisted facet or additional upstream case is claimed by this selection. The manifest binds every relative upstream path and SHA-256 to commit `1effec6f419798ce09617416d258a35bdc58320a`.

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

`candidate` is the exact validated package identity. It MAY be `null` only when outcome is `error` because structural/integrity preflight could not establish a trusted identity; non-error results MUST contain it. No placeholder package ID or digest is synthesized. Validation diagnostics are partitioned deterministically: artifact path/hash/size/required-reference/logical-digest failures belong to `aecctx.system.integrity`; all other package validation failures belong to `aecctx.system.validation`. `aecctx.system.policy`, validation and integrity are always present after successful preflight and cannot be waived.

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

Regular-file inputs only are accepted; symlinks are rejected. Findings are accumulated only up to `max_findings`, and canonical result bytes only up to `max_result_bytes`. Exceeding either bound raises the stable operational `GateError` `AECCTX_GATE_FINDING_LIMIT_EXCEEDED` or `AECCTX_GATE_RESULT_LIMIT_EXCEEDED`; it never returns a truncated result or partial `pass`.

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

Task 4 adds `AECCTX_GATE_CANDIDATE_INVALID`, `AECCTX_GATE_CANDIDATE_CHANGED_DURING_EVALUATION`, `AECCTX_GATE_CAPABILITY_MISSING`, `AECCTX_GATE_CAPABILITY_BELOW_MINIMUM`, `AECCTX_GATE_LOSS_MAXIMUM_EXCEEDED`, `AECCTX_GATE_LOSS_REASON_MAXIMUM_EXCEEDED`, `AECCTX_GATE_LOSS_EVIDENCE_MISSING`, `AECCTX_GATE_LOSS_EVIDENCE_INCONSISTENT`, `AECCTX_GATE_VALUE_FIELD_MISSING`, `AECCTX_GATE_VALUE_STATE_INVALID`, `AECCTX_GATE_VALUE_STATE_REQUIRES_REVIEW`, `AECCTX_GATE_VALUE_STATE_FAILED`, `AECCTX_GATE_DIAGNOSTIC_MAXIMUM_EXCEEDED`, `AECCTX_GATE_DIAGNOSTIC_CODE_MAXIMUM_EXCEEDED`, `AECCTX_GATE_DIAGNOSTIC_EVIDENCE_INVALID`, `AECCTX_GATE_FINDING_LIMIT_EXCEEDED`, `AECCTX_GATE_RESULT_LIMIT_EXCEEDED` and `AECCTX_GATE_CHECK_NOT_IMPLEMENTED` as stable codes. Until their owning tasks land, `diff.regression`, `ids.specification` and their optional inputs fail closed with `AECCTX_GATE_CHECK_NOT_IMPLEMENTED`; they are never ignored or reported as evaluated.

Task 5 adds `AECCTX_GATE_BASELINE_MISSING`, `AECCTX_GATE_BASELINE_INVALID`, `AECCTX_GATE_BASELINE_CHANGED_DURING_EVALUATION`, `AECCTX_GATE_DIFF_ADDED_RECORD`, `AECCTX_GATE_DIFF_REMOVED_RECORD`, `AECCTX_GATE_DIFF_CHANGED_RECORD`, `AECCTX_GATE_DIFF_ARTIFACT_CHANGED`, `AECCTX_GATE_CAPABILITY_REGRESSION`, `AECCTX_GATE_DIFF_LOSS_CHANGED`, `AECCTX_GATE_DIFF_IDENTITY_CHANGED`, `AECCTX_GATE_DIFF_PRODUCER_CHANGED`, `AECCTX_GATE_DIFF_VERSION_CHANGED` and `AECCTX_GATE_DIFF_CATEGORY_UNHANDLED` as stable codes. Task 5 implements only `diff.regression`; `ids.specification` and IDS inputs continue to fail closed with `AECCTX_GATE_CHECK_NOT_IMPLEMENTED` until Task 6.

Task 6 adds `AECCTX_GATE_IDS_INPUT_PAIR_REQUIRED`, `AECCTX_GATE_IDS_INPUT_INVALID`, `AECCTX_GATE_IDS_DIGEST_MISMATCH`, `AECCTX_GATE_IDS_SOURCE_ID_MISMATCH`, `AECCTX_GATE_IDS_SOURCE_HASH_MISMATCH`, `AECCTX_GATE_IDS_SOURCE_SCHEMA_MISMATCH`, `AECCTX_GATE_IDS_XML_INVALID`, `AECCTX_GATE_IDS_XML_ACTIVE_CONTENT`, `AECCTX_GATE_IDS_NAMESPACE_UNSUPPORTED`, `AECCTX_GATE_IDS_FACET_UNSUPPORTED`, `AECCTX_GATE_IDS_RESTRICTION_UNSUPPORTED`, `AECCTX_GATE_IDS_LIMIT_EXCEEDED`, `AECCTX_GATE_IDS_DEPENDENCY_UNAVAILABLE`, `AECCTX_GATE_IDS_DEPENDENCY_VERSION_MISMATCH`, `AECCTX_GATE_IDS_WORKER_TIMEOUT`, `AECCTX_GATE_IDS_WORKER_CRASH`, `AECCTX_GATE_IDS_WORKER_OUTPUT_INVALID`, `AECCTX_GATE_IDS_WORKER_OUTPUT_LIMIT`, `AECCTX_GATE_IDS_SPECIFICATION_FAILED` and `AECCTX_GATE_IDS_REQUIREMENT_FAILED` as stable codes. Pairing, binding, XML safety, dependency and worker-protocol failures are `aecctx.system.ids-input` errors. A safely parsed unsupported facet/restriction or completed IDS nonconformance is an exact policy finding using the check's `failure_mode`; it is never reported as a system pass or silently evaluated.

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
