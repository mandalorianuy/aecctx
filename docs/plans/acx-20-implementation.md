# ACX-20 Detached Package Signing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` and `superpowers:test-driven-development` task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not dispatch subagents unless the user explicitly authorizes delegation.

**Goal:** Implement optional, deterministic, offline Ed25519 signing and verification for valid AECCTX v0.1/v0.2 packages without conflating integrity, key possession, identity, key lifecycle, trust or policy authorization.

**Architecture:** A focused public facade in `src/aecctx/signing.py` orchestrates package validation, statement construction, signing and verification. Strict JSON/file handling lives in `src/aecctx/_signing_io.py`; the optional PyCA boundary lives in `src/aecctx/_signing_crypto.py`. Detached JWS sidecars never enter or mutate the AECCTX package, and verifier-owned registries/policies remain explicit offline inputs.

**Tech Stack:** Python 3.12+, JSON Schema 2020-12, RFC 7515 JWS General JSON Serialization, RFC 8032/RFC 9864 Ed25519, optional `cryptography>=45,<50`, existing AECCTX package/validation/diagnostic APIs, pytest, hatchling.

## Global Constraints

- Execute only ACX-20. ACX-21 remains `pending` until ACX-20 closes and is only promoted, never executed, by this plan.
- Normative authorities are `docs/specs/signing-v1-profile.md`, `docs/security/signing-threat-model.md`, ACXD-018 and the ACX-20 section of `docs/implementation-plan.md`.
- Unsigned AECCTX v0.1/v0.2 packages remain valid and their existing validation/query/diff/context behavior remains unchanged.
- Signing and verification require a structurally and integrally valid package before any signature result is admitted.
- Signature bundles are explicit detached sidecars and never become package artifacts, required extensions, logical-digest inputs or Markdown authority.
- Profile v1 permits only `alg = "Ed25519"`; `EdDSA`, ECDSA, RSA, Ed448, `none` and unknown algorithms are rejected without fallback.
- Every protected header contains exactly `alg`, `kid`, `typ` and `https://aecctx.dev/jws/statement-sha256`; unprotected/unknown/remote-key headers are rejected.
- Cryptographic, identity, key lifecycle, trust and authorization states remain independent fields.
- The host clock, network, LLM, environment-selected keys, implicit discovery, key generation and implicit trust-root selection are prohibited.
- `cryptography>=45,<50` is an optional `signing` extra. Core install and every non-signing command remain usable without it.
- All inputs are untrusted and bounded: 1 MiB bundle/registry/policy, 64 signatures, 1,024 keys, 64 KiB private key, 4 KiB password, no symlinks and no duplicate JSON names.
- Test keys are project-generated, deterministic and labeled test-only. They never represent a production identity or trust root.
- Every behavior change starts with a failing test, ends with a narrow green gate and receives a coherent commit.
- No task adds WoodFraming, `WFDomain`, `WFImport`, consumer mapping, quality-gate behavior, source write-back or package mutation.

## File and responsibility map

| File | Responsibility |
|---|---|
| `src/aecctx/signing.py` | Public dataclasses, stable states/diagnostics, schema-backed parsing facade, statement/sign/verify orchestration |
| `src/aecctx/_signing_io.py` | Strict duplicate-rejecting JSON, NFC canonicalization, base64url and bounded regular-file helpers |
| `src/aecctx/_signing_crypto.py` | Lazy optional PyCA import, PKCS#8 Ed25519 loading, sign/verify only |
| `schemas/v0.2/signature-*.schema.json` | Public sidecar, registry, policy and verification-result contracts |
| `src/aecctx/schemas/v0_2/signature-*.schema.json` | Byte-identical packaged schema mirrors |
| `tests/test_signing_contract.py` | Schemas, strict parsing, canonical statement, limits and package invariants |
| `tests/test_signing_crypto.py` | Private-key loading, deterministic signing, append and crypto failure boundaries |
| `tests/test_signing_policy.py` | Key lifecycle, trust, scopes, thresholds and per-signature result separation |
| `tests/test_signing_cli.py` | CLI arguments, JSON envelope, exit codes, secret handling and SDK parity |
| `tests/test_signing_conformance.py` | Corpus, mutation matrix, packaging, core-only install and deterministic replay |
| `fixtures/v0.2/signing/` | Publishable fixed keys, registries, policies, bundles and generation provenance |
| `conformance/v0.2/signing-corpus.json` | Case-to-input-to-expected-result mapping |
| `scripts/check_signing_conformance.py` | Portable corpus/schema/hash/expected-state checker |

---

### Task 1: Closed signing schemas and public result types

**Checkpoint:** Completed 2026-07-12. RED produced 14 expected missing-module/schema failures; GREEN passes 24 focused contract/package-data tests. Completion commit: `06b0104`.

