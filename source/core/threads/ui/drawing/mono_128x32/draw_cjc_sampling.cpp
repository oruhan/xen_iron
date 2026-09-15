#include "ui_drawing.hpp"
#include "TipThermoModel.h"
#ifdef OLED_128x32
void ui_draw_cjc_sampling(const uint8_t num_dots) {
  OLED::setCursor(0, 0);
  OLED::print(translatedString(Tr->CJCCalibrating), FontStyle::SMALL, 20);
  OLED::fillArea(0, 8, OLED_WIDTH, 8, 0x81);
  const uint8_t progressWidth = num_dots > 4 ? 126 : (num_dots * 126) / 4;
  OLED::fillArea(1, 8, progressWidth, 8, 0x7E);
  OLED::setCursor(0, 16);
  OLED::print(DebugMenu[5], FontStyle::SMALL, 3);
  ui_draw_temperature_small(TipThermoModel::getTipInC(), 24, 16);
  OLED::setCursor(78, 16);
  OLED::printNumber(num_dots * 4, 2, FontStyle::SMALL);
  OLED::print(SmallSymbolSlash, FontStyle::SMALL);
  OLED::printNumber(16, 2, FontStyle::SMALL);
  OLED::setCursor(0, 24);
  OLED::print(DebugMenu[6], FontStyle::SMALL, 3);
  ui_draw_temperature_small(getHandleTemperature(0) / 10, 24, 24);
  OLED::setCursor(66, 24);
  OLED::print(DebugMenu[12], FontStyle::SMALL, 5);
  OLED::printNumber(getSettingValue(SettingsOptions::CalibrationOffset), 5, FontStyle::SMALL);
}
#endif
