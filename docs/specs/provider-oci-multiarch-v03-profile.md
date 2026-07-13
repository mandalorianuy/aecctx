# AECCTX provider OCI multi-architecture profile v0.3

Status: normative for ACX-24 implementation; no public claim exists until the complete acceptance bundle passes.

Decision authority: ACXD-032.

## Purpose and boundary

This profile makes the three reviewed v0.2 external OCI providers executable under the same fail-closed contract on exactly `linux/arm64` and `linux/amd64`. It adds platform-bound runtime identity and cross-architecture conformance; it does not add extraction semantics, change the v0.2 package schemas, distribute provider images, or admit native macOS/Windows execution.

The core remains offline and application-agnostic. Provider input is untrusted data. AECCTX never executes source-provided commands, follows source links, pulls images, builds images during ingest, enables network access, or treats replay as live runtime evidence.

## Closed provider matrix

| Provider | Version | Runtime dependency | Formats/actions |
|---|---:|---|---|
| `org.aecctx.ocr.tesseract-tsv` | `0.2.0` | Tesseract `5.3.4`, `eng` data `4.1.0`, Pillow `12.3.0` | PGM OCR `extract` |
| `org.aecctx.step-iges.ocp` | `0.2.0` | cadquery-ocp `7.9.3.1.1`, OCCT `7.9.3` | STEP/IGES `extract` |
| `org.aecctx.dwg.libredwg` | `0.2.0` | LibreDWG `0.13.4` API/ABI 1 | bounded R2000 DWG `extract` |

Every row must pass on both `linux/arm64` and `linux/amd64`. Any other provider, version, OS, architecture, format or action is outside this profile.

## Runtime target contract

An `OCIRuntimeTarget` is immutable and contains exactly:

- `platform`: `linux`;
- `architecture`: `arm64` or `amd64`;
- `image`: a reviewed local tag;
- `image_id`: a lowercase `sha256:` Docker image ID.

A registration may expose multiple unique targets. Selection requires the caller to request one exact platform and architecture. Duplicate targets are invalid. Missing targets fail with `AECCTX_PROVIDER_ARCHITECTURE_UNSUPPORTED`. Before launch, Docker must be locally available and report Linux server operation; `docker image inspect` must report the target image's exact ID, OS and architecture. ID drift fails with `AECCTX_PROVIDER_IMAGE_DIGEST_MISMATCH`; OS or architecture drift fails with `AECCTX_PROVIDER_ARCHITECTURE_UNSUPPORTED`. These failures never trigger a pull or build.

The legacy single-image fields remain readable only for unchanged v0.2 registrations. They do not satisfy `sandbox.oci-multiarch` and cannot be selected as a v0.3 target implicitly.

## Reproducible build receipt

The reviewed build command accepts one provider, `linux` and one admitted architecture. It builds locally with the repository Dockerfile, pinned base manifest, locked runtime versions and no push. The canonical JSON receipt contains:

- profile and provider IDs and versions;
- platform and architecture;
- image tag and immutable local image ID;
- base image index and platform-manifest digests;
- Dockerfile, worker, dependency-lock and upstream archive digests as applicable;
- resolved dependency versions and SPDX expression;
- build-network policy and a statement that no image was pushed.

Canonical receipts contain no time, host path, builder identity or mutable host metadata. Repeating a build with unchanged reviewed inputs must produce the same semantic receipt fields; a changed image ID is new runtime evidence requiring review rather than an invented match.

## Semantic equivalence

For each provider, both targets consume the same publishable source bytes, canonical request and configuration. Verification compares canonical response JSON, ordered provider events and artifact bytes after removing only these governed attestation differences:

- `architecture`;
- `image_id`.

No source evidence, geometry, identity, diagnostic, value state, confidence, provenance, loss or capability field may be removed or defaulted for comparison. A genuine numerical or ordering difference fails the matrix and leaves the claim partial/unsupported for the affected combination.

## Live security gates

Each target must retain the reviewed OCI controls: no network, read-only root, dropped capabilities, no-new-privileges, non-root user, bounded PID tree, memory/CPU/open-file/output limits, bounded tmpfs and explicit read-only input mounts. Live adversarial cases cover timeout, PID ceiling, memory/output exhaustion, filesystem mutation, network denial, malformed response and wrong-architecture selection. A skipped or replayed case cannot satisfy a live gate.

## Licensing and provider gate

The Python core does not link or distribute any provider runtime. The repository may publish recipes and receipts, not images. Distribution remains subject to the provider records in `docs/licenses/`, including GPL corresponding-source obligations for LibreDWG and LGPL/OCCT exception obligations for OCP/OCCT. A dependency without a legally reproducible build for either admitted architecture blocks only its matrix row and prevents claim promotion.

## Conformance and claim lifecycle

`conformance/v0.3/provider-multiarch-corpus.json` binds every source, request, response, artifact, descriptor, image and receipt digest. `conformance/v0.3/claims.json` maps `sandbox.oci-multiarch` to all six live combinations and their tests. The claim remains `experimental partial` until all mappings exist and `scripts/verify_provider_matrix.sh` succeeds without skips. Portable CI validates schemas, mappings and replay artifacts but must not claim local Docker availability.

## Explicit non-claims

This profile does not claim native macOS or Windows execution, Kubernetes/remote execution, registry publication, image signing, binary transparency, automatic image acquisition, or support for any unlisted provider or architecture. It does not change the public format claims inherited from v0.2.