**Files:**
- Create: `schemas/v0.2/signature-bundle.schema.json`
- Create: `schemas/v0.2/signing-key-registry.schema.json`
- Create: `schemas/v0.2/signing-trust-policy.schema.json`
- Create: `schemas/v0.2/signature-verification-result.schema.json`
- Create identical mirrors under `src/aecctx/schemas/v0_2/`
- Create: `src/aecctx/signing.py`
- Create: `tests/test_signing_contract.py`
- Modify: `tests/test_package_data.py`

**Interfaces:**
- Produces `SigningLimits(max_document_bytes=1_048_576, max_signatures=64, max_keys=1024, max_private_key_bytes=65_536, max_password_bytes=4096)`.
- Produces immutable `SigningStatement(data: Mapping[str, Any], canonical_bytes: bytes, sha256: str)`.
- Produces immutable `SignatureEntry(protected: str, signature: str, kid: str, algorithm: str, statement_sha256: str)` and `SignatureBundle(signatures: tuple[SignatureEntry, ...])`.
- Produces immutable `SigningKey`, `KeyRegistry`, `TrustPolicy`, `SignatureVerification`, and `PackageSignatureResult` with exact state fields from the normative profile.
- Produces `SigningError(AECCTXError)` carrying a stable `code` and safe message.
- Produces `validate_signing_document(value, schema_name) -> None` using packaged schemas offline.

- [x] **Step 1: Write failing public-type and schema-mirror tests.**

```python
from importlib.resources import files
from aecctx.signing import SigningLimits, SignatureVerification

def test_signing_limits_are_normative() -> None:
    assert SigningLimits().max_document_bytes == 1_048_576
    assert SigningLimits().max_signatures == 64
    assert SigningLimits().max_keys == 1_024

def test_signature_result_keeps_axes_separate() -> None:
    result = SignatureVerification(
        kid="test-a", algorithm="Ed25519", subject="urn:test:a",
        cryptographic_status="valid", identity_status="resolved",
        key_status="expired", trust_status="untrusted",
        authorization_status="unauthorized", diagnostic_codes=(),
    )
    assert result.key_status == "expired"
    assert result.trust_status == "untrusted"

def test_public_and_packaged_signing_schemas_match() -> None:
    public = open("schemas/v0.2/signature-bundle.schema.json", "rb").read()
    packaged = files("aecctx.schemas.v0_2").joinpath("signature-bundle.schema.json").read_bytes()
    assert public == packaged
```

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_signing_contract.py tests/test_package_data.py -q`; expect import/file failures for the new contract.

- [x] **Step 3: Add four closed JSON Schemas and byte-identical mirrors.** Require `additionalProperties: false`, unique bounded arrays, UTC `date-time` strings, lowercase 64-hex digests, exact Ed25519 JWK fields, the six `key_status` values and independent trust/authorization enums. Bundle schema requires no `payload`, exactly 1..64 signatures and only `protected`/`signature` members.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "additionalProperties": false,
  "required": ["signatures"],
  "properties": {
    "signatures": {
      "type": "array",
      "minItems": 1,
      "maxItems": 64,
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["protected", "signature"],
        "properties": {
          "protected": {"type": "string", "minLength": 1, "maxLength": 2048},
          "signature": {"type": "string", "pattern": "^[A-Za-z0-9_-]{86}$"}
        }
      }
    }
  }
}
```

- [x] **Step 4: Add exact public dataclasses and state validation.** Reject constructor input outside the governed enums rather than accepting arbitrary strings.

```python
CRYPTOGRAPHIC_STATUSES = frozenset({"valid", "invalid", "malformed", "unknown_key", "unsupported_algorithm"})
KEY_STATUSES = frozenset({"valid", "not_yet_valid", "expired", "revoked", "unknown_status", "not_evaluated"})
TRUST_STATUSES = frozenset({"trusted", "untrusted", "not_evaluated"})
AUTHORIZATION_STATUSES = frozenset({"authorized", "unauthorized", "not_evaluated"})

class SigningError(AECCTXError):
    code = "AECCTX_SIGNING_ERROR"
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
```

- [x] **Step 5: Add offline schema loading.** Load only names from a fixed allowlist via `importlib.resources.files("aecctx.schemas.v0_2")`; use `Draft202012Validator` plus `FormatChecker`; sort errors by absolute path and raise `AECCTX_SIGNING_SCHEMA_INVALID` with no input dump.

- [x] **Step 6: Verify GREEN and package data.** Run `.venv/bin/python -m pytest tests/test_signing_contract.py tests/test_package_data.py -q`; expect all passing. Run `python3 -m json.tool` over all eight public/mirrored files.

- [x] **Step 7: Commit.**

```bash
git add schemas/v0.2/signature-*.schema.json schemas/v0.2/signing-*.schema.json \
  src/aecctx/schemas/v0_2/signature-*.schema.json src/aecctx/schemas/v0_2/signing-*.schema.json \
  src/aecctx/signing.py tests/test_signing_contract.py tests/test_package_data.py
git commit -m "feat: define ACX-20 signing contracts"
```

### Task 2: Strict JSON, canonical statement and package binding

