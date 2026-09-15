#include "OperatingModes.h"
#include "power.hpp"
#include "ui_drawing.hpp"

#ifdef OLED_128x32
namespace {
void drawVoltage(const uint32_t voltageX10) {
  OLED::printNumber(voltageX10 / 10, 2, FontStyle::SMALL);
  OLED::print(SmallSymbolDot, FontStyle::SMALL);
  OLED::printNumber(voltageX10 % 10, 1, FontStyle::SMALL);
  OLED::print(SmallSymbolVolts, FontStyle::SMALL);
}

void drawWattage(const uint32_t wattageX10) {
  if (wattageX10 > 999) {
    OLED::printNumber(wattageX10 / 10, 3, FontStyle::SMALL);
  } else {
    OLED::printNumber(wattageX10 / 10, 2, FontStyle::SMALL);
    OLED::print(SmallSymbolDot, FontStyle::SMALL);
    OLED::printNumber(wattageX10 % 10, 1, FontStyle::SMALL);
  }
  OLED::print(SmallSymbolWatts, FontStyle::SMALL);
}
} // namespace

void ui_draw_soldering_profile_advanced(TemperatureType_t tipTemp, TemperatureType_t profileCurrentTargetTemp, uint32_t phaseElapsedSeconds, uint32_t phase, const uint32_t phaseTimeGoal) {
  static const uint8_t DegreeSymbol[] = {0x0E, 0x0A, 0x0E};
  const uint8_t  profilePhases = getSettingValue(SettingsOptions::ProfilePhases);
  const uint32_t voltageX10    = getInputVoltageX10(getSettingValue(SettingsOptions::VoltageDiv), 0);
  const uint32_t wattageX10    = x10WattHistory.average();

  OLED::setCursor(0, 0);
  OLED::printNumber(tipTemp, 3, FontStyle::SMALL);
  OLED::print(SmallSymbolSlash, FontStyle::SMALL);
  OLED::printNumber(profileCurrentTargetTemp, 3, FontStyle::SMALL);
  OLED::drawArea(42, 0, sizeof(DegreeSymbol), 8, DegreeSymbol);
  OLED::setCursor(46, 0);
  OLED::printSymbolDeg(FontStyle::SMALL);
  OLED::setCursor(54, 0);
  OLED::printNumber(phase, 1, FontStyle::SMALL);
  OLED::print(SmallSymbolSlash, FontStyle::SMALL);
  OLED::printNumber(profilePhases, 1, FontStyle::SMALL);
  OLED::setCursor(83, 0);
  OLED::print(PowerSourceNames[getPowerSourceNumber()], FontStyle::SMALL, 3);

  OLED::setCursor(0, 8);
  OLED::printNumber(phaseElapsedSeconds / 60, 1, FontStyle::SMALL);
  OLED::print(SmallSymbolColon, FontStyle::SMALL);
  OLED::printNumber(phaseElapsedSeconds % 60, 2, FontStyle::SMALL, false);
  OLED::print(SmallSymbolSlash, FontStyle::SMALL);
  OLED::printNumber(phaseTimeGoal / 60, 1, FontStyle::SMALL);
  OLED::print(SmallSymbolColon, FontStyle::SMALL);
  OLED::printNumber(phaseTimeGoal % 60, 2, FontStyle::SMALL, false);
  OLED::setCursor(62, 8);
  drawVoltage(voltageX10);
  OLED::setCursor(98, 8);
  drawWattage(wattageX10);

  // A page-aligned progress bar uses every pixel without adding visual noise.
  OLED::fillArea(0, 16, 112, 8, 0x81);
  if (phaseTimeGoal > 0) {
    const uint32_t boundedElapsed = phaseElapsedSeconds > phaseTimeGoal ? phaseTimeGoal : phaseElapsedSeconds;
    const uint8_t  progressWidth  = (boundedElapsed * 110) / phaseTimeGoal;
    OLED::fillArea(1, 16, progressWidth, 8, 0x7E);
  }
  OLED::setCursor(116, 16);
  OLED::drawHeatSymbol(X10WattsToPWM(wattageX10));

  OLED::setCursor(0, 24);
  if (phase == 0) {
    OLED::print(translatedString(Tr->ProfilePreheatString), FontStyle::SMALL, 12);
  } else if (phase > profilePhases) {
    OLED::print(translatedString(Tr->ProfileCooldownString), FontStyle::SMALL, 12);
  } else {
    ui_draw_temperature_small(profileCurrentTargetTemp, 0, 24);
  }
}

#endif
