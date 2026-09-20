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


def ease_in_out_position(position: int, extent: int) -> int:
    if extent <= 0:
        return 0
    position = max(0, min(extent, position))
    denominator = extent * extent * extent
    numerator = extent * position * position * (3 * extent - 2 * position)
    return (numerator + denominator // 2) // denominator


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
    match = re.search(rf"const\s+uint8_t\s+{re.escape(name)}\[\](?:\[[^\]]+\])?\s*=\s*\{{(.*?)\}};", source, re.DOTALL)
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
    warning_block: bytes
    button_a: bytes
    button_b: bytes
    disconnected_tip: bytes
    home_button_outline: bytes
    home_button_mask: bytes
    home_solder_heat_mask: bytes
    full_height_batteries: bytes

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
            warning_block=parse_c_array(font_header, "WarningBlock24"),
            button_a=parse_c_array(font_header, "buttonA"),
            button_b=parse_c_array(font_header, "buttonB"),
            disconnected_tip=parse_c_array(font_header, "disconnectedTip"),
            home_button_outline=parse_c_array(font_header, "HomeButtonOutline"),
            home_button_mask=parse_c_array(font_header, "HomeButtonMask"),
            home_solder_heat_mask=parse_c_array(font_header, "HomeSolderHeatMask"),
            full_height_batteries=parse_c_array(font_header, "FullHeightBatteryIcons"),
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

    def xor_bitmap(self, data: bytes, width: int, height: int, x: int, y: int) -> None:
        for source_y in range(height):
            for source_x in range(width):
                if data[(source_y // 8) * width + source_x] & (1 << (source_y % 8)):
                    target_x, target_y = x + source_x, y + source_y
                    self.set_pixel(target_x, target_y, not self.pixels[target_y][target_x])

    def clear_bitmap(self, data: bytes, width: int, height: int, x: int, y: int) -> None:
        for source_y in range(height):
            for source_x in range(width):
                if data[(source_y // 8) * width + source_x] & (1 << (source_y % 8)):
                    self.set_pixel(x + source_x, y + source_y, False)

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

    def fullscreen_number(self, value: int, assets: FontAssets, panel_width: int = 80, panel_x: int = 0) -> None:
        text = str(value)
        x, _, _ = fullscreen_temperature_layout(value, panel_x, panel_width)
        for digit in text:
            self.bitmap(assets.large[int(digit)], 12, 16, x, 2, scale=2)
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


def fullscreen_temperature_layout(value: int, panel_x: int = 0, panel_width: int = 80) -> tuple[int, int, int]:
    places = len(str(value))
    digits_visible_width = (places - 1) * 24 + 22
    content_width = digits_visible_width + 1 + 3 + 1 + 4
    visible_start = panel_x + (panel_width - content_width) // 2
    return visible_start - 2, visible_start + digits_visible_width + 1, visible_start + digits_visible_width + 5


def draw_fullscreen_temperature(canvas: Canvas, value: int, assets: FontAssets, panel_x: int = 0, panel_width: int = 80) -> None:
    canvas.fullscreen_number(value, assets, panel_width, panel_x)
    _, degree_x, unit_x = fullscreen_temperature_layout(value, panel_x, panel_width)
    draw_degree(canvas, degree_x, 2)
    draw_compact_unit(canvas, assets, unit_x, 2)


def draw_compact_unit(canvas: Canvas, assets: FontAssets, x: int, y: int, unit: str = "C") -> None:
    glyph = assets.small[assets.small_chars[unit]]
    canvas.bitmap(bytes(glyph[column] for column in (0, 1, 3, 4)), 4, 8, x, y)


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
                    destination_y = 2 + y_offset + source_y * 2 + scale_y
                    if 0 <= destination_y < 32:
                        canvas.set_pixel(x + source_x * 2, destination_y)
                        canvas.set_pixel(x + source_x * 2 + 1, destination_y)


def draw_fullscreen_digits_offset(canvas: Canvas, value: int, assets: FontAssets, panel_x: int, y_offset: int) -> None:
    text = str(value)
    x, _, _ = fullscreen_temperature_layout(value, panel_x)
    for digit in text:
        draw_fullscreen_digit_offset(canvas, digit, assets, x, y_offset)
        x += 24


def draw_heat(canvas: Canvas, assets: FontAssets, level: int, x: int = 116, y: int = 16) -> None:
    symbol = assets.extras[14 * 24 : 15 * 24]
    canvas.bitmap(symbol, 12, 16, x, y)
    clear_height = 2 + (8 - max(0, min(8, level)))
    canvas.fill_rect(x, y, 12, clear_height, False)


def draw_full_height_battery(canvas: Canvas, assets: FontAssets, level: int, x: int) -> None:
    level = max(0, min(10, level))
    frame_size = 12 * 4
    canvas.bitmap(assets.full_height_batteries[level * frame_size : (level + 1) * frame_size], 12, 32, x, 0)


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
    SolderingState("soldering-single-digit", 350, "DC", 50, 50, heat_level=2),
    SolderingState("soldering-pd-boost", 380, "PD", 200, 960, boost=True, heat_level=8),
    SolderingState("soldering-battery", 320, "BAT", 122, 455, battery_level=7),
    SolderingState("soldering-low-temp", 25, "DC", 200, 0, heat_level=0),
)


def render_soldering(state: SolderingState, assets: FontAssets) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    draw_fullscreen_temperature(canvas, state.temperature, assets)
    canvas.vertical_line(80)
    canvas.small_text(state.source, assets, 83, 0)
    if state.boost:
        canvas.small_text("+", assets, 103 if state.battery_level is not None else 116, 0)
    voltage = f"{state.voltage_x10 // 10}.{state.voltage_x10 % 10}V"
    canvas.small_text(voltage, assets, 83, 8)
    if state.wattage_x10 > 999:
        wattage = f"{state.wattage_x10 // 10:03d}W"
    else:
        wattage = f"{state.wattage_x10 // 10}.{state.wattage_x10 % 10}W"
    canvas.small_text(wattage, assets, 83, 16)
    draw_small_temperature(canvas, 380 if state.boost else 350, assets, 83, 24)
    if state.battery_level is not None:
        draw_full_height_battery(canvas, assets, state.battery_level, 116)
    else:
        draw_heat(canvas, assets, state.heat_level)
    return canvas


def render_home_dashboard(voltage_x10: int, source: str, assets: FontAssets) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    draw_fullscreen_temperature(canvas, 34, assets)
    canvas.vertical_line(80)
    draw_small_temperature(canvas, 350, assets, 83, 0)
    canvas.small_text(f"{voltage_x10 // 10:02d}.{voltage_x10 % 10}V", assets, 83, 8)
    canvas.small_text(source, assets, 83, 16)
    draw_small_temperature(canvas, 32, assets, 83, 24)
    return canvas


def render_home_hot(assets: FontAssets) -> Canvas:
    canvas = render_home_voltage(12, assets)
    canvas.fill_rect(4, 0, 48, 32, False)
    value = "185"
    x = (56 - (len(value) * 8 + 4 + 8)) // 2
    for digit in value:
        draw_tall_small_glyph(canvas, assets.small[assets.small_chars[digit]], x)
        x += 8
    draw_degree(canvas, x, 8)
    draw_tall_small_glyph(canvas, assets.small[assets.small_chars["C"]], x + 4)
    canvas.bitmap(assets.home_button_outline, 56, 32, 0, 0)
    return canvas


def render_temperature_adjust(assets: FontAssets) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    canvas.large_text("-", assets, 0, 8)
    draw_fullscreen_temperature(canvas, 350, assets, panel_x=24)
    canvas.large_text("+", assets, 116, 8)
    return canvas


def render_tip_missing_warning(assets: FontAssets) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    canvas.bitmap(assets.warning_block, 24, 16, 0, 8)
    canvas.small_text("Ucu takın", assets, 28, 8)
    return canvas


def render_vertical_transition(old: Canvas, new: Canvas, progress: int, direction: str) -> Canvas:
    """Model the firmware's scan-line transition at one animation step."""
    progress = ease_in_out_position(progress, HEIGHT)
    canvas = Canvas()
    if direction == "down":
        canvas.pixels = [row[:] for row in old.pixels[progress:]] + [row[:] for row in new.pixels[:progress]]
    elif direction == "up":
        canvas.pixels = [row[:] for row in new.pixels[HEIGHT - progress :]] + [row[:] for row in old.pixels[: HEIGHT - progress]]
    else:
        raise ValueError(f"unknown vertical transition direction: {direction}")
    return canvas


def render_temperature_roll(screen: str, assets: FontAssets, increasing: bool = True) -> Canvas:
    if screen == "soldering":
        canvas = render_soldering(DEMO_STATES[0], assets)
        panel_x = 0
    elif screen == "adjust":
        canvas = render_temperature_adjust(assets)
        panel_x = 24
    else:
        canvas = render_home_hot(assets)
        canvas.fill_rect(8, 8, 40, 16, False)
        old_value, new_value = (("184", "185") if increasing else ("185", "184"))
        old_offset, new_offset = ((-8, 8) if increasing else (8, -8))
        x = (56 - (len(new_value) * 8 + 4 + 8)) // 2
        for old_digit, new_digit in zip(old_value, new_value):
            if old_digit == new_digit:
                draw_tall_small_glyph(canvas, assets.small[assets.small_chars[new_digit]], x)
            else:
                draw_tall_small_glyph(canvas, assets.small[assets.small_chars[old_digit]], x, old_offset)
                draw_tall_small_glyph(canvas, assets.small[assets.small_chars[new_digit]], x, new_offset)
            x += 8
        draw_degree(canvas, x, 8)
        draw_tall_small_glyph(canvas, assets.small[assets.small_chars["C"]], x + 4)
        return canvas

    canvas.fill_rect(panel_x, 0, 80, 32, False)
    old_value, new_value = (("349", "350") if increasing else ("350", "349"))
    old_offset, new_offset = ((-16, 16) if increasing else (16, -16))
    x, degree_x, unit_x = fullscreen_temperature_layout(int(new_value), panel_x)
    for old_digit, new_digit in zip(old_value, new_value):
        if old_digit == new_digit:
            draw_fullscreen_digit_offset(canvas, new_digit, assets, x, 0)
        else:
            draw_fullscreen_digit_offset(canvas, old_digit, assets, x, old_offset)
            draw_fullscreen_digit_offset(canvas, new_digit, assets, x, new_offset)
        x += 24
    draw_degree(canvas, degree_x, 2)
    draw_compact_unit(canvas, assets, unit_x, 2)
    return canvas


def render_sleep(assets: FontAssets) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    draw_fullscreen_temperature(canvas, 150, assets)
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
    output = output_dir / "home-battery.png"
    write_png(output, render_home_battery(7, assets).pixels, scale)
    outputs.append(output)
    for name, renderer in (("temperature-adjust", render_temperature_adjust), ("sleep", render_sleep), ("profile", render_profile), ("cjc-calibration", render_cjc)):
        output = output_dir / f"{name}.png"
        write_png(output, renderer(assets).pixels, scale)
        outputs.append(output)
    output = output_dir / "tip-missing-warning.png"
    write_png(output, render_tip_missing_warning(assets).pixels, scale)
    outputs.append(output)
    output = output_dir / "home-hot-tip.png"
    write_png(output, render_home_hot(assets).pixels, scale)
    outputs.append(output)
    output = output_dir / "home-tip-disconnected.png"
    write_png(output, render_home_disconnected(assets).pixels, scale)
    outputs.append(output)
    for screen in ("soldering", "home", "adjust"):
        output = output_dir / f"temperature-roll-{screen}-mid.png"
        write_png(output, render_temperature_roll(screen, assets).pixels, scale)
        outputs.append(output)
        output = output_dir / f"temperature-roll-{screen}-decrease-mid.png"
        write_png(output, render_temperature_roll(screen, assets, increasing=False).pixels, scale)
        outputs.append(output)
    for frame in range(8):
        output = output_dir / f"home-icons-frame-{frame}.png"
        write_png(output, render_home_icon_frame(frame, assets).pixels, scale)
        outputs.append(output)
    output = output_dir / "home-icons-rotated.png"
    write_png(output, render_home_icon_frame(1, assets, mirrored=True).pixels, scale)
    outputs.append(output)
    for pressed in ("solder", "settings"):
        output = output_dir / f"home-{pressed}-pressed.png"
        write_png(output, render_home_icon_frame(1, assets, pressed=pressed).pixels, scale)
        outputs.append(output)
    soldering = render_soldering(DEMO_STATES[0], assets)
    adjustment = render_temperature_adjust(assets)
    for name, old, new, direction in (
        ("transition-soldering-to-adjust", soldering, adjustment, "down"),
        ("transition-adjust-to-soldering", adjustment, soldering, "up"),
        ("transition-home-to-tip-warning", render_home_icon_frame(0, assets), render_tip_missing_warning(assets), "down"),
        ("transition-tip-warning-to-home", render_tip_missing_warning(assets), render_home_icon_frame(0, assets), "up"),
    ):
        output = output_dir / f"{name}-mid.png"
        write_png(output, render_vertical_transition(old, new, HEIGHT // 2, direction).pixels, scale)
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


def render_home_battery(level: int, assets: FontAssets) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    canvas.bitmap(assets.button_a, 56, 32, 0, 0)
    canvas.bitmap(assets.button_b, 56, 32, 58, 0)
    draw_full_height_battery(canvas, assets, level, 116)
    return canvas


def render_home_disconnected(assets: FontAssets) -> Canvas:
    canvas = render_home_voltage(12, assets)
    canvas.fill_rect(0, 0, 56, 32, False)
    canvas.bitmap(assets.disconnected_tip, 56, 32, 0, 0)
    canvas.bitmap(assets.home_button_outline, 56, 32, 0, 0)
    return canvas


def render_home_icon_frame(frame: int, assets: FontAssets, mirrored: bool = False, pressed: str | None = None) -> Canvas:
    canvas = Canvas().bind_assets(assets)
    if mirrored:
        button_a = bytes(value for page in range(4) for value in reversed(assets.button_a[page * 56 : (page + 1) * 56]))
        button_b = bytes(value for page in range(4) for value in reversed(assets.button_b[page * 56 : (page + 1) * 56]))
        canvas.bitmap(button_b, 56, 32, 12, 0)
        canvas.bitmap(button_a, 56, 32, 68, 0)
        solder_x, settings_x = 68, 12
    else:
        canvas.bitmap(assets.button_a, 56, 32, 0, 0)
        canvas.bitmap(assets.button_b, 56, 32, 58, 0)
        solder_x, settings_x = 0, 58

    def bitmap(width: int, height: int, points: set[tuple[int, int]]) -> bytes:
        data = bytearray(width * ((height + 7) // 8))
        for x, y in points:
            data[(y // 8) * width + x] |= 1 << (y % 8)
        return bytes(data)

    heat_points: set[tuple[int, int]] = set()
    wave = (-1, -1, 0, 1, 1, 1, 0, -1)
    for base in (1, 6, 11):
        for y in range(9):
            heat_points.add((base + wave[(y + frame) % 8], y))
    solder_heat = bitmap(14, 9, heat_points)

    slider_points: set[tuple[int, int]] = set()
    motion = (0, -1, -2, -1, 0, 1, 2, 1)[frame]
    for x, base_y in zip((2, 11, 20), (6, 16, 12)):
        slider_points.update((x, y) for y in range(24))
        center_y = base_y + motion
        for y_offset, radius in ((-2, 1), (-1, 2), (0, 2), (1, 2), (2, 1)):
            slider_points.update((x + x_offset, center_y + y_offset) for x_offset in range(-radius, radius + 1))
        slider_points.discard((x, center_y))
    settings_sliders = bitmap(23, 24, slider_points)

    def animated_part(button_x: int, local_x: int, y: int, width: int, height: int, data: bytes, clear_mask: bytes | None = None) -> None:
        draw_x = button_x + (56 - local_x - width if mirrored else local_x)
        if mirrored:
            pages = (height + 7) // 8
            data = bytes(value for page in range(pages) for value in reversed(data[page * width : (page + 1) * width]))
            if clear_mask is not None:
                clear_mask = bytes(value for page in range(pages) for value in reversed(clear_mask[page * width : (page + 1) * width]))
        if clear_mask is None:
            canvas.fill_rect(draw_x, y, width, height, False)
        else:
            canvas.clear_bitmap(clear_mask, width, height, draw_x, y)
        canvas.bitmap(data, width, height, draw_x, y)

    animated_part(solder_x, 7, 10, 14, 9, solder_heat, assets.home_solder_heat_mask)
    animated_part(settings_x, 16, 4, 23, 24, settings_sliders)
    for button_x in (solder_x, settings_x):
        canvas.bitmap(assets.home_button_outline, 56, 32, button_x, 0)
    if pressed == "solder":
        canvas.xor_bitmap(assets.home_button_mask, 56, 32, solder_x, 0)
        canvas.bitmap(assets.home_button_outline, 56, 32, solder_x, 0)
    elif pressed == "settings":
        canvas.xor_bitmap(assets.home_button_mask, 56, 32, settings_x, 0)
        canvas.bitmap(assets.home_button_outline, 56, 32, settings_x, 0)
    return canvas


def _default_paths() -> tuple[Path, Path]:
    root = Path(__file__).resolve().parents[1]
    return root / "source/core/gen/Translation.TR.cpp", root / "source/core/drivers/OLEDAssets.generated.h"


def self_test(assets: FontAssets) -> None:
    assert len(assets.large) >= 10
    assert len(assets.small) >= 10
    assert len(assets.extras) >= 15 * 24
    assert len(assets.warning_block) == 24 * 2
    assert len(assets.button_a) == 56 * 4 and len(assets.button_b) == 56 * 4 and len(assets.disconnected_tip) == 56 * 4
    assert len(assets.home_button_outline) == 56 * 4 and len(assets.home_button_mask) == 56 * 4
    assert len(assets.home_solder_heat_mask) == 14 * 2
    assert len(assets.full_height_batteries) == 11 * 12 * 4
    outline = framebuffer_to_pixels(assets.home_button_outline, 56, 32)
    mask = framebuffer_to_pixels(assets.home_button_mask, 56, 32)
    assert outline == outline[::-1] and all(row == row[::-1] for row in outline)
    assert mask == mask[::-1] and all(row == row[::-1] for row in mask)
    for outline_row, mask_row in zip(outline, mask):
        lit = [x for x, pixel in enumerate(outline_row) if pixel]
        assert lit and mask_row == [min(lit) <= x <= max(lit) for x in range(56)]
    for button_data in (assets.button_a, assets.button_b, assets.disconnected_tip):
        button = framebuffer_to_pixels(button_data, 56, 32)
        assert all(not button[y][x] or mask[y][x] for y in range(32) for x in range(56))
        assert all(not outline[y][x] or button[y][x] for y in range(32) for x in range(56))
    assert ease_in_out_position(0, HEIGHT) == 0
    assert ease_in_out_position(HEIGHT, HEIGHT) == HEIGHT
    assert ease_in_out_position(HEIGHT // 4, HEIGHT) < HEIGHT // 4
    assert ease_in_out_position(HEIGHT * 3 // 4, HEIGHT) > HEIGHT * 3 // 4
    eased_positions = [ease_in_out_position(step, HEIGHT) for step in range(HEIGHT + 1)]
    assert eased_positions == sorted(eased_positions)
    assert all(eased_positions[step] + eased_positions[HEIGHT - step] == HEIGHT for step in range(HEIGHT + 1))
    assert {"+", ".", "B", "A", "T", "D", "C", "P", "V", "W"} <= assets.small_chars.keys()
    pixels = framebuffer_to_pixels(bytes([1]) + bytes(FRAME_BYTES - 1))
    assert pixels[0][0] and not pixels[1][0] and not pixels[0][1]
    canvas = render_soldering(DEMO_STATES[0], assets)
    assert len(canvas.pixels) == HEIGHT and len(canvas.pixels[0]) == WIDTH
    assert all(canvas.pixels[y][80] for y in range(HEIGHT))
    digit_x, degree_x, unit_x = fullscreen_temperature_layout(350)
    assert (digit_x, degree_x, unit_x) == (-2, 71, 75)
    assert canvas.pixels[3][degree_x] and not canvas.pixels[3][degree_x - 1]
    assert not canvas.pixels[3][degree_x + 3] and canvas.pixels[3][unit_x]
    assert not any(canvas.pixels[y][79] for y in range(HEIGHT))
    # The 28px-visible fullscreen digits have equal 2px top/bottom margins.
    assert not any(canvas.pixels[y][x] for y in (0, 1, 30, 31) for x in range(0, degree_x))
    usb_canvas = render_home_voltage(5, assets)
    dc_canvas = render_home_voltage(12, assets)
    assert usb_canvas.pixels != dc_canvas.pixels
    home_battery = render_home_battery(7, assets)
    soldering_battery = render_soldering(next(state for state in DEMO_STATES if state.battery_level is not None), assets)
    for battery_canvas in (home_battery, soldering_battery):
        # The 12px battery column has equal (zero) top and bottom padding and
        # occupies all 32 rows without writing outside the framebuffer.
        assert any(battery_canvas.pixels[0][116:128])
        assert any(battery_canvas.pixels[31][116:128])
        assert battery_canvas.clipped_writes == 0
    for renderer in (render_temperature_adjust, render_tip_missing_warning, render_sleep, render_profile, render_cjc, render_home_hot, render_home_disconnected):
        assert renderer(assets).clipped_writes == 0
    assert all(render_temperature_roll(screen, assets, increasing).clipped_writes == 0 for screen in ("soldering", "home", "adjust") for increasing in (True, False))
    assert all(render_soldering(state, assets).clipped_writes == 0 for state in DEMO_STATES)
    single_digit = render_soldering(SolderingState("single", 350, "DC", 50, 50), assets)
    double_digit = render_soldering(SolderingState("double", 350, "DC", 550, 550), assets)
    assert min(x for y in range(8, 16) for x in range(83, 116) if single_digit.pixels[y][x]) == min(
        x for y in range(8, 16) for x in range(83, 116) if double_digit.pixels[y][x]
    )
    assert min(x for y in range(16, 24) for x in range(83, 116) if single_digit.pixels[y][x]) == min(
        x for y in range(16, 24) for x in range(83, 116) if double_digit.pixels[y][x]
    )
    assert usb_canvas.clipped_writes == 0 and dc_canvas.clipped_writes == 0
    assert all(render_home_icon_frame(frame, assets).clipped_writes == 0 for frame in range(8))
    assert render_home_icon_frame(1, assets, mirrored=True).clipped_writes == 0
    pressed_solder = render_home_icon_frame(1, assets, pressed="solder")
    pressed_settings = render_home_icon_frame(1, assets, pressed="settings")
    assert pressed_solder.clipped_writes == 0 and pressed_settings.clipped_writes == 0
    for y in range(32):
        for x in range(56):
            if outline[y][x]:
                assert pressed_solder.pixels[y][x]
                assert pressed_settings.pixels[y][58 + x]
    icon_frames = [render_home_icon_frame(frame, assets) for frame in range(8)]
    base_solder = framebuffer_to_pixels(assets.button_a, 56, 32)
    heat_mask = framebuffer_to_pixels(assets.home_solder_heat_mask, 14, 9)
    assert len({tuple(tuple(row) for row in frame.pixels) for frame in icon_frames}) == 8
    for frame, motion in zip(icon_frames, (0, -1, -2, -1, 0, 1, 2, 1)):
        # The original dithered cartridge pattern must remain untouched.
        assert frame.pixels[21][16]
        assert not frame.pixels[22][16] and frame.pixels[22][15] and frame.pixels[22][17]
        # Animation rendering may only alter pixels selected by its union mask;
        # neighbouring static pixels can never be clipped by a rectangle.
        for source_y in range(9):
            for source_x in range(14):
                if not heat_mask[source_y][source_x]:
                    assert frame.pixels[10 + source_y][7 + source_x] == base_solder[10 + source_y][7 + source_x]
        assert all(frame.pixels[y][x] == base_solder[y][x] for y in range(19, 26) for x in range(56))
        assert all(frame.pixels[0][x] and frame.pixels[31][x] for x in range(16, 40))
        assert frame.pixels[12][4] and frame.pixels[12][51]
        for x, center_y in zip((58 + 16 + 2, 58 + 16 + 11, 58 + 16 + 20), (4 + 6 + motion, 4 + 16 + motion, 4 + 12 + motion)):
            assert not frame.pixels[center_y][x]
    soldering = render_soldering(DEMO_STATES[0], assets)
    adjustment = render_temperature_adjust(assets)
    warning = render_tip_missing_warning(assets)
    home = render_home_icon_frame(0, assets)
    for old, new, direction in (
        (soldering, adjustment, "down"),
        (adjustment, soldering, "up"),
        (home, warning, "down"),
        (warning, home, "up"),
    ):
        assert render_vertical_transition(old, new, 0, direction).pixels == old.pixels
        assert render_vertical_transition(old, new, HEIGHT, direction).pixels == new.pixels
        assert render_vertical_transition(old, new, HEIGHT // 2, direction).clipped_writes == 0


def main() -> int:
    translation, font_header = _default_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--translation", type=Path, default=translation, help="generated Translation.<lang>.cpp")
    parser.add_argument("--font-header", type=Path, default=font_header, help="generated header containing OLED icon arrays")
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