**Checkpoint:** Completed 2026-07-12. Primitive RED produced 14 missing-module failures, statement RED produced 7 missing-interface failures, and the immutability review produced 2 focused failures. GREEN passes 52 signing-contract/validation/v0.2 compatibility tests. Completion commit: `8c2aa5a`.

**Files:**
- Create: `src/aecctx/_signing_io.py`
- Modify: `src/aecctx/signing.py`
- Modify: `tests/test_signing_contract.py`

**Interfaces:**
- Produces `load_strict_json(data: bytes, *, label: str, max_bytes: int) -> Any`.
- Produces `canonical_json_nfc(value: Any, *, terminal_lf: bool) -> bytes`.
- Produces `base64url_encode(data: bytes) -> str` and `base64url_decode(value: str, *, expected_bytes: int | None = None) -> bytes`.
- Produces `read_bounded_regular_file(path, *, max_bytes: int, label: str) -> bytes`.
- Produces `build_signing_statement(package_path, *, limits=SigningLimits()) -> SigningStatement`.

- [x] **Step 1: Write failing duplicate/NFC/base64/file-boundary tests.** Include exact duplicate keys, two distinct keys that collide after NFC normalization, invalid UTF-8, NaN/Infinity, padded/noncanonical base64url, symlink, oversize and directory inputs.

```python
def test_strict_json_rejects_duplicate_names() -> None:
    with pytest.raises(SigningError) as caught:
        load_strict_json(b'{"kid":"a","kid":"b"}', label="registry", max_bytes=1024)
    assert caught.value.code == "AECCTX_SIGNING_JSON_DUPLICATE_KEY"

def test_base64url_rejects_padding() -> None:
    with pytest.raises(SigningError) as caught:
        base64url_decode("YQ==")
    assert caught.value.code == "AECCTX_SIGNING_BASE64URL_INVALID"
```

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_signing_contract.py -k 'strict or canonical or base64 or bounded' -q`; expect missing helper failures.

- [x] **Step 3: Implement strict primitives.** Use `json.loads(..., object_pairs_hook=...)`, recursively NFC-normalize keys/string values, reject normalized-key collisions, reject booleans where integers are expected through schema validation, and compare base64url decode/re-encode for canonical equality.

```python
def base64url_decode(value: str, *, expected_bytes: int | None = None) -> bytes:
    if not value or "=" in value or not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise SigningError("AECCTX_SIGNING_BASE64URL_INVALID", "base64url value is not canonical")
    decoded = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if base64url_encode(decoded) != value or (expected_bytes is not None and len(decoded) != expected_bytes):
        raise SigningError("AECCTX_SIGNING_BASE64URL_INVALID", "base64url value has invalid length or encoding")
    return decoded
```

- [x] **Step 4: Write failing statement tests.** Cover v0.1/v0.2, directory/ZIP, semantic-manifest digest, required extensions, exact terminal LF, deterministic repeat, package-form-only change preserving statement, every other manifest-field mutation changing statement, duplicate manifest key rejection and invalid-package refusal.

```python
def test_package_form_is_the_only_ignored_manifest_field(tmp_path: Path) -> None:
    directory, archive = equivalent_packages(tmp_path)
    assert build_signing_statement(directory).canonical_bytes == build_signing_statement(archive).canonical_bytes

def test_producer_mutation_changes_statement(tmp_path: Path) -> None:
    package = copy_fixture(tmp_path)
    before = build_signing_statement(package).sha256
    mutate_manifest(package, lambda m: m["producer"].update({"version": "different"}))
    assert build_signing_statement(package).sha256 != before
