#!/usr/bin/env python3
"""Build-receipt and live verification helpers for ACX-24."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

from aecctx.providers import (
    DWG_CONFIGURATION,
    DWG_PROVIDER_ID,
    OCIDockerProfile,
    ProviderExecutionError,
    ProviderLimits,
    ProviderRegistration,
    ProviderRegistry,
    ProviderRunner,
    STEP_IGES_CONFIGURATION,
    STEP_IGES_PROVIDER_ID,
    TESSERACT_OCR_PROVIDER_ID,
    dwg_registry,
    reference_provider_registry,
    resolve_oci_target,
    step_iges_registry,
    tesseract_ocr_registry,
)


ROOT = Path(__file__).resolve().parents[1]
BASE_INDEX = "sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90"
BASE_MANIFESTS = {
    "amd64": "sha256:52df9b1ee71626e0088f7d400d5c6b5f7bb916f8f0c82b474289a4ece6cf3faf",
    "arm64": "sha256:7f622ca8766bccb22f04242ecb6f19f770b2f08827dc4b8c707de5e78a6da7ab",
}


class ProviderCase:
    def __init__(
        self,
        provider_id: str,
        registry: Callable[..., ProviderRegistry],
        source: str,
        configuration: dict[str, Any],
        context: str,
        license_spdx: str,
        limits: ProviderLimits,
    ) -> None:
        self.provider_id = provider_id
        self.registry = registry
        self.source = ROOT / source
        self.configuration = configuration
        self.context = ROOT / context
        self.license_spdx = license_spdx
        self.limits = limits


CASES = {
    "tesseract": ProviderCase(
        TESSERACT_OCR_PROVIDER_ID,
        tesseract_ocr_registry,
        "fixtures/v0.2/inference/ocr-aecctx-15.pgm",
        {"dpi": 300, "language": "eng", "minimum_confidence": 0, "page_segmentation_mode": 6},
        "providers/tesseract-ocr",
        "Apache-2.0 AND HPND",
        ProviderLimits(
            max_input_bytes=1_000_000,
            max_output_bytes=1_000_000,
            max_records=100,
            max_files=10,
            max_recursion_depth=8,
            max_decompression_ratio=20.0,
            wall_time_seconds=30,
            cpu_seconds=30,
            max_memory_bytes=512 * 1024 * 1024,
            max_open_files=32,
        ),
    ),
    "step-iges": ProviderCase(
        STEP_IGES_PROVIDER_ID,
        step_iges_registry,
        "fixtures/v0.2/step-iges/ap214-assembly.step",
        STEP_IGES_CONFIGURATION,
        "providers/step-iges-ocp",
        "Apache-2.0 AND LGPL-2.1-only WITH OCCT-exception",
        ProviderLimits(max_input_bytes=2_000_000, max_output_bytes=20_000_000, max_records=2_000, wall_time_seconds=60),
    ),
    "dwg": ProviderCase(
        DWG_PROVIDER_ID,
        dwg_registry,
        "fixtures/v0.2/dwg/r2000-profile.dwg",
        DWG_CONFIGURATION,
        "providers/libredwg",
        "GPL-3.0-or-later",
        ProviderLimits(max_input_bytes=2_000_000, max_output_bytes=30_000_000, max_records=2_000, wall_time_seconds=60),
    ),
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def docker() -> Path:
    executable = shutil.which("docker")
    if executable is None:
        raise SystemExit("AECCTX_PROVIDER_PROFILE_UNAVAILABLE: Docker is required")
    return Path(executable)


def docker_run(image: str, command: tuple[str, ...]) -> str:
    result = subprocess.run(
        [str(docker()), "run", "--rm", "--network=none", "--read-only", "--user=65532:65532", image, *command],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise SystemExit(f"AECCTX_PROVIDER_RUNTIME_INSPECTION_FAILED: {result.stderr.strip()}")
    return result.stdout


def package_lock(provider: str, image: str) -> list[str]:
    if provider == "step-iges":
        command = (
            "sh",
            "-c",
            "dpkg-query -W -f='${Package}=${Version}\\n' | LC_ALL=C sort; python3 -m pip freeze --all | LC_ALL=C sort",
        )
    elif provider == "dwg":
        command = ("sh", "-c", "dpkg-query -W -f='${Package}=${Version}\\n' | LC_ALL=C sort; dwgread --version")
    else:
        command = (
            "sh",
            "-c",
            "dpkg-query -W -f='${Package}=${Version}\\n' | LC_ALL=C sort; python3 -m pip freeze --all | LC_ALL=C sort; tesseract --version 2>&1 | head -1",
        )
    return [line for line in docker_run(image, command).splitlines() if line]


def receipt(provider: str, architecture: str) -> dict[str, Any]:
    case = CASES[provider]
    registration = case.registry(repository_root=ROOT).resolve(case.provider_id)
    target = resolve_oci_target(registration, "linux", architecture)
    inspect = subprocess.run(
        [str(docker()), "image", "inspect", "--format", "{{.Id}} {{.Os}} {{.Architecture}}", target.image],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if inspect.returncode != 0:
        raise SystemExit("AECCTX_PROVIDER_PROFILE_UNAVAILABLE: reviewed image is absent; images are never pulled implicitly")
    image_id, image_os, image_arch = inspect.stdout.strip().split()
    if (image_id, image_os, image_arch) != (target.image_id, target.platform, target.architecture):
        raise SystemExit("AECCTX_PROVIDER_IMAGE_DIGEST_MISMATCH: installed image does not match registration")
    inputs: dict[str, str] = {
        "Dockerfile": sha256_file(case.context / "Dockerfile"),
        "worker.py": sha256_file(case.context / "worker.py"),
    }
    requirements = case.context / "requirements.txt"
    if requirements.is_file():
        inputs["requirements.txt"] = sha256_file(requirements)
    lock = package_lock(provider, target.image)
    return {
        "architecture": architecture,
        "base_image_index": BASE_INDEX,
        "base_platform_manifest": BASE_MANIFESTS[architecture],
        "build_network": "dependency-fetch-only",
        "image": target.image,
        "image_id": target.image_id,
        "inputs": inputs,
        "license_spdx": case.license_spdx,
        "no_push": True,
        "package_lock": lock,
        "package_lock_sha256": sha256_bytes("\n".join(lock).encode("utf-8")),
        "platform": "linux",
        "profile": "https://aecctx.dev/provider-oci-multiarch/v0.3",
        "provider_id": case.provider_id,
        "provider_version": "0.2.0",
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value) + b"\n")


def semantic_result(result: Any) -> dict[str, Any]:
    return {
        "artifacts": list(result.artifacts),
        "attestation": dict(result.attestation),
        "capability_report": result.capability_report,
        "diagnostics": list(result.diagnostics),
        "error": result.error,
        "events": list(result.events),
        "ok": result.ok,
        "resource_usage": result.resource_usage,
    }


def run_positive(provider: str, architecture: str) -> tuple[dict[str, Any], dict[str, bytes]]:
    case = CASES[provider]
    registry = case.registry(repository_root=ROOT)
    target = resolve_oci_target(registry.resolve(case.provider_id), "linux", architecture)
    result = ProviderRunner(
        registry=registry,
        profile=OCIDockerProfile(
            docker_executable=docker(), image=target.image, platform="linux", architecture=architecture
        ),
        limits=case.limits,
    ).run(case.provider_id, "extract", case.source.read_bytes(), configuration=case.configuration)
    if not result.ok:
        raise SystemExit(f"AECCTX_PROVIDER_MATRIX_POSITIVE_FAILED: {provider}/{architecture}: {result.error}")
    return semantic_result(result), dict(result.artifact_bytes)


def reference_registration(architecture: str) -> tuple[ProviderRegistry, str]:
    base_registry = reference_provider_registry()
    base = base_registry.resolve("org.aecctx.reference-provider")
    tesseract = tesseract_ocr_registry(repository_root=ROOT).resolve(TESSERACT_OCR_PROVIDER_ID)
    target = resolve_oci_target(tesseract, "linux", architecture)
    registration = replace(
        base,
        container_image=None,
        container_image_id=None,
        container_command=("python3", "/provider/worker.py"),
        oci_targets=(target,),
        worker_path=ROOT / "src/aecctx/reference_provider_worker.py",
    )
    registry = ProviderRegistry(allowed_worker_modules={registration.worker_module})
    registry.register(registration)
    return registry, target.image


def run_adversarial(architecture: str) -> dict[str, str]:
    registry, image = reference_registration(architecture)

    def runner(**limits: Any) -> ProviderRunner:
        return ProviderRunner(
            registry=registry,
            profile=OCIDockerProfile(
                docker_executable=docker(), image=image, platform="linux", architecture=architecture
            ),
            limits=ProviderLimits(
                max_input_bytes=20_000,
                max_output_bytes=limits.pop("max_output_bytes", 32_000),
                max_records=10,
                max_memory_bytes=limits.pop("max_memory_bytes", 64 * 1024 * 1024),
                wall_time_seconds=limits.pop("wall_time_seconds", 5),
                **limits,
            ),
        )

    outcomes: dict[str, str] = {}
    for name, configuration, code in (
        ("network", {"network_attempt": True}, "AECCTX_PROVIDER_NETWORK_DENIED"),
        ("filesystem", {"outside_write": True}, "AECCTX_PROVIDER_FILESYSTEM_DENIED"),
        ("process_tree", {"spawn_process": True}, "AECCTX_PROVIDER_PROCESS_DENIED"),
    ):
        result = runner().run("org.aecctx.reference-provider", "extract", b"adversarial", configuration=configuration)
        actual = result.error["code"] if result.error else "missing"
        if actual != code:
            raise SystemExit(f"AECCTX_PROVIDER_MATRIX_ADVERSARIAL_FAILED: {architecture}/{name}: {actual}")
        outcomes[name] = actual
    for name, configuration, expected, limits in (
        ("timeout", {"sleep_seconds": 2}, "AECCTX_PROVIDER_TIMEOUT", {"wall_time_seconds": 0.1}),
        ("memory", {"allocate_bytes": 128 * 1024 * 1024}, "AECCTX_PROVIDER_MEMORY_LIMIT_EXCEEDED", {"max_memory_bytes": 32 * 1024 * 1024}),
        ("output", {"output_bytes": 16_000}, "AECCTX_PROVIDER_OUTPUT_LIMIT_EXCEEDED", {"max_output_bytes": 4_096}),
        ("malformed", {"malformed_response": True}, "AECCTX_PROVIDER_PROTOCOL_INVALID", {}),
    ):
        try:
            runner(**limits).run("org.aecctx.reference-provider", "extract", b"adversarial", configuration=configuration)
        except ProviderExecutionError as error:
            if error.code != expected:
                raise SystemExit(f"AECCTX_PROVIDER_MATRIX_ADVERSARIAL_FAILED: {architecture}/{name}: {error.code}") from error
            outcomes[name] = error.code
        else:
            raise SystemExit(f"AECCTX_PROVIDER_MATRIX_ADVERSARIAL_FAILED: {architecture}/{name}: no error")
    return outcomes


def verify(output_root: Path) -> dict[str, Any]:
    executions: list[dict[str, Any]] = []
    for provider in CASES:
        baseline_semantic: dict[str, Any] | None = None
        baseline_artifacts: dict[str, bytes] | None = None
        for architecture in ("arm64", "amd64"):
            semantic, artifacts = run_positive(provider, architecture)
            if baseline_semantic is not None and (semantic != baseline_semantic or artifacts != baseline_artifacts):
                raise SystemExit(f"AECCTX_PROVIDER_MATRIX_EQUIVALENCE_FAILED: {provider}")
            baseline_semantic, baseline_artifacts = semantic, artifacts
            case = CASES[provider]
            registration = case.registry(repository_root=ROOT).resolve(case.provider_id)
            target = resolve_oci_target(registration, "linux", architecture)
            execution = {
                "architecture": architecture,
                "artifact_digests": {path: sha256_bytes(data) for path, data in sorted(artifacts.items())},
                "image_id": target.image_id,
                "platform": "linux",
                "provider_id": case.provider_id,
                "response_semantic_sha256": sha256_bytes(canonical_bytes(semantic)),
                "source_sha256": sha256_file(case.source),
            }
            write_json(output_root / "executions" / f"{provider}-linux-{architecture}.json", execution)
            executions.append(execution)
    adversarial = {architecture: run_adversarial(architecture) for architecture in ("arm64", "amd64")}
    summary = {"adversarial": adversarial, "executions": executions, "ok": True, "profile_version": "0.3.0"}
    write_json(output_root / "verification-summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    receipt_parser = subparsers.add_parser("receipt")
    receipt_parser.add_argument("--provider", choices=sorted(CASES), required=True)
    receipt_parser.add_argument("--architecture", choices=("arm64", "amd64"), required=True)
    receipt_parser.add_argument("--output", type=Path, required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "receipt":
        write_json(args.output, receipt(args.provider, args.architecture))
    else:
        summary = verify(args.output_root)
        print(json.dumps({"executions": len(summary["executions"]), "ok": True}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
