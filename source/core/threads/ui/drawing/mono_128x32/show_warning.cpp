#include "Buttons.hpp"
#include "OperatingModeUtilities.h"
#include "OperatingModes.h"
#ifdef OLED_128x32
bool warnUser(const char *warning, const ButtonState buttons) {
  OLED::clearScreen();
  OLED::printWholeScreen(warning);
  // Also timeout after 5 seconds
  if ((xTaskGetTickCount() - lastButtonTime) > TICKS_SECOND * 5) {
    return true;
  }
  return buttons != BUTTON_NONE;
}

bool warnUserWithIcon(const char *warning, const ButtonState buttons) {
  constexpr uint8_t ContentY = (OLED_HEIGHT - 16) / 2;
  constexpr uint8_t TextX    = 28;
  OLED::clearScreen();
  OLED::drawArea(0, ContentY, 24, 16, WarningBlock24);

  OLED::setCursor(TextX, ContentY);
  if (warning[0] == '\x01') {
    // A leading newline is the translation format's large-font marker. This
    // is needed for languages whose glyphs are unavailable in the 6x8 font.
    OLED::print(warning, FontStyle::SMALL, 255, TextX);
  } else if (const char *secondLine = strchr(warning, '\x01')) {
    OLED::print(warning, FontStyle::SMALL, secondLine - warning, TextX);
    OLED::setCursor(TextX, ContentY + 8);
    OLED::print(secondLine + 1, FontStyle::SMALL, 255, TextX);
  } else {
    OLED::print(warning, FontStyle::SMALL, 255, TextX);
  }

  if ((xTaskGetTickCount() - lastButtonTime) > TICKS_SECOND * 5) {
    return true;
  }
  return buttons != BUTTON_NONE;
}
#endif
