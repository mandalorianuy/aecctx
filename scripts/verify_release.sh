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
"$python_runtime" -m aecctx.release_v03_conformance

artifacts=(dist/aecctx-0.3.0-py3-none-any.whl dist/aecctx-0.3.0.tar.gz)
for artifact in "${artifacts[@]}"; do
  [[ -f "$artifact" ]] || { echo "aecctx release verify: missing $artifact" >&2; exit 1; }
done

clean_root="$(mktemp -d "${TMPDIR:-/tmp}/aecctx-release-v03.XXXXXX")"
trap 'rm -rf "$clean_root"' EXIT
SOURCE_DATE_EPOCH=1783987200 "$python_runtime" -m build --wheel --sdist --outdir "$clean_root/rebuild" >/dev/null
cmp "${artifacts[0]}" "$clean_root/rebuild/aecctx-0.3.0-py3-none-any.whl"
cmp "${artifacts[1]}" "$clean_root/rebuild/aecctx-0.3.0.tar.gz"

sdist_members="$clean_root/sdist-members.txt"
tar -tf "${artifacts[1]}" >"$sdist_members"
for required in \
  "aecctx-0.3.0/conformance/v0.3/corpus.json" \
  "aecctx-0.3.0/conformance/v0.3/claims.json" \
  "aecctx-0.3.0/conformance/v0.3/provider-multiarch-corpus.json" \
  "aecctx-0.3.0/conformance/v0.3/rvt-provider-decision.json" \
  "aecctx-0.3.0/conformance/v0.3/plugin-corpus.json" \
  "aecctx-0.3.0/docs/compatibility-v0.3.md" \
  "aecctx-0.3.0/docs/release/v0.3.0-evidence-index.md" \
  "aecctx-0.3.0/docs/release/v0.3.0-supply-chain.md"; do
  grep -Fxq "$required" "$sdist_members" || {
    echo "aecctx release verify: sdist missing $required" >&2
    exit 1
  }
done

rm -f dist/aecctx-inspector-0.3.0.zip dist/aecctx-inspector-0.3.0.zip.json
"$python_runtime" scripts/build_inspector_distribution.py --output dist/aecctx-inspector-0.3.0.zip >/dev/null
"$python_runtime" scripts/build_inspector_distribution.py --output "$clean_root/aecctx-inspector-0.3.0.zip" >/dev/null
cmp dist/aecctx-inspector-0.3.0.zip "$clean_root/aecctx-inspector-0.3.0.zip"
artifacts+=(dist/aecctx-inspector-0.3.0.zip)
"$python_runtime" -c 'from aecctx.release_v03_conformance import scan_release_artifacts; print(scan_release_artifacts(__import__("sys").argv[1:]))' "${artifacts[@]}"

rm -f dist/SHA256SUMS dist/aecctx-0.3.0.spdx.json
"$python_runtime" -m aecctx.release "${artifacts[@]}" --output-directory dist >/dev/null
(cd dist && sha256sum -c SHA256SUMS)

"$python_runtime" -m venv "$clean_root/core"
"$python_runtime" -m venv "$clean_root/all"
if [[ -x "$clean_root/core/bin/python" ]]; then
  core_python="$clean_root/core/bin/python"
  core_cli="$clean_root/core/bin/aecctx"
  all_python="$clean_root/all/bin/python"
else
  core_python="$clean_root/core/Scripts/python.exe"
  core_cli="$clean_root/core/Scripts/aecctx.exe"
  all_python="$clean_root/all/Scripts/python.exe"
fi
"$core_python" -m pip install --disable-pip-version-check "${artifacts[0]}" >/dev/null
"$core_cli" version --json | "$core_python" -c 'import json,sys; assert json.load(sys.stdin)["data"]["version"] == "0.3.0"'
"$core_cli" validate fixtures/minimal-aecctx --json | "$core_python" -c 'import json,sys; assert json.load(sys.stdin)["ok"] is True'
"$core_python" -c 'import importlib.util; assert all(importlib.util.find_spec(name) is None for name in ("cryptography", "ezdxf", "ifcopenshell", "ifctester", "mcp", "PIL", "pypdf", "pyproj", "trimesh"))'
"$all_python" -m pip install --disable-pip-version-check "${artifacts[0]}[all]" >/dev/null
"$all_python" -c 'import aecctx, cryptography, ezdxf, ifcopenshell, ifctester, mcp, PIL, pypdf, pyproj, trimesh; assert aecctx.__version__ == "0.3.0"'

echo "aecctx release verify: ok"
