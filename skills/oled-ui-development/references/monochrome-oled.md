# Monochrome OLED framebuffer notes

## SSD1306-style page layout

A common monochrome buffer stores eight vertical pixels per byte. For a display of width `W` and height `H`, the buffer size is `W * ceil(H / 8)` bytes. Byte index `(y // 8) * W + x` contains pixel `(x, y)` in bit `y % 8`; bit zero is normally the top pixel of that page.

Confirm this convention in the target driver. Some controllers or libraries transpose columns, reverse bit order, apply a column offset, or perform rotation in controller commands rather than in RAM.

## Rendering invariants

- Page-aligned bitmap assets are usually stored one horizontal page at a time, not as scanlines.
- A 12x16 glyph therefore occupies 24 bytes: 12 columns for the upper page followed by 12 for the lower page.
- Scaling a page bitmap must scale pixels, not bytes. Doubling a byte horizontally alone does not double its vertical bits.
- When clipping a bitmap at the left or right edge, adjust the source-column range but preserve each page's source stride.
- Rectangle end coordinates are often exclusive. Check aligned end positions such as 8, 16, and 32 because an unguarded modulo mask can turn them into empty masks.
- A symbol renderer that clears or masks part of an icon must offset that mask by the symbol's actual cursor `y`; hard-coding row zero breaks when the icon moves to a lower page.

## Visual test matrix

For numeric screens, include `0`, `9`, `10`, `99`, `100`, and the domain maximum where applicable. Include both a zero-output state and a maximum-output state for gauges. Test the longest localized strings and all status-icon variants. If controller rotation is supported, verify both orientations on the device or on a correctly transformed framebuffer.

Inspect both the native-resolution image and an integer nearest-neighbour enlargement. Integer scaling exposes individual pixel decisions without introducing interpolation artifacts.
