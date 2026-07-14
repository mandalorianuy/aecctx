from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).parent
W, H = 128, 96


def pgm(pixels: bytearray) -> bytes:
    return f"P5\n{W} {H}\n255\n".encode() + pixels


def canvas() -> bytearray:
    return bytearray([255] * (W * H))


def setpx(p: bytearray, x: int, y: int) -> None: p[y * W + x] = 0


def rectangle(p: bytearray, x0: int, y0: int, x1: int, y1: int) -> None:
    for x in range(x0, x1 + 1): setpx(p, x, y0); setpx(p, x, y1)
    for y in range(y0, y1 + 1): setpx(p, x0, y); setpx(p, x1, y)


def positive() -> bytes:
    p = canvas(); rectangle(p, 3, 3, 24, 24)
    for x in range(35, 42): setpx(p, x, 12)
    for y in range(9, 16): setpx(p, 38, y)
    for x in range(50, 70): setpx(p, x, 12)
    for y in range(10, 15): setpx(p, 50, y); setpx(p, 69, y)
    for x in (80, 90, 100):
        for y in range(5, 26): setpx(p, x, y)
    for y in (5, 15, 25):
        for x in range(80, 101): setpx(p, x, y)
    return pgm(p)


def cases() -> dict[str, bytes]:
    blank = pgm(canvas())
    occluded = canvas(); rectangle(occluded, 3, 3, 24, 24); occluded[3 * W + 10] = 255
    cropped = canvas();
    for x in range(0, 18): setpx(cropped, x, 2)
    for y in range(2, 20): setpx(cropped, 17, y)
    redacted = canvas()
    for y in range(5, 20):
        for x in range(5, 30): setpx(redacted, x, y)
    prompt = canvas()
    for x in range(3, 30, 2): setpx(prompt, x, 8)
    rotated = canvas()
    for y in range(3, 25): setpx(rotated, 10, y)
    for x in range(8, 13): setpx(rotated, x, 3); setpx(rotated, x, 24)
    return {"positive.pgm": positive(), "blank.pgm": blank, "occluded.pgm": pgm(occluded), "cropped.pgm": pgm(cropped), "redacted.pgm": pgm(redacted), "prompt-like.pgm": pgm(prompt), "rotated.pgm": pgm(rotated), "calibration-conflict.pgm": positive(), "corrupt.pgm": b"P5\n999999 999999\n255\nshort"}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--check", action="store_true"); args = parser.parse_args()
    drift = []
    for name, data in cases().items():
        path = ROOT / name
        if args.check:
            if not path.is_file() or path.read_bytes() != data: drift.append(name)
        else: path.write_bytes(data)
    if drift: raise SystemExit("AECCTX_VISION_FIXTURE_DRIFT: " + ",".join(drift))
    for name, data in sorted(cases().items()): print(name, hashlib.sha256(data).hexdigest())
    return 0


if __name__ == "__main__": raise SystemExit(main())
