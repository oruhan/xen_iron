#!/usr/bin/env python3
"""Render IronOS 128x32 SSD1306 frames as dependency-free PNG previews."""

from __future__ import annotations

import argparse
import binascii
import re
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path


WIDTH = 128
HEIGHT = 32
FRAME_BYTES = WIDTH * HEIGHT // 8
DEFAULT_SCALE = 6
OFF_COLOR = (2, 8, 11)
ON_COLOR = (174, 242, 255)
def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)


def write_png(path: Path, pixels: list[list[bool]], scale: int = DEFAULT_SCALE) -> None:
    """Write a nearest-neighbour RGB PNG using only the Python standard library."""
    if scale < 1:
        raise ValueError("scale must be at least 1")
    source_height = len(pixels)
    source_width = len(pixels[0]) if pixels else 0
    rows = bytearray()
    for source_row in pixels:
        row = bytearray()
        for is_on in source_row:
            row.extend((ON_COLOR if is_on else OFF_COLOR) * scale)
        encoded_row = b"\x00" + bytes(row)
        for _ in range(scale):
            rows.extend(encoded_row)
    width = source_width * scale
    height = source_height * scale
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += _png_chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
    png += _png_chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def framebuffer_to_pixels(framebuffer: bytes, width: int = WIDTH, height: int = HEIGHT) -> list[list[bool]]:
    expected = width * ((height + 7) // 8)
    if len(framebuffer) != expected:
        raise ValueError(f"expected {expected} framebuffer bytes, got {len(framebuffer)}")
    return [
        [bool(framebuffer[(y // 8) * width + x] & (1 << (y % 8))) for x in range(width)]
        for y in range(height)
    ]


def _extract_array(source: str, name: str) -> str:
    match = re.search(rf"const\s+uint8_t\s+{re.escape(name)}\[\]\s*=\s*\{{(.*?)\}};", source, re.DOTALL)
    if not match:
        raise ValueError(f"C array {name!r} was not found")
    return match.group(1)


def parse_c_array(path: Path, name: str) -> bytes:
    body = _extract_array(path.read_text(encoding="utf-8"), name)
    body = re.sub(r"/\*.*?\*/", "", body, flags=re.DOTALL)
    body = re.sub(r"//.*", "", body)
    return bytes(int(value, 16) for value in re.findall(r"0[xX]([0-9A-Fa-f]+)", body))


def parse_font(path: Path, name: str, glyph_size: int) -> tuple[list[bytes], dict[str, int]]:
    body = _extract_array(path.read_text(encoding="utf-8"), name)
    values: list[int] = []
    char_to_index: dict[str, int] = {}
    for line in body.splitlines():
        data = re.findall(r"0[xX]([0-9A-Fa-f]+)", line.split("//", 1)[0])
        if not data:
            continue
        glyph_index = len(values) // glyph_size
        values.extend(int(value, 16) for value in data)
        comment = re.search(r"//\s*0x[0-9A-Fa-f]+\s*->\s*(.)", line)
        if comment:
            char_to_index.setdefault(comment.group(1), glyph_index)
    if len(values) % glyph_size:
        raise ValueError(f"{name} contains a partial glyph")
    glyphs = [bytes(values[offset : offset + glyph_size]) for offset in range(0, len(values), glyph_size)]
    return glyphs, char_to_index


@dataclass(frozen=True)
class FontAssets:
    large: list[bytes]
    large_chars: dict[str, int]
    small: list[bytes]
    small_chars: dict[str, int]
    extras: bytes
    button_a: bytes
    button_b: bytes

    @classmethod
    def load(cls, translation: Path, font_header: Path) -> "FontAssets":
        large, large_chars = parse_font(translation, "USER_FONT_12", 24)
        small, small_chars = parse_font(translation, "USER_FONT_6x8", 6)
        return cls(
            large=large,
            large_chars=large_chars,
            small=small,
            small_chars=small_chars,
            extras=parse_c_array(font_header, "ExtraFontChars"),
            button_a=parse_c_array(font_header, "buttonA"),
            button_b=parse_c_array(font_header, "buttonB"),
        )


class Canvas:
    def __init__(self, width: int = WIDTH, height: int = HEIGHT) -> None:
        self.width = width
        self.height = height
        self.clipped_writes = 0
        self.pixels = [[False for _ in range(width)] for _ in range(height)]

    def set_pixel(self, x: int, y: int, value: bool = True) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y][x] = value
        else:
            self.clipped_writes += 1

    def vertical_line(self, x: int, y0: int = 0, y1: int = HEIGHT) -> None:
        for y in range(y0, y1):
            self.set_pixel(x, y)

    def fill_rect(self, x: int, y: int, width: int, height: int, value: bool = True) -> None:
        for offset_y in range(height):
            for offset_x in range(width):
                self.set_pixel(x + offset_x, y + offset_y, value)

    def bitmap(self, data: bytes, width: int, height: int, x: int, y: int, scale: int = 1) -> None:
        pages = (height + 7) // 8
        if len(data) != width * pages:
            raise ValueError(f"bitmap needs {width * pages} bytes, got {len(data)}")
        for source_y in range(height):
            for source_x in range(width):
                byte = data[(source_y // 8) * width + source_x]
                if byte & (1 << (source_y % 8)):
                    for offset_y in range(scale):
                        for offset_x in range(scale):
                            self.set_pixel(x + source_x * scale + offset_x, y + source_y * scale + offset_y)

    def small_text(self, text: str, assets: FontAssets, x: int, y: int) -> int:
        for char in text:
            glyph_index = assets.small_chars.get(char)
            if glyph_index is None:
                raise ValueError(f"character {char!r} is absent from the generated small font")
            self.bitmap(assets.small[glyph_index], 6, 8, x, y)
            x += 6
        return x

    def small_number(self, value: int, places: int, assets: FontAssets, x: int, y: int) -> int:
        text = str(value).rjust(places)
        return self.small_text(text, assets, x, y)

    def fullscreen_number(self, value: int, assets: FontAssets, panel_width: int = 72, panel_x: int = 0) -> None:
        text = str(value)
        x = panel_x + (panel_width - len(text) * 24) // 2
        for digit in text:
            self.bitmap(assets.large[int(digit)], 12, 16, x, 0, scale=2)
            x += 24

    def large_text(self, text: str, assets: FontAssets, x: int, y: int) -> int:
        for char in text:
            glyph_index = assets.large_chars.get(char)
            if glyph_index is None:
                raise ValueError(f"character {char!r} is absent from the generated large font")
            self.bitmap(assets.large[glyph_index], 12, 16, x, y)
            x += 12
        return x

    def large_digit(self, value: int, assets: FontAssets, x: int, y: int) -> None:
        self.bitmap(assets.large[value], 12, 16, x, y)

    def extra(self, symbol: int, x: int, y: int) -> None:
        offset = symbol * 24
        self.bitmap(self._assets.extras[offset : offset + 24], 12, 16, x, y)

    def bind_assets(self, assets: FontAssets) -> "Canvas":
        self._assets = assets
        return self


def draw_degree(canvas: Canvas, x: int, y: int) -> None:
    for offset_x, offset_y in ((0, 1), (1, 1), (2, 1), (0, 2), (2, 2), (0, 3), (1, 3), (2, 3)):
        canvas.set_pixel(x + offset_x, y + offset_y)


def draw_small_temperature(canvas: Canvas, value: int, assets: FontAssets, x: int, y: int) -> int:
    text = str(value)
    end = canvas.small_text(text, assets, x, y)
    draw_degree(canvas, end, y)
    canvas.small_text("C", assets, end + 4, y)
    return end + 10


def draw_tall_small_glyph(canvas: Canvas, glyph: bytes, x: int, y_offset: int = 0) -> None:
    source_columns = (0, 1, 1, 2, 3, 4, 4, 5)
    for source_y in range(7):
        for output_x, source_x in enumerate(source_columns):
            if glyph[source_x] & (1 << source_y):
                for doubled_y in (1, 2):
                    destination_y = 8 + y_offset + source_y * 2 + doubled_y
                    if 8 <= destination_y < 24:
                        canvas.set_pixel(x + output_x, destination_y)


def draw_fullscreen_digit_offset(canvas: Canvas, digit: str, assets: FontAssets, x: int, y_offset: int) -> None:
    glyph = assets.large[int(digit)]
    for source_y in range(16):
        for source_x in range(12):
            if glyph[(source_y // 8) * 12 + source_x] & (1 << (source_y % 8)):
                for scale_y in range(2):
                    destination_y = y_offset + source_y * 2 + scale_y
                    if 0 <= destination_y < 32:
                        canvas.set_pixel(x + source_x * 2, destination_y)
                        canvas.set_pixel(x + source_x * 2 + 1, destination_y)


def draw_fullscreen_digits_offset(canvas: Canvas, value: int, assets: FontAssets, panel_x: int, y_offset: int) -> None:
    text = str(value)
    x = panel_x + (72 - len(text) * 24) // 2
    for digit in text:
        draw_fullscreen_digit_offset(canvas, digit, assets, x, y_offset)
        x += 24


def draw_heat(canvas: Canvas, assets: FontAssets, level: int, x: int = 116, y: int = 16) -> None:
    symbol = assets.extras[14 * 24 : 15 * 24]
    canvas.bitmap(symbol, 12, 16, x, y)
    clear_height = 2 + (8 - max(0, min(8, level)))
    canvas.fill_rect(x, y, 12, clear_height, False)


@dataclass(frozen=True)
class SolderingState:
    name: str
    temperature: int
    source: str
    voltage_x10: int
    wattage_x10: int
    boost: bool = False
    battery_level: int | None = None
    heat_level: int = 7


DEMO_STATES = (
    SolderingState("soldering-dc", 350, "DC", 200, 650, heat_level=7),
    SolderingState("soldering-pd-boost", 380, "PD", 200, 960, boost=True, heat_level=8),
    SolderingState("soldering-battery", 320, "BAT", 122, 455, battery_level=7),
    SolderingState("soldering-low-temp", 25, "DC", 200, 0, heat_level=0),
)


def render_soldering(state: SolderingState, assets: FontAssets) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    canvas.fullscreen_number(state.temperature, assets)
    draw_degree(canvas, 70, 0)
    canvas.small_text("C", assets, 74, 0)
    canvas.vertical_line(80)
    canvas.small_text(state.source, assets, 83, 0)
    if state.boost:
        canvas.small_text("+", assets, 116, 0)
    voltage = f"{state.voltage_x10 // 10:02d}.{state.voltage_x10 % 10}V"
    canvas.small_text(voltage, assets, 83, 8)
    if state.wattage_x10 > 999:
        wattage = f"{state.wattage_x10 // 10:03d}W"
    else:
        wattage = f"{state.wattage_x10 // 10:02d}.{state.wattage_x10 % 10}W"
    canvas.small_text(wattage, assets, 83, 16)
    draw_small_temperature(canvas, 380 if state.boost else 350, assets, 83, 24)
    if state.battery_level is not None:
        symbol = 3 + max(1, min(10, state.battery_level))
        canvas.extra(symbol, 116, 16)
    else:
        draw_heat(canvas, assets, state.heat_level)
    return canvas


def render_home_dashboard(voltage_x10: int, source: str, assets: FontAssets) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    canvas.fullscreen_number(34, assets)
    draw_degree(canvas, 70, 0)
    canvas.small_text("C", assets, 74, 0)
    canvas.vertical_line(80)
    draw_small_temperature(canvas, 350, assets, 83, 0)
    canvas.small_text(f"{voltage_x10 // 10:02d}.{voltage_x10 % 10}V", assets, 83, 8)
    canvas.small_text(source, assets, 83, 16)
    draw_small_temperature(canvas, 32, assets, 83, 24)
    return canvas


def render_home_hot(assets: FontAssets) -> Canvas:
    canvas = render_home_voltage(12, assets)
    canvas.fill_rect(10, 4, 36, 4, False)
    canvas.fill_rect(8, 8, 40, 16, False)
    canvas.fill_rect(10, 24, 36, 4, False)
    canvas.fill_rect(8, 30, 40, 2, False)
    canvas.fill_rect(13, 30, 29, 1, True)
    value = "185"
    x = (56 - (len(value) * 8 + 4 + 8)) // 2
    for digit in value:
        draw_tall_small_glyph(canvas, assets.small[assets.small_chars[digit]], x)
        x += 8
    draw_degree(canvas, x, 8)
    draw_tall_small_glyph(canvas, assets.small[assets.small_chars["C"]], x + 4)
    return canvas


def render_temperature_adjust(assets: FontAssets) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    canvas.large_text("-", assets, 0, 8)
    canvas.fullscreen_number(350, assets, panel_x=24)
    draw_degree(canvas, 94, 0)
    canvas.small_text("C", assets, 98, 0)
    canvas.large_text("+", assets, 116, 8)
    return canvas


def render_temperature_roll(screen: str, assets: FontAssets) -> Canvas:
    if screen == "soldering":
        canvas = render_soldering(DEMO_STATES[0], assets)
        panel_x = 0
    elif screen == "adjust":
        canvas = render_temperature_adjust(assets)
        panel_x = 24
    else:
        canvas = render_home_hot(assets)
        canvas.fill_rect(8, 8, 40, 16, False)
        old_value, new_value = "184", "185"
        x = (56 - (len(new_value) * 8 + 4 + 8)) // 2
        for old_digit, new_digit in zip(old_value, new_value):
            if old_digit == new_digit:
                draw_tall_small_glyph(canvas, assets.small[assets.small_chars[new_digit]], x)
            else:
                draw_tall_small_glyph(canvas, assets.small[assets.small_chars[old_digit]], x, 8)
                draw_tall_small_glyph(canvas, assets.small[assets.small_chars[new_digit]], x, -8)
            x += 8
        draw_degree(canvas, x, 8)
        draw_tall_small_glyph(canvas, assets.small[assets.small_chars["C"]], x + 4)
        return canvas

    canvas.fill_rect(panel_x, 0, 72, 32, False)
    old_value, new_value = "349", "350"
    x = panel_x
    for old_digit, new_digit in zip(old_value, new_value):
        if old_digit == new_digit:
            draw_fullscreen_digit_offset(canvas, new_digit, assets, x, 0)
        else:
            draw_fullscreen_digit_offset(canvas, old_digit, assets, x, 16)
            draw_fullscreen_digit_offset(canvas, new_digit, assets, x, -16)
        x += 24
    draw_degree(canvas, panel_x + 70, 0)
    canvas.small_text("C", assets, panel_x + 74, 0)
    return canvas


def render_sleep(assets: FontAssets) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    canvas.fullscreen_number(150, assets)
    draw_degree(canvas, 70, 0)
    canvas.small_text("C", assets, 74, 0)
    canvas.vertical_line(80)
    canvas.small_text("Be", assets, 83, 0)
    draw_small_temperature(canvas, 150, assets, 98, 0)
    canvas.small_text("20.0V", assets, 83, 8)
    canvas.small_text("PD", assets, 83, 16)
    canvas.small_text("12.5W", assets, 83, 24)
    draw_heat(canvas, assets, 3)
    return canvas


def render_profile(assets: FontAssets) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    canvas.small_text("285/320", assets, 0, 0)
    draw_degree(canvas, 42, 0)
    canvas.small_text("C", assets, 46, 0)
    canvas.small_text("2/3", assets, 54, 0)
    canvas.small_text("PD", assets, 83, 0)
    canvas.small_text("0:35/1:00", assets, 0, 8)
    canvas.small_text("20.0V", assets, 62, 8)
    canvas.small_text("65.0W", assets, 98, 8)
    for x in range(112):
        canvas.set_pixel(x, 16)
        canvas.set_pixel(x, 23)
    canvas.fill_rect(1, 17, 64, 6)
    draw_heat(canvas, assets, 7)
    draw_small_temperature(canvas, 320, assets, 0, 24)
    return canvas


def render_cjc(assets: FontAssets) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    canvas.small_text("kalibre ediliyor", assets, 0, 0)
    for x in range(128):
        canvas.set_pixel(x, 8)
        canvas.set_pixel(x, 15)
    canvas.fill_rect(1, 9, 63, 6)
    canvas.small_text("Tip", assets, 0, 16)
    draw_small_temperature(canvas, 34, assets, 24, 16)
    canvas.small_text("08/16", assets, 78, 16)
    canvas.small_text("Han", assets, 0, 24)
    draw_small_temperature(canvas, 32, assets, 24, 24)
    canvas.small_text("Tip O", assets, 66, 24)
    canvas.small_text("  125", assets, 96, 24)
    return canvas


def render_demos(output_dir: Path, assets: FontAssets, scale: int) -> list[Path]:
    outputs = []
    for state in DEMO_STATES:
        output = output_dir / f"{state.name}.png"
        write_png(output, render_soldering(state, assets).pixels, scale)
        outputs.append(output)
    for name, volts in (("home-usb-5v", 5), ("home-dc-12v", 12)):
        output = output_dir / f"{name}.png"
        write_png(output, render_home_voltage(volts, assets).pixels, scale)
        outputs.append(output)
    for name, renderer in (("temperature-adjust", render_temperature_adjust), ("sleep", render_sleep), ("profile", render_profile), ("cjc-calibration", render_cjc)):
        output = output_dir / f"{name}.png"
        write_png(output, renderer(assets).pixels, scale)
        outputs.append(output)
    output = output_dir / "home-hot-tip.png"
    write_png(output, render_home_hot(assets).pixels, scale)
    outputs.append(output)
    for screen in ("soldering", "home", "adjust"):
        output = output_dir / f"temperature-roll-{screen}-mid.png"
        write_png(output, render_temperature_roll(screen, assets).pixels, scale)
        outputs.append(output)
    return outputs


def render_home_voltage(volts: int, assets: FontAssets) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    canvas.bitmap(assets.button_a, 56, 32, 0, 0)
    canvas.bitmap(assets.button_b, 56, 32, 58, 0)
    if volts < 10:
        canvas.large_digit(volts, assets, 116, 8)
    else:
        canvas.large_digit((volts // 10) % 10, assets, 116, 0)
        canvas.large_digit(volts % 10, assets, 116, 16)
    return canvas


def _default_paths() -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[1]
    return root / "source/core/gen/Translation.TR.cpp", root / "source/core/drivers/Font.h"


def self_test(assets: FontAssets) -> None:
    assert len(assets.large) >= 10
    assert len(assets.small) >= 10
    assert len(assets.extras) >= 15 * 24
    assert len(assets.button_a) == 56 * 4 and len(assets.button_b) == 56 * 4
    assert {"+", ".", "B", "A", "T", "D", "C", "P", "V", "W"} <= assets.small_chars.keys()
    pixels = framebuffer_to_pixels(bytes([1]) + bytes(FRAME_BYTES - 1))
    assert pixels[0][0] and not pixels[1][0] and not pixels[0][1]
    canvas = render_soldering(DEMO_STATES[0], assets)
    assert len(canvas.pixels) == HEIGHT and len(canvas.pixels[0]) == WIDTH
    assert all(canvas.pixels[y][80] for y in range(HEIGHT))
    assert canvas.pixels[1][72] and not canvas.pixels[1][73]
    usb_canvas = render_home_voltage(5, assets)
    dc_canvas = render_home_voltage(12, assets)
    assert usb_canvas.pixels != dc_canvas.pixels
    for renderer in (render_temperature_adjust, render_sleep, render_profile, render_cjc, render_home_hot):
        assert renderer(assets).clipped_writes == 0
    assert all(render_temperature_roll(screen, assets).clipped_writes == 0 for screen in ("soldering", "home", "adjust"))
    assert all(render_soldering(state, assets).clipped_writes == 0 for state in DEMO_STATES)
    assert usb_canvas.clipped_writes == 0 and dc_canvas.clipped_writes == 0


def main() -> int:
    translation, font_header = _default_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--translation", type=Path, default=translation, help="generated Translation.<lang>.cpp")
    parser.add_argument("--font-header", type=Path, default=font_header, help="Font.h containing ExtraFontChars")
    parser.add_argument("--output-dir", type=Path, default=Path("oled-previews"))
    parser.add_argument("--scale", type=int, default=DEFAULT_SCALE)
    parser.add_argument("--framebuffer", type=Path, help="render one raw 512-byte SSD1306 framebuffer")
    parser.add_argument("--output", type=Path, help="PNG path used with --framebuffer")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    assets = FontAssets.load(args.translation, args.font_header)
    if args.self_test:
        self_test(assets)
        print("OLED preview self-test: PASS")
        return 0
    if args.framebuffer:
        output = args.output or args.output_dir / f"{args.framebuffer.stem}.png"
        write_png(output, framebuffer_to_pixels(args.framebuffer.read_bytes()), args.scale)
        print(output)
        return 0
    for output in render_demos(args.output_dir, assets, args.scale):
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
