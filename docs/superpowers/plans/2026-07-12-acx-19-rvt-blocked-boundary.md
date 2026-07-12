# ACX-19 RVT Blocked Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close ACX-19 as a machine-validated `blocked` task while keeping RVT extraction publicly `unsupported`, proving deterministic opaque fallback and preventing accidental provider, dependency, fixture or consumer claims.

**Architecture:** ACX-19 adds no RVT adapter or runtime code. A repository conformance checker validates one governed provider-decision record, its exact unsupported claim, executable-source boundaries and built wheel/sdist contents; a project-authored invalid `.rvt` sentinel exercises the existing v0.1 opaque path without impersonating an RVT corpus.

**Tech Stack:** Python 3.12+, stdlib `argparse`/`json`/`pathlib`/`tarfile`/`zipfile`, existing `jsonschema[format]`, pytest, Hatchling build, Bash verification scripts.

## Global Constraints

- Execute only ACX-19; ACX-20 remains `pending` until the final ACX-19 promotion commit.
- `docs/specs/rvt-v02-blocked-profile.md` and ACXD-030 are normative.
- Do not create `ingest_rvt`, an `rvt` CLI adapter, an RVT provider descriptor/event/replay, or a valid/representative RVT fixture.
- RVT semantic extraction remains `unsupported`; ordinary unknown-input ingest remains `opaque`.
- The only `.rvt` fixture is `fixtures/v0.2/rvt/not-a-real-rvt.rvt`, whose bytes state that it is not an RVT file.
- No Autodesk, APS, ODA, Revit, proprietary runtime, credential, GPL/commercial decoder or consumer dependency enters the Apache-2.0 core.
- No WoodFraming, `WFDomain`, `WFImport` or construction-family mapping enters executable source or generated sentinel output.
- Unknown, unsupported, conflicted, explicit-null and not-applicable states remain explicit; no provider facts are inferred.
- Every implementation change follows red/green TDD and each task ends in a focused commit.

---

## File map

- Create `schemas/v0.2/rvt-provider-decision.schema.json`: structural contract for the blocked provider record; it is conformance material, not an extraction schema.
- Create `conformance/v0.2/rvt-provider-decision.json`: accepted ACXD-030 candidate evaluation and reopening requirements.
- Create `scripts/check_rvt_blocked_conformance.py`: semantic, claim, source-boundary and built-artifact checker.
- Create `tests/test_rvt_blocked_conformance.py`: negative/positive checker tests.
- Create `fixtures/v0.2/rvt/not-a-real-rvt.rvt`: project-authored anti-claim sentinel.
- Create `tests/test_rvt_blocked_profile.py`: deterministic opaque fallback, CLI auto-detection and consumer-output checks.
- Create `docs/evidence/ACX-19.md`: incremental `in_progress` evidence required by the public unsupported claim; Task 4 finalizes it before closure.
- Modify `conformance/v0.2/claims.json`: replace the RVT target with one public `unsupported` boundary claim.
- Modify `scripts/check_spec_contract.py`: require the ACX-19 schema, record, checker, sentinel and profile.
- Modify `scripts/verify_portable.sh`: validate JSON/schema, run the checker before tests and inspect built artifacts after build.
- Modify `tests/test_package_data.py`: lock portable-gate and sdist inclusion wiring.
- Modify `docs/capability-matrix.md`, `docs/implementation-plan.md`, `docs/HANDOFF.md`: close ACX-19 as `blocked`, record residuals and promote only ACX-20.
- Create `docs/evidence/ACX-19.md`: acceptance evidence and exact reopening decision.

---

### Task 1: Provider-decision schema, record and semantic checker

**Files:**
- Create: `schemas/v0.2/rvt-provider-decision.schema.json`
- Create: `conformance/v0.2/rvt-provider-decision.json`
- Create: `scripts/check_rvt_blocked_conformance.py`
- Create: `tests/test_rvt_blocked_conformance.py`

