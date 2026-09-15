#include "OperatingModeUtilities.h"
#include "OperatingModes.h"
#include "SolderingCommon.h"
#include "TipThermoModel.h"
#ifdef OLED_128x32

void ui_draw_tip_temperature(bool symbol, const FontStyle font) {
  // Draw tip temp handling unit conversion & tolerance near setpoint
  TemperatureType_t Temp = getTipTemp();

  OLED::printNumber(Temp, 3, font); // Draw the tip temp out
  if (symbol) {
    // For big font, can draw nice symbols, otherwise fall back to chars
    OLED::printSymbolDeg(font == FontStyle::LARGE ? FontStyle::EXTRAS : font);
  }
}

void ui_draw_temperature_fullscreen(const TemperatureType_t temperature, const uint8_t x) {
  static const uint8_t DegreeSymbol[]       = {0x0E, 0x0A, 0x0E};
  constexpr uint8_t TemperatureDigitsWidth = 72;
  constexpr uint8_t FullscreenGlyphWidth   = 24;
  constexpr uint8_t DegreeSymbolOffset     = 70;
  constexpr uint8_t UnitSymbolOffset       = 74;
  const uint8_t places                     = temperature >= 100 ? 3 : (temperature >= 10 ? 2 : 1);
  const uint8_t horizontalOffset            = (TemperatureDigitsWidth - places * FullscreenGlyphWidth) / 2;

  OLED::setCursor(x + horizontalOffset, 0);
  OLED::printNumber(temperature, places, FontStyle::FULLSCREEN);

  // A compact 3x3 degree ring fits into the last digit's blank right margin.
  // Keep one empty pixel between the degree mark and the C/F glyph.
  OLED::drawArea(x + DegreeSymbolOffset, 0, sizeof(DegreeSymbol), 8, DegreeSymbol);
  OLED::setCursor(x + UnitSymbolOffset, 0);
  OLED::printSymbolDeg(FontStyle::SMALL);
}

void ui_draw_temperature_small(const TemperatureType_t temperature, const uint8_t x, const uint8_t y) {
  static const uint8_t DegreeSymbol[] = {0x0E, 0x0A, 0x0E};
  const uint8_t places                = temperature >= 100 ? 3 : (temperature >= 10 ? 2 : 1);
  const uint8_t degreeX               = x + places * 6;

  OLED::setCursor(x, y);
  OLED::printNumber(temperature, places, FontStyle::SMALL);
  OLED::drawArea(degreeX, y, sizeof(DegreeSymbol), 8, DegreeSymbol);
  OLED::setCursor(degreeX + 4, y);
  OLED::printSymbolDeg(FontStyle::SMALL);
}

void ui_draw_tip_temperature_fullscreen(void) { ui_draw_temperature_fullscreen(getTipTemp(), 0); }
#endif
