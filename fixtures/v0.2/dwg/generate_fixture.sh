#!/usr/bin/env bash
set -euo pipefail

fixture_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$fixture_root/../../.." && pwd)"
image="aecctx-dwg-libredwg:0.2.0"
expected_id="sha256:bb237d62599b5204b550fb075ee9f738e4198e031b71f3a6d7f85eae07c0c7c1"
actual_id="$(docker image inspect --format '{{.Id}}' "$image")"

if [[ "$actual_id" != "$expected_id" ]]; then
  echo "AECCTX_DWG_IMAGE_DIGEST_MISMATCH: expected $expected_id, got $actual_id" >&2
  exit 2
fi

"$repo_root/.venv/bin/python" "$fixture_root/generate_fixture.py"
temporary="$(mktemp -d)"
trap 'rm -rf "$temporary"' EXIT
chmod 0777 "$temporary"
cp "$fixture_root/r2000-profile.dxf" "$temporary/input.dxf"
chmod 0444 "$temporary/input.dxf"
docker run --rm --network=none --user=65532:65532 -v "$temporary:/work" -w /work "$image" \
  dxf2dwg --as r2000 -o /work/r2000-profile.dwg /work/input.dxf
cp "$temporary/r2000-profile.dwg" "$fixture_root/r2000-profile.dwg"
"$repo_root/.venv/bin/python" -c 'from pathlib import Path; p=Path("'"$fixture_root"'"); data=(p/"r2000-profile.dwg").read_bytes(); (p/"wrong-version.dwg").write_bytes(b"AC1027"+data[6:]); (p/"truncated.dwg").write_bytes(b"AC10")'
