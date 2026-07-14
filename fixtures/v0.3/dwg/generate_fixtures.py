#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from aecctx.providers import OCIDockerProfile, ProviderLimits, ProviderRunner, build_provider_request
from aecctx.providers.dwg import DWG_CONFIGURATIONS, DWG_OCI_TARGETS, DWG_PROVIDER_ID, dwg_v03_descriptor, dwg_v03_registry


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
IMAGE = "aecctx-dwg-libredwg:0.3.0-linux-arm64"
IMAGE_ID = "sha256:bb237d62599b5204b550fb075ee9f738e4198e031b71f3a6d7f85eae07c0c7c1"
LIMITS = ProviderLimits(max_input_bytes=2_000_000, max_output_bytes=30_000_000, max_records=2_000, max_files=10, max_recursion_depth=64, max_decompression_ratio=20.0, wall_time_seconds=30.0, cpu_seconds=30, max_memory_bytes=1_073_741_824, max_open_files=32)
PROFILES = (("r13-profile", "R12", "r13", "acx33-r13-v1", None), ("r14-profile", "R12", "r14", "acx33-r14-v1", None), ("r2000-m-profile", "R2000", "r2000", "acx33-r2000-v1", 6), ("r2000-mm-xref", "R2000", "r2000", "acx33-r2000-v1", 4))


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True) + "\n"


def write_dxf(doc: object, path: Path) -> None:
    stream = io.StringIO(newline="\n")
    doc.write(stream, fmt="asc")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(doc.encode(stream.getvalue()))


def drawing(version: str, label: str, units: int | None) -> object:
    import ezdxf

    ezdxf.options.write_fixed_meta_data_for_testing = True
    doc = ezdxf.new(version, units=units or 0)
    doc.header["$TDCREATE"] = 2461234.5
    doc.header["$TDUPDATE"] = 2461234.5
    model = doc.modelspace()
    model.add_line((0, 0, 0), (4, 2, 3))
    model.add_point((1, 2, 4))
    model.add_3dface([(0, 0, 0), (2, 0, 1), (2, 2, 2), (0, 2, 1)])
    model.add_text(label, dxfattribs={"insert": (0, 5), "height": 0.4})
    if version != "R12":
        doc.appids.add("AECCTX_EVIDENCE")
        line = model.add_line((0, 7, 0), (3, 7, 0))
        line.set_xdata("AECCTX_EVIDENCE", [(1000, "refs/child.dwg")])
    return doc


def encode(source: Path, output: Path, target: str) -> None:
    inspected = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", IMAGE], capture_output=True, text=True, check=True).stdout.strip()
    if inspected != IMAGE_ID:
        raise RuntimeError(f"AECCTX_DWG_IMAGE_DIGEST_MISMATCH: {inspected}")
    with tempfile.TemporaryDirectory(prefix="aecctx-dwg-fixture-") as temporary:
        workspace = Path(temporary)
        workspace.chmod(0o777)
        (workspace / "input.dxf").write_bytes(source.read_bytes())
        (workspace / "input.dxf").chmod(0o444)
        process = subprocess.run(["docker", "run", "--rm", "--network=none", "--user=65532:65532", "-v", f"{workspace}:/work", "-w", "/work", IMAGE, "dxf2dwg", "--as", target, "-o", f"/work/{output.name}", "/work/input.dxf"], capture_output=True, text=True, check=False)
        if process.returncode:
            raise RuntimeError(f"AECCTX_DWG_FIXTURE_ENCODING_FAILED: {target}: {process.stderr[-1000:]}")
        output.write_bytes((workspace / output.name).read_bytes())


def reference(path: Path) -> dict[str, str]:
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def portable_check() -> None:
    corpus_path = ROOT / "conformance/v0.3/dwg-corpus.json"
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    references = [corpus.get(key) for key in ("generator", "profile", "schema", "worker")]
    references.extend(corpus.get("fixtures", []))
    for item in references:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise SystemExit("AECCTX_DWG_V03_REFERENCE_INVALID")
        path = ROOT / str(item["path"])
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"AECCTX_DWG_V03_REFERENCE_MISSING: {path}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise SystemExit(f"AECCTX_DWG_V03_FIXTURE_DRIFT: {path}")


def snapshot(corpus_path: Path) -> tuple[dict[Path, bytes], bytes]:
    return ({path.relative_to(HERE): path.read_bytes() for path in HERE.rglob("*") if path.is_file() and path.name != "generate_fixtures.py"}, corpus_path.read_bytes())