**Interfaces:**
- Consumes: ACXD-030, `docs/specs/rvt-v02-blocked-profile.md`, `conformance/v0.2/claims.json`.
- Produces: `validate_decision(record: object) -> tuple[str, ...]`, `validate_claim(registry: object) -> tuple[str, ...]`, `validate_source_boundary(root: Path) -> tuple[str, ...]`, and CLI exit `0` only for the complete blocked boundary.

- [ ] **Step 1: Write failing schema/record validation tests**

Create tests that load the committed record, invoke the checker as a subprocess, and mutate one property per rejected class:

```python
def run_checker(tmp_path: Path, record: dict[str, object]) -> subprocess.CompletedProcess[str]:
    decision = tmp_path / "decision.json"
    decision.write_text(json.dumps(record), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(CHECKER), "--decision", str(decision), "--claims", str(CLAIMS), "--root", str(ROOT)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_committed_rvt_blocked_decision_is_valid() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECKER), "--decision", str(DECISION), "--claims", str(CLAIMS), "--root", str(ROOT)],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "aecctx RVT blocked conformance: ok\n"


@pytest.mark.parametrize("mutation, expected", [
    (lambda value: value.__setitem__("selected_provider", "autodesk-revit-desktop"), "selected_provider must be null"),
    (lambda value: value["candidates"].append(dict(value["candidates"][0])), "duplicate candidate id"),
    (lambda value: value["candidates"][0]["axes"].pop("ci_access"), "ci_access"),
    (lambda value: value["candidates"][0]["blocker_codes"].append("AECCTX_RVT_UNKNOWN"), "unknown blocker code"),
    (lambda value: value["candidates"][0]["official_sources"].append("https://example.invalid/rvt"), "non-official decision source"),
    (lambda value: value["candidates"][0].__setitem__("notes", "/Users/operator/license.dat"), "host path or credential-like value"),
])
def test_rvt_decision_rejects_incomplete_or_unsafe_values(tmp_path: Path, mutation: Callable[[dict[str, object]], None], expected: str) -> None:
    record = json.loads(DECISION.read_text(encoding="utf-8"))
    mutation(record)
    result = run_checker(tmp_path, record)
    assert result.returncode == 1
    assert expected in result.stderr
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run: `.venv/bin/python -m pytest tests/test_rvt_blocked_conformance.py -q`

Expected: FAIL because the schema, record and checker do not exist.

- [ ] **Step 3: Add the exact decision schema and record**

The schema must require:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://aecctx.dev/schemas/v0.2/rvt-provider-decision.schema.json",
  "type": "object",
  "additionalProperties": false,
  "required": ["version", "decision", "selected_provider", "evaluated_at", "candidates", "reopening_alternatives"],
  "properties": {
    "version": {"const": "0.2.0"},
    "decision": {"const": "blocked"},
    "selected_provider": {"type": "null"},
    "evaluated_at": {"const": "2026-07-12"},
    "candidates": {"type": "array", "minItems": 4, "items": {"$ref": "#/$defs/candidate"}},
    "reopening_alternatives": {"type": "array", "minItems": 2, "items": {"$ref": "#/$defs/reopening"}}
  },
  "$defs": {
    "axes": {
      "type": "object",
      "additionalProperties": false,
      "required": ["license_entitlement", "runtime_platform", "sandbox_profile", "ci_access", "fixture_rights", "network", "telemetry_retention", "lifecycle"],
      "properties": {
        "license_entitlement": {"enum": ["available", "unavailable", "unapproved", "not_applicable", "unknown"]},
        "runtime_platform": {"enum": ["available", "unavailable", "unapproved", "not_applicable", "unknown"]},
        "sandbox_profile": {"enum": ["available", "unavailable", "unapproved", "not_applicable", "unknown"]},
        "ci_access": {"enum": ["available", "unavailable", "unapproved", "not_applicable", "unknown"]},
        "fixture_rights": {"enum": ["available", "unavailable", "unapproved", "not_applicable", "unknown"]},
        "network": {"enum": ["available", "unavailable", "unapproved", "not_applicable", "unknown"]},
        "telemetry_retention": {"enum": ["available", "unavailable", "unapproved", "not_applicable", "unknown"]},
        "lifecycle": {"enum": ["available", "unavailable", "unapproved", "not_applicable", "unknown"]}
      }
    },
    "candidate": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "official_sources", "axes", "blocker_codes", "impact"],
      "properties": {
        "id": {"enum": ["autodesk-revit-desktop", "autodesk-aps-automation", "oda-bimrv", "autodesk-revit-ifc-exporter"]},
        "official_sources": {"type": "array", "minItems": 1, "items": {"type": "string", "format": "uri"}},
        "axes": {"$ref": "#/$defs/axes"},
        "blocker_codes": {"type": "array", "minItems": 1, "uniqueItems": true, "items": {"type": "string"}},
        "impact": {"type": "string", "minLength": 1}
      }
    },
    "reopening": {
      "type": "object",
      "additionalProperties": false,
      "required": ["id", "human_authorization", "required_evidence"],
      "properties": {
        "id": {"enum": ["licensed-local-runtime", "aps-network-provider"]},
        "human_authorization": {"type": "string", "minLength": 1},
        "required_evidence": {"type": "array", "minItems": 1, "uniqueItems": true, "items": {"type": "string", "minLength": 1}}
      }
    }
  }
}
```

