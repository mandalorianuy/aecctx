# LibreDWG ACX-18 provider licensing record

Status: reviewed external runtime; not distributed by the AECCTX core package

- Provider: `org.aecctx.dwg.libredwg@0.2.0`
- Runtime: GNU LibreDWG 0.13.4 API/ABI 1
- License: GPL-3.0-or-later
- Official source archive: `https://github.com/LibreDWG/libredwg/releases/download/0.13.4/libredwg-0.13.4.tar.xz`
- Archive SHA-256: `7e153ea4dac4cbf3dc9c50b9ef7a5604e09cdd4c5520bcf8017877bbe1422cd5`
- Reviewed image ID: `sha256:bb237d62599b5204b550fb075ee9f738e4198e031b71f3a6d7f85eae07c0c7c1`
- Base image: Ubuntu Noble at `sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90`

LibreDWG does not enter `pyproject.toml`, the core import path, wheels, sdists or in-process extras. Operators build the image explicitly; AECCTX never pulls or builds it during ingest. The repository does not publish the image by default.

Any party that distributes the image must independently satisfy GPL-3.0-or-later obligations, including license notices, complete corresponding source/build material and user replacement rights applicable to that distribution. This record is not permission to redistribute the image without those obligations.

The R2000 DXF fixture is authored by this project and generated with `ezdxf`. Its DWG counterpart is a mechanical encoding produced locally by the reviewed `dxf2dwg` binary. No proprietary fixture or commercial SDK output is committed.