def generate() -> None:
    HERE.mkdir(parents=True, exist_ok=True)
    descriptor = dwg_v03_descriptor()
    (HERE / "descriptor.json").write_text(canonical(descriptor.to_dict()), encoding="utf-8")
    target = DWG_OCI_TARGETS[0]
    runner = ProviderRunner(registry=dwg_v03_registry(repository_root=ROOT), profile=OCIDockerProfile(image=target.image, platform=target.platform, architecture=target.architecture), limits=LIMITS)
    entries = []
    for entry_id, dxf_version, target_version, profile, units in PROFILES:
        source_dxf = HERE / f"{entry_id}.dxf"
        source_dwg = HERE / f"{entry_id}.dwg"
        write_dxf(drawing(dxf_version, entry_id, units), source_dxf)
        encode(source_dxf, source_dwg, target_version)
        configuration = DWG_CONFIGURATIONS[profile]
        source_bytes = source_dwg.read_bytes()
        request = build_provider_request(DWG_PROVIDER_ID, "extract", source_bytes, limits=LIMITS, configuration=configuration)
        request_path = HERE / "requests" / f"{entry_id}.json"
        request_path.parent.mkdir(exist_ok=True)
        request_path.write_text(canonical(request), encoding="utf-8")
        result = runner.run(DWG_PROVIDER_ID, "extract", source_bytes, configuration=configuration)
        if not result.ok:
            raise RuntimeError(f"provider failed for {entry_id}: {result.error}")
        destination = HERE / "outputs" / entry_id
        if destination.exists(): shutil.rmtree(destination)
        for logical, content in result.artifact_bytes.items():
            artifact = destination / logical; artifact.parent.mkdir(parents=True, exist_ok=True); artifact.write_bytes(content)
        response = {"protocol_version": "0.2", "provider_id": DWG_PROVIDER_ID, "request_id": request["request_id"], "ok": result.ok, "events": list(result.events), "artifacts": list(result.artifacts), "diagnostics": list(result.diagnostics), "capability_report": result.capability_report, "resource_usage": result.resource_usage, "attestation": result.attestation}
        (destination / "response.json").write_text(canonical(response), encoding="utf-8")
        entries.append({"action": "extract", "configuration": configuration, "descriptor": "fixtures/v0.3/dwg/descriptor.json", "id": entry_id, "input": f"fixtures/v0.3/dwg/{entry_id}.dwg", "limits": LIMITS.to_dict(), "output_root": f"fixtures/v0.3/dwg/outputs/{entry_id}", "request": f"fixtures/v0.3/dwg/requests/{entry_id}.json", "response": f"fixtures/v0.3/dwg/outputs/{entry_id}/response.json"})
    root_data = (HERE / "r2000-m-profile.dwg").read_bytes(); child_data = (HERE / "r2000-mm-xref.dwg").read_bytes()
    bundle = HERE / "xref-bundle"; (bundle / "refs").mkdir(parents=True, exist_ok=True)
    (bundle / "root.dwg").write_bytes(root_data); (bundle / "refs/child.dwg").write_bytes(child_data)
    manifest = {"version": "0.2", "root": "root.dwg", "entries": [{"path": "root.dwg", "role": "root", "media_type": "image/vnd.dwg", "bytes": len(root_data), "sha256": hashlib.sha256(root_data).hexdigest()}, {"path": "refs/child.dwg", "role": "xref", "media_type": "image/vnd.dwg", "bytes": len(child_data), "sha256": hashlib.sha256(child_data).hexdigest()}]}
    (bundle / "source-bundle.json").write_text(canonical(manifest), encoding="utf-8")
    corpus = {"version": "0.2.0", "entries": entries, "generator": reference(Path(__file__).resolve()), "profile": reference(ROOT / "docs/specs/dwg-v03-profile.md"), "schema": reference(ROOT / "schemas/v0.2/dwg-v03-event.schema.json"), "worker": reference(ROOT / "providers/libredwg/worker.py"), "fixtures": [reference(HERE / f"{entry_id}.dwg") for entry_id, *_rest in PROFILES]}
    (ROOT / "conformance/v0.3/dwg-corpus.json").write_text(canonical(corpus), encoding="utf-8")


def main() -> None:
    if os.environ.get("PYTHONHASHSEED") != "0":
        env = dict(os.environ); env["PYTHONHASHSEED"] = "0"
        os.execve(sys.executable, [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]], env)
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--live-check", action="store_true")
    arguments = parser.parse_args()
    corpus_path = ROOT / "conformance/v0.3/dwg-corpus.json"
    if arguments.check:
        portable_check()
        return
    before = snapshot(corpus_path) if arguments.live_check else None
    generate()
    if before is not None:
        after = snapshot(corpus_path)
        if before != after:
            raise SystemExit("AECCTX_DWG_V03_FIXTURE_DRIFT")


if __name__ == "__main__":
    main()