```

- [x] **Step 5: Implement canonical statement construction.** Call `validate_package` first; then reread raw `manifest.json` through `PackageReader.read_bytes`, strict-parse it, remove only `package_form`, compute its canonical SHA-256 and construct the exact seven-field statement. Refuse any ordinary validation diagnostic with `AECCTX_SIGNING_PACKAGE_INVALID`.

```python
statement_data = {
    "aecctx_version": manifest["aecctx_version"],
    "logical_digest": manifest["logical_digest"],
    "package_id": manifest["package_id"],
    "profile": "https://aecctx.dev/signing/v1",
    "required_extensions": manifest.get("required_extensions", []),
    "semantic_manifest_sha256": hashlib.sha256(semantic_bytes).hexdigest(),
    "statement_version": "1",
}
```

- [x] **Step 6: Verify GREEN.** Run `.venv/bin/python -m pytest tests/test_signing_contract.py tests/test_validation.py tests/test_v02_compatibility.py -q`; expect existing validation behavior unchanged and all new statement cases passing.

- [x] **Step 7: Commit.** Commit as `feat: build canonical ACX-20 signing statements` with only `_signing_io.py`, `signing.py` and contract tests.

### Task 3: Optional Ed25519 signing and deterministic bundle append

**Checkpoint:** Completed 2026-07-12. Dependency RED produced 1 expected missing-extra failure while the lazy-import assertion already passed; behavior RED produced 12 expected missing-interface failures. GREEN passes 14 signing-crypto tests and 51 combined signing-crypto/contract tests with `cryptography==49.0.0`. Full `./scripts/verify.sh` passes 334 tests with 9 optional skips, builds wheel and sdist, and passes portable, release and baseline-integration gates. Completion commit is the Task 3 milestone commit on `codex/acx-20-signing`.

**Files:**
- Create: `src/aecctx/_signing_crypto.py`
- Modify: `src/aecctx/signing.py`
- Modify: `pyproject.toml`
- Create: `tests/test_signing_crypto.py`

**Interfaces:**
- Produces `load_private_key(private_key_pem: bytes, password: bytes | None) -> Ed25519PrivateKey` behind a lazy import.
- Produces `load_public_key(raw_public_key: bytes) -> Ed25519PublicKey`.
- Produces `sign_bytes(private_key, message: bytes) -> bytes` and `verify_bytes(public_key, signature: bytes, message: bytes) -> bool`.
- Produces `sign_package(package_path, *, private_key_pem: bytes, kid: str, password: bytes | None = None, limits=SigningLimits()) -> SignatureBundle`.
- Produces `append_signature(package_path, bundle: SignatureBundle, *, private_key_pem: bytes, kid: str, password: bytes | None = None, limits=SigningLimits()) -> SignatureBundle`.
- `SignatureBundle.to_bytes() -> bytes` emits deterministic canonical JWS General JSON with detached payload absent.

- [x] **Step 1: Add the optional dependency boundary and write RED import tests.** Add `signing = ["cryptography>=45,<50"]`; include the same bounded dependency in `all` and `test`, but not base `dependencies`. Assert `src/aecctx/signing.py` imports without eagerly importing `cryptography`.

```python
def test_signing_module_does_not_eagerly_import_crypto() -> None:
    code = "import sys, aecctx.signing; print('cryptography' in sys.modules)"
    completed = subprocess.run([sys.executable, "-c", code], text=True, capture_output=True, check=True)
    assert completed.stdout.strip() == "False"
```

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_signing_crypto.py -q`; expect missing crypto/signing functions.

- [x] **Step 3: Implement the lazy PyCA boundary.** Catch only `ImportError` as `AECCTX_SIGNING_CRYPTO_UNAVAILABLE`; require an `Ed25519PrivateKey`; map malformed PEM or wrong password to `AECCTX_SIGNING_PRIVATE_KEY_INVALID` without echoing library text that may expose paths/content.

```python
def _serialization_modules():
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    except ImportError as error:
        raise SigningError("AECCTX_SIGNING_CRYPTO_UNAVAILABLE", "install aecctx[signing]") from error
    return InvalidSignature, serialization, Ed25519PrivateKey, Ed25519PublicKey
```

- [x] **Step 4: Write failing signing/bundle tests.** Use a fixed 32-byte test seed in test memory. Assert exact four protected headers, statement hash, 64-byte signature, payload absence, deterministic repeated bytes, package bytes unchanged, encrypted PKCS#8 password success/failure, invalid key type, duplicate `kid`, deterministic append ordering and preservation of previous signature objects.

- [x] **Step 5: Implement sign and append.** Validate `kid` length/UTF-8/NFC, construct the protected header with `alg`, `kid`, `typ` and statement SHA-256, sign the RFC 7515 input, sort entries by `(kid, protected, signature)` and reject duplicate decoded `kid` before output.

```python
protected = {
    "alg": "Ed25519",
    "https://aecctx.dev/jws/statement-sha256": statement.sha256,
    "kid": kid,
    "typ": "aecctx-signing-statement+jws",
}
signing_input = f"{base64url_encode(canonical_json_nfc(protected, terminal_lf=False))}.".encode("ascii") + base64url_encode(statement.canonical_bytes).encode("ascii")
```

- [x] **Step 6: Verify GREEN.** Run `.venv/bin/python -m pytest tests/test_signing_crypto.py tests/test_signing_contract.py -q`; compare two generated bundle byte strings exactly and revalidate the original package after every sign/append case.

- [x] **Step 7: Commit.** Commit as `feat: sign packages with detached Ed25519 JWS`.

### Task 4: Strict bundle, registry and trust-policy parsing

**Checkpoint:** Completed 2026-07-12. Parser RED produced 25 expected missing-interface failures; lifecycle/policy RED produced 12 expected missing-interface failures. GREEN passes 74 policy/contract tests and 88 combined crypto/policy/contract tests. Full `./scripts/verify.sh` passes 371 tests with 9 optional skips, builds wheel and sdist, and passes portable, release and baseline-integration gates. Completion commit is the Task 4 milestone commit on `codex/acx-20-signing`.

**Files:**
- Modify: `src/aecctx/signing.py`
- Modify: `tests/test_signing_contract.py`
- Create: `tests/test_signing_policy.py`

