# AECCTX signing threat model

Date: 2026-07-12
Decision: ACXD-018
Claimed profile: none until ACX-20 conformance completes

## Assets and actors

The package author creates AECCTX evidence. A signer possesses a caller-selected private key. A distributor or storage service transports packages and detached bundles. A verifier validates package integrity and signatures. A trust administrator owns the offline key registry and policy. An attacker may control package bytes, container metadata, sidecars, filenames, JSON documents, key identifiers, public keys presented outside the trusted registry and source content.

Private signing keys, trust-policy decisions, registry contents, package evidence, signature results and deterministic diagnostics are protected assets. The host, Python runtime and installed `cryptography` implementation are trusted execution dependencies. Packages, sidecars, registries, policies, PEM files and password files are untrusted parser inputs even when selected by the caller.

The boundary is:

`untrusted package -> ordinary structural/integrity validation -> canonical statement -> detached JWS verification -> candidate-key resolution -> verifier-owned trust/time/revocation policy -> separate result fields`

Signing uses:

`validated package -> canonical statement + explicit caller key/kid -> detached JWS sidecar`

Neither path mutates package evidence or promotes Markdown to authority.

## Threats and controls

| Threat | Control | Required conformance evidence |
|---|---|---|
| Artifact or manifest substitution | ordinary package validation precedes signing/verification; statement binds logical digest and semantic-manifest digest | artifact, digest and every bound manifest-field mutation |
| ZIP/directory ambiguity | semantic manifest removes only `package_form`; container paths/metadata never enter statement | directory/ZIP/repackaged equivalence and traversal tests |
| Signature-wrapper substitution or confusion | exact detached JWS General JSON shape, exact protected `typ`, no payload member, no unprotected/unknown headers | malformed envelope, wrong `typ`, attached payload and unknown-header rejection |
| Algorithm confusion or downgrade | profile v1 allowlists only fully specified `Ed25519`; no fallback or negotiation | `EdDSA`, ECDSA, RSA, `none` and unknown-algorithm rejection |
| Attacker-supplied key or remote key discovery | JWS carries `kid` only; public key must exist in explicit registry; `jwk`, `jku`, `x5u`, `x5c` and network are forbidden | embedded/remote-key rejection and socket-denial proof |
| Key-ID or JSON parser ambiguity | duplicate JSON names and duplicate `kid` rejected; canonical UTF-8/base64url and bounded strings | duplicate-name, Unicode, invalid/base64 padding and duplicate-key tests |
| Cryptographic validity confused with identity/trust | per-signature cryptographic, identity, trust and authorization statuses remain independent | valid unknown/untrusted/trusted/unauthorized/authorized fixtures |
| Expired, rotated, revoked or compromised key accepted | explicit policy time, key validity interval, revocation state/time, distinct key IDs and threshold evaluation | before/after expiry/revocation, rotation and multi-signature corpus |
| Host-clock nondeterminism | policy supplies `verification_time`; host clock is never consulted for trust | repeated verification at fixed time and clock monkeypatch test |
| Sidecar loss or package mutation during signing | unsigned package remains valid; signing output is separate and package is read-only | package byte/hash equality before/after sign and unsigned validation |
| Private-key or password disclosure | explicit bounded regular files; no secrets in arguments, results, logs or diagnostics; no persistence | malformed-key/password and output-capture tests |
| Resource exhaustion | 1 MiB documents, 64 signatures, 1,024 keys, bounded key/password/string lengths and closed schemas | oversize/count/deep/malformed adversarial tests |
| Policy code execution or prompt injection | policy is closed JSON data with no expressions, callbacks, URLs, commands, links or LLM interpretation | command/prompt-like string and unknown-field rejection |
| Dependency absence or unsupported backend | signing is an optional extra; absence is an operational diagnostic and core remains usable | core-only install/import and missing-extra CLI tests |
| Threshold bypass with duplicated signer | unique `kid` per bundle and unique authorized signature counting | duplicate signature/key and N-of-N failure tests |

## Trust decisions deliberately outside the profile

- The profile proves possession of an Ed25519 private key for the exact statement bytes. It does not prove real-world authorship beyond the verifier's registry mapping.
- The verifier owns registry provenance, policy distribution and compromise response. AECCTX does not provide a trust service.
- Revocation is offline policy data. Freshness beyond the explicit policy document and time is unknown.
- Host compromise, malicious `cryptography` binaries, private-key theft and trust-administrator compromise are outside the package-format boundary.
- There is no certificate-chain, transparency-log, timestamp-authority, hardware-token or long-term archival validation claim.
- Policy authorization is limited to declared scopes and is never engineering, regulatory, construction or consumer approval.

## Dependency and license posture

The reference implementation uses PyCA `cryptography` only through the optional `signing` extra, bounded to `>=45,<50` for the ACX-20 implementation line. The library exposes Ed25519 signing/verification and PKCS#8 serialization APIs and is distributed under Apache-2.0 OR BSD-3-Clause terms. No general-purpose dynamic JOSE policy engine is required; AECCTX implements only the fixed RFC 7515 framing and validates every allowed field.

The implementation evidence MUST record the exact tested version and supported Linux/macOS/Windows wheel matrix. An upper-bound or backend change requires dependency review and the repository gates before release.

## Residual risk

- Offline revocation can be stale; `unknown` remains explicit and policy administrators must distribute updated registries/policies.
- Ed25519 may be unavailable in some compliance-constrained environments; this profile reports it unsupported and does not downgrade.
- Detached sidecars can be lost or mismatched during transport; explicit sidecar selection and statement reconstruction make mismatch visible but cannot guarantee co-transport.
- A malicious trust administrator can authorize a malicious key. That is policy authority, not a cryptographic failure AECCTX can infer away.
- The initial profile has no trusted timestamp, so it evaluates key status only at the caller-selected verification time and makes no historical signing-time claim.
