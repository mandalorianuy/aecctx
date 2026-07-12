#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
image="aecctx-dwg-libredwg:0.2.0"
expected_id="sha256:9bae0e6084613c08f7f283381a2be45ba3b480992ddef92887f7ed4ddf425679"
actual_id="$(docker image inspect --format '{{.Id}}' "$image")"

if [[ "$actual_id" != "$expected_id" ]]; then
  echo "AECCTX_DWG_IMAGE_DIGEST_MISMATCH: expected $expected_id, got $actual_id" >&2
  exit 2
fi

version="$(docker run --rm --network=none --read-only --user=65532:65532 "$image" dwgread --version)"
if [[ "$version" != "dwgread 0.13.4" ]]; then
  echo "AECCTX_DWG_RUNTIME_VERSION_MISMATCH: expected dwgread 0.13.4, got $version" >&2
  exit 2
fi

if [[ -f "$repo_root/fixtures/v0.2/dwg/r2000-profile.dwg" ]]; then
  AECCTX_RUN_DWG_PROVIDER=1 "$repo_root/.venv/bin/python" -m pytest \
    "$repo_root/tests/test_dwg_provider.py" -k live -q
fi

echo "aecctx DWG provider runtime: ok $actual_id"