**Interfaces:**
- Produces `parse_signature_bundle(data: bytes, *, limits=SigningLimits()) -> SignatureBundle`.
- Produces `parse_key_registry(data: bytes, *, limits=SigningLimits()) -> KeyRegistry`.
- Produces `parse_trust_policy(data: bytes, *, limits=SigningLimits()) -> TrustPolicy`.
- Produces `evaluate_key(key: SigningKey | None, policy: TrustPolicy | None) -> KeyPolicyEvaluation` with independent `key_status`, `trust_status`, `authorization_status` and codes.

- [x] **Step 1: Write failing parser-adversarial tests.** Cover attached `payload`, empty/excessive signatures, unprotected header, missing/unknown protected header, `EdDSA`, invalid `typ`, wrong statement digest grammar, duplicate decoded `kid`, padded base64url, wrong public/signature length, duplicate registry keys, 1,025 keys, invalid intervals, inconsistent `revoked_at`, unknown fields, invalid time zone and threshold 0/65.

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_signing_contract.py -k 'bundle or registry or policy' -q`; expect missing parser failures.

- [x] **Step 3: Implement strict schema-first parsers.** Size-check bytes before decoding, call `load_strict_json`, validate the closed schema, decode protected headers strictly, reject all but the four exact protected names and sort/compare entries against canonical order rather than silently normalizing hostile input.

```python
allowed_headers = {"alg", "kid", "typ", "https://aecctx.dev/jws/statement-sha256"}
if set(protected) != allowed_headers:
    raise SigningError("AECCTX_SIGNING_HEADER_INVALID", "protected header set does not match profile v1")
```

- [x] **Step 4: Write failing key-lifecycle/trust tests.** At exact boundary instants assert `not_yet_valid` before `valid_from`, `valid` at `valid_from`, `expired` at `valid_until`, `valid` before `revoked_at`, `revoked` at `revoked_at`, and `unknown_status` independently of trust. Assert an expired key can simultaneously be `untrusted`; an unknown `kid` and a verification without policy produce `not_evaluated`, never `unknown_status`.

```python
def test_key_lifecycle_and_trust_are_independent() -> None:
    evaluation = evaluate_key(expired_untrusted_key(), policy_at("2030-01-01T00:00:00Z"))
    assert evaluation.key_status == "expired"
    assert evaluation.trust_status == "untrusted"
    assert evaluation.authorization_status == "unauthorized"
```

- [x] **Step 5: Implement deterministic policy evaluation.** Accept `key=None` and/or `policy=None` and return `key_status`, `trust_status` and `authorization_status` all `not_evaluated`; otherwise parse RFC3339 UTC instants without consulting `datetime.now`, compute lifecycle independently, trust only registry-controlled `kid`/subject allowlists, and authorize only a trusted lifecycle-valid key whose scopes contain every required scope.

- [x] **Step 6: Verify GREEN.** Run `.venv/bin/python -m pytest tests/test_signing_policy.py tests/test_signing_contract.py -q`; monkeypatch the host clock and socket APIs and require unchanged results/no calls.

- [x] **Step 7: Commit.** Commit as `feat: evaluate offline signing trust policies`.

### Task 5: Multi-signature verification and separated result records

**Checkpoint:** Completed 2026-07-12. Verifier RED produced 14 expected missing-interface failures and the raw Ed25519 boundary RED produced 1 expected missing-interface failure. GREEN passes 15 focused verification/threshold/foreign/unsigned tests and 105 complete signing contract/crypto/policy tests. Full `./scripts/verify.sh` passes 388 tests with 9 optional skips, builds wheel and sdist, and passes portable, release and baseline-integration gates. Completion commit is the Task 5 milestone commit on `codex/acx-20-signing`.

**Files:**
- Modify: `src/aecctx/signing.py`
- Modify: `src/aecctx/_signing_crypto.py`
- Modify: `tests/test_signing_crypto.py`
- Modify: `tests/test_signing_policy.py`

**Interfaces:**
- Produces `verify_package_signatures(package_path, *, bundle: SignatureBundle | None, registry: KeyRegistry, policy: TrustPolicy | None = None, limits=SigningLimits()) -> PackageSignatureResult`.
- `PackageSignatureResult.to_dict()` validates against `signature-verification-result.schema.json` and emits ordered `package_validation`, `statement`, `signatures`, and `policy_evaluation` sections.
- Missing bundle returns `signature_presence="unsigned"`, an empty signatures tuple and `policy_satisfied=False` when policy exists or `None` without policy.

- [x] **Step 1: Write failing cryptographic/result-state tests.** Cover authorized valid, matching statement hash plus invalid signature, foreign statement hash, unknown key, unsupported algorithm, valid-untrusted, trusted-unauthorized, not-yet-valid, expired, revoked, unknown status, no policy, unsigned, 1-of-N, 2-of-2, duplicated signer rejection and rotation under one subject.

```python
def test_foreign_bundle_is_distinct_from_corrupt_signature() -> None:
    foreign = verify(package_b, bundle_for_package_a)
    corrupt = verify(package_a, corrupt_signature(bundle_for_package_a))
    assert foreign.signatures[0].diagnostic_codes == ("AECCTX_SIGNING_STATEMENT_BINDING_MISMATCH",)
    assert corrupt.signatures[0].diagnostic_codes == ("AECCTX_SIGNING_SIGNATURE_INVALID",)
