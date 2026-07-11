#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import sys


def _load_runner(repo_root: Path):
    try:
        from agent_baseline.meta_agent_tooling import run_meta_agent_baseline_integration_check_cli
        return run_meta_agent_baseline_integration_check_cli, "", "python-package"
    except ModuleNotFoundError:
        pass

    env_root = os.environ.get("AGENT_BASELINE_ROOT", "").strip()
    candidates = []
    if env_root:
        candidates.append((Path(env_root).resolve(), "environment"))
    candidates.extend(
        [
            ((repo_root / "../codex-agent-baseline").resolve(), "sibling-1"),
            ((repo_root / "../../codex-agent-baseline").resolve(), "sibling-2"),
        ]
    )
    for baseline_root, label in candidates:
        package_path = baseline_root / "packages"
        if not package_path.exists():
            continue
        sys.path.insert(0, str(package_path))
        try:
            from agent_baseline.meta_agent_tooling import run_meta_agent_baseline_integration_check_cli
        except ModuleNotFoundError:
            sys.path.pop(0)
            continue
        return run_meta_agent_baseline_integration_check_cli, str(baseline_root), label
    raise ModuleNotFoundError(
        "unable to resolve agent_baseline for integration checking; install the package, set AGENT_BASELINE_ROOT, or keep a sibling codex-agent-baseline checkout"
    )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    runner, baseline_root, resolution = _load_runner(repo_root)
    return runner(
        sys.argv[1:],
        default_repo_root=repo_root,
        baseline_root=Path(baseline_root) if baseline_root else None,
        baseline_resolution=resolution,
    )


if __name__ == "__main__":
    raise SystemExit(main())
