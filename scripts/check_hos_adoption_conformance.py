#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def _load_baseline_symbols(repo_root: Path):
    try:
        from agent_baseline.hos_adoption import HOS_ARTIFACT_REFS, check_hos_adoption_conformance

        return HOS_ARTIFACT_REFS, check_hos_adoption_conformance
    except ModuleNotFoundError:
        pass

    candidates: list[Path] = []
    env_root = os.environ.get("AGENT_BASELINE_ROOT", "").strip()
    if env_root:
        candidates.append(Path(env_root).resolve())
    candidates.extend(
        [
            repo_root.resolve(),
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
            from agent_baseline.hos_adoption import HOS_ARTIFACT_REFS, check_hos_adoption_conformance
        except ModuleNotFoundError:
            sys.path.pop(0)
            continue
        return HOS_ARTIFACT_REFS, check_hos_adoption_conformance
    raise ModuleNotFoundError("unable to resolve agent_baseline.hos_adoption; set AGENT_BASELINE_ROOT or install baseline package")


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _offer_payload_path(repo_root: Path, source_ref: str) -> Path:
    source_path = Path(source_ref)
    offer_root = repo_root / ".agent_baseline" / "baseline_offer"
    if source_ref.startswith("artifacts/agent_baseline/"):
        published_ref = Path("artifacts") / source_path.relative_to("artifacts/agent_baseline")
        offer = offer_root / published_ref
        if offer.exists():
            return offer
    offer = offer_root / source_path
    if offer.exists():
        return offer
    return repo_root / source_path


def _local_payload_path(repo_root: Path, source_ref: str) -> Path:
    return repo_root / source_ref


def _resolve_source_mode(repo_root: Path, artifact_refs: dict[str, str], requested: str) -> str:
    if requested != "auto":
        return requested
    has_local_projection = any(_local_payload_path(repo_root, source_ref).exists() for source_ref in artifact_refs.values())
    return "local" if has_local_projection else "offer"


def _payload_path(repo_root: Path, source_ref: str, source_mode: str) -> Path:
    if source_mode == "local":
        return _local_payload_path(repo_root, source_ref)
    return _offer_payload_path(repo_root, source_ref)


def _build_local_payloads(repo_root: Path) -> dict[str, dict[str, object]]:
    builder = repo_root / "scripts" / "build_hos_adoption_projection.py"
    if not builder.exists():
        return {}
    result = subprocess.run(
        [sys.executable, str(builder), "--repo-root", str(repo_root)],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {}
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate consumer HOS adoption projections against baseline contract shapes.")
    parser.add_argument("--repo-root", default=".", help="Consumer repo root. Defaults to current directory.")
    parser.add_argument("--payload", action="append", default=[], help="Override payload as contract_id=/path/to/payload.json")
    parser.add_argument(
        "--source",
        choices=("auto", "offer", "local"),
        default="auto",
        help="Payload source. `auto` validates local projections when present, otherwise the synced baseline offer.",
    )
    parser.add_argument("--adapter-id", default="hos-adoption-adapter")
    parser.add_argument("--consumer-ref", default="consumer-repo")
    parser.add_argument("--fail-on-issues", action="store_true")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    artifact_refs, checker = _load_baseline_symbols(repo_root)
    overrides: dict[str, Path] = {}
    for item in args.payload:
        if "=" not in item:
            raise SystemExit(f"--payload must use contract_id=path, got `{item}`")
        contract_id, raw_path = item.split("=", 1)
        overrides[contract_id.strip()] = Path(raw_path).resolve()

    payloads: dict[str, dict[str, object]] = {}
    missing_paths: list[str] = []
    source_mode = _resolve_source_mode(repo_root, artifact_refs, args.source)
    built_local_payloads: dict[str, dict[str, object]] = {}
    can_build_local = args.source == "local" and not overrides
    for contract_id, source_ref in artifact_refs.items():
        path = overrides.get(contract_id) or _payload_path(repo_root, source_ref, source_mode)
        if not path.exists():
            if source_mode == "local" and can_build_local:
                if not built_local_payloads:
                    built_local_payloads = _build_local_payloads(repo_root)
                payload = built_local_payloads.get(contract_id)
                if isinstance(payload, dict):
                    payloads[contract_id] = payload
                    continue
            missing_paths.append(f"{contract_id}:{path}")
            continue
        payloads[contract_id] = _load_json(path)
    if missing_paths:
        print(json.dumps({"conformance_status": "missing-input", "source_mode": source_mode, "missing_paths": missing_paths}, indent=2))
        return 1 if args.fail_on_issues else 0

    conformance = checker(payloads, adapter_id=args.adapter_id, consumer_ref=args.consumer_ref)
    payload = conformance.to_dict()
    payload["source_mode"] = source_mode
    print(json.dumps(payload, indent=2))
    has_issues = payload.get("conformance_status") != "passing"
    return 1 if args.fail_on_issues and has_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