```

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_signing_crypto.py tests/test_signing_policy.py -k 'verify or threshold or foreign or unsigned' -q`; expect missing verifier failures.

- [x] **Step 3: Implement per-signature verification in fixed order.** Check header/profile and protected statement digest; resolve candidate key and identity; evaluate key lifecycle, trust and scopes through `evaluate_key(key, policy)`; then evaluate the allowlisted algorithm and Ed25519 signature; finally aggregate unique authorized `kid`. Unknown keys and verification without policy retain `key_status = "not_evaluated"`. An unsigned verification returns without importing `cryptography`. Never skip package integrity validation and never convert an operational parse error into `invalid`.

```python
authorized = {
    item.kid for item in results
    if item.cryptographic_status == "valid"
    and item.key_status == "valid"
    and item.trust_status == "trusted"
    and item.authorization_status == "authorized"
}
policy_satisfied = len(authorized) >= policy.minimum_authorized_signatures
```

- [x] **Step 4: Add stable diagnostics.** Define and test exact codes for package invalid, malformed bundle, statement mismatch, unsupported algorithm, unknown key, invalid signature, not-yet-valid/expired/revoked/unknown status, untrusted, unauthorized, threshold failure and crypto absence. Diagnostic messages must not contain package host paths, key bytes or input JSON.

- [x] **Step 5: Validate every result document.** `to_dict()` must pass the packaged result schema, preserve signature order and include statement/package/policy SHA-256 values. `policy_evaluation` contains the requested threshold, authorized unique IDs and `policy_satisfied`; it never emits approval language.

- [x] **Step 6: Run the complete mutation matrix.** Run `.venv/bin/python -m pytest tests/test_signing_contract.py tests/test_signing_crypto.py tests/test_signing_policy.py -q`; expect all states machine-distinct and deterministic across two executions.

- [x] **Step 7: Commit.** Commit as `feat: verify ACX-20 signatures and trust states`.

### Task 6: CLI sign/verify commands and exit contract

**Checkpoint:** Completed 2026-07-12. Parser/happy-path RED produced 5 expected unknown-command failures; exit/copy RED left 1 expected missing-status-summary failure after 38 cases already passed. GREEN passes 39 signing/existing CLI tests, including atomic no-clobber, secret redaction, explicit password files and exit `0/1/2`. Manual `validate` and `info` remain unchanged and successful for the minimal v0.1 and v0.2 fixtures. Full `./scripts/verify.sh` passes 404 tests with 9 optional skips, builds wheel and sdist, and passes portable, release and baseline-integration gates. Completion commit is the Task 6 milestone commit on `codex/acx-20-signing`.

**Files:**
- Modify: `src/aecctx/cli.py`
- Create: `tests/test_signing_cli.py`
- Modify: `tests/test_cli.py`

**Interfaces:**
- Adds `aecctx sign PACKAGE --private-key KEY --kid KID --output BUNDLE [--password-file FILE] [--append-to EXISTING] [--json]`.
- Adds `aecctx verify-signatures PACKAGE [--signature-bundle BUNDLE] --key-registry REGISTRY [--trust-policy POLICY] [--json]`.
- Both commands call the public SDK only; CLI contains argument/file/output handling but no duplicate signing semantics.

- [x] **Step 1: Write failing parser and happy-path CLI tests.** Assert exact help/options, missing required arguments, sign output, append, JSON structure and SDK byte parity.