The record must contain exactly the four candidates and official URLs listed in the normative profile. Every candidate must enumerate all eight axes and at least one of the eight allowed blocker codes. Reopening alternatives must be exactly `licensed-local-runtime` and `aps-network-provider`, with the approvals/evidence from sections 6.1 and 6.2 of the profile.

- [ ] **Step 4: Implement the minimal checker**

The checker must:

```python
ALLOWED_BLOCKERS = frozenset({
    "AECCTX_RVT_ENTITLEMENT_UNAVAILABLE",
    "AECCTX_RVT_RUNTIME_UNAVAILABLE",
    "AECCTX_RVT_SANDBOX_PROFILE_UNAVAILABLE",
    "AECCTX_RVT_CI_UNAVAILABLE",
    "AECCTX_RVT_FIXTURE_RIGHTS_UNAVAILABLE",
    "AECCTX_RVT_NETWORK_POLICY_UNAPPROVED",
    "AECCTX_RVT_BILLING_POLICY_UNAPPROVED",
    "AECCTX_RVT_RETENTION_POLICY_UNAPPROVED",
})
OFFICIAL_HOSTS = frozenset({"help.autodesk.com", "aps.autodesk.com", "www.opendesign.com", "github.com"})


def validate_decision(record: object) -> tuple[str, ...]:
    errors: list[str] = []
    validator = Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8")), format_checker=FormatChecker())
    errors.extend(error.message for error in validator.iter_errors(record))
    if not isinstance(record, dict):
        return tuple(sorted(set(errors)))
    if record.get("selected_provider") is not None:
        errors.append("selected_provider must be null")
    candidates = record.get("candidates", [])
    ids = [item.get("id") for item in candidates if isinstance(item, dict)]
    if len(ids) != len(set(ids)):
        errors.append("duplicate candidate id")
    for item in candidates if isinstance(candidates, list) else []:
        if not isinstance(item, dict):
            continue
        for code in item.get("blocker_codes", []):
            if code not in ALLOWED_BLOCKERS:
                errors.append(f"unknown blocker code: {code}")
        for source in item.get("official_sources", []):
            if not isinstance(source, str) or urlparse(source).hostname not in OFFICIAL_HOSTS:
                errors.append(f"non-official decision source: {source}")
    serialized = json.dumps(record, sort_keys=True)
    if re.search(r"(?:/Users/|[A-Za-z]:\\\\|AKIA|BEGIN (?:RSA |EC )?PRIVATE KEY|client_secret)", serialized, re.IGNORECASE):
        errors.append("host path or credential-like value")
    if re.search(r'"(?:pending|to_be_decided|tbd)"', serialized, re.IGNORECASE):
        errors.append("mutable decision value")
    return tuple(sorted(set(errors)))
```

