#include "ui_drawing.hpp"
#ifdef OLED_128x32
void ui_draw_power_source_icon(void) {
#ifdef POW_DC
  if (getIsPoweredByDCIN() && getSettingValue(SettingsOptions::MinDCVoltageCells)) {
    // User is on a lithium battery
    // we need to calculate which of the 10 levels they are on
    uint8_t  cellCount = getSettingValue(SettingsOptions::MinDCVoltageCells) + 2;
    uint32_t cellV     = getInputVoltageX10(getSettingValue(SettingsOptions::VoltageDiv), 0) / cellCount;
    // Should give us approx cell voltage X10
    // Range is 42 -> Minimum voltage setting (systemSettings.minVoltageCells) = 9 steps therefore we will use battery 0-9
    if (cellV < getSettingValue(SettingsOptions::MinVoltageCells)) {
      cellV = getSettingValue(SettingsOptions::MinVoltageCells);
    }
    cellV -= getSettingValue(SettingsOptions::MinVoltageCells); // Should leave us a number of 0-9
    if (cellV > 9) {
      cellV = 9;
    }
    OLED::drawBatteryFullHeight(cellV + 1);
    return;
  }
#endif

#if defined(POW_DC) || defined(POW_PD) || defined(POW_QC) || defined(POW_PD_EXT)
  // Show the rounded input voltage for USB, PD and ordinary DC supplies. A
  // single digit is vertically centred; two digits are stacked in the 12x32
  // icon slot. Only an explicitly configured battery keeps the battery icon.
  const uint16_t inputVolts = (getInputVoltageX10(getSettingValue(SettingsOptions::VoltageDiv), 0) + 5) / 10;
  const int16_t  xPos       = OLED::getCursorX();
  if (inputVolts < 10) {
    OLED::setCursor(xPos, 8);
    OLED::printNumber(inputVolts, 1, FontStyle::LARGE);
  } else {
    OLED::printNumber(inputVolts / 10, 1, FontStyle::LARGE);
    OLED::setCursor(xPos, 16);
    OLED::printNumber(inputVolts % 10, 1, FontStyle::LARGE);
  }
#endif
}

#endif
