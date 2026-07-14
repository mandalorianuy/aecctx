# LibreDWG ACX-18 provider licensing record

Status: reviewed external runtime; not distributed by the AECCTX core package

- Provider: `org.aecctx.dwg.libredwg@0.2.0`
- Runtime: GNU LibreDWG 0.13.4 API/ABI 1
- License: GPL-3.0-or-later
- Official source archive: `https://github.com/LibreDWG/libredwg/releases/download/0.13.4/libredwg-0.13.4.tar.xz`
- Archive SHA-256: `7e153ea4dac4cbf3dc9c50b9ef7a5604e09cdd4c5520bcf8017877bbe1422cd5`
- Reviewed image ID: `sha256:bb237d62599b5204b550fb075ee9f738e4198e031b71f3a6d7f85eae07c0c7c1`
- ACX-24 targets: exact `linux/arm64` and `linux/amd64` image IDs and resolved package locks in `fixtures/v0.3/provider-multiarch/receipts/`
- Base image: Ubuntu Noble at `sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90`

LibreDWG does not enter `pyproject.toml`, the core import path, wheels, sdists or in-process extras. Operators build the image explicitly; AECCTX never pulls or builds it during ingest. The repository does not publish the image by default.

Any party that distributes the image must independently satisfy GPL-3.0-or-later obligations, including license notices, complete corresponding source/build material and user replacement rights applicable to that distribution. This record is not permission to redistribute the image without those obligations.

The R2000 DXF fixture is authored by this project and generated with `ezdxf`. Its DWG counterpart is a mechanical encoding produced locally by the reviewed `dxf2dwg` binary. No proprietary fixture or commercial SDK output is committed.

## ACX-33 v0.3 profile amendment

The provider identity `org.aecctx.dwg.libredwg@0.3.0` retains GNU LibreDWG 0.13.4 API/ABI 1 under GPL-3.0-or-later and the same external OCI isolation. No GPL binary, library, source, worker, or generated image enters the Apache-2.0 wheel or sdist.

The R13/AC1012, R14/AC1014 and R2000/AC1015 fixtures are mechanical encodings of project-authored R12/R2000 DXF source data generated with `ezdxf==1.4.4`. The exact reviewed arm64 image invokes `dxf2dwg` with network disabled and a non-root user. Generator, source and output hashes are bound in `conformance/v0.3/dwg-corpus.json`. The profile does not distribute third-party proprietary drawings or commercial SDK output. R12 is excluded because the exact runtime rejects its help-advertised option; R2004+ writing and all other provider routes remain non-claims.

The existing source archive, SHA-256, build instructions, notice, corresponding-source and replacement obligations continue to govern any operator distribution of either architecture image. Core and CLI never download, build, link, import, or launch a writer.
