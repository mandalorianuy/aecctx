# ACX-17 STEP/IGES provider security review

Date: 2026-07-12
Profile: `oci-docker-v1`, Linux arm64, image ID `sha256:875cbbbc5198ae44e8957e3a90c9a8afd0dc541f01029fb5186a296e3d2a0d47`

STEP/IGES bytes, entity graphs, OCCT transfer results and artifacts are untrusted. The provider is allowlisted by ID, worker path, container tag and immutable local image ID. Core ingest never pulls or builds the image.

Runtime controls are inherited from ACX-12: no network, non-root UID/GID 65532, read-only root, dropped capabilities, `no-new-privileges`, one process, bounded memory/CPU/open files/file size/output/time, private tmpfs, read-only input/request/worker mounts and one writable output mount. The parent validates schema, sequence, attestation, paths, symlinks, sizes, hashes, limits and host-path leakage before admitting output.

The worker accepts one exact configuration. It does not accept commands, environment, plugins, resource paths, callbacks or translator flags. External STEP/IGES references are recorded and rejected; they are never opened. Runtime network, telemetry and retention are absent. Temporary workspaces are parent-owned and deleted after each execution.

OCCT translator processing can alter or heal topology. The provider reports this condition on every successful B-Rep transfer and labels BREP as translator-derived. No output establishes source-exact geometry, survey authority, engineering correctness or consumer classification.

ACX-24 adds no STEP/IGES semantics. The same project-authored AP214 fixture produces identical canonical response, BREP and mesh bytes on the reviewed `linux/arm64` and `linux/amd64` images. Exact image/package-lock receipts and adversarial sandbox results are bound by `conformance/v0.3/provider-multiarch-corpus.json`; other platforms remain unsupported.
