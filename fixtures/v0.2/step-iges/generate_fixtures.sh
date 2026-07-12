#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
output="$repo_root/fixtures/v0.2/step-iges"

chmod 0777 "$output"
docker run --rm --network=none --read-only --user=65532:65532 \
  --mount="type=bind,src=$repo_root/providers/step-iges-ocp/generate_fixtures.py,dst=/provider/generate_fixtures.py,readonly" \
  --mount="type=bind,src=$output,dst=/output" \
  aecctx-step-iges-ocp:0.2.0 python3 /provider/generate_fixtures.py
chmod 0755 "$output"
chmod 0644 "$output"/*.step "$output"/*.igs
