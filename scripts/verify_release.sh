#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ -x .venv/bin/python ]]; then
  python_runtime=".venv/bin/python"
else
  python_runtime="${PYTHON:-python3}"
fi

"$python_runtime" -m aecctx.conformance conformance/v0.1/corpus.json

rm -f dist/SHA256SUMS dist/aecctx-0.1.0.spdx.json
artifacts=(dist/aecctx-0.1.0-py3-none-any.whl dist/aecctx-0.1.0.tar.gz)
for artifact in "${artifacts[@]}"; do
  [[ -f "$artifact" ]] || { echo "aecctx release verify: missing $artifact" >&2; exit 1; }
done
for required in \
  "aecctx-0.1.0/conformance/v0.2/provider-corpus.json" \
  "aecctx-0.1.0/conformance/v0.2/ifc-corpus.json" \
  "aecctx-0.1.0/docs/providers/provider-review-template.md" \
  "aecctx-0.1.0/docs/security/external-provider-threat-model.md" \
  "aecctx-0.1.0/docs/specs/ifc-v02-profile.md" \
  "aecctx-0.1.0/fixtures/v0.2/ifc/ifc4-native-2d-georef.ifc"; do
  tar -tf "${artifacts[1]}" | grep -Fxq "$required" || {
    echo "aecctx release verify: sdist missing $required" >&2
    exit 1
  }
done
"$python_runtime" -m aecctx.release "${artifacts[@]}" --output-directory dist >/dev/null

clean_root="$(mktemp -d "${TMPDIR:-/tmp}/aecctx-clean-install.XXXXXX")"
trap 'rm -rf "$clean_root"' EXIT
"$python_runtime" -m venv "$clean_root/venv"
if [[ -x "$clean_root/venv/bin/python" ]]; then
  clean_python="$clean_root/venv/bin/python"
  clean_aecctx="$clean_root/venv/bin/aecctx"
else
  clean_python="$clean_root/venv/Scripts/python.exe"
  clean_aecctx="$clean_root/venv/Scripts/aecctx.exe"
fi
"$clean_python" -m pip install --disable-pip-version-check "${artifacts[0]}" >/dev/null
"$clean_aecctx" version --json | "$clean_python" -c 'import json,sys; assert json.load(sys.stdin)["data"]["version"] == "0.1.0"'
"$clean_aecctx" validate fixtures/minimal-aecctx --json | "$clean_python" -c 'import json,sys; assert json.load(sys.stdin)["ok"] is True'

echo "aecctx release verify: ok"
