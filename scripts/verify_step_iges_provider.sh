#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
image="aecctx-step-iges-ocp:0.2.0"
expected_id="sha256:875cbbbc5198ae44e8957e3a90c9a8afd0dc541f01029fb5186a296e3d2a0d47"
actual_id="$(docker image inspect --format '{{.Id}}' "$image")"

if [[ "$actual_id" != "$expected_id" ]]; then
  echo "AECCTX_STEP_IGES_IMAGE_DIGEST_MISMATCH: expected $expected_id, got $actual_id" >&2
  exit 2
fi

docker run --rm --network=none --read-only --user=65532:65532 "$image" \
  python3 -c 'import importlib.metadata, OCP; assert importlib.metadata.version("cadquery-ocp") == "7.9.3.1.1"'

echo "aecctx STEP/IGES provider runtime: ok $actual_id"
