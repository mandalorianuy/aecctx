# ACX-20 Acceptance Evidence

## 1. Task status, commits and date

- Status while this candidate is evaluated: `in_progress`; the public claim remains `target` until the candidate CI and closure gates pass.
- Date: 2026-07-12.
- Design/plan commits: `692a608`, `06b0104`.
- Implementation commits: `8c2aa5a`, `b830e12`, `52424bc`, `7599cde`, `f73e045`, `d1041df`, `b42271f`.
- Candidate, closure and main publication commits/runs are recorded in section 12 after their exact SHAs pass CI.

## 2. Normative coverage

- Expansion specification section 12 and release-claim gate sections 16–17.
- `docs/specs/signing-v1-profile.md`, sections 1–16.
- `docs/security/signing-threat-model.md`.
- ACXD-018 and the ACX-20 section of `docs/implementation-plan.md`.
- Detailed execution authority: `docs/plans/acx-20-implementation.md`.

The implementation follows the accepted detached JWS General JSON profile with canonical semantic-manifest binding and caller-owned offline registry/policy inputs. Package integrity, cryptographic validity, key identity, key lifecycle, trust and authorization remain separate results.

## 3. Implemented deliverables and explicit non-scope

Implemented:

- public strict schemas and immutable result types for detached bundles, key registries, trust policies and verification results;
- deterministic v0.1/v0.2 signing statements that ignore only `package_form` and preserve directory/ZIP equivalence;
- optional lazy `cryptography>=45,<50` Ed25519 PKCS#8 boundary with deterministic sign/append and no package mutation;
- schema-first bounded parsers, explicit key lifecycle/trust/scope/threshold evaluation and stable diagnostics;
- SDK plus explicit `aecctx sign` and `aecctx verify-signatures` CLI commands with atomic sidecars and exit `0/1/2`;
- 24-case, offline, deterministic conformance corpus and clean base/`[signing]` installation proof.

Not implemented or claimed:

- no mandatory signing, implicit key generation/discovery, environment-selected key, implicit trust root or host-clock policy;
- no X.509/PKIX, certificate chain, transparency log, online revocation, OCSP/CRL fetch, remote JWKS, timestamp authority, countersignature or notarization;
- no universal authorization, engineering approval, regulatory certification or construction-readiness decision;
- no package mutation, source write-back, quality gate, consumer ontology or WoodFraming integration.

## 4. Claim table

| Capability | Source/profile/version | Support at closure | Conformance tests |
|---|---|---|---|
| `package.authenticity-signing` | `detached-jws-ed25519-offline-v1`; valid AECCTX v0.1/v0.2; optional `cryptography>=45,<50` | bounded `partial`: detached Ed25519 possession plus explicit caller-owned offline trust/policy evaluation | `tests/test_signing_conformance.py::test_signing_corpus_executes_offline_and_matches_governed_results`; `tests/test_signing_conformance.py::test_clean_install_base_and_signing_extra_boundaries` |

`partial` is deliberate: a valid signature demonstrates possession of the selected private key over the governed statement. Identity, lifecycle, trust and authorization depend on explicit registry/policy evidence and never become universal approval.

## 5. Fixtures, origin, license and hashes

All material below is project-authored Apache-2.0 test material. The three deterministic PKCS#8 keys are visibly `TEST ONLY`; they are neither production identities nor trust roots. SHA-256:

