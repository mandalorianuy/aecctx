#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
image="aecctx-step-iges-ocp:0.2.0"

docker build --pull=false --network=default --tag "$image" "$repo_root/providers/step-iges-ocp"
docker image inspect --format '{{.Id}}' "$image"
