# AECCTX Advanced Offline Trust Profile v2

Version: `2.0.0-draft.1`
Date: 2026-07-14
Status: Normative; ACX-35 implemented public `partial` for the exact selected profile

## 1. Purpose and claim ceiling

This optional profile evaluates X.509 identity, certificate lifecycle, offline revocation evidence, trusted-time evidence and multi-party signature relationships over the immutable ACX-20 `SigningStatement`. It never replaces package validation or the detached Ed25519 JWS profile.

The sole selected profile is `aecctx-x509-ed25519-crl-time-v1`. Public support may become `partial` only for the exact project-authored corpus. Integrity, cryptographic validity, identity, lifecycle, trust, authorization and archival-time results MUST remain separate.

## 2. Dependency and algorithms

The implementation uses optional `cryptography>=45,<50`, which is already the `signing` extra. Certificates, CRLs and every selected signature use Ed25519. SHA-256 is the only digest. RSA, ECDSA, Ed448, SHA-1, algorithm negotiation and fallback are unsupported.

Core and ACX-20 signing remain usable without the optional dependency. A missing dependency produces `AECCTX_TRUST_DEPENDENCY_UNAVAILABLE`.

## 3. Explicit inputs and deterministic time

Every evaluation receives explicit bytes for the v1 signature bundle, leaf/intermediate/root certificates, zero or more CRLs, timestamp tokens, countersignatures, policy and `verification_time`. Inputs are bounded regular files or in-memory bytes. The host trust store, host clock, environment, network, URL discovery, AIA, CRL distribution points and OCSP discovery are forbidden.

The closed policy selects trusted root SHA-256 fingerprints, authorized certificate subjects, required scopes, a signature threshold, a CRL freshness requirement, an archival-time threshold and whether a valid trusted-time result is mandatory. No certificate name or root is trusted merely because it parses or chains.

## 4. X.509 identity and path

Each v1 `kid` maps explicitly to one leaf certificate. The leaf Ed25519 public key MUST verify that exact v1 JWS signature. A path MUST terminate at one explicitly supplied and policy-selected root, contain at most one intermediate, and pass the closed issuer, Ed25519 signature, validity, Basic Constraints and Key Usage checks implemented with `cryptography` X.509 primitives at the explicit evaluation time. The leaf MUST contain `clientAuth` extended key usage. Unlisted algorithms, missing required extensions and invalid CA constraints fail closed.

Identity is the leaf RFC 4514 subject plus its SHA-256 fingerprint. Identity resolution does not imply root trust, lifecycle validity or organizational authorization.

## 5. Offline status profile

Only complete base CRLs supplied explicitly are selected. A CRL MUST be signed by the certificate issuer, have matching issuer identity, be active at the evaluation time and have a non-null `nextUpdate`. A stale, premature, malformed, wrongly signed, delta or indirect CRL yields a distinct status and cannot authorize a signer. A matching serial is `revoked`; a valid fresh covering CRL with no matching serial is `good`; absence or unusable evidence is `unknown`.

Offline OCSP parsing, delegated responders, online status retrieval and ACX-26 transport are not selected by this profile and remain `unsupported`.

## 6. AECCTX trusted-time token

The selected token is closed canonical JSON, not RFC 3161/CMS. It contains profile `aecctx-trusted-time-v1`, target kind (`statement` or `signature`), target SHA-256, a UTC `gen_time`, TSA leaf fingerprint and a base64url Ed25519 signature. The signed payload is the canonical object without `signature`.

The TSA certificate follows the same explicit X.509 path and CRL evaluation, MUST contain `timeStamping` extended key usage and MUST be policy-authorized as a TSA. Token signature validity, TSA path trust, TSA status at `gen_time`, target binding and whether `gen_time` precedes the policy archival threshold are separate results. This token proves only the selected TSA assertion under the caller policy; it is not RFC 3161, legal qualified time, transparency evidence or a universal archival signature.

## 7. Independent and counter signatures

Existing v1 signatures remain independent. A countersignature is a closed canonical JSON object with profile `aecctx-countersignature-v1`, a unique `kid`, `target_signature_sha256` over the exact canonical target signature object, and an Ed25519 signature over the canonical object without `signature`. It MUST target a signature in the same v1 bundle, MUST NOT target another countersignature and MUST use a distinct `kid`. Cycles, missing targets, duplicate relationships and algorithm confusion fail closed.

A valid countersignature attests only to the exact target signature bytes. It does not increase the independent-signature threshold and never implies approval or authorization.

## 8. Result contract

The result publishes ordered per-signer axes:

- `integrity_status`: `valid` or `invalid`;
- `cryptographic_status`: `valid`, `invalid`, `malformed` or `unsupported_algorithm`;
- `identity_status`: `resolved` or `unresolved`;
- `lifecycle_status`: `valid`, `not_yet_valid`, `expired`, `revoked`, `unknown_status` or `not_evaluated`;
- `trust_status`: `trusted`, `untrusted` or `not_evaluated`;
- `authorization_status`: `authorized`, `unauthorized` or `not_evaluated`;
- `archival_time_status`: `valid`, `invalid`, `untrusted`, `outside_policy`, `absent` or `not_evaluated`.

The aggregate records independent authorized-signature count and policy satisfaction. It MUST NOT expose an aggregate `authentic`, `genuine`, `approved` or `safe` boolean.

## 9. Limits and hostile inputs

Policy/result/token/countersignature documents are limited to 1 MiB each; certificate and CRL files to 1 MiB each; 64 signers, 64 tokens and 64 countersignatures; paths to three certificates; UTF-8 JSON with duplicate-name rejection; canonical unpadded base64url; no symlinks. Embedded URLs, source paths, commands and unknown fields are rejected and never followed.

## 10. Conformance and non-claims

The project-generated test PKI MUST cover valid, expired, revoked, unknown-status and rotated signers; valid/stale/mutated CRLs; trusted/untrusted/mutated timestamps; independent signatures and countersignatures; chain, threshold and algorithm-confusion failures; no-network execution; missing-extra behavior; and unchanged ACX-20 fixtures.

The following remain unsupported: RFC 3161/CMS, OCSP, delta/indirect CRLs, online retrieval, host stores/clocks, production key generation/custody/rotation, hardware keys, transparency logs, legal/qualified signatures, universal identity, organizational authority outside explicit policy and long-term archival validity beyond the supplied evidence.

## 11. References

- RFC 5280, X.509 and CRL profile.
- RFC 8032, Ed25519.
- RFC 3161, explicitly not selected; used only to bound the non-claim.
- PyCA cryptography X.509 verification and CRL APIs.
