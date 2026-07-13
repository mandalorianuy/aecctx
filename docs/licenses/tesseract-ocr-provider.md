# Tesseract OCR provider licensing and distribution boundary

Date: 2026-07-12
Profile: `tesseract-5.3.4-capi-eng-psm6-v1`

The optional ACX-15 provider is an operator-built OCI image and is not part of the `aecctx` wheel or sdist. ACX-24 reviews exact `linux/arm64` and `linux/amd64` targets containing Ubuntu Noble `tesseract-ocr=5.3.4-1build5`, `tesseract-ocr-eng=1:4.1.0-2`, their distribution dependencies, Python 3.12 and `Pillow==12.3.0`.

- Tesseract OCR and the selected `eng` trained data are Apache-2.0 under their upstream project repositories and Ubuntu package metadata.
- Pillow uses the HPND license recorded by its upstream distribution metadata.
- Ubuntu base and transitive runtime packages retain their own notices and licenses; an operator distributing the image must satisfy those obligations and produce an image SBOM/notices bundle.
- No provider dependency is linked into or redistributed by the Apache-2.0 core Python package.

The checked registration accepts only local image ID `sha256:6d52ebcafef0ccdf59f58beccc7483c16a6e160fc94e3c3ea59f3f10c991f492`. Rebuilding against changed Ubuntu dependency revisions creates a different runtime and requires a new reviewed digest and corpus run. This document is an engineering distribution record, not legal advice.

For ACX-24 the architecture-specific image IDs and complete resolved package locks are authority-bound in `fixtures/v0.3/provider-multiarch/receipts/`. The repository still publishes no image; a distributor must produce its own SBOM/notices bundle and satisfy every base/transitive obligation.
