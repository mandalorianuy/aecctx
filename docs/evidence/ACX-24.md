# ACX-24 acceptance evidence

Status: implementation candidate; local acceptance complete, remote exact-SHA acceptance pending.

ACX-24 is governed by `docs/specs/provider-oci-multiarch-v03-profile.md` and ACXD-032. This evidence record becomes final only after the complete local and remote gate bundle passes and the implementation ledger is promoted.

## Implemented result

- Exact `OCIRuntimeTarget` selection for `linux/arm64` and `linux/amd64`, with no implicit pull or build.
- Architecture, OS and local image-ID preflight binding for the reviewed Tesseract, OCP/OCCT and LibreDWG providers.
- Operator-only local build recipes, package-lock receipts and digest-bound portable corpus.
- Cross-architecture live semantic/artifact equivalence and adversarial sandbox verification.

## Claim boundary

The candidate claim is `sandbox.oci-multiarch`, public partial only for the six listed provider/architecture combinations. Native macOS/Windows, automatic acquisition, remote execution, image distribution and image signing remain unsupported. Existing v0.2 format semantics are unchanged.

## Validation evidence

- TDD RED: `tests/test_provider_multiarch.py` initially failed because `OCIRuntimeTarget`, exact resolution and architecture-aware preflight did not exist.
- Focused GREEN: provider/multiarch/existing provider suites passed 78 tests with 9 intentional opt-in skips.
- Live positive matrix: six of six provider/architecture combinations passed against project-authored fixtures. Tesseract response payload digest was `17939fb7...`; STEP/IGES `ed988f32...`; DWG `09352765...`, equal across architectures with equal artifacts.
- Live security matrix: network, filesystem, process-tree, timeout, memory, output and malformed-response cases returned their seven exact governed codes on both architectures.
- Build proof: `scripts/build_provider_matrix.sh` rebuilt the reviewed Tesseract arm64 target to the registered image ID and refreshed an identical digest-bound receipt without pushing.
- Portable gate: 221 focused tests and 640 full tests passed with 10 explicit skips; deterministic corpora, wheel and sdist built successfully.
- Full maintainer gate: `PYTHONPATH=src PYTHON=/Users/facundo/desarrollo/aecctx/.venv/bin/python AECCTX_VERIFY_PROVIDER_MATRIX=1 ./scripts/verify.sh` passed, including six live executions, portable corpus, baseline integration and release verification.
- Runtime: Docker Desktop 4.79.0, Engine 29.5.3, buildx 0.34.1; Docker reported each loaded image as its requested Linux architecture.

Candidate commit SHA and remote CI URL are added only after publication succeeds. The claim remains `experimental partial` until that gate and governed closure complete.
