#include "power.hpp"
#include "SolderingCommon.h"
#include "ui_drawing.hpp"
#include <OperatingModes.h>
#ifdef OLED_128x32

namespace {
constexpr uint8_t TemperaturePanelWidth = 80;
constexpr uint8_t DividerX              = TemperaturePanelWidth;
constexpr uint8_t StatusPanelX          = DividerX + 3;
constexpr uint8_t StatusIconX           = OLED_WIDTH - 12;

uint8_t integerPlacesForTenths(const uint32_t valueX10) { return valueX10 >= 100 ? 2 : 1; }

void drawInputVoltage(const uint32_t voltageX10) {
  OLED::printNumber(voltageX10 / 10, integerPlacesForTenths(voltageX10), FontStyle::SMALL);
  OLED::print(SmallSymbolDot, FontStyle::SMALL);
  OLED::printNumber(voltageX10 % 10, 1, FontStyle::SMALL);
  OLED::print(SmallSymbolVolts, FontStyle::SMALL);
}

void drawWattage(const uint32_t wattageX10) {
  if (wattageX10 > 999) {
    OLED::printNumber(wattageX10 / 10, 3, FontStyle::SMALL);
  } else {
    OLED::printNumber(wattageX10 / 10, integerPlacesForTenths(wattageX10), FontStyle::SMALL);
    OLED::print(SmallSymbolDot, FontStyle::SMALL);
    OLED::printNumber(wattageX10 % 10, 1, FontStyle::SMALL);
  }
  OLED::print(SmallSymbolWatts, FontStyle::SMALL);
}

void drawBatteryOrHeatStatus(const int8_t powerSource, const uint32_t voltageX10, const uint32_t wattageX10) {
  OLED::setCursor(StatusIconX, 16);
  if (powerSource == 4) {
    const uint8_t cellCount = getSettingValue(SettingsOptions::MinDCVoltageCells) + 2;
    uint32_t      cellV     = voltageX10 / cellCount;
    if (cellV < getSettingValue(SettingsOptions::MinVoltageCells)) {
      cellV = getSettingValue(SettingsOptions::MinVoltageCells);
    }
    cellV -= getSettingValue(SettingsOptions::MinVoltageCells);
    OLED::drawBatteryFullHeight((cellV > 9 ? 9 : cellV) + 1);
  } else {
    OLED::drawHeatSymbol(X10WattsToPWM(wattageX10));
  }
}
} // namespace

void ui_draw_soldering_fullscreen_status(bool boostModeOn) {
  ui_draw_temperature_fullscreen_animated(getTipTemp(), 0, TemperatureAnimationSlot::Soldering);

  // Split the 128x32 display into an 80px temperature area and a 48px
  // live-power panel. The temperature still uses the full 32px height.
  OLED::fillArea(DividerX, 0, 1, OLED_HEIGHT, 0xFF);

  const int8_t   powerSource = getPowerSourceNumber();
  const uint32_t voltageX10  = getInputVoltageX10(getSettingValue(SettingsOptions::VoltageDiv), 0);
  const uint32_t wattageX10  = x10WattHistory.average();
  OLED::setCursor(StatusPanelX, 0);
  OLED::print(PowerSourceNames[powerSource], FontStyle::SMALL, 3);
  if (boostModeOn) {
    // A battery uses the complete 12x32 status column. Keep boost visible in
    // the gap after the three-character BAT source label instead of drawing
    // it under the full-height battery.
    OLED::setCursor(powerSource == 4 ? StatusPanelX + 20 : StatusIconX, 0);
    OLED::print(SmallSymbolPlus, FontStyle::SMALL);
  }

  OLED::setCursor(StatusPanelX, 8);
  drawInputVoltage(voltageX10);
  OLED::setCursor(StatusPanelX, 16);
  drawWattage(wattageX10);
  const TemperatureType_t target = getSettingValue(boostModeOn ? SettingsOptions::BoostTemp : SettingsOptions::SolderingTemp);
  ui_draw_temperature_small(target, StatusPanelX, 24);
  drawBatteryOrHeatStatus(powerSource, voltageX10, wattageX10);
}

void ui_draw_soldering_power_status(bool boost_mode_on) { ui_draw_soldering_fullscreen_status(boost_mode_on); }
#endif
