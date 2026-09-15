#include "OperatingModes.h"
#include "ui_drawing.hpp"
#include "TipThermoModel.h"
#ifdef OLED_128x32

void ui_draw_homescreen_detailed(TemperatureType_t tipTemp) {
  constexpr uint8_t DividerX    = 80;
  constexpr uint8_t StatusX     = DividerX + 3;
  const uint32_t    voltageX10  = getInputVoltageX10(getSettingValue(SettingsOptions::VoltageDiv), 0);
  const int8_t      powerSource = getPowerSourceNumber();
  TemperatureType_t handleTemp  = getHandleTemperature(0) / 10;
  if (getSettingValue(SettingsOptions::TemperatureInF)) {
    handleTemp = TipThermoModel::convertCtoF(handleTemp);
  }

  if (isTipDisconnected()) {
    OLED::drawArea(0, 0, 56, 32, disconnectedTip);
    OLED::fillArea(57, 0, 1, OLED_HEIGHT, 0xFF);
    OLED::setCursor(61, 0);
    OLED::print(PowerSourceNames[powerSource], FontStyle::SMALL, 3);
    OLED::setCursor(61, 8);
    OLED::printNumber(voltageX10 / 10, 2, FontStyle::SMALL);
    OLED::print(SmallSymbolDot, FontStyle::SMALL);
    OLED::printNumber(voltageX10 % 10, 1, FontStyle::SMALL);
    OLED::print(SmallSymbolVolts, FontStyle::SMALL);
    ui_draw_temperature_small(handleTemp, 61, 16);
    ui_draw_temperature_small(getSettingValue(SettingsOptions::SolderingTemp), 61, 24);
  } else {
    if (!(getSettingValue(SettingsOptions::CoolingTempBlink) && (tipTemp > 55) && (xTaskGetTickCount() % 1000 < 300))) {
      ui_draw_tip_temperature_fullscreen();
    }
    OLED::fillArea(DividerX, 0, 1, OLED_HEIGHT, 0xFF);
    ui_draw_temperature_small(getSettingValue(SettingsOptions::SolderingTemp), StatusX, 0);
    OLED::setCursor(StatusX, 8);
    OLED::printNumber(voltageX10 / 10, 2, FontStyle::SMALL);
    OLED::print(SmallSymbolDot, FontStyle::SMALL);
    OLED::printNumber(voltageX10 % 10, 1, FontStyle::SMALL);
    OLED::print(SmallSymbolVolts, FontStyle::SMALL);
    OLED::setCursor(StatusX, 16);
    OLED::print(PowerSourceNames[powerSource], FontStyle::SMALL, 3);
    ui_draw_temperature_small(handleTemp, StatusX, 24);
  }
}
#endif
