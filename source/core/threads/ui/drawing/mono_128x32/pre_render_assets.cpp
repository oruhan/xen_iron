#include "ui_drawing.hpp"
#ifdef OLED_128x32

uint8_t buttonAF[sizeof(buttonA)];
uint8_t buttonBF[sizeof(buttonB)];
uint8_t disconnectedTipF[sizeof(disconnectedTip)];

void ui_pre_render_assets(void) {
  for (int row = 0; row < 4; row++) {
    for (int x = 0; x < 56; x++) {
      buttonAF[(row * 56) + x]          = buttonA[(row * 56) + (55 - x)];
      buttonBF[(row * 56) + x]          = buttonB[(row * 56) + (55 - x)];
      disconnectedTipF[(row * 56) + x] = disconnectedTip[(row * 56) + (55 - x)];
    }
  }
}
#endif
