# ACX-35 advanced trust threat model

Date: 2026-07-14

## Assets and boundaries

Protected assets are the immutable ACX-20 statement binding, explicit certificate identity, caller trust policy, lifecycle/status evidence, trusted-time assertion and exact countersignature relationship. AECCTX evaluates caller-supplied public evidence only; production private keys and trust administration remain outside the product.

All packages, JWS bundles, policies, certificates, CRLs, tokens and countersignatures are untrusted. No URL, AIA/CDP value, host store, host clock, environment value, command, embedded path or active content is followed.

## Threats and controls

| Threat | Control | Residual |
|---|---|---|
| algorithm substitution or key-type confusion | exact Ed25519/SHA-256 allowlist; closed schemas; no fallback | other algorithms unsupported |
| attacker-selected trust anchor or time | explicit policy root fingerprints and UTC instants | policy administration remains caller-owned |
| chain/path ambiguity | maximum three certificates, exact issuer/signature/CA checks and selected root termination | general Web PKI and name constraints are not claimed |
| revoked certificate accepted from missing/stale evidence | fresh signed complete base CRL required; absence/staleness remains `unknown_status` | OCSP and delta/indirect CRLs unsupported |
| timestamp replay or substitution | exact target digest, TSA leaf fingerprint, signature, path, status and policy time checks | token is not RFC 3161 or legal qualified time |
| countersignature cycle or threshold inflation | target must be an exact v1 signature object; countersignatures cannot target countersignatures and never count toward threshold | organizational meaning remains policy-external |
| parser/resource abuse | 1 MiB documents/certificates/CRLs, 64-entry ceilings, strict JSON and canonical base64url | cryptography parser defects remain dependency risk |
| secret leakage | verifier accepts public evidence only; core never generates, chooses, stores or rotates production keys | operator key custody is out of scope |

## Security gates

Acceptance requires mutation, stale/revoked/unknown/expired/rotation, algorithm-confusion, exact-target, no-network, missing-extra, deterministic replay, closed-schema, wheel/sdist and cross-platform CI evidence. Any unsupported profile fails closed without a positive trust claim.
