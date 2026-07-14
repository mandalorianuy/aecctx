# AECCTX Quality Gate v0.3 Expanded IDS Profile

Version: `0.3.0-draft.1`
Date: 2026-07-14
Status: Normative ACX-36 implementation authority
Decision authority: ACXD-045

## 1. Relationship to the v0.2 gate

This profile extends only the IDS evaluator selected by `docs/specs/quality-gate-v02-profile.md`. The gate policy, result, finding, waiver, aggregate outcome, exit code, SDK, CLI, projection, atomic-output and limit contracts remain unchanged. A v0.2 policy and every accepted v0.2 corpus result MUST remain byte-compatible.

The new public target is claim `quality-gate.ids-expanded` under profile `aecctx-gate-v1-ids-1.0-expanded-v1`. Until ACX-36 acceptance completes, it remains a target and MUST NOT be advertised as implemented.

## 2. Fixed standard and runtime

- buildingSMART IDS `v1.0.0`, final commit `1effec6f419798ce09617416d258a35bdc58320a`;
- namespace `http://standards.buildingsmart.org/IDS`; historical `xsi:schemaLocation` hints remain inert;
- optional `ifctester==0.8.5` and `ifcopenshell==0.8.5`;
- IFC schemas `IFC2X3` and `IFC4` only;
- Python 3.12+ on Linux, macOS and Windows;
- the existing fixed `python -I -m aecctx.gate._ids_worker` process and hard limits.

No host trust, network, bSDD, URI dereference, schema download, caller command, clock or LLM participates.

## 3. Selected expansion

### 3.1 `partOf`

`partOf` is accepted in applicability or requirements only for:

- `IFCRELAGGREGATES`;
- `IFCRELASSIGNSTOGROUP`;
- `IFCRELCONTAINEDINSPATIALSTRUCTURE`;
- `IFCRELNESTS`.

The nested entity contains an exact or admitted restricted uppercase IFC entity name and MAY contain an exact or admitted restricted predefined type. Direct/ancestral behavior is whatever the unchanged official IDS v1.0 case establishes for that exact relation. No other relation, relationship inference or consumer hierarchy is admitted.

### 3.2 Restrictions

Only these XML Schema restriction forms are admitted inside existing supported facet values and the nested `partOf` entity:

- `xs:restriction base="xs:string"` containing one `xs:pattern` or one or more `xs:enumeration` values;
- numeric `xs:restriction` with base `xs:double`, `xs:decimal` or `xs:integer` containing one or both matching lower/upper operators from `xs:minInclusive`, `xs:maxInclusive`, `xs:minExclusive` and `xs:maxExclusive`.

Restriction children MUST contain only a `value` attribute and no nested content. Pattern/enumeration values are bounded by the existing human-string limit. Numeric values MUST be finite lexical numbers. Mixed pattern/enumeration, mixed inclusive/exclusive operators for one side, empty restrictions, duplicate bounds and every unlisted XSD facet/base fail closed as unsupported. Length, min/max length, total/fraction digits, whitespace, nested restrictions and arbitrary types remain unsupported.

### 3.3 Cardinality

Specification applicability admits exactly:

- required: omitted `minOccurs` or `minOccurs="1"`, with omitted `maxOccurs` or `maxOccurs="unbounded"`;
- optional: `minOccurs="0"` and omitted `maxOccurs` or `maxOccurs="unbounded"`;
- prohibited: `minOccurs="0"` and `maxOccurs="0"`, with no requirements.

Existing requirement-facet cardinalities `required`, `optional` and `prohibited` retain their v0.2 semantics. Other occurrence values or prohibited specifications with requirements fail closed before evaluation.

## 4. Result and authority contract

The worker response protocol remains version `1` and adds `partof` as an admitted requirement kind. Findings continue to use `AECCTX_GATE_IDS_SPECIFICATION_FAILED` and `AECCTX_GATE_IDS_REQUIREMENT_FAILED`; safe out-of-profile content uses exact `AECCTX_GATE_IDS_FACET_UNSUPPORTED`, `AECCTX_GATE_IDS_RESTRICTION_UNSUPPORTED` or `AECCTX_GATE_IDS_CARDINALITY_UNSUPPORTED` findings under the policy failure mode.

The candidate package source record, supplied IFC bytes, supplied IDS bytes and their SHA-256 bindings remain authoritative. Markdown and CI annotations project the canonical `GateResult`; they never independently evaluate IDS or establish approval.

## 5. Safety and failure behavior

All v0.2 XML, path, size, count, process-tree, timeout, output and dependency controls remain mandatory. Preflight MUST complete before dependency import or worker creation. Unsupported constructs produce a completed policy finding and never pass silently. Malformed/active XML, input binding errors, worker failures and limit failures remain non-waivable system errors.

`uri`, bSDD, geometry and quantity-specific interpretation, remote lookup, XInclude, DTD/entity content and unlisted namespaces are prohibited. Source strings, descriptions, instructions and patterns are untrusted inert data except for their bounded evaluation inside the fixed worker.

## 6. Fixtures and conformance

Official cases are vendored unchanged from the selected commit under CC BY-ND 4.0 and recorded with upstream paths and SHA-256. At minimum, positive and negative official pairs cover every selected relation, pattern, enumeration, numeric bound and specification cardinality. Apache-2.0 project cases independently cover all selected constructs, exact evidence references and fail/review outcomes.

Conformance additionally covers unsupported relation/URI/geometry/quantity/restriction/cardinality, malicious XML, missing/mismatched dependencies, timeout/crash/malformed/oversized worker output, clean core installation, deterministic repeated bytes and SDK/CLI/Markdown/CI parity. Every v0.2 gate test and corpus case remains unchanged and passing.

## 7. Public claim ceiling and non-claims

After acceptance, `quality-gate.ids-expanded` is at most public `partial` for the exact profile, runtime, schemas, fixtures and platforms above. It is information-requirement conformance only.

The following remain unsupported or unclaimed: other IDS versions/namespaces; other IFC schemas; URI/bSDD/remote lookup; geometry and quantity-specific semantics; unlisted relations, facets, XSD restrictions or cardinalities; source correctness; engineering approval; regulatory certification; construction readiness; consumer acceptance; and universal IDS implementation behavior.

## 8. Normative and reviewed references

- buildingSMART IDS v1.0 release and commit: `https://github.com/buildingSMART/IDS/releases/tag/v1.0.0`
- buildingSMART IDS repository license: CC BY-ND 4.0
- IfcTester 0.8.5 API: `https://docs.ifcopenshell.org/autoapi/ifctester/index.html`
- IfcTester 0.8.5 distribution: `https://pypi.org/project/ifctester/0.8.5/`
- IfcTester and IfcOpenShell license: LGPL-3.0-or-later
