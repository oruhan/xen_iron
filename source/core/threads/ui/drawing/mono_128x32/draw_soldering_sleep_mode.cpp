#include "OperatingModes.h"
#include "power.hpp"
#include "ui_drawing.hpp"

#ifdef OLED_128x32
void ui_draw_soldering_detailed_sleep(TemperatureType_t tipTemp) {

  OLED::clearScreen();
  ui_draw_temperature_fullscreen(tipTemp);
  OLED::fillArea(80, 0, 1, OLED_HEIGHT, 0xFF);
  OLED::setCursor(83, 0);
  OLED::print(translatedString(Tr->SleepingAdvancedString), FontStyle::SMALL, 2);
  ui_draw_temperature_small(getSettingValue(SettingsOptions::SleepTemp), 98, 0);
  OLED::setCursor(83, 8);
  printVoltage();
  OLED::print(SmallSymbolVolts, FontStyle::SMALL);
  OLED::setCursor(83, 16);
  const int8_t powerSource = getPowerSourceNumber();
  OLED::print(PowerSourceNames[powerSource], FontStyle::SMALL, 3);
  OLED::setCursor(83, 24);
  const uint32_t wattageX10 = x10WattHistory.average();
  OLED::printNumber(wattageX10 / 10, 2, FontStyle::SMALL);
  OLED::print(SmallSymbolDot, FontStyle::SMALL);
  OLED::printNumber(wattageX10 % 10, 1, FontStyle::SMALL);
  OLED::print(SmallSymbolWatts, FontStyle::SMALL);
  OLED::setCursor(116, 16);
  OLED::drawHeatSymbol(X10WattsToPWM(wattageX10));

  OLED::refresh();
}

void ui_draw_soldering_basic_sleep(TemperatureType_t tipTemp) {

  ui_draw_soldering_detailed_sleep(tipTemp);
}
#endif
