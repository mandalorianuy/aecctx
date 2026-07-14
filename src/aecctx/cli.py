from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .context import render_context
from .diff import diff_packages
from .ingest import ingest_opaque
from .query import QuerySyntaxError, query_package
from .validation import ValidationResult, validate_package


class IngestVersionError(ValueError):
    code = "AECCTX_INGEST_VERSION_UNSUPPORTED"


def _envelope(ok: bool, data: Any, diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    return {"data": data, "diagnostics": diagnostics, "ok": ok}


def _emit_result(result: ValidationResult, *, as_json: bool, info: bool = False) -> int:
    diagnostics = [item.to_dict() for item in result.diagnostics]
    if info and result.manifest is not None:
        data = {
            key: result.manifest[key]
            for key in ("aecctx_version", "package_id", "logical_digest", "package_form", "source_ids", "capabilities", "loss_summary")
        }
    else:
        data = {"package_id": result.package_id, "valid": result.valid}
    if as_json:
        print(json.dumps(_envelope(result.valid, data, diagnostics), sort_keys=True, separators=(",", ":")))
    elif result.valid:
        print(f"AECCTX package valid: {result.package_id}")
    else:
        for diagnostic in result.diagnostics:
            location = f" [{diagnostic.path}]" if diagnostic.path else ""
            print(f"{diagnostic.code}{location}: {diagnostic.message}", file=sys.stderr)
    return 0 if result.valid else 2


def _emit_signing_error(error: Exception, *, as_json: bool) -> int:
    from .signing import SigningError

    code = error.code if isinstance(error, SigningError) else "AECCTX_SIGNING_OPERATION_FAILED"
    message = str(error) if isinstance(error, SigningError) else "signing operation failed safely"
    diagnostic = {"code": code, "message": message, "severity": "error"}
    if as_json:
        print(json.dumps(_envelope(False, None, [diagnostic]), sort_keys=True, separators=(",", ":")))
    else:
        print(f"{code}: {message}", file=sys.stderr)
    return 2


def _write_new_sidecar(path: str | Path, data: bytes) -> None:
    from ._atomic import AtomicCreateError, atomic_create
    from .signing import SigningError

    try:
        atomic_create(path, data)
    except AtomicCreateError as error:
        if error.reason == "exists":
            raise SigningError("AECCTX_SIGNING_OUTPUT_EXISTS", "signing output already exists") from error
        raise SigningError("AECCTX_SIGNING_OUTPUT_FAILED", "signing output could not be published safely") from error


def _emit_gate_error(error: Exception, *, as_json: bool) -> int:
    from .gate import GateError, canonical_gate_json

    code = error.code if isinstance(error, GateError) else "AECCTX_GATE_OPERATION_FAILED"
    message = str(error) if isinstance(error, GateError) else "gate operation failed safely"
    diagnostic = {"code": code, "message": message, "severity": "error"}
    if as_json:
        sys.stdout.buffer.write(canonical_gate_json(_envelope(False, None, [diagnostic])))
    else:
        print(f"{code}: {message}", file=sys.stderr)
    return 2


def _preflight_gate_outputs(arguments: argparse.Namespace) -> tuple[tuple[Path, str], ...]:
    from .gate import GateError

    requested = tuple(
        (Path(value), kind)
        for value, kind in (
            (arguments.output, "result"),
            (arguments.markdown, "markdown"),
            (arguments.ci_annotations, "ci"),
        )
        if value is not None
    )
    outputs = tuple(path.resolve(strict=False) for path, _kind in requested)
    inputs = tuple(
        Path(value).resolve(strict=False)
        for value in (
            arguments.package,
            arguments.policy,
            arguments.baseline,
            arguments.ids,
            arguments.ifc_source,
        )
        if value is not None
    )
    if len(set(outputs)) != len(outputs) or any(output in inputs for output in outputs):
        raise GateError("AECCTX_GATE_OUTPUT_CONFLICT", "gate inputs and outputs must be distinct")
    if any(path.exists() or path.is_symlink() for path, _kind in requested):
        raise GateError("AECCTX_GATE_OUTPUT_EXISTS", "gate output already exists")
    return requested


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aecctx")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "info"):
        command_parser = subparsers.add_parser(command)
        command_parser.add_argument("package")
        command_parser.add_argument("--json", action="store_true", dest="as_json")
    version = subparsers.add_parser("version")
    version.add_argument("--json", action="store_true", dest="as_json")
    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("source")
    ingest.add_argument("--output", required=True)
    ingest.add_argument("--form", choices=("directory", "zip"), default="directory")
    ingest.add_argument("--embedding-policy", choices=("external", "embedded", "redacted"), default="external")
    ingest.add_argument("--adapter", choices=("auto", "opaque", "ifc", "dxf", "dwg", "pdf", "image", "geometry", "step-iges"), default="auto")
    ingest.add_argument("--aecctx-version", choices=("0.1.0", "0.2.0"), default="0.1.0")
    ingest.add_argument("--inference-replay", help="validated bounded OCR provider replay corpus (AECCTX v0.2 PDF/image package profile)")
    ingest.add_argument("--inference-entry", help="entry ID inside --inference-replay")
    ingest.add_argument("--vision-replay", help="validated bounded vision provider replay corpus (AECCTX v0.2 PDF/image package profile)")
    ingest.add_argument("--vision-entry", help="entry ID inside --vision-replay")
    ingest.add_argument("--provider-replay", help="validated STEP/IGES or DWG provider replay corpus (v0.2 only)")
    ingest.add_argument("--provider-entry", help="entry ID inside --provider-replay")
    ingest.add_argument("--mesh-coordinate-profile", help="manual mesh coordinate profile JSON (v0.2 geometry only)")
    ingest.add_argument("--mesh-crs-profile", help="governed offline CRS registry JSON (v0.2 geometry only)")
    ingest.add_argument("--created-at")
    ingest.add_argument("--json", action="store_true", dest="as_json")
    query = subparsers.add_parser("query")
    query.add_argument("package")
    query.add_argument("expression")
    query.add_argument("--json", action="store_true", dest="as_json")
    diff = subparsers.add_parser("diff")
    diff.add_argument("before")
    diff.add_argument("after")
    diff.add_argument("--json", action="store_true", dest="as_json")
    context = subparsers.add_parser("context")
    context.add_argument("package")
    context.add_argument("--profile", choices=("agent", "audit", "compact"), default="agent")
    context.add_argument("--token-budget", type=int, default=40_000)
    context.add_argument("--chunk-token-budget", type=int, default=4_000)
    context.add_argument("--json", action="store_true", dest="as_json")
    sign = subparsers.add_parser("sign")
    sign.add_argument("package")
    sign.add_argument("--private-key", required=True)
    sign.add_argument("--kid", required=True)
    sign.add_argument("--output", required=True)
    sign.add_argument("--password-file")
    sign.add_argument("--append-to")
    sign.add_argument("--json", action="store_true", dest="as_json")
    verify_signatures = subparsers.add_parser("verify-signatures")
    verify_signatures.add_argument("package")
    verify_signatures.add_argument("--signature-bundle")
    verify_signatures.add_argument("--key-registry", required=True)
    verify_signatures.add_argument("--trust-policy")
    verify_signatures.add_argument("--json", action="store_true", dest="as_json")
    gate = subparsers.add_parser("gate")
    gate.add_argument("package")
    gate.add_argument("--policy", required=True)
    gate.add_argument("--baseline")
    gate.add_argument("--ids")
    gate.add_argument("--ifc-source")
    gate.add_argument("--output")
    gate.add_argument("--markdown")
    gate.add_argument("--ci-annotations")
    gate.add_argument("--json", action="store_true", dest="as_json")
    crs_validate = subparsers.add_parser("crs-validate")
    crs_validate.add_argument("registry")
    crs_validate.add_argument("identifier")
    crs_validate.add_argument("--require-current", action="store_true")
    crs_validate.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    if arguments.command == "version":
        if arguments.as_json:
            print(json.dumps(_envelope(True, {"version": __version__}, []), sort_keys=True, separators=(",", ":")))
        else:
            print(__version__)
        return 0
    if arguments.command == "crs-validate":
        from .crs import CRSProfileError, load_crs_registry, validate_crs_identifier

        try:
            registry_path = Path(arguments.registry)
            if not registry_path.is_file() or registry_path.is_symlink():
                raise CRSProfileError("AECCTX_CRS_REGISTRY_INVALID", "CRS registry must be a regular file")
            if registry_path.stat().st_size > 1024 * 1024:
                raise CRSProfileError("AECCTX_CRS_REGISTRY_INVALID", "CRS registry exceeds 1 MiB")
            document = json.loads(registry_path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise CRSProfileError("AECCTX_CRS_REGISTRY_INVALID", "CRS registry must contain a JSON object")
            registry = load_crs_registry(document)
            record = validate_crs_identifier(registry, arguments.identifier, require_current=arguments.require_current)
            data = {
                **record.to_dict(),
                "database_sha256": registry.database_sha256,
                "profile_id": registry.profile_id,
                "registry_digest": registry.registry_digest,
            }
            if arguments.as_json:
                print(json.dumps(_envelope(True, data, []), sort_keys=True, separators=(",", ":")))
            else:
                print(f"AECCTX CRS valid: {record.identifier} ({record.crs_type})")
            return 0
        except (CRSProfileError, OSError, UnicodeError, json.JSONDecodeError) as error:
            code = getattr(error, "code", "AECCTX_CRS_REGISTRY_INVALID")
            diagnostic = {"code": code, "message": str(error), "severity": "error"}
            if arguments.as_json:
                print(json.dumps(_envelope(False, None, [diagnostic]), sort_keys=True, separators=(",", ":")))
            else:
                print(f"{code}: {error}", file=sys.stderr)
            return 2
    if arguments.command == "gate":
        from ._atomic import AtomicCreateError, atomic_create_many
        from .gate import (
            GateError,
            GateLimits,
            canonical_gate_json,
            evaluate_gate,
            load_gate_policy,
            read_gate_document,
            render_ci_annotations,
            render_gate_markdown,
        )

        limits = GateLimits()
        try:
            requested = _preflight_gate_outputs(arguments)
            policy = load_gate_policy(
                read_gate_document(
                    arguments.policy,
                    maximum_bytes=limits.max_policy_bytes,
                    label="gate policy",
                ),
                limits=limits,
            )
            result = evaluate_gate(
                arguments.package,
                policy,
                baseline_package=arguments.baseline,
                ids_document=arguments.ids,
                ifc_source=arguments.ifc_source,
                limits=limits,
            )
            output_data = {
                "result": result.canonical_bytes(),
                "markdown": render_gate_markdown(result),
                "ci": render_ci_annotations(result),
            }
            atomic_create_many(tuple((path, output_data[kind]) for path, kind in requested))
        except AtomicCreateError as error:
            code = "AECCTX_GATE_OUTPUT_EXISTS" if error.reason == "exists" else "AECCTX_GATE_OUTPUT_FAILED"
            return _emit_gate_error(GateError(code, "gate output could not be published safely"), as_json=arguments.as_json)
        except (GateError, OSError, TypeError, ValueError) as error:
            return _emit_gate_error(error, as_json=arguments.as_json)

        data = result.to_dict()
        diagnostics = [item.to_dict() for item in result.diagnostics]
        if arguments.as_json:
            sys.stdout.buffer.write(canonical_gate_json(_envelope(True, data, diagnostics)))
        else:
            print(
                f"AECCTX gate outcome={result.outcome} exit={result.exit_code}; "
                "projection only; canonical GateResult is authority"
            )
        return result.exit_code
    if arguments.command == "sign":
        from ._signing_io import read_bounded_regular_file
        from .signing import SigningError, SigningLimits, append_signature, parse_signature_bundle, sign_package

        limits = SigningLimits()
        try:
            output = Path(arguments.output)
            if arguments.append_to and output.resolve(strict=False) == Path(arguments.append_to).resolve(strict=False):
                raise SigningError("AECCTX_SIGNING_OUTPUT_CONFLICT", "append input and output must be distinct")
            private_key = read_bounded_regular_file(
                arguments.private_key,
                max_bytes=limits.max_private_key_bytes,
                label="private key",
            )
            password = None
            if arguments.password_file:
                password = read_bounded_regular_file(
                    arguments.password_file,
                    max_bytes=limits.max_password_bytes,
                    label="password",
                )
                if password.endswith(b"\n"):
                    password = password[:-1]
            if arguments.append_to:
                bundle_bytes = read_bounded_regular_file(
                    arguments.append_to,
                    max_bytes=limits.max_document_bytes,
                    label="signature bundle",
                )
                bundle = append_signature(
                    arguments.package,
                    parse_signature_bundle(bundle_bytes, limits=limits),
                    private_key_pem=private_key,
                    kid=arguments.kid,
                    password=password,
                    limits=limits,
                )
            else:
                bundle = sign_package(
                    arguments.package,
                    private_key_pem=private_key,
                    kid=arguments.kid,
                    password=password,
                    limits=limits,
                )
            _write_new_sidecar(output, bundle.to_bytes())
        except (OSError, SigningError, ValueError) as error:
            return _emit_signing_error(error, as_json=arguments.as_json)
        data = {"kids": [entry.kid for entry in bundle.signatures], "signature_count": len(bundle.signatures)}
        if arguments.as_json:
            print(json.dumps(_envelope(True, data, []), sort_keys=True, separators=(",", ":")))
        else:
            print(f"AECCTX signature bundle created: {len(bundle.signatures)} signature(s)")
        return 0
    if arguments.command == "verify-signatures":
        from ._signing_io import read_bounded_regular_file
        from .signing import (
            SigningError,
            SigningLimits,
            parse_key_registry,
            parse_signature_bundle,
            parse_trust_policy,
            verify_package_signatures,
        )

        limits = SigningLimits()
        try:
            registry = parse_key_registry(
                read_bounded_regular_file(
                    arguments.key_registry,
                    max_bytes=limits.max_document_bytes,
                    label="key registry",
                ),
                limits=limits,
            )
            bundle = None
            if arguments.signature_bundle:
                bundle = parse_signature_bundle(
                    read_bounded_regular_file(
                        arguments.signature_bundle,
                        max_bytes=limits.max_document_bytes,
                        label="signature bundle",
                    ),
                    limits=limits,
                )
            policy = None
            if arguments.trust_policy:
                policy = parse_trust_policy(
                    read_bounded_regular_file(
                        arguments.trust_policy,
                        max_bytes=limits.max_document_bytes,
                        label="trust policy",
                    ),
                    limits=limits,
                )
            result = verify_package_signatures(
                arguments.package,
                bundle=bundle,
                registry=registry,
                policy=policy,
                limits=limits,
            )
        except (OSError, SigningError, ValueError) as error:
            return _emit_signing_error(error, as_json=arguments.as_json)
        data = result.to_dict()
        diagnostics = [item.to_dict() for item in result.diagnostics]
        if arguments.as_json:
            print(json.dumps(_envelope(True, data, diagnostics), sort_keys=True, separators=(",", ":")))
        elif result.signature_presence == "unsigned":
            print("AECCTX signatures: unsigned")
        else:
            def counts(field: str) -> str:
                values = Counter(getattr(item, field) for item in result.signatures)
                return ",".join(f"{value}:{values[value]}" for value in sorted(values))

            policy_state = "none" if result.policy_satisfied is None else str(result.policy_satisfied).lower()
            print(
                "AECCTX signatures: signed "
                f"signatures={len(result.signatures)} "
                f"cryptographic={counts('cryptographic_status')} "
                f"key={counts('key_status')} "
                f"trust={counts('trust_status')} "
                f"authorization={counts('authorization_status')} "
                f"policy_satisfied={policy_state}"
            )
        return 0 if result.policy_satisfied is True else 1
    if arguments.command == "ingest":
        try:
            adapter = arguments.adapter
            if adapter == "auto":
                from .adapters.ifc import IFCPlugin
                from .adapters.dxf import DXFPlugin
                from .adapters.image import ImagePlugin
                from .adapters.pdf import PDFPlugin
                from .adapters.geometry import GeometryPlugin
                from .step_iges import probe_step_iges
                from .dwg import probe_dwg

                source_candidate = Path(arguments.source)
                if source_candidate.is_dir() and (source_candidate / "source-bundle.json").is_file():
                    adapter = "dxf"
                    prefix = b""
                else:
                    with open(arguments.source, "rb") as source_handle:
                        prefix = source_handle.read(64 * 1024)
                if adapter == "dxf":
                    pass
                elif IFCPlugin().probe(prefix)["confidence"] == 1.0:
                    adapter = "ifc"
                elif probe_step_iges(prefix)["confidence"] == 1.0:
                    adapter = "step-iges"
                elif probe_dwg(prefix)["confidence"] == 1.0:
                    adapter = "dwg"
                elif DXFPlugin().probe(prefix)["confidence"] == 1.0:
                    adapter = "dxf"
                elif PDFPlugin().probe(prefix)["confidence"] == 1.0:
                    adapter = "pdf"
                elif GeometryPlugin().probe(prefix)["confidence"] == 1.0:
                    adapter = "geometry"
                elif ImagePlugin().probe(prefix)["confidence"] == 1.0:
                    adapter = "image"
                else:
                    adapter = "opaque"
            if arguments.aecctx_version == "0.2.0" and adapter not in {"ifc", "dxf", "dwg", "pdf", "image", "geometry", "step-iges"}:
                raise IngestVersionError(f"Adapter {adapter} has no governed AECCTX v0.2 profile")
            coordinate_profile = None
            if arguments.mesh_coordinate_profile:
                if arguments.aecctx_version != "0.2.0" or adapter != "geometry":
                    raise ValueError("--mesh-coordinate-profile is limited to the governed v0.2 geometry profile")
                profile_path = Path(arguments.mesh_coordinate_profile)
                if not profile_path.is_file() or profile_path.is_symlink():
                    raise ValueError("mesh coordinate profile must be a regular file")
                if profile_path.stat().st_size > 1024 * 1024:
                    raise ValueError("mesh coordinate profile exceeds the 1 MiB safety limit")
                coordinate_profile = json.loads(profile_path.read_text(encoding="utf-8"))
                if not isinstance(coordinate_profile, dict):
                    raise ValueError("mesh coordinate profile must contain a JSON object")
            crs_profile = None
            if arguments.mesh_crs_profile:
                if arguments.aecctx_version != "0.2.0" or adapter != "geometry":
                    raise ValueError("--mesh-crs-profile is limited to the governed v0.2 geometry profile")
                if coordinate_profile is not None:
                    raise ValueError("--mesh-coordinate-profile and --mesh-crs-profile are mutually exclusive")
                profile_path = Path(arguments.mesh_crs_profile)
                if not profile_path.is_file() or profile_path.is_symlink():
                    raise ValueError("mesh CRS profile must be a regular file")
                if profile_path.stat().st_size > 1024 * 1024:
                    raise ValueError("mesh CRS profile exceeds the 1 MiB safety limit")
                crs_profile = json.loads(profile_path.read_text(encoding="utf-8"))
                if not isinstance(crs_profile, dict):
                    raise ValueError("mesh CRS profile must contain a JSON object")
            if bool(arguments.inference_replay) != bool(arguments.inference_entry):
                raise ValueError("--inference-replay and --inference-entry must be provided together")
            inference_result = None
            if arguments.inference_replay:
                if arguments.aecctx_version != "0.2.0" or adapter not in {"pdf", "image"}:
                    raise ValueError("inference replay is limited to governed OCR PDF/image profiles in AECCTX v0.2 packages")
                from .providers import load_provider_replay_entry

                inference_result = load_provider_replay_entry(arguments.inference_replay, arguments.inference_entry).result
            if bool(arguments.vision_replay) != bool(arguments.vision_entry):
                raise ValueError("--vision-replay and --vision-entry must be provided together")
            vision_result = None
            if arguments.vision_replay:
                if arguments.aecctx_version != "0.2.0" or adapter not in {"pdf", "image"}:
                    raise ValueError("vision replay is limited to governed PDF/image profiles in AECCTX v0.2 packages")
                from .providers import load_provider_replay_entry
                replay = load_provider_replay_entry(arguments.vision_replay, arguments.vision_entry)
                if replay.descriptor.provider_id != "org.aecctx.vision.raster-rules":
                    raise ValueError("vision replay does not contain the governed ACX-30 provider")
                vision_result = replay.result
            if bool(arguments.provider_replay) != bool(arguments.provider_entry):
                raise ValueError("--provider-replay and --provider-entry must be provided together")
            external_provider_result = None
            if arguments.provider_replay:
                if arguments.aecctx_version != "0.2.0" or adapter not in {"step-iges", "dwg"}:
                    raise ValueError("provider replay is limited to governed v0.2 STEP/IGES or DWG profiles")
                from .providers import load_provider_replay_entry
                replay = load_provider_replay_entry(arguments.provider_replay, arguments.provider_entry)
                expected_provider = "org.aecctx.step-iges.ocp" if adapter == "step-iges" else "org.aecctx.dwg.libredwg"
                if replay.descriptor.provider_id != expected_provider:
                    raise ValueError(f"provider replay does not contain the governed {adapter} provider")
                external_provider_result = replay.result
            if adapter == "ifc":
                from .adapters.ifc import ingest_ifc

                result = ingest_ifc(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                    aecctx_version=arguments.aecctx_version,
                )
            elif adapter == "dxf":
                from .adapters.dxf import ingest_dxf

                result = ingest_dxf(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                    aecctx_version=arguments.aecctx_version,
                )
            elif adapter == "dwg":
                from .adapters.dwg import ingest_dwg

                result = ingest_dwg(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                    aecctx_version=arguments.aecctx_version,
                    provider_result=external_provider_result,
                )
            elif adapter == "pdf":
                from .adapters.pdf import ingest_pdf

                result = ingest_pdf(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                    aecctx_version=arguments.aecctx_version,
                    ocr_result=inference_result,
                    vision_result=vision_result,
                )
            elif adapter == "image":
                from .adapters.image import ingest_image

                result = ingest_image(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                    aecctx_version=arguments.aecctx_version,
                    ocr_result=inference_result,
                    vision_result=vision_result,
                )
            elif adapter == "geometry":
                from .adapters.geometry import ingest_geometry

                result = ingest_geometry(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                    aecctx_version=arguments.aecctx_version,
                    coordinate_profile=coordinate_profile,
                    crs_profile=crs_profile,
                )
            elif adapter == "step-iges":
                from .adapters.step_iges import ingest_step_iges

                result = ingest_step_iges(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                    aecctx_version=arguments.aecctx_version,
                    provider_result=external_provider_result,
                )
            else:
                result = ingest_opaque(
                    arguments.source,
                    arguments.output,
                    created_at=arguments.created_at,
                    embedding_policy=arguments.embedding_policy,
                    package_form=arguments.form,
                )
        except (OSError, ValueError) as error:
            diagnostic = {"code": getattr(error, "code", "AECCTX_INGEST_FAILED"), "message": str(error), "severity": "error"}
            if arguments.as_json:
                print(json.dumps(_envelope(False, None, [diagnostic]), sort_keys=True, separators=(",", ":")))
            else:
                print(f"AECCTX_INGEST_FAILED: {error}", file=sys.stderr)
            return 2
        data = {
            "logical_digest": result.logical_digest,
            "output": str(result.output),
            "package_id": result.package_id,
            "source_id": result.source_id,
            "support": "partial" if adapter in {"ifc", "dxf", "dwg", "pdf", "image", "geometry", "step-iges"} else "opaque",
            "adapter": adapter,
            "aecctx_version": arguments.aecctx_version,
        }
        if arguments.as_json:
            print(json.dumps(_envelope(True, data, []), sort_keys=True, separators=(",", ":")))
        else:
            print(f"AECCTX opaque package created: {result.output}")
        return 0
    if arguments.command == "query":
        try:
            result = query_package(arguments.package, arguments.expression)
        except (QuerySyntaxError, ValueError) as error:
            diagnostic = {"code": getattr(error, "code", "AECCTX_QUERY_FAILED"), "message": str(error), "severity": "error"}
            if arguments.as_json:
                print(json.dumps(_envelope(False, None, [diagnostic]), sort_keys=True, separators=(",", ":")))
            else:
                print(f"{diagnostic['code']}: {error}", file=sys.stderr)
            return 2
        data = result.to_dict()
        if arguments.as_json:
            print(json.dumps(_envelope(True, data, []), sort_keys=True, separators=(",", ":")))
        else:
            for record_id in result.record_ids:
                print(record_id)
        return 0
    if arguments.command == "diff":
        result = diff_packages(arguments.before, arguments.after)
        data = result.to_dict()
        if arguments.as_json:
            print(json.dumps(_envelope(True, data, []), sort_keys=True, separators=(",", ":")))
        else:
            print(json.dumps(data, indent=2, sort_keys=True))
        return 1 if result.semantic_change else 0
    if arguments.command == "context":
        try:
            projection = render_context(
                arguments.package,
                profile=arguments.profile,
                token_budget=arguments.token_budget,
                chunk_token_budget=arguments.chunk_token_budget,
            )
        except ValueError as error:
            diagnostic = {"code": "AECCTX_CONTEXT_FAILED", "message": str(error), "severity": "error"}
            if arguments.as_json:
                print(json.dumps(_envelope(False, None, [diagnostic]), sort_keys=True, separators=(",", ":")))
            else:
                print(f"AECCTX_CONTEXT_FAILED: {error}", file=sys.stderr)
            return 2
        if arguments.as_json:
            print(json.dumps(_envelope(True, projection.to_dict(), []), sort_keys=True, separators=(",", ":")))
        else:
            sys.stdout.buffer.write(projection.files["context/index.md"])
        return 0
    result = validate_package(arguments.package)
    return _emit_result(result, as_json=arguments.as_json, info=arguments.command == "info")
