#!/usr/bin/env python3
"""Manage editable monochrome OLED icon sources for the TS101 firmware.

The source of truth is one plain-text PBM (P1) file per icon or animation
frame under assets/oled/icons.  This tool validates those files, renders PNG
previews, and emits the packed SSD1306 page-buffer arrays used by IronOS.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from oled_preview import framebuffer_to_pixels, parse_c_array, write_png


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "assets/oled/icons"
MANIFEST = ASSET_ROOT / "manifest.json"
PREVIEW_ROOT = ASSET_ROOT / "previews"
GENERATED_HEADER = ROOT / "source/core/drivers/OLEDAssets.generated.h"
LEGACY_HEADER = ROOT / "source/core/drivers/Font.h"

EXTRA_NAMES = [
    "degree_f",
    "degree_c",
    "arrow_up",
    "battery_empty",
    *[f"battery_{level:02d}" for level in range(1, 11)],
    "heating",
    "ac_power",
    "checkbox_on",
    "checkbox_off",
]
SETTINGS_NAMES = ["power", "soldering", "sleep", "ui", "advanced"]


def packed_to_pixels(data: bytes, width: int, height: int) -> list[list[bool]]:
    return framebuffer_to_pixels(data, width, height)


def pixels_to_packed(pixels: list[list[bool]], width: int, height: int) -> bytes:
    data = bytearray(width * ((height + 7) // 8))
    for y, row in enumerate(pixels):
        for x, enabled in enumerate(row):
            if enabled:
                data[(y // 8) * width + x] |= 1 << (y % 8)
    return bytes(data)


def write_pbm(path: Path, pixels: list[list[bool]], name: str) -> None:
    height = len(pixels)
    width = len(pixels[0]) if pixels else 0
    lines = ["P1", f"# {name} - edit 0/1 pixels; 1 is lit", f"{width} {height}"]
    lines.extend(" ".join("1" if pixel else "0" for pixel in row) for row in pixels)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def read_pbm(path: Path, expected_width: int, expected_height: int) -> list[list[bool]]:
    tokens: list[str] = []
    for line in path.read_text(encoding="ascii").splitlines():
        tokens.extend(line.split("#", 1)[0].split())
    if len(tokens) < 3 or tokens[0] != "P1":
        raise ValueError(f"{path}: expected plain PBM (P1)")
    width, height = int(tokens[1]), int(tokens[2])
    if (width, height) != (expected_width, expected_height):
        raise ValueError(
            f"{path}: expected {expected_width}x{expected_height}, got {width}x{height}"
        )
    values = tokens[3:]
    if len(values) != width * height or any(value not in ("0", "1") for value in values):
        raise ValueError(f"{path}: expected exactly {width * height} binary pixels")
    return [
        [values[y * width + x] == "1" for x in range(width)]
        for y in range(height)
    ]


def extract_settings_icons(source: str) -> list[bytes]:
    start = source.index("const uint8_t SettingsMenuIcons")
    end = source.index("// clang-format on", start)
    values = bytes(int(value, 16) for value in re.findall(r"0[xX]([0-9A-Fa-f]+)", source[start:end]))
    frame_size = 21 * 4
    expected = len(SETTINGS_NAMES) * 3 * frame_size
    if len(values) != expected:
        raise ValueError(f"SettingsMenuIcons: expected {expected} bytes, got {len(values)}")
    return [values[offset : offset + frame_size] for offset in range(0, len(values), frame_size)]


def home_solder_frame(frame: int) -> bytes:
    width, height = 14, 9
    wave = (-1, -1, 0, 1, 1, 1, 0, -1)
    pixels = [[False] * width for _ in range(height)]
    for base in (1, 6, 11):
        for y in range(height):
            pixels[y][base + wave[(y + frame) % 8]] = True
    return pixels_to_packed(pixels, width, height)


def home_settings_frame(frame: int) -> bytes:
    width, height = 23, 24
    motion = (0, -1, -2, -1, 0, 1, 2, 1)
    pixels = [[False] * width for _ in range(height)]
    for x, base_y in zip((2, 11, 20), (6, 16, 12)):
        center_y = base_y + motion[frame]
        for y in range(height):
            pixels[y][x] = True
        for y_offset in range(-2, 3):
            radius = 1 if abs(y_offset) == 2 else 2
            for x_offset in range(-radius, radius + 1):
                pixels[center_y + y_offset][x + x_offset] = True
        pixels[center_y][x] = False
    return pixels_to_packed(pixels, width, height)


def full_height_battery_pixels(source: list[list[bool]]) -> list[list[bool]]:
    pixels = [[False] * 12 for _ in range(32)]
    for destination_y in range(32):
        source_y = 1 + (destination_y * 13 + 15) // 31
        for destination_x in range(12):
            source_x = 1 + (destination_x * 9 + 5) // 11
            pixels[destination_y][destination_x] = source[source_y][source_x]
    return pixels


def default_manifest() -> dict:
    standalone = [
        {"name": "warning_triangle", "file": "static/warning_triangle.pbm", "width": 24, "height": 16, "cpp": "WarningBlock24"},
        {"name": "home_solder_button", "file": "static/home_solder_button.pbm", "width": 56, "height": 32, "cpp": "buttonA"},
        {"name": "tip_disconnected", "file": "static/tip_disconnected.pbm", "width": 56, "height": 32, "cpp": "disconnectedTip"},
        {"name": "home_settings_button", "file": "static/home_settings_button.pbm", "width": 56, "height": 32, "cpp": "buttonB"},
        {"name": "repeat_once", "file": "static/repeat_once.pbm", "width": 32, "height": 32, "cpp": "RepeatOnce"},
        {"name": "repeat_forever", "file": "static/repeat_forever.pbm", "width": 32, "height": 32, "cpp": "RepeatInf"},
        {"name": "unavailable", "file": "static/unavailable.pbm", "width": 32, "height": 32, "cpp": "UnavailableIcon"},
        {"name": "degree_small", "file": "static/degree_small.pbm", "width": 3, "height": 8, "cpp": "DegreeSymbol"},
    ]
    extras = [
        {"name": name, "file": f"symbols/{name}.pbm", "width": 12, "height": 16}
        for name in EXTRA_NAMES
    ]
    settings = [
        {
            "name": f"settings_{name}_{frame}",
            "file": f"settings/{name}/frame_{frame}.pbm",
            "width": 21,
            "height": 32,
        }
        for name in SETTINGS_NAMES
        for frame in range(3)
    ]
    solder = [
        {"name": f"home_solder_heat_{frame}", "file": f"animations/home_solder_heat/frame_{frame}.pbm", "width": 14, "height": 9}
        for frame in range(8)
    ]
    sliders = [
        {"name": f"home_settings_sliders_{frame}", "file": f"animations/home_settings_sliders/frame_{frame}.pbm", "width": 23, "height": 24}
        for frame in range(8)
    ]
    full_height_batteries = [
        {
            "name": f"battery_full_height_{'empty' if level == 0 else f'{level:02d}'}",
            "file": f"battery/full_height/{'battery_empty' if level == 0 else f'battery_{level:02d}'}.pbm",
            "width": 12,
            "height": 32,
        }
        for level in range(11)
    ]
    return {
        "format": 1,
        "notes": "Add standalone icons to standalone. Keep collection order stable because firmware indexes these arrays.",
        "standalone": standalone,
        "collections": {
            "extra_font_chars": {"cpp": "ExtraFontChars", "items": extras},
            "settings_menu": {"cpp": "SettingsMenuIcons", "groups": 5, "frames_per_group": 3, "items": settings},
            "home_solder_heat": {"cpp": "HomeSolderHeatFrames", "items": solder},
            "home_settings_sliders": {"cpp": "HomeSettingsSlidersFrames", "items": sliders},
            "full_height_batteries": {"cpp": "FullHeightBatteryIcons", "items": full_height_batteries},
        },
    }


def bootstrap() -> None:
    manifest = default_manifest()
    source = LEGACY_HEADER.read_text(encoding="utf-8")
    legacy = {
        "WarningBlock24": parse_c_array(LEGACY_HEADER, "WarningBlock24"),
        "buttonA": parse_c_array(LEGACY_HEADER, "buttonA"),
        "disconnectedTip": parse_c_array(LEGACY_HEADER, "disconnectedTip"),
        "buttonB": parse_c_array(LEGACY_HEADER, "buttonB"),
        "RepeatOnce": parse_c_array(LEGACY_HEADER, "RepeatOnce"),
        "RepeatInf": parse_c_array(LEGACY_HEADER, "RepeatInf"),
        "UnavailableIcon": parse_c_array(LEGACY_HEADER, "UnavailableIcon"),
        "DegreeSymbol": bytes((0x0E, 0x0A, 0x0E)),
    }
    for item in manifest["standalone"]:
        data = legacy[item["cpp"]]
        write_pbm(ASSET_ROOT / item["file"], packed_to_pixels(data, item["width"], item["height"]), item["name"])

    extra_data = parse_c_array(LEGACY_HEADER, "ExtraFontChars")
    for index, item in enumerate(manifest["collections"]["extra_font_chars"]["items"]):
        data = extra_data[index * 24 : (index + 1) * 24]
        write_pbm(ASSET_ROOT / item["file"], packed_to_pixels(data, 12, 16), item["name"])

    settings_frames = extract_settings_icons(source)
    for item, data in zip(manifest["collections"]["settings_menu"]["items"], settings_frames):
        write_pbm(ASSET_ROOT / item["file"], packed_to_pixels(data, 21, 32), item["name"])

    for frame, item in enumerate(manifest["collections"]["home_solder_heat"]["items"]):
        write_pbm(ASSET_ROOT / item["file"], packed_to_pixels(home_solder_frame(frame), 14, 9), item["name"])
    for frame, item in enumerate(manifest["collections"]["home_settings_sliders"]["items"]):
        write_pbm(ASSET_ROOT / item["file"], packed_to_pixels(home_settings_frame(frame), 23, 24), item["name"])

    ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    generate()


def load_item(item: dict) -> bytes:
    pixels = read_pbm(ASSET_ROOT / item["file"], item["width"], item["height"])
    return pixels_to_packed(pixels, item["width"], item["height"])


def cpp_bytes(data: bytes, indent: str = "  ") -> str:
    lines = []
    for offset in range(0, len(data), 16):
        lines.append(indent + ", ".join(f"0x{value:02X}" for value in data[offset : offset + 16]) + ",")
    return "\n".join(lines)


def array_text(name: str, data: bytes) -> str:
    return f"const uint8_t {name}[] = {{\n{cpp_bytes(data)}\n}};\n"


def generate() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    blocks = [
        "// Generated by tools/oled_assets.py. Edit assets/oled/icons/*.pbm, not this file.\n",
        "#ifndef OLED_ASSETS_GENERATED_H_\n#define OLED_ASSETS_GENERATED_H_\n\n#include <stdint.h>\n\n",
        "#define SETTINGS_ICON_WIDTH 21\n#define SETTINGS_ICON_HEIGHT 32\n",
        "#define HOME_ICON_FRAME_COUNT 8\n#define HOME_SOLDER_HEAT_WIDTH 14\n#define HOME_SOLDER_HEAT_HEIGHT 9\n",
        "#define HOME_SETTINGS_SLIDERS_WIDTH 23\n#define HOME_SETTINGS_SLIDERS_HEIGHT 24\n\n",
    ]

    for item in manifest["standalone"]:
        blocks.append(array_text(item["cpp"], load_item(item)) + "\n")

    extras = manifest["collections"]["extra_font_chars"]
    extra_data = b"".join(load_item(item) for item in extras["items"])
    blocks.append(array_text(extras["cpp"], extra_data) + "\n")

    settings = manifest["collections"]["settings_menu"]
    settings_items = settings["items"]
    frame_bytes = settings_items[0]["width"] * ((settings_items[0]["height"] + 7) // 8)
    blocks.append(f"const uint8_t {settings['cpp']}[][{frame_bytes} * {settings['frames_per_group']}] = {{\n")
    for group in range(settings["groups"]):
        first = group * settings["frames_per_group"]
        data = b"".join(load_item(item) for item in settings_items[first : first + settings["frames_per_group"]])
        blocks.append("  {\n" + cpp_bytes(data, "    ") + "\n  },\n")
    blocks.append("};\n\n")

    for key in ("home_solder_heat", "home_settings_sliders", "full_height_batteries"):
        collection = manifest["collections"][key]
        items = collection["items"]
        frame_bytes = items[0]["width"] * ((items[0]["height"] + 7) // 8)
        frames = [load_item(item) for item in items]
        blocks.append(f"const uint8_t {collection['cpp']}[][{'%d' % frame_bytes}] = {{\n")
        for frame in frames:
            blocks.append("  {\n" + cpp_bytes(frame, "    ") + "\n  },\n")
        blocks.append("};\n\n")
        if key == "home_solder_heat":
            clear_mask = bytearray(frame_bytes)
            for frame in frames:
                for index, value in enumerate(frame):
                    clear_mask[index] |= value
            # The editable base icon contains the animation's resting frame.
            # Include those heat pixels in the union mask, but never the
            # cartridge itself, which starts immediately below at y=19.
            button_item = next(item for item in manifest["standalone"] if item["cpp"] == "buttonA")
            button_pixels = read_pbm(ASSET_ROOT / button_item["file"], button_item["width"], button_item["height"])
            mask_pixels = packed_to_pixels(clear_mask, items[0]["width"], items[0]["height"])
            for y in range(items[0]["height"]):
                for x in range(items[0]["width"]):
                    mask_pixels[y][x] |= button_pixels[10 + y][7 + x]
            clear_mask = pixels_to_packed(mask_pixels, items[0]["width"], items[0]["height"])
            blocks.append(array_text("HomeSolderHeatMask", clear_mask) + "\n")

    blocks.append("#endif // OLED_ASSETS_GENERATED_H_\n")
    GENERATED_HEADER.write_text("".join(blocks), encoding="utf-8")
    render_previews(manifest)
    print(f"Generated {GENERATED_HEADER.relative_to(ROOT)}")


def all_items(manifest: dict):
    yield from manifest["standalone"]
    for collection in manifest["collections"].values():
        yield from collection["items"]


def render_previews(manifest: dict) -> None:
    for item in all_items(manifest):
        pixels = read_pbm(ASSET_ROOT / item["file"], item["width"], item["height"])
        output = PREVIEW_ROOT / Path(item["file"]).with_suffix(".png")
        write_png(output, pixels, scale=8)


def check() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    names: set[str] = set()
    files: set[str] = set()
    count = 0
    for item in all_items(manifest):
        if item["name"] in names or item["file"] in files:
            raise ValueError(f"duplicate asset name or file: {item}")
        names.add(item["name"])
        files.add(item["file"])
        load_item(item)
        count += 1
    before = GENERATED_HEADER.read_bytes() if GENERATED_HEADER.exists() else b""
    generate()
    after = GENERATED_HEADER.read_bytes()
    if before and before != after:
        raise ValueError("generated header was stale; it has been refreshed")
    print(f"OLED asset check: PASS ({count} independent files)")


def create_icon(name: str, width: int, height: int, cpp_name: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise ValueError("name must use lowercase letters, digits, and underscores")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", cpp_name):
        raise ValueError("cpp name is not a valid C++ identifier")
    if not (1 <= width <= 128 and 1 <= height <= 64):
        raise ValueError("icon dimensions must be within 1..128 by 1..64")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if any(item["name"] == name or item.get("cpp") == cpp_name for item in all_items(manifest)):
        raise ValueError(f"asset name or C++ identifier already exists: {name} / {cpp_name}")
    item = {
        "name": name,
        "file": f"custom/{name}.pbm",
        "width": width,
        "height": height,
        "cpp": cpp_name,
    }
    manifest["standalone"].append(item)
    write_pbm(ASSET_ROOT / item["file"], [[False] * width for _ in range(height)], name)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    generate()
    print(f"Created {item['file']} as {cpp_name}")


def create_full_height_batteries() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if "full_height_batteries" in manifest["collections"]:
        raise ValueError("full-height battery assets already exist")
    source_items = manifest["collections"]["extra_font_chars"]["items"][3:14]
    items = []
    for level, source_item in enumerate(source_items):
        suffix = "empty" if level == 0 else f"{level:02d}"
        filename = "battery_empty" if level == 0 else f"battery_{level:02d}"
        item = {
            "name": f"battery_full_height_{suffix}",
            "file": f"battery/full_height/{filename}.pbm",
            "width": 12,
            "height": 32,
        }
        source = read_pbm(ASSET_ROOT / source_item["file"], 12, 16)
        write_pbm(ASSET_ROOT / item["file"], full_height_battery_pixels(source), item["name"])
        items.append(item)
    manifest["collections"]["full_height_batteries"] = {"cpp": "FullHeightBatteryIcons", "items": items}
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    generate()
    print("Created 11 independently editable full-height battery assets")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "check", "preview", "new", "new-full-height-batteries"))
    parser.add_argument("name", nargs="?")
    parser.add_argument("width", nargs="?", type=int)
    parser.add_argument("height", nargs="?", type=int)
    parser.add_argument("cpp_name", nargs="?")
    args = parser.parse_args()
    if args.command == "generate":
        generate()
    elif args.command == "preview":
        render_previews(json.loads(MANIFEST.read_text(encoding="utf-8")))
    elif args.command == "new":
        if None in (args.name, args.width, args.height, args.cpp_name):
            parser.error("new requires: name width height CppIdentifier")
        create_icon(args.name, args.width, args.height, args.cpp_name)
    elif args.command == "new-full-height-batteries":
        create_full_height_batteries()
    else:
        check()


if __name__ == "__main__":
    main()