```python
def test_verify_cli_exit_zero_only_for_satisfied_policy(tmp_path: Path) -> None:
    completed = run_cli("verify-signatures", PACKAGE, "--signature-bundle", BUNDLE,
                        "--key-registry", REGISTRY, "--trust-policy", POLICY, "--json")
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["data"]["policy_evaluation"]["policy_satisfied"] is True
```

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_signing_cli.py -q`; expect argparse unknown-command failures.

- [x] **Step 3: Add CLI parsers and bounded reads.** Reject output that already exists; `--append-to` requires a distinct new `--output`; read every control/key/password file through `read_bounded_regular_file`; strip exactly one terminal LF from password bytes; never accept a password argument or environment fallback.

- [x] **Step 4: Implement atomic sidecar writes.** Serialize first, create a mode-0600 temporary file in the destination directory, `fsync`, then replace only the previously nonexistent output path. On error, remove temporary data and leave package/input sidecar unchanged.

- [x] **Step 5: Write failing exit/diagnostic/secret tests.** Verify sign `0/2`; verify `0` satisfied, `1` unsigned/no-policy/unsatisfied, `2` invalid package/malformed controls/missing crypto. Capture stdout/stderr and assert private key/password bytes and absolute input paths are absent.

- [x] **Step 6: Implement JSON and text emission.** JSON uses the existing `{data, diagnostics, ok}` envelope. `ok` is true when evaluation executes even if exit is `1`; `policy_satisfied` remains separate. Text output states `unsigned`, counts each status axis and never says trusted/authorized unless the corresponding fields do.

- [x] **Step 7: Verify GREEN and regress existing CLI.** Run `.venv/bin/python -m pytest tests/test_signing_cli.py tests/test_cli.py -q`; run manual `aecctx validate` and `aecctx info` against both minimal fixtures to prove unchanged output.

- [x] **Step 8: Commit.** Commit as `feat: expose explicit signing CLI`.

### Task 7: Publishable signing corpus, portable gates and packaging proof

**Checkpoint:** Completed 2026-07-12. Corpus-contract RED produced 7 expected missing-corpus/checker/fixture failures; the clean-install packaging boundary separately exposed a missing sdist checker and was corrected by including `scripts/` in the sdist. The first remote portable run then exposed that the deterministic ZIP was locally present but excluded from the commit by the repository-wide `*.aecctx` ignore rule; a tracked-corpus regression failed before the fixture was force-added intentionally. GREEN passes all 8 conformance tests and deterministically replays 24/24 signing corpus cases offline. Clean base and `[signing]` installs prove the optional dependency boundary, wheel/sdist contents include all four signing schemas and test-only material remains confined to fixtures. Full `./scripts/verify.sh` passes 412 tests with 9 optional skips, builds wheel and sdist, and passes portable, release and baseline-integration gates. The exact claim remains `target`; promotion is reserved for Task 8.

**Files:**
- Create: `fixtures/v0.2/signing/README.md`
- Create: `fixtures/v0.2/signing/generate_fixtures.py`
- Create generated test-only keys, registry, policies and bundles under `fixtures/v0.2/signing/`
- Create: `conformance/v0.2/signing-corpus.json`
- Create: `scripts/check_signing_conformance.py`
- Create: `tests/test_signing_conformance.py`
- Modify: `conformance/v0.2/claims.json`
- Modify: `scripts/check_spec_contract.py`
- Modify: `scripts/verify_portable.sh`
- Modify: `pyproject.toml`

**Interfaces:**
- Corpus entries identify `case_id`, package fixture, bundle/registry/policy paths, expected exit/result axes and every file SHA-256.
- `validate_signing_corpus(path) -> tuple[str, ...]` returns ordered errors without signing or network side effects.
- Fixture generator derives Ed25519 private seeds from fixed project labels with SHA-256 and writes unencrypted test-only PKCS#8; encrypted-key behavior remains an ephemeral unit test because PKCS#8 encryption bytes are randomized.

- [x] **Step 1: Write failing corpus-contract tests.** Require unique cases, only repository-relative safe paths, known expected states, complete file hashes, at least one case for every governed status/mutation and rejection of missing/duplicate/unmapped cases.

- [x] **Step 2: Verify RED.** Run `.venv/bin/python -m pytest tests/test_signing_conformance.py -q`; expect missing corpus/checker failures.

- [x] **Step 3: Implement deterministic fixture generation.** Use fixed labels `aecctx-acx20-test-a/b/c` to derive 32-byte seeds. Emit canonical registry/policies/bundles through public APIs, label all private material `TEST ONLY`, and fail generation if a committed file differs.

```python
seed = hashlib.sha256(f"aecctx-acx20-{label}".encode("ascii")).digest()
private_key = Ed25519PrivateKey.from_private_bytes(seed)
private_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
```

- [x] **Step 4: Populate the complete corpus.** Include unsigned v0.1/v0.2, directory/ZIP equivalence, valid authorized, invalid, foreign statement, unknown key, unsupported algorithm, untrusted, unauthorized, not-yet-valid, expired, revoked, unknown status, rotation, 1-of-N, N-of-N, artifact/manifest/header/signature mutation, duplicate JSON, oversize and missing-extra cases.

- [x] **Step 5: Implement the portable checker and claim mapping.** Validate schemas/hashes, execute each offline verification case, compare only governed expected fields and assert no socket call. Register the exact ACX-20 claim as `target` during implementation; promotion occurs only in Task 8.

- [x] **Step 6: Add clean-install packaging tests.** Build wheel/sdist; inspect metadata to prove no base `Requires-Dist: cryptography`; create one clean venv with base wheel and one with `[signing]`. Base venv must validate packages and return `AECCTX_SIGNING_CRYPTO_UNAVAILABLE` for sign; signing venv must execute the positive corpus. Assert all four packaged schemas are present and no private production material exists.

- [x] **Step 7: Wire portable verification.** Add JSON syntax, mirrored-schema checks, corpus checker and `tests/test_signing_*` to existing test discovery without weakening RVT/provider/release checks.

- [x] **Step 8: Verify GREEN.** Run:

```bash
.venv/bin/python -m pytest tests/test_signing_contract.py tests/test_signing_crypto.py \
  tests/test_signing_policy.py tests/test_signing_cli.py tests/test_signing_conformance.py -q
