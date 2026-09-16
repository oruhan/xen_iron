#include "ui_drawing.hpp"

#ifdef OLED_128x32
void ui_draw_temperature_change(void) {
  constexpr uint8_t TemperatureX = 24;
  const char       *leftSymbol    = OLED::getRotation() ? LargeSymbolPlus : LargeSymbolMinus;
  const char       *rightSymbol   = OLED::getRotation() ? LargeSymbolMinus : LargeSymbolPlus;

  OLED::setCursor(0, 8);
  OLED::print(leftSymbol, FontStyle::LARGE);
  ui_draw_temperature_fullscreen_animated(getSettingValue(SettingsOptions::SolderingTemp), TemperatureX, TemperatureAnimationSlot::Adjust);
  OLED::setCursor(OLED_WIDTH - 12, 8);
  OLED::print(rightSymbol, FontStyle::LARGE);
}
#endif
