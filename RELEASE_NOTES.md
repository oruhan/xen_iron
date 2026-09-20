# xen_iron v2.23 — First Stable Release

This is the first stable release of **xen_iron**, a TS101-focused custom firmware based on IronOS v2.23 and designed specifically for the built-in 128×32 OLED.

## Highlights

- Redesigned the 128×32 home and soldering screens to use the available pixels efficiently while keeping the interface readable.
- Added smooth, deterministic animations to the soldering and settings icons.
- Added inverted press feedback while keeping the complete pixel-perfect button outline visible.
- Added directional, digit-by-digit temperature rolling: only digits that change are animated.
- Replaced linear movement with smooth ease-in-out transitions throughout the interface.
- Added animated transitions between soldering, temperature adjustment, warnings, and the home screen without intermediate black frames.

## Temperature and safety

- Enforced a hard maximum temperature of **380 °C**, including Boost mode and final heater-output guarding.
- Improved temperature alignment, vertical centering, degree symbol rendering, and spacing between `°` and `C`/`F`.
- Simplified the temperature adjustment screen to show only the target temperature and its controls.
- Added an animated missing-tip warning when soldering is requested without a tip.
- Added localized missing-tip text for German, English, Spanish, French, Japanese, Russian, and Turkish.

## Power and status display

- Added full-height battery indicators to the home and soldering screens.
- Improved voltage and wattage alignment for both one-digit and two-digit values.
- Improved hot-tip temperature presentation on the home screen.
- Consumed the first physical button press used to wake the display, preventing accidental actions immediately after wake-up.

## OLED asset workflow

- Moved OLED icons and every animation frame into independently editable PBM files.
- Added generated firmware asset tables and automatic asset validation.
- Added a framebuffer-based preview tool for static screens, animated states, transitions, clipping checks, rotation, and button-press states.
- Included PNG previews for the complete 128×32 interface.

## Available Languages

| Firmware file     | Language |
| ----------------- | -------- |
| `TS101_DE.hex`    | German   |
| `TS101_EN.hex`    | English  |
| `TS101_ES.hex`    | Spanish  |
| `TS101_FR.hex`    | French   |
| `TS101_JA_JP.hex` | Japanese |
| `TS101_RU.hex`    | Russian  |
| `TS101_TR.hex`    | Turkish  |

## Installation

1. Download the `.hex` file for your preferred language.
2. Disconnect the TS101 from power.
3. Hold the **A button** while connecting the USB-C cable.
4. The TS101 will appear as a USB storage device.
5. Copy the downloaded `.hex` file to the device.
6. Wait for the file extension to change to `.RDY`.
7. Disconnect the USB cable and power the TS101 normally.

If the file changes to `.ERR`, copy the `.hex` file again without deleting the `.ERR` file first.

> [!NOTE]
> Existing settings should normally remain stored when updating through the standard HEX flashing method. Keeping a record of important calibration values before updating is still recommended.

## Credits

Based on the IronOS project and the  
[IronOS-TS101-FullOLED](https://github.com/vtolvr/IronOS-TS101-FullOLED) fork.
