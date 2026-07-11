#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


def _load_checker(repo_root: Path):
    try:
        from agent_baseline.mission_control import check_mission_adapter_conformance

        return check_mission_adapter_conformance
    except ModuleNotFoundError:
        pass

    env_root = os.environ.get("AGENT_BASELINE_ROOT", "").strip()
    candidates: list[Path] = []
    if env_root:
        candidates.append(Path(env_root).resolve())
    candidates.extend(
        [
            (repo_root / "../codex-agent-baseline").resolve(),
            (repo_root / "../../codex-agent-baseline").resolve(),
        ]
    )
    for baseline_root in candidates:
        package_path = baseline_root / "packages"
        if not package_path.exists():
            continue
        sys.path.insert(0, str(package_path))
        try:
            from agent_baseline.mission_control import check_mission_adapter_conformance
        except ModuleNotFoundError:
            sys.path.pop(0)
            continue
        return check_mission_adapter_conformance
    raise ModuleNotFoundError(
        "unable to resolve agent_baseline.mission_control; install the package, set AGENT_BASELINE_ROOT, "
        "or keep a sibling codex-agent-baseline checkout"
    )


def _read_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return {"events": payload}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object or event list")
    return payload


def _default_artifact(repo_root: Path, relative_offer_path: str, relative_source_path: str) -> Path:
    offer = repo_root / relative_offer_path
    if offer.exists():
        return offer
    return repo_root / relative_source_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a consumer Mission Control projection against baseline v2.")
    parser.add_argument("--repo-root", default=".", help="Consumer repo root. Defaults to current directory.")
    parser.add_argument("--session", default="", help="Mission Control session JSON path.")
    parser.add_argument("--view", default="", help="Mission Control view JSON path.")
    parser.add_argument("--events", default="", help="Mission Control events JSON path.")
    parser.add_argument("--adapter-id", default="mission-control-adapter")
    parser.add_argument("--consumer-ref", default="consumer-repo")
    parser.add_argument("--source-surface", default="mission_control_projection")
    parser.add_argument("--fail-on-issues", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    session_path = Path(args.session).resolve() if args.session else _default_artifact(
        repo_root,
        ".agent_baseline/baseline_offer/artifacts/mission_control/latest-mission-control-session.json",
        "artifacts/agent_baseline/mission_control/latest-mission-control-session.json",
    )
    view_path = Path(args.view).resolve() if args.view else _default_artifact(
        repo_root,
        ".agent_baseline/baseline_offer/artifacts/mission_control/latest-mission-control-view.json",
        "artifacts/agent_baseline/mission_control/latest-mission-control-view.json",
    )
    events_path = Path(args.events).resolve() if args.events else _default_artifact(
        repo_root,
        ".agent_baseline/baseline_offer/artifacts/mission_control/latest-mission-control-events.json",
        "artifacts/agent_baseline/mission_control/latest-mission-control-events.json",
    )
    missing = [str(path) for path in (session_path, view_path, events_path) if not path.exists()]
    if missing:
        print(json.dumps({"status": "missing-input", "missing": missing}, indent=2))
        return 1 if args.fail_on_issues else 0

    checker = _load_checker(repo_root)
    conformance = checker(
        session_payload=_read_json(session_path),
        view_payload=_read_json(view_path),
        events_payload=_read_json(events_path),
        adapter_id=args.adapter_id,
        consumer_ref=args.consumer_ref,
        source_surface=args.source_surface,
    )
    payload = conformance.to_dict()
    print(json.dumps(payload, indent=2))
    has_issues = payload.get("conformance_status") != "passing"
    return 1 if args.fail_on_issues and has_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
