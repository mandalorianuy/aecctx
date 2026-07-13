#!/usr/bin/env bash
set -euo pipefail

repo_root="${AECCTX_RELEASE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$repo_root"

if [[ -x .venv/bin/python ]]; then
  python_runtime=".venv/bin/python"
else
  python_runtime="${PYTHON:-python3}"
fi

"$python_runtime" -m aecctx.conformance conformance/v0.1/corpus.json
"$python_runtime" -c 'from aecctx.release_conformance import validate_release_corpus; print(validate_release_corpus("conformance/v0.2/corpus.json", repository_root="."))'

rm -f dist/SHA256SUMS dist/aecctx-0.2.0.spdx.json dist/aecctx-inspector-0.2.0.zip
artifacts=(dist/aecctx-0.2.0-py3-none-any.whl dist/aecctx-0.2.0.tar.gz)
for artifact in "${artifacts[@]}"; do
  [[ -f "$artifact" ]] || { echo "aecctx release verify: missing $artifact" >&2; exit 1; }
done
sdist_members="$(mktemp "${TMPDIR:-/tmp}/aecctx-sdist-members.XXXXXX")"
tar -tf "${artifacts[1]}" >"$sdist_members"
for required in \
  "aecctx-0.2.0/conformance/v0.2/corpus.json" \
  "aecctx-0.2.0/conformance/v0.2/provider-corpus.json" \
  "aecctx-0.2.0/conformance/v0.2/gate-corpus.json" \
  "aecctx-0.2.0/conformance/v0.2/plugin-corpus.json" \
  "aecctx-0.2.0/docs/release/v0.2.0-evidence-index.md" \
  "aecctx-0.2.0/docs/release/v0.2.0-supply-chain.md" \
  "aecctx-0.2.0/docs/specs/ifc-v02-profile.md" \
  "aecctx-0.2.0/docs/specs/dxf-v02-profile.md" \
  "aecctx-0.2.0/fixtures/v0.2/dxf/r2018-semantics-3d-binary.dxf" \
  "aecctx-0.2.0/fixtures/v0.2/ifc/ifc4-native-2d-georef.ifc"; do
  grep -Fxq "$required" "$sdist_members" || {
    echo "aecctx release verify: sdist missing $required" >&2
    exit 1
  }
done
rm -f "$sdist_members"
"$python_runtime" - <<'PY'
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
root = Path("plugins/aecctx-inspector")
with ZipFile("dist/aecctx-inspector-0.2.0.zip", "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        info = ZipInfo(path.relative_to(root.parent).as_posix(), (1980, 1, 1, 0, 0, 0))
        info.compress_type = ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, path.read_bytes())
PY
artifacts+=(dist/aecctx-inspector-0.2.0.zip)
"$python_runtime" -m aecctx.release "${artifacts[@]}" --output-directory dist >/dev/null

clean_root="$(mktemp -d "${TMPDIR:-/tmp}/aecctx-clean-install.XXXXXX")"
trap 'rm -rf "$clean_root"; rm -f "${sdist_members:-}"' EXIT
"$python_runtime" -m venv "$clean_root/venv"
if [[ -x "$clean_root/venv/bin/python" ]]; then
  clean_python="$clean_root/venv/bin/python"
  clean_aecctx="$clean_root/venv/bin/aecctx"
else
  clean_python="$clean_root/venv/Scripts/python.exe"
  clean_aecctx="$clean_root/venv/Scripts/aecctx.exe"
fi
"$clean_python" -m pip install --disable-pip-version-check "${artifacts[0]}" >/dev/null
"$clean_aecctx" version --json | "$clean_python" -c 'import json,sys; assert json.load(sys.stdin)["data"]["version"] == "0.2.0"'
"$clean_aecctx" validate fixtures/minimal-aecctx --json | "$clean_python" -c 'import json,sys; assert json.load(sys.stdin)["ok"] is True'
"$clean_python" -m pip install --disable-pip-version-check "${artifacts[0]}[all]" >/dev/null
"$clean_python" -c 'import cryptography, ezdxf, ifcopenshell, ifctester, mcp, PIL, pypdf, trimesh'

echo "aecctx release verify: ok"