`main()` loads `--decision`, `--claims`, and `--root`; unreadable/invalid JSON becomes one stable error per file. It prints sorted errors prefixed with `aecctx RVT blocked conformance:` to stderr and exits `1`, otherwise prints exactly `aecctx RVT blocked conformance: ok` and exits `0`.

- [ ] **Step 5: Run the focused tests and confirm GREEN**

Run: `.venv/bin/python -m pytest tests/test_rvt_blocked_conformance.py -q`

Expected: all tests PASS.

- [ ] **Step 6: Commit the decision checker**

```bash
git add schemas/v0.2/rvt-provider-decision.schema.json conformance/v0.2/rvt-provider-decision.json scripts/check_rvt_blocked_conformance.py tests/test_rvt_blocked_conformance.py
git commit -m "test: enforce ACX-19 RVT provider decision"
```

---

### Task 2: Unsupported claim and deterministic opaque sentinel

**Files:**
- Create: `fixtures/v0.2/rvt/not-a-real-rvt.rvt`
- Create: `tests/test_rvt_blocked_profile.py`
- Create: `docs/evidence/ACX-19.md`
- Modify: `conformance/v0.2/claims.json`
- Modify: `tests/test_rvt_blocked_conformance.py`

**Interfaces:**
- Consumes: existing `aecctx.ingest.ingest_opaque`, CLI `--adapter auto|opaque`, `PackageReader`, `validate_claim_registry_file`.
- Produces: claim `rvt.external-provider` with exact public `unsupported` boundary and executable proof that suffixes have no semantic authority.

- [ ] **Step 1: Write failing sentinel and claim tests**

