#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject


ROOT = Path(__file__).resolve().parent
FONT = ImageFont.load_default(size=28)


def image(lines: list[tuple[int, int, str]], size: tuple[int, int] = (640, 240)) -> Image.Image:
    value = Image.new("L", size, 255)
    draw = ImageDraw.Draw(value)
    for x, y, text in lines:
        draw.text((x, y), text, fill=0, font=FONT)
    return value


def pdf_bytes(raster: Image.Image) -> bytes:
    import io
    writer = PdfWriter(); page = writer.add_blank_page(width=640, height=240)
    stream = DecodedStreamObject(); stream.set_data(raster.tobytes()); stream.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"), NameObject("/Width"): NumberObject(raster.width), NameObject("/Height"): NumberObject(raster.height), NameObject("/ColorSpace"): NameObject("/DeviceGray"), NameObject("/BitsPerComponent"): NumberObject(8)})
    reference = writer._add_object(stream); page[NameObject("/Resources")] = DictionaryObject({NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): reference})})
    content = DecodedStreamObject(); content.set_data(f"q {raster.width} 0 0 {raster.height} 0 0 cm /Im0 Do Q\n".encode("ascii")); page[NameObject("/Contents")] = writer._add_object(content)
    output = io.BytesIO(); writer.write(output); return output.getvalue()


def generated() -> dict[str, bytes]:
    values = {
        "eng-block.png": image([(30, 30, "AECCTX BUILDING CONTEXT")]),
        "spa-block.png": image([(30, 30, "contexto espanol verificable")]),
        "por-block.png": image([(30, 30, "contexto portugues verificavel")]),
        "multi-column.png": image([(30, 30, "LEFT ONE"), (30, 80, "LEFT TWO"), (360, 30, "RIGHT ONE"), (360, 80, "RIGHT TWO")]),
        "table.png": image([(30, 30, "A"), (300, 30, "B"), (30, 90, "C"), (300, 90, "D")]),
        "blank.png": image([]),
        "low-confidence.png": image([(30, 30, "faint evidence")]).point(lambda value: 245 if value < 255 else 255),
        "mixed-script.png": image([(30, 30, "AECCTX Cyrillic unsupported")]),
    }
    values["rotated-90.png"] = values["eng-block.png"].transpose(Image.Transpose.ROTATE_90)
    output: dict[str, bytes] = {}
    import io
    for name, value in values.items():
        buffer = io.BytesIO(); value.save(buffer, format="PNG", optimize=False, compress_level=9)
        output[name] = buffer.getvalue()
    output["spa-raster.pdf"] = pdf_bytes(values["spa-block.png"])
    output["corrupt.png"] = b"\x89PNG\r\n\x1a\nAECCTX-corrupt"
    return output


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--check", action="store_true"); args = parser.parse_args()
    drift: list[str] = []
    for name, payload in generated().items():
        path = ROOT / name
        if args.check:
            if not path.is_file() or path.read_bytes() != payload: drift.append(name)
        else: path.write_bytes(payload)
    if drift:
        raise SystemExit("fixture drift: " + ", ".join(drift))
    for name, payload in sorted(generated().items()):
        print(name, hashlib.sha256(payload).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
