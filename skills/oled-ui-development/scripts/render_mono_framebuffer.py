#!/usr/bin/env python3
"""Convert an SSD1306-style page framebuffer to a dependency-free RGB PNG."""

from __future__ import annotations

import argparse
import binascii
import re
import struct
import zlib
from pathlib import Path


def chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)


def decode_input(path: Path, input_format: str) -> bytes:
    if input_format == "bin":
        return path.read_bytes()
    text = path.read_text(encoding="utf-8")
    if input_format == "hex":
        tokens = re.findall(r"(?:0[xX])?([0-9A-Fa-f]{2})", text)
    else:
        tokens = re.findall(r"0[xX]([0-9A-Fa-f]{1,2})", text)
    if not tokens:
        raise ValueError(f"no framebuffer bytes found in {path}")
    return bytes(int(token, 16) for token in tokens)


def render(framebuffer: bytes, width: int, height: int, scale: int, on: tuple[int, int, int], off: tuple[int, int, int]) -> bytes:
    expected = width * ((height + 7) // 8)
    if len(framebuffer) != expected:
        raise ValueError(f"expected {expected} bytes for {width}x{height}, got {len(framebuffer)}")
    rows = bytearray()
    for y in range(height):
        row = bytearray()
        for x in range(width):
            byte = framebuffer[(y // 8) * width + x]
            row.extend((on if byte & (1 << (y % 8)) else off) * scale)
        encoded = b"\x00" + bytes(row)
        for _ in range(scale):
            rows.extend(encoded)
    png_width = width * scale
    png_height = height * scale
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", png_width, png_height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + chunk(b"IEND", b"")
    )


def rgb(value: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
        raise argparse.ArgumentTypeError("color must use #RRGGBB")
    return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--format", choices=("bin", "hex", "c"), default="bin")
    parser.add_argument("--width", type=int, default=128)
    parser.add_argument("--height", type=int, default=32)
    parser.add_argument("--scale", type=int, default=6)
    parser.add_argument("--on", type=rgb, default=rgb("#AEF2FF"))
    parser.add_argument("--off", type=rgb, default=rgb("#02080B"))
    args = parser.parse_args()
    if args.width < 1 or args.height < 1 or args.scale < 1:
        parser.error("width, height, and scale must be positive")
    data = decode_input(args.input, args.format)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(render(data, args.width, args.height, args.scale, args.on, args.off))
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
