# Reviewed LibreDWG provider image

This operator-built image contains GNU LibreDWG 0.13.4 for the governed ACX-18 R2000/AC1015 profile.

The Apache-2.0 AECCTX core does not contain or link LibreDWG. Provider execution is allowed only through the digest-pinned ACX-12 OCI profile. The image is not published by default. Any distribution must comply with GPL-3.0-or-later source and notice obligations.

The runtime provider invokes only `dwgread`. `dxf2dwg` exists solely for the explicit project fixture generator and is never selected by provider input or configuration.

