"""Generate project-authored ACX-15 raster and PDF fixtures."""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject


ROOT = Path(__file__).parent
GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
}


def raster_text(text: str, *, scale: int = 8) -> Image.Image:
    glyph_width = 5 * scale
    gap = 2 * scale
    width = 2 * gap + sum((glyph_width if char != " " else 3 * scale) + gap for char in text)
    height = 7 * scale + 2 * gap
    image = Image.new("L", (width, height), 255)
    pixels = image.load()
    x = gap
    for char in text:
        if char == " ":
            x += 3 * scale + gap
            continue
        for row, pattern in enumerate(GLYPHS[char]):
            for column, bit in enumerate(pattern):
                if bit == "1":
                    for offset_y in range(scale):
                        for offset_x in range(scale):
                            pixels[x + column * scale + offset_x, gap + row * scale + offset_y] = 0
        x += glyph_width + gap
    return image


def build_pdf(image: Image.Image, path: Path) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=420, height=180)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    image_stream = DecodedStreamObject()
    image_stream.set_data(image.tobytes())
    image_stream.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Image"),
            NameObject("/Width"): NumberObject(image.width),
            NameObject("/Height"): NumberObject(image.height),
            NameObject("/ColorSpace"): NameObject("/DeviceGray"),
            NameObject("/BitsPerComponent"): NumberObject(8),
        }
    )
    font_ref = writer._add_object(font)
    image_ref = writer._add_object(image_stream)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref}),
            NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): image_ref}),
        }
    )
    content = DecodedStreamObject()
    content.set_data(
        (
            "BT /F1 18 Tf 20 145 Td (Native value) Tj ET\n"
            f"q {image.width} 0 0 {image.height} 20 20 cm /Im0 Do Q\n"
        ).encode("ascii")
    )
    page[NameObject("/Contents")] = writer._add_object(content)
    with path.open("wb") as stream:
        writer.write(stream)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    image = raster_text("AECCTX 15")
    pdf_path = ROOT / "native-conflict-raster.pdf"
    build_pdf(image, pdf_path)
    extracted = PdfReader(pdf_path).pages[0].images[0].data
    (ROOT / "ocr-aecctx-15.png").write_bytes(extracted)
    (ROOT / "ocr-aecctx-15.pgm").write_bytes(f"P5\n{image.width} {image.height}\n255\n".encode("ascii") + image.tobytes())


if __name__ == "__main__":
    main()
