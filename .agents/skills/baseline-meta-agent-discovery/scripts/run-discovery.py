#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path


def _candidate_baseline_roots(repo_root: Path) -> list[Path]:
    candidates: list[Path] = []
    env_root = os.environ.get("AGENT_BASELINE_ROOT", "")
    if env_root:
        candidates.append(Path(env_root).expanduser().resolve())
    for candidate in (
        repo_root.parent / "codex-agent-baseline",
        repo_root.parent.parent / "codex-agent-baseline",
        Path(__file__).resolve().parents[4],
    ):
        candidate = candidate.resolve()
        if candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _resolve_check_cli(repo_root: Path):
    try:
        from agent_baseline.meta_agent_tooling import run_meta_agent_baseline_integration_check_cli

        return run_meta_agent_baseline_integration_check_cli
    except ImportError:
        pass

    for baseline_root in _candidate_baseline_roots(repo_root):
        module_path = baseline_root / "packages" / "agent_baseline" / "meta_agent_tooling.py"
        if not module_path.exists():
            continue
        sys.path.insert(0, str((baseline_root / "packages").resolve()))
        from agent_baseline.meta_agent_tooling import run_meta_agent_baseline_integration_check_cli

        return run_meta_agent_baseline_integration_check_cli
    raise SystemExit(
        "Could not resolve codex-agent-baseline. Install agent_baseline, set AGENT_BASELINE_ROOT, or keep a sibling codex-agent-baseline checkout."
    )


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    repo_root = Path.cwd()
    if "--repo-root" in args:
        idx = args.index("--repo-root")
        if idx + 1 < len(args):
            repo_root = Path(args[idx + 1]).resolve()
    else:
        args = ["--repo-root", str(repo_root), *args]
    runner = _resolve_check_cli(repo_root)
    return runner(args)


if __name__ == "__main__":
    raise SystemExit(main())