```python
SENTINEL_BYTES = b"AECCTX anti-claim sentinel. This is not an Autodesk Revit RVT file.\n"
FIXED_TIME = "2026-07-12T00:00:00Z"


def test_rvt_sentinel_is_explicitly_invalid_and_stable() -> None:
    assert SENTINEL.read_bytes() == SENTINEL_BYTES
    assert hashlib.sha256(SENTINEL_BYTES).hexdigest() == "a0e93c6e20f3ee4356fc8f6ecca029d95da723154f7b2f25e49ed7268d2e1a49"


def test_rvt_suffix_uses_deterministic_opaque_fallback(tmp_path: Path) -> None:
    first = tmp_path / "first.aecctx"
    second = tmp_path / "second.aecctx"
    ingest_opaque(SENTINEL, first, created_at=FIXED_TIME, package_form="zip")
    ingest_opaque(SENTINEL, second, created_at=FIXED_TIME, package_form="zip")
    assert first.read_bytes() == second.read_bytes()
    package = PackageReader(first)
    assert package.manifest["capabilities"]["identity"] == "full"
    assert all(value == "opaque" for key, value in package.manifest["capabilities"].items() if key not in {"identity", "validation"})
    source = json.loads(package.read_bytes("sources/sources.jsonl").decode("utf-8"))
    assert source["detected_format"] == {"reason_code": "AECCTX_NO_FORMAT_ADAPTER", "state": "unknown"}
    assert source["extractor"]["plugin_id"] == "aecctx.core.opaque"


def test_cli_auto_does_not_promote_rvt_suffix(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output = tmp_path / "auto.aecctx"
    assert cli.main(["ingest", str(SENTINEL), "--output", str(output), "--form", "zip", "--adapter", "auto", "--created-at", FIXED_TIME, "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["support"] == "opaque"


def test_claim_registry_exposes_only_unsupported_rvt_boundary() -> None:
    registry = json.loads(CLAIMS.read_text(encoding="utf-8"))
    claim = next(item for item in registry["claims"] if item["id"] == "rvt.external-provider")
    assert claim == {
        "id": "rvt.external-provider",
        "status": "public",
        "support_level": "unsupported",
        "profile": "rvt-no-provider-blocked-v1",
        "platform_scope": ["any"],
        "provider_scope": "none",
        "fixture_ids": ["v02-rvt-acx19-anti-claim"],
        "test_ids": [
            "tests/test_rvt_blocked_profile.py::test_rvt_suffix_uses_deterministic_opaque_fallback",
            "tests/test_rvt_blocked_profile.py::test_cli_auto_does_not_promote_rvt_suffix",
        ],
        "evidence": "docs/evidence/ACX-19.md",
    }
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `.venv/bin/python -m pytest tests/test_rvt_blocked_profile.py tests/test_rvt_blocked_conformance.py -q`

Expected: FAIL because the sentinel/claim/evidence mapping do not exist.

- [ ] **Step 3: Create the sentinel and record its real hash**

Create the sentinel with exactly the bytes in `SENTINEL_BYTES`, then run:

```bash
shasum -a 256 fixtures/v0.2/rvt/not-a-real-rvt.rvt
```

Replace the test's hash literal with the printed 64-character digest before running GREEN. This is a measured fixture identity, not a guessed value.

- [ ] **Step 4: Replace the target claim with the bounded unsupported claim**

Add fixture registry entry:

```json
{"id": "v02-rvt-acx19-anti-claim", "path": "fixtures/v0.2/rvt/not-a-real-rvt.rvt"}
```

Replace only `rvt.external-provider` with the exact claim asserted by the test. Do not add RVT versions, element classes, geometry, schemas, provider IDs or replay claims.

Create `docs/evidence/ACX-19.md` with status `in_progress`, links to ACXD-030 and the blocked profile, the Task 1 commit, the Task 2 sentinel hash/tests, retained support `unsupported` with opaque fallback, and an explicit “not yet accepted” section listing Task 3 distribution gates and Task 4 full verification/promotion as pending. This file satisfies claim traceability without claiming ACX-19 completion.

- [ ] **Step 5: Add claim cross-validation to the checker**

`validate_claim()` must require the exact claim object above, require the sentinel fixture path, reject any other claim ID beginning with `rvt.`, and reject any non-null selected provider in the decision record. Add negative tests for `status="experimental"`, `support_level="partial"`, a versioned profile, a provider name and a second `rvt.*` claim.

- [ ] **Step 6: Run focused tests and confirm GREEN**

Run: `.venv/bin/python -m pytest tests/test_rvt_blocked_profile.py tests/test_rvt_blocked_conformance.py tests/test_claim_registry.py -q`

Expected: all tests PASS.

- [ ] **Step 7: Commit the unsupported boundary**

```bash
git add fixtures/v0.2/rvt/not-a-real-rvt.rvt tests/test_rvt_blocked_profile.py tests/test_rvt_blocked_conformance.py conformance/v0.2/claims.json scripts/check_rvt_blocked_conformance.py docs/evidence/ACX-19.md
git commit -m "test: prove RVT opaque anti-claim boundary"
```

---

### Task 3: Source, distribution and portable-gate enforcement

**Files:**
- Modify: `scripts/check_rvt_blocked_conformance.py`
- Modify: `tests/test_rvt_blocked_conformance.py`
- Modify: `tests/test_rvt_blocked_profile.py`
- Modify: `scripts/check_spec_contract.py`
- Modify: `scripts/verify_portable.sh`
- Modify: `tests/test_package_data.py`

**Interfaces:**
- Consumes: repository root and optional `--artifact` paths produced by Hatchling.
- Produces: deterministic rejection of runtime/provider/consumer source, prohibited dependencies, proprietary binaries, extra RVT samples and adapter/provider scaffolding in wheel/sdist.

- [ ] **Step 1: Write failing source/artifact boundary tests**

Add temporary-root tests proving rejection of:

```python
@pytest.mark.parametrize("relative, content, expected", [
    ("src/aecctx/adapters/rvt.py", "def ingest_rvt(): pass\n", "RVT adapter/provider scaffolding"),
    ("src/aecctx/providers/rvt.py", "PROVIDER = 'autodesk'\n", "RVT adapter/provider scaffolding"),
    ("src/aecctx/consumer.py", "import WFDomain\n", "consumer symbol in executable source"),
])
def test_source_boundary_rejects_rvt_scaffolding_and_consumer_symbols(tmp_path: Path, relative: str, content: str, expected: str) -> None:
    path = tmp_path / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    assert expected in validate_source_boundary(tmp_path)
