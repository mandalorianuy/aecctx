from __future__ import annotations

import ctypes
import hashlib
import io
import json
from pathlib import Path
from typing import Any

from PIL import Image


PROVIDER_ID = "org.aecctx.ocr.tesseract-tsv"
RUNTIME_DIGEST = "sha256:6d52ebcafef0ccdf59f58beccc7483c16a6e160fc94e3c3ea59f3f10c991f492"
REQUIRED_AXES = (
    "cpu", "decompression", "environment", "filesystem", "input_bytes", "memory", "network", "open_files",
    "output_bytes", "process", "process_tree", "records", "recursion", "temporary_storage", "user_permissions", "wall_time",
)
CONFIGURATION_KEYS = {"dpi", "language", "minimum_confidence", "page_segmentation_mode"}


def descriptor() -> dict[str, Any]:
    return {
        "actions": ["extract"],
        "deterministic": True,
        "distribution": "operator-built-oci-image",
        "enforced_axes": {axis: True for axis in REQUIRED_AXES},
        "enforcement_profile": "oci-docker-v1",
        "formats": ["image/png", "image/jpeg", "image/tiff"],
        "license_spdx": "Apache-2.0 AND HPND",
        "network_mode": "disabled",
        "platforms": ["linux-container"],
        "protocol_version": "0.2",
        "provider_id": PROVIDER_ID,
        "provider_version": "0.2.0",
        "runtime_version": "tesseract-5.3.4+capi+eng",
        "runtime_digest": RUNTIME_DIGEST,
    }


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _capability_report(ok: bool) -> dict[str, dict[str, Any]]:
    names = ("identity", "hierarchy", "properties", "relationships", "text", "2d_geometry", "3d_geometry", "materials_styles", "georeferencing", "validation")
    report: dict[str, dict[str, Any]] = {}
    for name in names:
        if name == "text" and ok:
            report[name] = {
                "affected": ["raster-word-evidence"],
                "fallback": "retain source pixels and provider attestation",
                "reason_codes": ["AECCTX_OCR_INFERRED_UNVERIFIED"],
                "support_level": "partial",
            }
        elif name == "validation":
            report[name] = {"affected": [], "fallback": "none", "reason_codes": [], "support_level": "full"}
        else:
            report[name] = {
                "affected": ["raster-input"],
                "fallback": "retain opaque source evidence",
                "reason_codes": ["AECCTX_OCR_CAPABILITY_UNSUPPORTED"],
                "support_level": "unsupported",
            }
    return report


def _configuration(request: dict[str, Any]) -> tuple[int, float]:
    configuration = request.get("configuration")
    if not isinstance(configuration, dict) or set(configuration) != CONFIGURATION_KEYS:
        raise ValueError("AECCTX_OCR_CONFIGURATION_INVALID")
    if configuration.get("language") != "eng" or configuration.get("page_segmentation_mode") != 6:
        raise ValueError("AECCTX_OCR_CONFIGURATION_OUTSIDE_PROFILE")
    dpi = configuration.get("dpi")
    confidence = configuration.get("minimum_confidence")
    if not isinstance(dpi, int) or isinstance(dpi, bool) or not 70 <= dpi <= 1200:
        raise ValueError("AECCTX_OCR_DPI_INVALID")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= float(confidence) <= 100:
        raise ValueError("AECCTX_OCR_CONFIDENCE_INVALID")
    return dpi, float(confidence)


def _ocr_tsv(pixels: bytes, width: int, height: int, dpi: int) -> str:
    library = ctypes.CDLL("libtesseract.so.5")
    library.TessBaseAPICreate.restype = ctypes.c_void_p
    library.TessBaseAPIInit3.argtypes = (ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p)
    library.TessBaseAPISetPageSegMode.argtypes = (ctypes.c_void_p, ctypes.c_int)
    library.TessBaseAPISetImage.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int)
    library.TessBaseAPISetSourceResolution.argtypes = (ctypes.c_void_p, ctypes.c_int)
    library.TessBaseAPIRecognize.argtypes = (ctypes.c_void_p, ctypes.c_void_p)
    library.TessBaseAPIGetTsvText.argtypes = (ctypes.c_void_p, ctypes.c_int)
    library.TessBaseAPIGetTsvText.restype = ctypes.c_void_p
    library.TessDeleteText.argtypes = (ctypes.c_void_p,)
    library.TessBaseAPIEnd.argtypes = (ctypes.c_void_p,)
    library.TessBaseAPIDelete.argtypes = (ctypes.c_void_p,)
    handle = library.TessBaseAPICreate()
    if not handle:
        raise RuntimeError("AECCTX_OCR_ENGINE_CREATE_FAILED")
    text_pointer: int | None = None
    buffer = ctypes.create_string_buffer(pixels)
    try:
        if library.TessBaseAPIInit3(handle, None, b"eng") != 0:
            raise RuntimeError("AECCTX_OCR_ENGINE_INIT_FAILED")
        library.TessBaseAPISetPageSegMode(handle, 6)
        library.TessBaseAPISetImage(handle, buffer, width, height, 1, width)
        library.TessBaseAPISetSourceResolution(handle, dpi)
        if library.TessBaseAPIRecognize(handle, None) != 0:
            raise RuntimeError("AECCTX_OCR_RECOGNITION_FAILED")
        text_pointer = library.TessBaseAPIGetTsvText(handle, 0)
        if not text_pointer:
            raise RuntimeError("AECCTX_OCR_TSV_FAILED")
        return ctypes.string_at(text_pointer).decode("utf-8", errors="strict")
    finally:
        if text_pointer:
            library.TessDeleteText(text_pointer)
        library.TessBaseAPIEnd(handle)
        library.TessBaseAPIDelete(handle)


