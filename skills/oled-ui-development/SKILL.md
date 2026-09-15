---
name: oled-ui-development
description: Design, optimize, and visually verify compact monochrome OLED interfaces, especially page-buffered 128x32 and 128x64 firmware UIs. Use for embedded screen layout, bitmap-font rendering, framebuffer previews, clipping checks, and tiny-display UI review; do not use for ordinary web or mobile UI work.
---

# OLED UI Development

Treat the device framebuffer and its actual font/icon data as the visual source of truth. A desktop approximation using unrelated fonts is useful for ideation but cannot validate the firmware result.

## Workflow

1. Inspect display dimensions, pixel/page ordering, font metrics, drawing primitives, orientation handling, and RAM/flash limits before changing layouts.
2. Map each screen's information hierarchy. Give the primary live value the largest stable region; reserve fixed columns for status data so changing digit counts do not shift the entire layout.
3. Keep coordinates and repeated measurements in named constants. Cache sensor/settings values once per render pass when several elements use them.
4. Exercise the real edge cases: minimum and maximum values, digit-count transitions, longest localized label, each icon, alert/boost states, and every supported rotation.
5. Compile or run the repository's native tests after firmware changes.
6. Render PNG previews from the same bitmap fonts/icons or from a captured framebuffer, inspect the images at native size and integer zoom, then iterate on any collision, clipping, or weak hierarchy.

Prefer a project-native preview or simulator when one exists. Otherwise use `scripts/render_mono_framebuffer.py` for SSD1306-style page buffers. Read [references/monochrome-oled.md](references/monochrome-oled.md) when implementing or debugging page-buffer conversion, vertical masking, scaling, or clipping.

Do not silently change control logic, sensor behavior, temperature limits, or safety policy as part of a visual cleanup. Report such issues separately unless the user included them in scope.

## Acceptance criteria

- No draw operation writes outside the framebuffer.
- Dynamic content remains legible and non-overlapping for all tested states.
- One-pixel rules and icons land on intentional coordinates at native resolution.
- Preview pixels match the device's bit order and font assets.
- The firmware build and the preview tool's self-tests pass.
