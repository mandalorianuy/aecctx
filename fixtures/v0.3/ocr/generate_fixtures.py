#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
}


def image(lines: list[tuple[int, int, str]], size: tuple[int, int] = (900, 240), scale: int = 4) -> Image.Image:
    value = Image.new("L", size, 255)
    pixels = value.load()
    for x, y, text in lines:
        cursor = x
        for character in text.upper():
            if character == " ":
                cursor += 4 * scale
                continue
            pattern = GLYPHS[character]
            for row, bits in enumerate(pattern):
                for column, bit in enumerate(bits):
                    if bit == "1":
                        for dy in range(scale):
                            for dx in range(scale):
                                pixels[cursor + column * scale + dx, y + row * scale + dy] = 0
            cursor += 7 * scale
    return value


def pdf_bytes(raster: Image.Image) -> bytes:
    content = f"q {raster.width} 0 0 {raster.height} 0 0 cm /Im0 Do Q\n".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {raster.width} {raster.height}] /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>".encode("ascii"),
        f"<< /Type /XObject /Subtype /Image /Width {raster.width} /Height {raster.height} /ColorSpace /DeviceGray /BitsPerComponent 8 /Length {len(raster.tobytes())} >>\nstream\n".encode("ascii") + raster.tobytes() + b"\nendstream",
        f"<< /Length {len(content)} >>\nstream\n".encode("ascii") + content + b"endstream",
    ]
    result = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"); offsets = [0]
    for index, body in enumerate(objects, 1):
        offsets.append(len(result)); result.extend(f"{index} 0 obj\n".encode("ascii") + body + b"\nendobj\n")
    xref = len(result); result.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]: result.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    result.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(result)


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
