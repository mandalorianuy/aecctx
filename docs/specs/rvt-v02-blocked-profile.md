# AECCTX RVT v0.2 Blocked Provider Profile

Version: `0.2.0-draft.1`
Date: 2026-07-12
Status: Normative ACX-19 design approved 2026-07-12; no RVT extraction capability is implemented or claimed

## 1. Purpose

This profile governs ACX-19 when no RVT decoder/provider satisfies the repository's licensing, runtime, sandbox, CI, privacy and fixture-publication gates. It turns that absence into executable anti-claim behavior instead of creating a nominal adapter or a documentation-only backlog item.

The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT and MAY are normative.

## 2. Decision outcome

No RVT provider is selected. AECCTX MUST retain RVT semantic extraction as `unsupported` and normal unknown-input ingestion as `opaque`. The repository MUST NOT register an RVT provider, add an `rvt` CLI adapter, infer RVT semantics from an extension, or publish an RVT extraction fixture/claim without reopening ACXD-030 and updating the implementation plan first.

The evaluated routes are:

| Route | Technically relevant capability | Blocking evidence |
|---|---|---|
| Autodesk Revit desktop API | Direct database API over documents, elements and parameters | Requires a licensed Windows Revit installation; the API is installed with Revit. No reviewed Windows ACX-12 enforcement profile, license entitlement, CI runtime or publishable fixture exists in this repository. |
| Autodesk Platform Services Automation API for Revit | Headless cloud Revit DB API through app bundles, activities and work items | Requires network egress, Autodesk application credentials, remote input/output transfer, billing/subscription governance, retention/jurisdiction review and a network-provider enforcement profile. None is authorized or available. |
| Open Design Alliance BimRv SDK | Native RVT/RFA/RTE read APIs for multiple Revit versions | Requires ODA Sustaining membership plus a separately licensed BimRv module. The repository has no entitlement, redistributable runtime, public CI access or fixture-generation rights. |
| Autodesk Revit IFC exporter | IFC conversion from Revit through Autodesk's exporter | Requires Revit and proprietary Revit assemblies; it is not a standalone RVT parser. Converted IFC could only be derived evidence after a licensed RVT execution profile exists. |

Trial downloads, personal installations, proprietary samples and unreviewed cloud accounts MUST NOT support a public claim.

## 3. Functional blocked outcome

ACX-19 completion as `blocked` requires all of the following executable behavior:

1. A machine-readable provider-decision record enumerates every candidate, blocking axis and reopening requirement.
2. Portable conformance validates that record and fails if a provider is marked selected without exact entitlement, runtime, platform, sandbox, CI, privacy and fixture-rights evidence.
3. A project-authored sentinel named with an `.rvt` extension is explicitly identified as **not a valid RVT file**. It proves only that extensions do not trigger semantic extraction and that the existing opaque fallback preserves exact bytes, hash, explicit capability/loss and deterministic package identity.
4. The claim registry publishes only the bounded unsupported boundary. It MUST NOT name an RVT version, schema, element class, geometry capability or provider as supported.
5. Distribution tests prove that core wheel/sdist and dependency metadata contain no Revit, Autodesk APS, ODA BimRv, proprietary binary, credential or consumer dependency.
6. Repository scans prove that no WoodFraming, `WFDomain`, `WFImport` or construction-family mapping enters the result.

The sentinel is anti-claim evidence, not a positive RVT fixture. It MUST NOT be described as parsed, decoded, valid, representative or version-scoped RVT.

## 4. Provider decision record

`conformance/v0.2/rvt-provider-decision.json` MUST contain:

- record version and decision status `blocked`;
- `selected_provider: null`;
- candidate IDs, official source URLs and evaluation date;
- exact license/entitlement, runtime/platform, sandbox, CI, fixture-rights, network, telemetry/retention and lifecycle states;
- stable blocker codes and human-readable impact;
- reopening alternatives and the exact human authorization/evidence each requires.

Allowed blocker codes for this cut are:

- `AECCTX_RVT_ENTITLEMENT_UNAVAILABLE`;
- `AECCTX_RVT_RUNTIME_UNAVAILABLE`;
- `AECCTX_RVT_SANDBOX_PROFILE_UNAVAILABLE`;
- `AECCTX_RVT_CI_UNAVAILABLE`;
- `AECCTX_RVT_FIXTURE_RIGHTS_UNAVAILABLE`;
- `AECCTX_RVT_NETWORK_POLICY_UNAPPROVED`;
- `AECCTX_RVT_BILLING_POLICY_UNAPPROVED`;
- `AECCTX_RVT_RETENTION_POLICY_UNAPPROVED`.

The checker MUST reject unknown blocker codes, duplicate candidates, incomplete axes, a non-null selected provider, mutable/TBD values, host paths, credentials and non-official decision sources.

## 5. Opaque fallback contract

Default and explicit v0.1 ingest of the sentinel use the existing `ingest_opaque` behavior. Auto detection MUST choose `opaque`; an `.rvt` suffix alone has zero detection authority. Output MUST preserve exact SHA-256 and byte size while reporting semantic, relationship, 2D/3D geometry, material and georeferencing capabilities no higher than `opaque`/`unsupported` according to the existing package contract.

No `ingest_rvt()`, RVT event schema, provider descriptor, provider replay, element record, converted IFC/mesh artifact or `--adapter rvt` option is permitted in the blocked cut. Such output would be scaffolding that could be mistaken for capability.

## 6. Reopening gates

ACX-19 may be reopened only through one separately reviewed provider profile and an implementation-plan update accepted before code:

### 6.1 Local commercial runtime

The human owner supplies written entitlement for automation and redistribution, an exact supported RVT/runtime version, a reviewed Windows or other complete ACX-12 enforcement profile, private provider CI, a legally publishable project-authored RVT fixture strategy, security history and lifecycle support. For ODA, the record additionally supplies the BimRv module license and redistribution terms.

### 6.2 APS Automation API

The human owner approves Autodesk application credentials, billing/subscription, source upload consent, storage and retention/jurisdiction policy, allowed regions, telemetry, timeout/retry/rate limits and an ACX-12 network-provider profile. The provider must bind engine/app-bundle/activity/work-item versions and every input/output hash. Portable replay alone cannot establish live availability.

Either route MUST define exact RVT versions, source locator/identity rules, direct-versus-converted evidence, element/property/relation/geometry scope, negative/protected/corrupt behavior and fixture publication rights before implementation.

## 7. Non-scope

- no RVT parsing, conversion, authoring or mutation;
- no Autodesk/ODA credential acquisition, license bypass or trial-based claim;
- no Windows/native/network sandbox implementation;
- no fabricated RVT header, version, element ID, category, property, geometry, unit or coordinate evidence;
- no WoodFraming or consumer ontology;
- no ACX-20 signing work.

## 8. Acceptance

ACX-19 may close as `blocked` only when the decision record, anti-claim checker, sentinel opaque-fallback tests, distribution/consumer scans, capability matrix, claim registry and `docs/evidence/ACX-19.md` all agree; `python3 scripts/check_spec_contract.py`, task tests, `./scripts/verify_portable.sh` and `./scripts/verify.sh` pass; and ACX-20 alone is promoted to `pending-next`.

Documentation, an empty adapter, a provider descriptor without runtime access, a mock successful response, a proprietary sample or a replay fabricated without a real reviewed provider do not count as progress.

## 9. Official decision sources

- Autodesk, Revit Platform API installation: <https://help.autodesk.com/cloudhelp/2018/ENU/Revit-API/Revit_API_Developers_Guide/Introduction/Getting_Started/Welcome_to_the_Revit_Platform_API/Installation.html>
- Autodesk Platform Services, Automation API overview: <https://aps.autodesk.com/en/docs/design-automation/v3/developers_guide/overview/>
- Autodesk Platform Services, business model and Automation API pricing: <https://aps.autodesk.com/blog/aps-business-model-evolution>
- Open Design Alliance, BimRv FAQ and licensing: <https://www.opendesign.com/faq/bimrv>
- Open Design Alliance, BimRv product scope: <https://www.opendesign.com/products/bimrv>
- Autodesk, Revit IFC open-source exporter repository: <https://github.com/Autodesk/revit-ifc>