```text
8def30e1afd1b5947a0216ea6e8c4623894363568c6ddd0c4d119c9b2ccf48dd  README.md
c2bc74910539510182936ecd8d557c834c46447b60ab0ccfcb09f6c29c821478  adversarial/duplicate-json.json
4f057ecc2e38eb35463f3a367ea753522a2fc2286ae9e4cd40b093b6e0def2bf  adversarial/oversize.json
12e709930ca214f2dd1d2717eca6eb7414dd16e1665fc5d7a53b201be0dd99cf  bundles/invalid-header.json
1478e591a0c4d73dd713d02f07f23cf7a208a22bf0c53e5df260a313ee656ec8  bundles/invalid-signature.json
30e8451702000161078342461a3998eece148483d8a28c92a82b5ad6150a7ceb  bundles/multi-ab.json
3b5a96cb4d62bf4171acd7243f3b49ddadef599f546aa518d119fc2daecf2160  bundles/unsupported-algorithm.json
8d0b9572f45f99283de055f7e1dd0ca3be05fe4b57ae194b22ff77088a4a05f2  bundles/valid-a.json
1e6a7c615eaf7264280728c4226e0f4b311a7b49669a64af8df795e1f2b36deb  bundles/valid-b.json
cb9e34adeea81e0435a45183315b0e4adcc9b37839d0771de69f2bc5cb68db79  bundles/valid-c.json
af6ec2fb549f2e808756a618db34577a54754121c89f9c2de306cf6fc3d8c017  bundles/valid-v02.json
a62201474242866ecb7c02c64aa9d73bfb86c5b79d1ee647608e7cd5965cff78  generate_fixtures.py
dd2714743db87d678ebcb588be24ce34070e12a797594b7a6f68d738af1fb789  keys/test-a.pem
670473f52d6fb09601243b643a666099ea2c116cf4e40ca15d1e05397624ca28  keys/test-b.pem
756f43afd21b4cea025f2648307482f5dd6ae9bec7d03cdba1dcdc2ed1be34da  keys/test-c.pem
9ea16cb1c27681f2d185ecb47eafd3449f80191d9171081377d1a479c8b58b0a  packages/artifact-mutated/context/index.md
36f6598b588493a0d33df97546dea904a5e81eef603c97588c53ec8b91c6965b  packages/artifact-mutated/diagnostics/diagnostics.jsonl
0c9ccba7f7492f3f23cf7e4fcded5f6b53d9a6eba63534a59d2b1a54fb79640e  packages/artifact-mutated/evidence/assertions.jsonl
9e7de0190515cd8a2a13b0f42d435365e7622d186f587ca5435094a5ff5c555f  packages/artifact-mutated/evidence/primitives.jsonl
b3c8bbf18d7529feb23e21b66ea08eda6be6cae0172f22fc97dafa108c183fb7  packages/artifact-mutated/manifest.json
1ebc7268d58f682a11de1d1f78242c56ebdb971824deb4bd1c547e8c731d10ad  packages/artifact-mutated/model/entities.jsonl
01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b  packages/artifact-mutated/model/relations.jsonl
2ce90deeb651469b57878acfab844b4b60152f3bc65b4caa08568ced96a5c895  packages/artifact-mutated/sources/sources.jsonl
66e7154f40fb4db63b0a0fb4326c192f4fadba6a8e8e12fb4b63fd99d54c035c  packages/manifest-mutated/context/index.md
36f6598b588493a0d33df97546dea904a5e81eef603c97588c53ec8b91c6965b  packages/manifest-mutated/diagnostics/diagnostics.jsonl
0c9ccba7f7492f3f23cf7e4fcded5f6b53d9a6eba63534a59d2b1a54fb79640e  packages/manifest-mutated/evidence/assertions.jsonl
9e7de0190515cd8a2a13b0f42d435365e7622d186f587ca5435094a5ff5c555f  packages/manifest-mutated/evidence/primitives.jsonl
80c99937b409a13d0cb2fe27db5ab68c0b544c3aac93e4fad4f4fb6883bc938a  packages/manifest-mutated/manifest.json
1ebc7268d58f682a11de1d1f78242c56ebdb971824deb4bd1c547e8c731d10ad  packages/manifest-mutated/model/entities.jsonl
01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b  packages/manifest-mutated/model/relations.jsonl
2ce90deeb651469b57878acfab844b4b60152f3bc65b4caa08568ced96a5c895  packages/manifest-mutated/sources/sources.jsonl
e7568a0efaaf7c3fcd68152c8f2c63e2a849b4372d2d63ac703815fe21e58729  packages/minimal-v01.aecctx
a01bcb40ddfd155ab7f090f422900eaa4d34fd69b3c91c6c57bf0b5623dd40d7  policies/trust-a.json
aa1d38c877c3e0521191e8f48eb8179fe1d3aa95aec8825f4f09a8d337d17dee  policies/trust-ab-1.json
30a97842f3f80dda8f0766f6dc5788447cb313412e792b509e4b47b2101a09ca  policies/trust-ab-2.json
e5fd5c3ccc9a9a0c2c2862b4b543491ef82c80fa4722e19d8342273789266c3e  policies/trust-none.json
5235509062ee8cb85795e59729b9124a5c3dff1e5b4efa371a18ca1343ff810c  registries/a-only.json
0a7a66c98bc6fdfeba661cbe46e301ec7086daeaed955beb8b8cfb878eecb791  registries/expired.json
5d590e5e33ce9212e3d46ab36d799b9c8c191304a1c0a7798e35022e5b01b8f9  registries/no-scope.json
0f6d86fe1e8e5ef82ef04bee8072498c03fce29b68fac628b528bef653d7916f  registries/not-yet-valid.json
2ff2ac2948269aff9fe254902be743411605e631598589dbe5b5082a39e7dec4  registries/revoked.json
ed6576d0f5ea50169c48336fc22c8671270c8ddfc55cdbbd445f8956ae7b8fed  registries/unknown-status.json
ed3957320a50b5540c2eb14e2cc0187ed169fa279004a4d02974b7a3abd160e3  registries/valid.json
```

The authoritative corpus SHA-256 is `ee4362c1ce21692b2634f289a9ac4da8ba98f33a9eb7cc0d72bb24ca856a3eee`. Every case-referenced input hash is also embedded in that corpus and validated before execution.

## 6. Commands and results

