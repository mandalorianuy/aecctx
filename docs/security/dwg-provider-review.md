# ACX-18 LibreDWG provider security review

Profile: `oci-docker-v1`, Linux arm64, image ID `sha256:bb237d62599b5204b550fb075ee9f738e4198e031b71f3a6d7f85eae07c0c7c1`

## Boundary

- Network is disabled; root filesystem is read-only; UID/GID is 65532; capabilities are dropped; `no-new-privileges` is active.
- Registration permits exactly two PIDs: the read-only mounted Python worker and one sequential fixed `/opt/libredwg/bin/dwgread` child.
- The caller cannot supply a command, shell, environment path, resource path, external reference policy or LibreDWG option.
- Input/request/worker mounts are read-only. Only bounded output and private temporary storage are writable.
- CPU, memory, wall time, file size/count, open files, input/output bytes, record count and recursion are bounded by ACX-12.
- Xrefs, file paths, macros, OLE data, scripts and commands remain inert values. No referenced path is opened.
- Raw stderr is not package evidence; only stable diagnostic codes cross the boundary.

## Decoder risk

LibreDWG describes advanced and newer classes as beta, unstable, undertested or unhandled. ACX-18 therefore claims only exact self-contained `AC1015` input and retains unknown/proxy/custom objects as observed or opaque loss. A successful decoder exit is never interpreted as complete semantics.

The official upstream issue [#1037](https://github.com/LibreDWG/libredwg/issues/1037) reports a heap-buffer-overflow in `dwg_decode_MATERIAL_private`, with allocation in `MATERIAL_Texture_diffusemap_private`. Upstream closed it on 2025-08-18 as no longer reproducible, before the selected 0.13.4 release of 2026-03-18. No fixing commit, CVE or dedicated regression test is linked in that issue, so this review cannot prove the exact fix lineage. The selected release is newer than the closure, but native-decoder compromise remains a residual risk and the full sandbox is mandatory.

## Verification limits

- Official `programs/dxf.test` passes in the reviewed build and covers the read/DWG-to-DXF plus project fixture generation paths used here.
- Aggregate `programs/alive.test` has 25 JSON-to-DWG writer round-trip failures on this arm64 build. The provider never exposes writer actions; this remains evidence that full upstream conformance is not established.
- Two cached builds with BuildKit provenance disabled produced the same inspected image ID. Source/archive/base/Dockerfile/test evidence is retained directly.
- The project fixture reproducibly produces explicit duplicate-handle conflicts (`1F`, `B`). Objects remain distinct and ambiguous references are not resolved.

Residual risk is accepted only for the experimental partial claim. A decoder upgrade, broader DWG version, image distribution, native execution or removal of sandbox axes requires a new governed review.

ACX-24 adds no DWG semantics. The project R2000 fixture produces identical canonical response, source JSON and converted DXF bytes on the reviewed `linux/arm64` and `linux/amd64` images. Exact source/archive, image and resolved-package evidence is bound in `conformance/v0.3/provider-multiarch-corpus.json`; native and unlisted platforms remain unsupported.