```

Build minimal wheel ZIP and sdist tar fixtures inside `tmp_path`, then assert rejection for `Requires-Dist: Autodesk-Revit`, `.dll`, `.exe`, `src/aecctx/adapters/rvt.py`, and any `.rvt` member other than the exact sentinel path. Unit tests MUST NOT depend on a pre-existing `dist/` because pytest runs before build in the portable gate. Acceptance of the real wheel/sdist occurs through the post-build checker invocation in Step 4.

- [ ] **Step 2: Run tests and confirm RED**

Run: `.venv/bin/python -m pytest tests/test_rvt_blocked_conformance.py tests/test_rvt_blocked_profile.py tests/test_package_data.py -q`

Expected: FAIL because artifact/source scans and gate wiring are absent.

- [ ] **Step 3: Implement source and artifact scans**

`validate_source_boundary(root)` must scan only executable `src/aecctx/**/*.py` and reject case-insensitive `woodframing`, exact `WFDomain`, exact `WFImport`, `ingest_rvt`, plus paths `src/aecctx/adapters/rvt.py` and `src/aecctx/providers/rvt.py`. This avoids false positives from governance documentation that intentionally names the boundary.

`validate_artifact(path)` must:

```python
PROHIBITED_RUNTIME_SUFFIXES = (".dll", ".dylib", ".exe", ".pyd", ".so")
PROHIBITED_DEPENDENCY_NAMES = ("autodesk", "aps", "bimrv", "oda", "revit", "woodframing", "wfdomain", "wfimport")
ALLOWED_RVT_MEMBER_SUFFIX = "fixtures/v0.2/rvt/not-a-real-rvt.rvt"
PROHIBITED_CODE_SUFFIXES = ("src/aecctx/adapters/rvt.py", "src/aecctx/providers/rvt.py", "src/aecctx/schemas/v0_2/rvt-provider-event.schema.json")
```

For wheels, inspect ZIP member names and only `*.dist-info/METADATA` `Requires-Dist:` lines. For sdists, inspect tar member names and the root `pyproject.toml` dependency sections. Reject unsafe/symlink/hardlink members before reading. Do not scan prose in `docs/`, because the governance authorities must name the rejected products and consumer boundary.

- [ ] **Step 4: Wire portable and spec gates**

Add required files to `check_required_files()` and these commands to `verify_portable.sh`:

```bash
"$python_runtime" -m json.tool schemas/v0.2/rvt-provider-decision.schema.json >/dev/null
"$python_runtime" -m json.tool conformance/v0.2/rvt-provider-decision.json >/dev/null
"$python_runtime" scripts/check_rvt_blocked_conformance.py
```

After the existing build command:

```bash
"$python_runtime" scripts/check_rvt_blocked_conformance.py --artifact dist/aecctx-0.1.0-py3-none-any.whl --artifact dist/aecctx-0.1.0.tar.gz
```

`tests/test_package_data.py` must assert those paths/commands are wired and that `/schemas/v0.2`, `/conformance/v0.2`, `/fixtures/v0.2`, `/docs` remain in the sdist include list.

- [ ] **Step 5: Run narrow and portable gates**

Run:

```bash
.venv/bin/python -m pytest tests/test_rvt_blocked_conformance.py tests/test_rvt_blocked_profile.py tests/test_package_data.py tests/test_claim_registry.py -q
./scripts/verify_portable.sh
```

Expected: focused tests PASS and final line `aecctx portable verify: ok`.

- [ ] **Step 6: Commit enforcement wiring**

```bash
git add scripts/check_rvt_blocked_conformance.py scripts/check_spec_contract.py scripts/verify_portable.sh tests/test_rvt_blocked_conformance.py tests/test_rvt_blocked_profile.py tests/test_package_data.py
git commit -m "test: gate RVT blocked distribution boundary"
```

---

### Task 4: Finalize acceptance evidence, blocked closure and next-task promotion

**Files:**
- Modify: `docs/evidence/ACX-19.md`
- Modify: `docs/capability-matrix.md`
- Modify: `docs/implementation-plan.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/specs/rvt-v02-blocked-profile.md` only if implementation evidence reveals a bounded clarification; record any behavioral change in `docs/decisions/decision-log.md` before code.

**Interfaces:**
- Consumes: green Task 1–3 commits and gate output.
- Produces: ACX-19 status `blocked`, exact evidence/reopening decision, ACX-20 status `pending-next`, and no other task promotion.

- [ ] **Step 1: Write ACX-19 evidence before changing status**

Follow the 12-field acceptance template in `docs/implementation-plan.md`. Include:

- completion status `blocked`, date and all Task 1–3 commits;
- ACXD-019/ACXD-030 and normative profile links;
- exact files and public unsupported claim;
- official provider research sources and evaluation date;
- local narrow/portable/full commands and results;
- CI run URL/IDs after publication;
- retained RVT support `unsupported` plus opaque fallback;
- impact: no neutral RVT elements/properties/relationships/geometry are available;
- alternatives attempted: Revit desktop, APS Automation, ODA BimRv, Revit IFC exporter;
- exact reopening authorization/evidence for local runtime or APS;
- distribution and consumer-boundary scan results;
- promotion of ACX-20 only.

- [ ] **Step 2: Update truthful capability and task state**

Change the capability-matrix RVT row to:

```markdown
| RVT | public `unsupported`; deterministic v0.1 opaque fallback is anti-claim evidence only | No provider selected under ACXD-030; future extraction requires a separately reviewed reopening profile | ACX-19 blocked |
```

In the task ledger set ACX-19 to `blocked`, ACX-20 to `pending-next`, and leave ACX-21–ACX-23 `pending`. Add an ACX-19 completion resolution stating that no provider, adapter, descriptor, replay, version or semantic claim was added. Update HANDOFF to execute only ACX-20 after a new continuation request.

- [ ] **Step 3: Run the complete local gate**

Run:

```bash
python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues
./scripts/verify.sh
git diff --check
```

Expected: baseline integration healthy, final line `aecctx verify: ok`, and no diff errors. If the baseline checker refreshes only its generated timestamps, restore those two timestamp-only changes before committing.

- [ ] **Step 4: Commit the ACX-19 closure**

```bash
git add docs/evidence/ACX-19.md docs/capability-matrix.md docs/implementation-plan.md docs/HANDOFF.md docs/specs/rvt-v02-blocked-profile.md docs/decisions/decision-log.md
git commit -m "docs: close ACX-19 as blocked"
```

- [ ] **Step 5: Publish and verify remote CI**

```bash
git push origin codex/acx-11-shared-expansion-contracts
gh run list --commit "$(git rev-parse HEAD)" --limit 5
```

Wait for the matching CI run and require successful Ubuntu, macOS and Windows `verify_portable.sh` jobs. Record the final run and job URLs in `docs/evidence/ACX-19.md`; if that requires a final evidence-only commit, rerun `python3 scripts/check_spec_contract.py`, push it and require the replacement CI run green.

- [ ] **Step 6: Stop before ACX-20**

Report ACX-19 as documented `blocked`, 9 of 13 expansion milestones resolved (`69.2%`), residual provider requirements, exact validation evidence and ACX-20 as the only `pending-next` task. Do not inspect or implement signing until the user explicitly asks to continue.

---

## Plan self-review

- Spec coverage: sections 2–7 map to Tasks 1–3; section 8 and promotion map to Task 4.
- Capability honesty: no positive RVT claim, version, provider, descriptor, replay or parser is planned.
- Type consistency: checker signatures and CLI arguments are defined once and reused unchanged.
- Portability: all live gates use Python stdlib/jsonschema, pytest, Hatchling and existing scripts; no network/provider runtime is required.
- Consumer boundary: executable-source and generated-output scans are explicit; governance prose is intentionally excluded to avoid false positives.
- Closure discipline: ACX-20 is promoted only in the evidence/status commit and is not executed by this plan.
