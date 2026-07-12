from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .errors import Diagnostic
from .package import PackageReadError, PackageReader, SafetyLimits
from .records import CoordinateQualification, ProviderAttestation, RecordModelError, RepresentationFidelity


REQUIRED_ARTIFACTS = (
    "sources/sources.jsonl",
    "evidence/primitives.jsonl",
    "evidence/assertions.jsonl",
    "model/entities.jsonl",
    "model/relations.jsonl",
    "diagnostics/diagnostics.jsonl",
    "context/index.md",
)
SCHEMA_PACKAGES = {"0.1.0": "aecctx.schemas.v0_1", "0.2.0": "aecctx.schemas.v0_2"}
SUPPORTED_REQUIRED_EXTENSIONS: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    diagnostics: tuple[Diagnostic, ...]
    package_id: str | None = None
    manifest: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "package_id": self.package_id,
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
        }


def _load_schema(version: str, name: str) -> dict[str, Any]:
    resource = files(SCHEMA_PACKAGES[version]).joinpath(name)
    return json.loads(resource.read_text(encoding="utf-8"))


def _diagnostic(code: str, message: str, *, path: str | None = None) -> Diagnostic:
    return Diagnostic(code=code, message=message, path=path)


def _read_json(path: Path, logical_path: str, diagnostics: list[Diagnostic]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as error:
        diagnostics.append(_diagnostic("AECCTX_UTF8_INVALID", str(error), path=logical_path))
    except json.JSONDecodeError as error:
        diagnostics.append(
            _diagnostic(
                "AECCTX_JSON_INVALID",
                f"Invalid JSON at line {error.lineno}, column {error.colno}",
                path=logical_path,
            )
        )
    except OSError as error:
        diagnostics.append(_diagnostic("AECCTX_ARTIFACT_UNREADABLE", str(error), path=logical_path))
    return None


def _schema_diagnostics(instance: Any, schema_name: str, path: str, *, version: str) -> list[Diagnostic]:
    validator = Draft202012Validator(_load_schema(version, schema_name), format_checker=FormatChecker())
    diagnostics: list[Diagnostic] = []
    for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.absolute_path)):
        location = "/".join(str(part) for part in error.absolute_path)
        logical_path = f"{path}#/{location}" if location else path
        diagnostics.append(_diagnostic("AECCTX_SCHEMA_INVALID", error.message, path=logical_path))
    return diagnostics


def _validate_artifacts(root: Path, manifest: dict[str, Any], diagnostics: list[Diagnostic]) -> None:
    inventory = manifest.get("artifacts")
    if not isinstance(inventory, list):
        return
    digest_lines: list[bytes] = []
    inventory_paths: set[str] = set()
    for artifact in inventory:
        if not isinstance(artifact, dict) or not isinstance(artifact.get("path"), str):
            continue
        logical_path = artifact["path"]
        if logical_path in inventory_paths:
            diagnostics.append(_diagnostic("AECCTX_ARTIFACT_PATH_DUPLICATE", "Duplicate artifact path", path=logical_path))
            continue
        inventory_paths.add(logical_path)
        artifact_path = root.joinpath(*logical_path.split("/"))
        if not artifact_path.is_file():
            diagnostics.append(_diagnostic("AECCTX_ARTIFACT_MISSING", "Inventoried artifact is missing", path=logical_path))
            continue
        data = artifact_path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if artifact.get("bytes") != len(data):
            diagnostics.append(_diagnostic("AECCTX_ARTIFACT_SIZE_MISMATCH", "Artifact byte size differs from manifest", path=logical_path))
        if artifact.get("sha256") != digest:
            diagnostics.append(_diagnostic("AECCTX_ARTIFACT_HASH_MISMATCH", "Artifact SHA-256 differs from manifest", path=logical_path))
        digest_lines.append(f"{logical_path}\0{digest}\0{len(data)}\n".encode())

    for required in REQUIRED_ARTIFACTS:
        if required not in inventory_paths:
            diagnostics.append(_diagnostic("AECCTX_REQUIRED_ARTIFACT_MISSING", "Required artifact is not inventoried", path=required))

    logical_digest = hashlib.sha256(b"".join(sorted(digest_lines))).hexdigest()
    if manifest.get("logical_digest") != logical_digest:
        diagnostics.append(
            _diagnostic("AECCTX_LOGICAL_DIGEST_MISMATCH", "Package logical digest differs from artifact inventory", path="manifest.json#/logical_digest")
        )


