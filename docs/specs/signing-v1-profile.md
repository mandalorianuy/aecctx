# AECCTX Detached Signing Profile v1

Version: `1.0.0-draft.2`
Date: 2026-07-12
Status: Normative ACX-20 design approved 2026-07-12; implementation and public authenticity claims remain pending conformance

## 1. Purpose

This profile defines optional, offline package signing and verification for valid AECCTX v0.1 and v0.2 packages. It binds a deterministic package statement to one or more detached JSON Web Signatures without changing the package, its artifact inventory or its logical digest.

The key words MUST, MUST NOT, REQUIRED, SHOULD, SHOULD NOT and MAY are normative.

Integrity, cryptographic validity, signer identity, verifier trust and policy authorization are separate results. No one result implies another. An unsigned package remains conforming to its original AECCTX version.

## 2. Profile identifiers and scope

The signing statement profile identifier is `https://aecctx.dev/signing/v1`. The JWS protected `typ` value is `aecctx-signing-statement+jws`.

This profile supports:

- AECCTX `0.1.0` and `0.2.0` directory and ZIP packages;
- detached JWS General JSON Serialization;
- one or more independent signatures;
- the fully specified JOSE algorithm identifier `Ed25519`;
- caller-owned offline key registries and trust policies;
- deterministic verification at a caller-declared time.

This profile does not support X.509 chains, online key discovery, OCSP, remote CRLs, transparency services, countersignatures, timestamp authorities, hardware-key protocols, universal authorization or secret management. These states MUST remain unclaimed rather than approximated.

## 3. Trust boundary and prerequisites

Signing and verification operate only on a package that first passes ordinary AECCTX structural and integrity validation. A package with an invalid manifest, artifact hash, byte size, logical digest, schema or required extension MUST NOT receive a successful signature result.

The caller supplies every signing key, key identifier, signature bundle, candidate-key registry, trust policy and verification time explicitly. AECCTX MUST NOT generate, discover, select, download, rotate, trust or persist key material implicitly. Signing never mutates the package.

`docs/security/signing-threat-model.md` defines the actors, assets, threats and controls for this profile.

## 4. Semantic manifest and canonical statement

The verifier constructs a semantic manifest by parsing `manifest.json`, removing only the top-level `package_form` field and canonicalizing the remaining object with the AECCTX JSON convention: UTF-8, Unicode NFC strings, sorted object keys, no insignificant whitespace, finite numbers and one terminal LF.

`created_at`, `producer`, artifact metadata, capability claims, loss, source IDs, embedding policy, extensions and every other manifest field remain bound. Removing `package_form` is the sole normalization and makes directory/ZIP repackaging container-neutral. A change to any other manifest field changes the signed statement.

The canonical signing statement is exactly:

```json
{
  "aecctx_version": "0.2.0",
  "logical_digest": "<lowercase sha256>",
  "package_id": "<manifest package_id>",
  "profile": "https://aecctx.dev/signing/v1",
  "required_extensions": [],
  "semantic_manifest_sha256": "<lowercase sha256>",
  "statement_version": "1"
}
```

The actual bytes use the same compact AECCTX canonical JSON convention and terminal LF. `required_extensions` is the manifest list in its validated order for v0.2 and an empty list for v0.1. `semantic_manifest_sha256` is SHA-256 of the semantic-manifest bytes. The statement never incorporates the signature bundle, filesystem name, ZIP metadata, compression, host path or current clock.

The logical digest binds exact artifact paths, hashes and byte sizes. The semantic-manifest digest additionally binds the authoritative manifest claims. Both are REQUIRED because the logical digest alone does not cover all manifest semantics.

## 5. Detached JWS envelope

The signature bundle is a separate file supplied explicitly to the signing or verification API. It is not an AECCTX artifact, required extension or source of package identity. Moving, renaming or losing the sidecar does not make the underlying unsigned package invalid.

The bundle conforms to JWS General JSON Serialization and contains exactly one `signatures` array. The detached `payload` member MUST be absent. Each signature object contains exactly:

```json
{
  "protected": "<base64url protected header>",
  "signature": "<base64url Ed25519 signature>"
}
```

The protected header contains exactly:

```json
{
  "https://aecctx.dev/jws/statement-sha256": "<lowercase sha256>",
  "alg": "Ed25519",
  "kid": "<explicit key id>",
  "typ": "aecctx-signing-statement+jws"
}
```

`https://aecctx.dev/jws/statement-sha256` is SHA-256 of the exact canonical statement bytes. It is a collision-resistant private JOSE header name and lets a verifier distinguish a sidecar bound to another package statement from a corrupted signature. A mismatched statement hash produces `AECCTX_SIGNING_STATEMENT_BINDING_MISMATCH` before signature verification; a matching hash with failed Ed25519 verification produces `AECCTX_SIGNING_SIGNATURE_INVALID`.