- Complete signing suite: 128 passed across contract, crypto, policy, CLI and conformance files.
- `python scripts/check_signing_conformance.py`: 24/24 governed cases matched offline.
- Schema mirror test: one passed; all four public/packaged schema pairs are byte-identical.
- Deterministic generator `--check` plus fixture/corpus diff: no drift.
- Secret/path slice: three passed; restricted-header/algorithm slice: seven passed; no-clock/network slice: two passed.
- Clean base and `[signing]` installation matrix: one passed, including wheel/sdist inspection and crypto-unavailable core behavior.
- Candidate build succeeded with hatchling 1.31.0. Candidate wheel SHA-256: `32c2cc65eca26c0cf5908a3e448b2f3d6c10e3f1361180f284fc1d2d4ba81e80`; candidate sdist SHA-256: `2f8af7da40833c4fe8d8288101fa69478f4259830b4598db1525147060138f4c`.
- Fresh candidate repository gates: `check_spec_contract.py` passed; baseline integration reported healthy with zero issues and bundle `baseline-shared-v1`; portable and full verification each passed 412 tests with nine expected opt-in skips, built wheel/sdist, passed RVT anti-claim and release verification, and ended in `aecctx portable verify: ok` / `aecctx verify: ok`.
- Task 7 CI `29212954852` for `b42271f`: Ubuntu `86703658768`, macOS `86703658767`, Windows `86703658772`, all passed.
- Candidate, closure and merged-main CI are pending section 12 publication steps and do not yet justify claim promotion.

## 7. Determinism and reproducibility

Fixed labels derive the three test seeds; public APIs emit canonical registries, policies and bundles. The generator compares every expected byte, including the stored ZIP, and fails on drift. Directory and ZIP forms produce the same signing statement. Repeated statement, signature, append, policy and verification operations are byte/record deterministic. The corpus blocks network calls and policy evaluation never reads the host clock.

## 8. Capability, loss and diagnostics

Unsigned packages remain valid packages and report `unsigned`, never fabricated identity. Per-signature results preserve `valid`, `invalid`, `foreign`, `unknown_key` and unsupported-algorithm outcomes separately from key lifecycle (`valid`, `not_yet_valid`, `expired`, `revoked`, `unknown_status`, `not_evaluated`), trust and authorization. Threshold failure is explicit. Operational parse, input-limit, package-integrity and missing-extra errors remain diagnostics rather than signature states. Signing does not alter package capability/loss reports or elevate generated Markdown.

## 9. Dependency, license, security, privacy and platform review

- Governed optional dependency: `cryptography>=45,<50`; validated local version `49.0.0`, license expression `Apache-2.0 OR BSD-3-Clause`.
- Transitive local binding: `cffi==2.1.0`, license expression `MIT-0`.
- Base metadata has no unconditional cryptography dependency. The crypto import is lazy and unsigned/core behavior works without the extra.
- Input limits are 1 MiB per control document, 64 signatures, 1,024 keys, 64 KiB private key and 4 KiB password; duplicate JSON names, noncanonical base64url, symlinks, unsafe paths and closed-schema violations are rejected.
- Private material is accepted only from an explicit bounded regular file; password input is file-only; CLI diagnostics redact secrets and absolute input paths; output sidecars are atomic mode `0600` files.
- No network, remote key lookup, host clock, LLM, environment-selected secret, telemetry or source upload is required. Public CI executes the portable profile on Linux, macOS and Windows.

## 10. Residual risks and unsupported cases

- Registry provenance and policy correctness are caller responsibilities; a trusted/authorized result is only relative to the supplied bytes and explicit verification time.
- Compromised private keys, malicious trust registries and incorrect organizational scope policy are not detected by cryptographic verification alone.
- Secure hardware, key custody/rotation operations, X.509 chains, online revocation, remote JWKS, timestamping, transparency, countersignatures, notarization and long-term archival validation remain unsupported.
- `Ed25519` is the only accepted algorithm profile. Other algorithms and the ambiguous `EdDSA` identifier are rejected without negotiation.
- A signature or satisfied threshold does not imply engineering approval, regulatory compliance, construction readiness or consumer acceptance.

## 11. WoodFraming boundary proof

All ACX-20 changed paths are within `/Users/facundo/desarrollo/aecctx`. Executable and distribution scans continue to reject `woodframing`, `WFDomain` and `WFImport`; matches are limited to governance/boundary checks. No file under `/Users/facundo/desarrollo/woodframing` was modified, and no consumer dependency, model or mapping entered AECCTX.

## 12. Promotion and publication

Current candidate state: ACX-20 remains `in_progress`, `package.authenticity-signing` remains `target`, ACX-21 remains `pending`, and no merge has occurred. The implementation candidate must first pass exact-SHA Ubuntu, macOS and Windows CI.

After that gate, one closure commit may promote only the bounded claim in section 4, set ACX-20 `completed` and ACX-21 `pending-next`. That closure SHA must pass all three CI jobs before a `--no-ff` merge to `main`; the merged main SHA then requires fresh maintainer verification and green main CI. ACX-21 is not executed. No tag or release is authorized here; ACX-23 owns release authority.

Documentation without those exact candidate, closure and main gates; an unmapped fixture; test-only keys; a happy-path signature; or a cryptographically valid but policy-unevaluated signature does not count as public authenticity support.
