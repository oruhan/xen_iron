# xen_iron

Custom Miniware TS101 soldering iron firmware.

> [!WARNING]
> This is custom firmware. Flashing it might void your warranty.

## Fork

Forked from [IronOS-TS101-FullOLED](https://github.com/vtolvr/IronOS-TS101-FullOLED).

## Installation

**What you need:**

- 1x Miniware TS101 soldering iron
- 1x USB-C cable

**Steps:**

1. Download the firmware from [Releases](../../releases) (grab the TS101\_<PREFERRED_LANGUAGE>.hex)

2. Put your TS101 in DFU mode:
   - Unplug the iron
   - Hold down the `A` button
   - While holding it, plug in the USB-C cable
   - The iron should show up as a USB drive

3. Flash it:
   - Copy the .hex file to that USB drive
   - Wait for it to finish copying
   - The file will rename itself to .RDY if it worked, or .ERR if it didn't
   - If you get .ERR, don't panic. Just copy the file again without deleting the .ERR file. Usually works the second time.

4. Unplug, power it up with your preferred power supply, done.

## Building from Source on Fedora

The repository supports only TS101 with its fixed 128x32 OLED. Available languages are
`DE`, `EN`, `ES`, `FR`, `JA_JP`, `RU`, and `TR`.

Install the ARM toolchain and Python support:

```bash
sudo dnf install arm-none-eabi-gcc-cs arm-none-eabi-gcc-cs-c++ arm-none-eabi-newlib make python3
python3 -m venv source/.venv-build
source source/.venv-build/bin/activate
python -m pip install -r source/requirements-build.txt
```

The USB-PD code is a Git submodule. A new clone must be recursive. For an existing clone,
initialize it once:

```bash
git submodule update --init --recursive
```

Build one language (for example Turkish):

```bash
cd source
source .venv-build/bin/activate
make -j"$(nproc)" firmware-TR
```

Build selected languages or every retained language:

```bash
./build.sh -l "DE EN TR"
./build.sh
```

The files are written to `source/hexfile/`, for example
`source/hexfile/TS101_TR.hex`. The `model=TS101` argument is optional because TS101 is
now the fixed and only target; another model name is rejected.

## Docker Build

**Docker (works everywhere):**

```bash
git clone --recurse-submodules https://github.com/oruhan/IronOS-TS101-Custom.git
cd IronOS-TS101-Custom
./scripts/deploy.sh
cd source/
./build.sh -l <PREFERRED_LANGUAGE>
```

Your firmware ends up in `source/hexfile/TS101_<PREFERRED_LANGUAGE>.hex`.

## 128x32 OLED previews

Render the main soldering states with the same generated bitmap font used by the
firmware. The renderer uses only Python's standard library:

```bash
make oled-preview
make test-oled-preview
```

PNG files are written to `development_resources/oled_previews/`. A captured raw
SSD1306 framebuffer can also be rendered directly:

```bash
python3 tools/oled_preview.py --framebuffer frame.bin --output frame.png
```

The raw input must contain 512 bytes in the display's four-page layout.

## Contributing

Contributions are welcome.

## License

GNU General Public License v3.0