Protected-header JSON uses UTF-8, sorted keys and no insignificant whitespace, without a terminal LF before base64url encoding. Base64url encoding MUST be unpadded and canonical. The JWS signing input follows RFC 7515: ASCII base64url of the protected header, a period and base64url of the canonical statement bytes.

Unprotected headers and `jku`, `x5u`, `x5c`, `jwk`, `crit` or any unknown protected header are prohibited. The bundle itself is canonical AECCTX JSON with a terminal LF. Signatures are sorted lexicographically by decoded `kid`, then protected value, then signature value. Duplicate `kid` values are invalid.

Adding an independent signature does not rewrite prior signature objects. Appending requires an explicit operation and output path. A signature bundle from another package is syntactically valid but every signature fails against the reconstructed statement for the current package.

## 6. Algorithm profile and agility

Profile v1 permits only `alg = "Ed25519"`, the fully specified JOSE identifier standardized by RFC 9864 for Ed25519 as defined by RFC 8032. The older polymorphic `EdDSA` identifier and every ECDSA, RSA, Ed448, post-quantum or unknown identifier are unsupported in this profile.

Algorithm agility is profile-versioned, not negotiated from input. Adding an algorithm requires a reviewed specification revision, library/security review, fixtures and conformance mapping. An implementation MUST NOT fall back to another algorithm.

The Python reference implementation uses the optional `cryptography>=45,<50` extra for Ed25519 and PKCS#8 key loading. The core package without this extra remains fully usable for ingest, validation, query, diff and context. Absence of the extra produces a stable operational diagnostic and never a false verification result.

## 7. Key registry

The verifier-owned key registry is a closed, versioned JSON document supplied explicitly. It contains at most 1,024 unique key records. Each record contains:

- unique `kid`;
- public JWK with exactly `kty = "OKP"`, `crv = "Ed25519"` and a canonical 32-byte base64url `x` value;
- non-empty `subject` controlled by the trust administrator;
- inclusive `valid_from` and exclusive `valid_until` UTC instants;
- `revocation_status`: `good`, `revoked` or `unknown`;
- `revoked_at` when status is `revoked`;
- a sorted unique list of declared authorization `scopes`.

The registry is a set of candidate verification keys, not a trust decision. A key may resolve identity and verify a signature while remaining untrusted. Duplicate keys, duplicate JSON names, inconsistent revocation data, invalid intervals, unknown fields or unsupported key types make the registry invalid.

## 8. Trust policy

The verifier-owned trust policy is a closed, versioned JSON document supplied explicitly. It contains:

- `verification_time`, an explicit UTC instant;
- `allowed_algorithms`, which MUST be a subset of this profile allowlist;
- trusted `kid` and/or trusted `subject` allowlists;
- sorted unique `required_scopes`;
- `minimum_authorized_signatures`, from 1 through 64.

A candidate key is trusted only if its `kid` or its registry-controlled subject is selected by policy and the key is valid, non-revoked and in a known-good revocation state at `verification_time`. It is authorized only if it is trusted and its declared scopes include every policy-required scope.

Trusting a subject is safe only within the caller-supplied registry: a JWS header cannot introduce a subject or public key. Rotation uses multiple registry keys for the same subject with distinct `kid`, validity and revocation state. Historical verification is deterministic because it uses policy time rather than the host clock.

No policy is universal. Passing a policy does not imply engineering approval, regulatory acceptance, construction readiness, source authorship beyond key possession or consumer authorization outside the policy's declared scopes.

## 9. Result model

The machine-readable result keeps these package fields separate:

- `package_integrity`: `valid` or `invalid`;
- `signature_presence`: `unsigned` or `signed`;
- `verification_completed`: boolean;
- `policy_satisfied`: boolean or `null` when no policy was evaluated;
- statement bytes SHA-256, package ID and logical digest;
- ordered per-signature results and stable diagnostics.

Each signature result contains:

- `cryptographic_status`: `valid`, `invalid`, `malformed`, `unknown_key` or `unsupported_algorithm`;
- `identity_status`: `resolved` or `unresolved`;
- `key_status`: `valid`, `not_yet_valid`, `expired`, `revoked`, `unknown_status` or `not_evaluated`;
- `trust_status`: `trusted`, `untrusted` or `not_evaluated`;
- `authorization_status`: `authorized`, `unauthorized` or `not_evaluated`;
- `kid`, algorithm, resolved subject when available and cited diagnostic codes.

Key lifecycle and administrator trust are independent: a key can be both `expired` and `untrusted`. A registry key with `revocation_status = "revoked"` is `valid` before `revoked_at` and `revoked` at or after that instant. `not_yet_valid` applies before `valid_from`; `expired` applies at or after `valid_until`; `unknown_status` applies when a resolved key's revocation status is unknown. `not_evaluated` applies only when no registry key is resolved or no trust policy supplies `verification_time`; it MUST NOT be substituted for an evaluated unknown revocation state. An unsigned result contains no fabricated signature entry. Unknown, expired, revoked and unsupported states remain explicit. Aggregate policy satisfaction counts unique signatures whose cryptographic, key, trust and authorization statuses are respectively `valid`, `valid`, `trusted` and `authorized`.

