# ACX-17 OCP provider runtime

This operator-built image contains the native OCP/OCCT runtime selected by ACXD-028. It is not part of the AECCTX core distribution and is never pulled or built by core ingest.

Build and inspect it explicitly:

```bash
./scripts/build_step_iges_provider.sh
docker image inspect --format '{{.Id}}' aecctx-step-iges-ocp:0.2.0
```

Runtime execution is limited to the digest-pinned ACX-12 `oci-docker-v1` profile. Network is disabled at runtime and the worker is mounted read-only by the reviewed registration.