def _validate_records(root: Path, diagnostics: list[Diagnostic], *, version: str) -> None:
    seen: set[str] = set()
    for logical_path in REQUIRED_ARTIFACTS:
        if not logical_path.endswith(".jsonl"):
            continue
        record_path = root.joinpath(*logical_path.split("/"))
        if not record_path.is_file():
            continue
        previous_id = ""
        try:
            lines = record_path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as error:
            diagnostics.append(_diagnostic("AECCTX_JSONL_UNREADABLE", str(error), path=logical_path))
            continue
        for line_number, line in enumerate(lines, 1):
            if not line.strip():
                continue
            line_path = f"{logical_path}:{line_number}"
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                diagnostics.append(_diagnostic("AECCTX_JSONL_INVALID", str(error), path=line_path))
                continue
            diagnostics.extend(_schema_diagnostics(record, "record.schema.json", line_path, version=version))
            if not isinstance(record, dict):
                continue
            if version == "0.2.0":
                coordinate = record.get("coordinate_qualification")
                if isinstance(coordinate, dict):
                    try:
                        CoordinateQualification.from_dict(coordinate)
                    except RecordModelError as error:
                        diagnostics.append(_diagnostic(error.code, str(error), path=line_path))
                fidelity = record.get("representation_fidelity")
                if isinstance(fidelity, dict):
                    try:
                        RepresentationFidelity.from_dict(fidelity)
                    except RecordModelError as error:
                        diagnostics.append(_diagnostic(error.code, str(error), path=line_path))
                attestation = record.get("provider_attestation")
                if isinstance(attestation, dict):
                    try:
                        ProviderAttestation.from_dict(attestation)
                    except RecordModelError as error:
                        diagnostics.append(_diagnostic(error.code, str(error), path=line_path))
            record_id = record.get("record_id")
            if not isinstance(record_id, str) or not record_id:
                continue
            if record_id in seen:
                diagnostics.append(_diagnostic("AECCTX_RECORD_ID_DUPLICATE", "Record ID is not globally unique", path=line_path))
            if previous_id and record_id < previous_id:
                diagnostics.append(_diagnostic("AECCTX_RECORD_ORDER_INVALID", "Records are not sorted by record_id", path=line_path))
            previous_id = record_id
            seen.add(record_id)


def _validate_directory(root: Path) -> ValidationResult:
    diagnostics: list[Diagnostic] = []
    if not root.is_dir():
        diagnostics.append(_diagnostic("AECCTX_PACKAGE_NOT_DIRECTORY", "ACX-01 accepts directory-form packages", path=str(root)))
        return ValidationResult(False, tuple(diagnostics))

    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        diagnostics.append(_diagnostic("AECCTX_MANIFEST_MISSING", "Package root does not contain manifest.json", path="manifest.json"))
        return ValidationResult(False, tuple(diagnostics))

    manifest = _read_json(manifest_path, "manifest.json", diagnostics)
    if not isinstance(manifest, dict):
        return ValidationResult(False, tuple(diagnostics))

    version = manifest.get("aecctx_version")
    if version not in SCHEMA_PACKAGES:
        diagnostics.append(_diagnostic("AECCTX_VERSION_UNSUPPORTED", f"Unsupported AECCTX version: {version!r}", path="manifest.json#/aecctx_version"))
        return ValidationResult(False, tuple(diagnostics), manifest.get("package_id"), manifest)
    diagnostics.extend(_schema_diagnostics(manifest, "manifest.schema.json", "manifest.json", version=version))
    required_extensions = manifest.get("required_extensions", [])
    if isinstance(required_extensions, list):
        for extension in sorted(item for item in required_extensions if isinstance(item, str)):
            if extension not in SUPPORTED_REQUIRED_EXTENSIONS:
                diagnostics.append(
                    _diagnostic(
                        "AECCTX_REQUIRED_EXTENSION_UNSUPPORTED",
                        f"Required extension is not supported: {extension}",
                        path="manifest.json#/required_extensions",
                    )
                )
    _validate_artifacts(root, manifest, diagnostics)
    _validate_records(root, diagnostics, version=version)
    ordered = tuple(sorted(diagnostics, key=lambda item: (item.path or "", item.code, item.message)))
    return ValidationResult(not ordered, ordered, manifest.get("package_id"), manifest)


def validate_package(package_path: str | Path, *, limits: SafetyLimits | None = None) -> ValidationResult:
    path = Path(package_path)
    if path.is_dir():
        return _validate_directory(path)
    if not path.is_file():
        diagnostic = _diagnostic("AECCTX_PACKAGE_NOT_FOUND", "Package path does not exist", path=str(path))
        return ValidationResult(False, (diagnostic,))
    try:
        reader = PackageReader(path, limits=limits)
        with tempfile.TemporaryDirectory(prefix="aecctx-validate-") as temporary:
            reader.extract_to(temporary)
            return _validate_directory(Path(temporary))
    except PackageReadError as error:
        diagnostic = _diagnostic(error.code, str(error), path=str(path))
        return ValidationResult(False, (diagnostic,))