## 10. SDK and CLI contract

The Python SDK exposes focused operations equivalent to:

- `build_signing_statement(package)`;
- `sign_package(package, private_key, kid)`;
- `append_signature(package, bundle, private_key, kid)`;
- `verify_package_signatures(package, bundle, registry, policy)`.

The CLI exposes:

```text
aecctx sign PACKAGE --private-key KEY --kid KID --output BUNDLE [--password-file FILE]
aecctx sign PACKAGE --private-key KEY --kid KID --output BUNDLE --append-to EXISTING [--password-file FILE]
aecctx verify-signatures PACKAGE [--signature-bundle BUNDLE] --key-registry REGISTRY [--trust-policy POLICY] [--json]
```

Private keys are caller-owned PKCS#8 PEM files. Encrypted keys accept only an explicit password file; secrets in command arguments, implicit environment variables and interactive prompts are prohibited. SDK callers may supply key/password bytes directly. Results and diagnostics MUST NOT expose private key or password content.

Signing returns exit `0` on success and `2` on malformed input, invalid package, unavailable cryptography or operational failure. Verification returns `0` when an evaluated policy is satisfied, `1` when evaluation completes but the package is unsigned or policy is not satisfied, and `2` for invalid package, malformed control input, unavailable dependency or operational failure. JSON `ok` describes successful evaluation execution; it MUST NOT replace `policy_satisfied`.

## 11. Stable diagnostic families

The implementation MUST provide stable diagnostics for at least:

- invalid package or package integrity;
- malformed or oversized signature bundle, registry, policy, key or password file;
- statement binding mismatch;
- unsupported algorithm or serialization;
- duplicate or unknown `kid`;
- invalid signature;
- unresolved identity;
- untrusted, expired, revoked or unknown-status key;
- unauthorized signer and unmet threshold;
- unavailable cryptographic dependency;
- invalid private key or password.

Diagnostics explain the failed layer and MUST NOT collapse a valid signature into trusted or authorized status.

## 12. Input limits and safety

All signing inputs are untrusted data. The reference implementation enforces:

- 1 MiB maximum each for bundle, registry and policy;
- 64 signatures per bundle;
- 1,024 registry keys;
- 64 KiB private-key file and 4 KiB password file;
- bounded identifiers, subjects and scope strings;
- regular input files only, with symlinks rejected;
- duplicate JSON-name rejection and closed schemas;
- canonical base64url and exact 32-byte public/64-byte signature lengths.

Parsing MUST NOT resolve URLs, imports, callbacks, expressions or active content. No signing or verification operation requires network or an LLM.

## 13. Conformance corpus

ACX-20 MUST publish project-generated, legally reusable test-only keys and fixtures covering:

- unsigned v0.1 and v0.2 packages;
- directory, ZIP and repackaged equivalents;
- deterministic statement, signature and bundle bytes;
- valid, invalid, malformed, unknown-key and unsupported-algorithm signatures;
- valid-untrusted, trusted-unauthorized and authorized signers;
- expiry, revocation, unknown status and rotation;
- multiple signatures with 1-of-N and N-of-N thresholds;
- artifact, manifest, digest, header, statement and signature mutation;
- container-form-only change that preserves validity;
- a bundle signed for another package;
- duplicate JSON names, noncanonical base64url, oversized input and excessive signatures/keys;
- no implicit key generation, discovery, network, clock or trust-root selection;
- operation without the optional dependency;
- CLI/SDK parity and stable exit behavior.

Fixtures MUST be labeled test-only and MUST NOT be presented as producer identity or production trust roots.

## 14. Claim boundary

Acceptance of this design does not implement authenticity. The public capability remains `unsupported` until schemas, SDK, CLI, fixtures, conformance mapping, dependency review, evidence and all repository gates pass and ACX-20 closes.

When ACX-20 completes, the bounded claim is optional offline Ed25519 verification under this exact profile. It is not X.509 PKI, online revocation, key custody, source authorship proof, long-term archival signature, countersigning, timestamping or universal authorization.

## 15. Normative references

- RFC 7515, JSON Web Signature (JWS): <https://www.rfc-editor.org/rfc/rfc7515>
- RFC 8032, Edwards-Curve Digital Signature Algorithm: <https://www.rfc-editor.org/rfc/rfc8032>
- RFC 9864, Fully-Specified Algorithms for JOSE and COSE: <https://www.rfc-editor.org/rfc/rfc9864>
- PyCA cryptography, Ed25519 API: <https://cryptography.io/en/stable/hazmat/primitives/asymmetric/ed25519/>
- PyCA cryptography, license: <https://cryptography.io/en/stable/license/>