def _words(tsv: str, minimum_confidence: float, width: int, height: int) -> list[dict[str, Any]]:
    rows = tsv.splitlines()
    if not rows:
        raise ValueError("AECCTX_OCR_TSV_SCHEMA_INVALID")
    header = ["level", "page_num", "block_num", "par_num", "line_num", "word_num", "left", "top", "width", "height", "conf", "text"]
    if rows[0].split("\t") == header:
        rows = rows[1:]
    words: list[dict[str, Any]] = []
    for row in rows:
        fields = row.split("\t", 11)
        if len(fields) != 12 or fields[0] != "5":
            continue
        left, top, box_width, box_height = (int(fields[index]) for index in range(6, 10))
        confidence = float(fields[10])
        text = fields[11]
        if not text or confidence < minimum_confidence:
            continue
        if left < 0 or top < 0 or box_width < 1 or box_height < 1 or left + box_width > width or top + box_height > height:
            raise ValueError("AECCTX_OCR_WORD_BOUNDS_INVALID")
        words.append({
            "bbox": [left, top, box_width, box_height],
            "confidence": round(confidence, 6),
            "language": "eng",
            "reading_order": len(words),
            "text": text,
        })
    return words


def main() -> int:
    workspace = Path.cwd()
    response_path = workspace / "output" / "response.json"
    request = json.loads((workspace / "request.json").read_text(encoding="utf-8"))
    described = descriptor()
    events: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    error: dict[str, str] | None = None
    ok = True
    width = height = 0
    try:
        if request.get("provider_id") != PROVIDER_ID or request.get("action") != "extract":
            raise ValueError("AECCTX_OCR_REQUEST_OUTSIDE_PROFILE")
        dpi, minimum_confidence = _configuration(request)
        input_path = workspace / request["input"]["path"]
        input_bytes = input_path.read_bytes()
        if hashlib.sha256(input_bytes).hexdigest() != request["input"]["sha256"]:
            raise ValueError("AECCTX_OCR_INPUT_HASH_MISMATCH")
        Image.MAX_IMAGE_PIXELS = 100_000_000
        with Image.open(io.BytesIO(input_bytes)) as image:
            image.verify()
        with Image.open(io.BytesIO(input_bytes)) as image:
            grayscale = image.convert("L")
            width, height = grayscale.size
            pixels = grayscale.tobytes()
        accepted = _words(_ocr_tsv(pixels, width, height, dpi), minimum_confidence, width, height)
        events.append({
            "event_type": "primitive",
            "payload": {
                "height": height,
                "language": "eng",
                "page_segmentation_mode": 6,
                "schema": "aecctx.ocr.words.v1",
                "width": width,
                "words": accepted,
            },
            "sequence": 0,
            "source_locator": f"sha256:{request['input']['sha256']}",
        })
    except Exception as caught:
        ok = False
        code = str(caught) if str(caught).startswith("AECCTX_") else "AECCTX_OCR_PROVIDER_FAILED"
        error = {"code": code, "message": f"{type(caught).__name__}: OCR extraction failed"}
        diagnostics.append({"code": code, "severity": "error"})
    response: dict[str, Any] = {
        "artifacts": [],
        "attestation": {
            "descriptor_digest": _digest(described),
            "deterministic": True,
            "enforcement_profile": "oci-docker-v1",
            "network_mode": "disabled",
            "provider_id": PROVIDER_ID,
            "provider_version": "0.2.0",
            "request_digest": _digest(request),
            "response_payload_digest": "0" * 64,
            "runtime_digest": RUNTIME_DIGEST,
            "runtime_version": "tesseract-5.3.4+capi+eng",
        },
        "capability_report": _capability_report(ok),
        "diagnostics": diagnostics,
        "events": events,
        "ok": ok,
        "protocol_version": "0.2",
        "provider_id": PROVIDER_ID,
        "request_id": request["request_id"],
        "resource_usage": {"artifacts": 0, "events": len(events), "height": height, "width": width},
    }
    if error is not None:
        response["error"] = error
    response["attestation"]["response_payload_digest"] = _digest({key: value for key, value in response.items() if key != "attestation"})
    response_path.write_text(_canonical(response).decode("utf-8"), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