.venv/bin/python scripts/check_signing_conformance.py
python3 scripts/check_spec_contract.py
./scripts/verify_portable.sh
```

Expected: all signing cases pass, 282 pre-ACX-20 tests remain non-regressed, wheel/sdist build and portable verification reports `ok`.

- [x] **Step 9: Commit.** Commit as `test: publish ACX-20 signing conformance corpus`.

### Task 8: Evidence, capability promotion, full gates and publication

**Files:**
- Create: `docs/evidence/ACX-20.md`
- Modify: `README.md`
- Modify: `docs/capability-matrix.md`
- Modify: `docs/compatibility-v0.2.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/implementation-plan.md`
- Modify: `docs/plans/acx-20-implementation.md`
- Modify: `conformance/v0.2/claims.json`

**Interfaces:**
- Evidence binds the normative profile, exact dependency versions/licenses, every fixture hash, test IDs/counts, deterministic comparisons, security/privacy/platform review, branch/main CI and WoodFraming scan.
- Ledger moves ACX-20 from `in_progress` to `completed` and only ACX-21 from `pending` to `pending-next` after every gate passes.
- Public claim becomes only: optional offline detached JWS General JSON verification with `Ed25519`, caller-owned registry/policy and the exact documented states. X.509, online revocation, countersignatures, timestamps and universal authorization remain `unsupported`.

- [x] **Step 1: Write evidence before promotion.** Complete all twelve evidence-template sections with actual commands/results/hashes and explicit non-claims. Keep task status `in_progress` and claim `target` until gates pass.

- [x] **Step 2: Run narrow and adversarial gates.** Run every signing test, corpus checker, schema mirror check, deterministic regeneration/diff, secret/path scan, restricted-header scan, no-network test and clean-install matrix. Record exact counts and artifact hashes.

- [x] **Step 3: Run repository gates.** Run:

```bash
python3 scripts/check_spec_contract.py
python3 scripts/check_meta_agent_baseline_integration.py --fail-on-issues
./scripts/verify_portable.sh
./scripts/verify.sh
git diff --check
```

Expected: every command exits 0; no generated timestamp/unrelated diff remains.

- [ ] **Step 4: Create and publish the implementation candidate.** Commit all remaining implementation/evidence work without promoting ACX-21, push `codex/acx-20-signing`, wait for Ubuntu/macOS/Windows CI on the exact SHA and record the run URL/status in evidence.

- [ ] **Step 5: Promote only after candidate CI is green.** Change the claim from `target` to the exact bounded public support state, set ACX-20 `completed`, promote only ACX-21 to `pending-next`, update handoff/evidence/this plan, rerun `check_spec_contract.py` and `verify.sh`, and commit as `docs: close ACX-20 signing milestone`.

- [ ] **Step 6: Publish and validate the closure commit.** Push the branch, require green Ubuntu/macOS/Windows CI for the closure SHA, then merge `codex/acx-20-signing` into `main` with `--no-ff`, rerun `./scripts/verify.sh`, push `main` and require green main CI. Do not execute ACX-21.

- [ ] **Step 7: Record final publication evidence without changing claims.** If the evidence file lacks final branch/main run IDs, add one documentation-only commit, push it and require its CI green. Do not rewrite published history or tag a release; release authority remains ACX-23.

## Plan self-review

- Spec sections 1-3 map to Tasks 1-2; package validity always precedes signing.
- Canonical semantic manifest, directory/ZIP equivalence and protected statement digest map to Tasks 2-3 and the Task 5 foreign-bundle test.
- JWS General JSON, exact protected headers, Ed25519-only agility and multiple independent signatures map to Tasks 3-5.
- Key registry, explicit policy time, lifecycle/trust separation, revocation, rotation, scopes and thresholds map to Tasks 4-5.
- SDK/CLI, atomic sidecars, password safety and exit codes map to Tasks 3, 5 and 6.
- Limits, duplicate JSON/base64 adversarial cases, no network/clock/discovery and secret non-disclosure map to Tasks 2, 4, 6 and 7.
- Public fixtures, deterministic regeneration, clean core/signing-extra installs, packaged schemas and claim mapping map to Task 7.
- Evidence, residual unsupported capabilities, WoodFraming proof, branch/main CI and next-task promotion map to Task 8.
- Every production behavior has a named failing test before implementation and a narrow command after implementation.
- Function/type names are consistent across tasks: parsing produces typed documents; signing consumes bytes and returns `SignatureBundle`; verification consumes typed inputs and returns `PackageSignatureResult`.
- No task mutates package evidence, relies on Markdown, invents unknown states, requires network/LLM or borrows ACX-21 scope.
- Documentation, dependency installation, fixtures without mapped tests and a happy-path signature do not count as ACX-20 progress or a public claim.
