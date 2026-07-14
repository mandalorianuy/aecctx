# AECCTX Remote Provider v0.3 Profile

Version: `0.3.0-draft.1`
Date: 2026-07-13
Status: Normative ACX-26 implementation profile
Decision authority: ACXD-034

## 1. Purpose and claim boundary

This profile defines an optional, caller-selected protocol for sending one content-addressed AECCTX provider request to one explicitly registered customer-managed HTTPS origin. Core validation, package I/O, opaque ingest, query, diff and context remain offline and never discover or select a remote provider.

The claim ID is `sandbox.remote-provider`. Its ceiling is public `partial` for the exact `remote-https-spki-v1` transport and deterministic repository-owned loopback corpus. It is a protocol/interoperability claim, not a claim that any third-party service exists, is available, is safe, is correctly licensed or produces correct AEC semantics.

## 2. Closed endpoint identity

A registration binds exactly one normalized HTTPS origin and one lowercase SHA-256 digest of the peer certificate's DER SubjectPublicKeyInfo (SPKI). The only request target is `/aecctx/provider/v1/extract`. Origins containing user information, query, fragment, non-root path, ambiguous/default ports or non-ASCII host names are invalid. Production origins require HTTPS; the conformance server also uses TLS on loopback.

The client opens a direct connection with Python `http.client.HTTPSConnection`, uses no proxy or environment-derived endpoint, performs the TLS handshake, computes the peer SPKI digest and compares it in constant time before sending credentials or source bytes. Redirects are never followed. Any `3xx` response fails `AECCTX_REMOTE_REDIRECT_DENIED`.

The explicit SPKI pin is the transport identity authority. The client does not consult the ambient CA trust store, certificate-discovery service, revocation service or wall clock. Certificate lifecycle and pin rotation are operator-owned and require an updated registration plus policy review. This is deliberately narrower than general Web PKI validation.

Official API references:

- Python HTTPS client: <https://docs.python.org/3/library/http.client.html#http.client.HTTPSConnection>
- Python TLS peer certificate access: <https://docs.python.org/3/library/ssl.html#ssl.SSLSocket.getpeercert>
- `cryptography` public-key serialization: <https://cryptography.io/en/latest/hazmat/primitives/asymmetric/serialization/>
- HTTP status semantics: <https://www.rfc-editor.org/rfc/rfc9110.html>

## 3. Policy and consent

`RemoteProviderPolicy` is parsed against `remote-provider-policy.schema.json` with no ignored fields. Before DNS lookup or socket creation the caller MUST explicitly provide:

- `upload_consent=true` and `billing_consent=true`;
- an endpoint origin and SPKI digest exactly matching the registration;
- a non-empty allowlist of regions and one expected response region;
- maximum retention seconds and explicit telemetry consent;
- request/response byte ceilings, timeout, attempt ceiling and fixed retry delay.

Telemetry is denied unless `telemetry_consent=true`. The server attests its region, retention and telemetry behavior; a region outside the policy, retention above the policy, or undeclared telemetry fails closed. Consent is invocation-local and cannot be inferred from configuration, credentials or a prior call.

## 4. Credential contract

The caller supplies credential bytes directly. They must be non-empty printable ASCII without CR, LF, NUL or other control bytes. They are used only as the value of the `Authorization` request header after SPKI verification. Credentials MUST NOT appear in the request body, request digest, response, artifacts, attestation, diagnostics, exception messages/details, fixtures, logs or replay corpus.

No credential is read from environment variables, files, keychains, URL user information, netrc, proxy settings or SDK defaults. HTTP `401` and `403` produce the stable code `AECCTX_REMOTE_AUTH_FAILED` and are never retried.

## 5. Request and response envelope

The canonical request envelope contains:

- `protocol_version="0.3-remote"`;
- the existing validated v0.2 provider request;
- source bytes encoded as canonical base64 with the exact byte count and SHA-256 already present in that request;
- the SHA-256 digest of the non-secret canonical policy projection.

The envelope digest is transmitted as `X-AECCTX-Request-SHA256`. The response is strict JSON with no duplicate keys, non-finite numbers or trailing data and contains:

- `protocol_version="0.3-remote"` and the request-envelope digest;
- provider ID/version and policy-bound region, retention and telemetry attestations;
- the existing v0.2 provider response;
- a base64 artifact map whose paths, byte counts and hashes exactly match that response.

The response body digest MUST match `X-AECCTX-Response-SHA256`. The core materializes artifacts only inside a fresh temporary output directory, then applies the existing `validate_provider_response()` contract. Host paths, traversal, symlinks, duplicate paths, excess files/records/bytes, forged hashes and incomplete capability/loss reports remain rejected.

## 6. Bounds, retry and rate behavior

Policy limits are deterministic: positive timeout, one through three attempts, bounded request/response bytes and non-negative fixed retry delay. The client reads at most `max_response_bytes + 1` and rejects before parsing if exceeded. It never streams provider output into a package before complete validation.

Only connection/timeout failures before a valid response and HTTP `429`, `502`, `503` or `504` are retryable. Authentication, redirect, identity, consent, policy, malformed/digest-invalid response and semantic validation failures are terminal. Every attempt reuses byte-identical request content and request digest. `Retry-After` and server clocks are ignored; retries use only the caller policy's fixed delay and a monotonic sleeper. Exhaustion produces `AECCTX_REMOTE_RETRY_EXHAUSTED` with attempt count and stable last-error code, never secrets.

## 7. Deterministic replay

Replay consumes the canonical request envelope and response envelope plus their hashes without opening a socket. It applies the same policy, envelope, artifact and v0.2 response validation. Replay proves protocol mapping only. A live positive claim requires the repository-owned loopback TLS server and adversarial transport tests on the exact implementation.

## 8. Security, privacy and licensing gates

The client dependency is optional `cryptography>=45,<50`, used only to parse the peer certificate and serialize SPKI. It remains outside the core dependency set and is licensed Apache-2.0 OR BSD-3-Clause. The reference worker is Apache-2.0 project code and is not a production service or bundled credential.

Conformance MUST prove: pre-network consent rejection; exact origin/SPKI binding; redirect and auth denial; timeout/retry ceilings; oversized, malformed and digest-invalid response denial; artifact confinement; credential redaction; declared region/retention/telemetry enforcement; replay drift rejection; no restricted provider binary in wheel/sdist; and no network call from core commands.

## 9. Residuals and non-claims

This profile does not claim general Web PKI validation, certificate expiry/revocation, multi-endpoint discovery, OAuth refresh, mTLS, streaming/resume, provider billing accuracy, service availability/SLA, provider-side sandboxing, provider-side deletion, jurisdictional compliance, semantic correctness, entitlement, signing/trust, consumer approval or use of any commercial/GPL decoder. Those require separately governed profiles and evidence.
