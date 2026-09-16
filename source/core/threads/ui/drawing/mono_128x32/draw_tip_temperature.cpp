#include "OperatingModeUtilities.h"
#include "OperatingModes.h"
#include "SolderingCommon.h"
#include "TipThermoModel.h"
#include "ui_drawing.hpp"
#ifdef OLED_128x32

namespace {
struct TemperatureAnimationState {
  TemperatureType_t currentValue;
  TemperatureType_t previousValue;
  TickType_t         startedAt;
  TickType_t         lastFrameAt;
  bool               initialized;
};

TemperatureAnimationState temperatureAnimations[3] = {};
constexpr TickType_t TemperatureAnimationDuration  = TICKS_100MS * 2;
constexpr TickType_t TemperatureAnimationResetGap  = TICKS_100MS * 5;

uint8_t temperaturePlaces(const TemperatureType_t temperature) { return temperature >= 100 ? 3 : (temperature >= 10 ? 2 : 1); }

uint16_t temperatureDivisor(const uint8_t places) { return places == 3 ? 100 : (places == 2 ? 10 : 1); }

void drawFullscreenDigit(const uint8_t digit, const int16_t x, const int8_t yOffset) {
  constexpr uint8_t SourceGlyphWidth  = 12;
  constexpr uint8_t SourceGlyphHeight = 16;
  OLED::drawAreaClipped(x, yOffset, SourceGlyphWidth, SourceGlyphHeight, FontSectionInfo.font12_start_ptr + digit * 24, 2, 0, OLED_HEIGHT);
}

void drawFullscreenDigits(const TemperatureType_t temperature, const int16_t x, const int8_t yOffset) {
  constexpr uint8_t TemperatureDigitsWidth = 72;
  constexpr uint8_t FullscreenGlyphWidth   = 24;
  const uint8_t places                     = temperaturePlaces(temperature);
  int16_t       cursorX                    = x + (TemperatureDigitsWidth - places * FullscreenGlyphWidth) / 2;
  uint16_t      divisor                    = temperatureDivisor(places);
  for (uint8_t digitIndex = 0; digitIndex < places; digitIndex++) {
    const uint8_t digit = (temperature / divisor) % 10;
    drawFullscreenDigit(digit, cursorX, yOffset);
    cursorX += FullscreenGlyphWidth;
    divisor /= 10;
  }
}

void drawFullscreenDigitTransition(const TemperatureType_t temperature, const int16_t x, const TemperatureSlideFrame &frame) {
  constexpr uint8_t TemperatureDigitsWidth = 72;
  constexpr uint8_t FullscreenGlyphWidth   = 24;
  const uint8_t currentPlaces              = temperaturePlaces(temperature);
  const uint8_t previousPlaces             = temperaturePlaces(frame.previousValue);
  if (!frame.active) {
    drawFullscreenDigits(temperature, x, 0);
    return;
  }
  if (currentPlaces != previousPlaces) {
    drawFullscreenDigits(frame.previousValue, x, frame.previousOffset);
    drawFullscreenDigits(temperature, x, frame.currentOffset);
    return;
  }

  int16_t  cursorX         = x + (TemperatureDigitsWidth - currentPlaces * FullscreenGlyphWidth) / 2;
  uint16_t divisor        = temperatureDivisor(currentPlaces);
  for (uint8_t digitIndex = 0; digitIndex < currentPlaces; digitIndex++) {
    const uint8_t previousDigit = (frame.previousValue / divisor) % 10;
    const uint8_t currentDigit  = (temperature / divisor) % 10;
    if (previousDigit == currentDigit) {
      drawFullscreenDigit(currentDigit, cursorX, 0);
    } else {
      drawFullscreenDigit(previousDigit, cursorX, frame.previousOffset);
      drawFullscreenDigit(currentDigit, cursorX, frame.currentOffset);
    }
    cursorX += FullscreenGlyphWidth;
    divisor /= 10;
  }
}
} // namespace

void ui_get_temperature_slide_frame(const TemperatureType_t temperature, const TemperatureAnimationSlot slot, const uint8_t height, TemperatureSlideFrame &frame) {
  TemperatureAnimationState &state = temperatureAnimations[static_cast<uint8_t>(slot)];
  const TickType_t now              = xTaskGetTickCount();
  if (!state.initialized || now - state.lastFrameAt > TemperatureAnimationResetGap) {
    state.currentValue  = temperature;
    state.previousValue = temperature;
    state.startedAt     = now;
    state.initialized   = true;
  } else if (temperature != state.currentValue) {
    state.previousValue = state.currentValue;
    state.currentValue  = temperature;
    state.startedAt     = now;
  }
  state.lastFrameAt = now;

  const TickType_t elapsed = now - state.startedAt;
  if (elapsed >= TemperatureAnimationDuration || state.previousValue == state.currentValue) {
    frame.previousValue  = state.previousValue;
    frame.previousOffset = 0;
    frame.currentOffset  = 0;
    frame.active         = false;
    return;
  }
  const uint8_t progress = (elapsed * height) / TemperatureAnimationDuration;
  frame.previousValue  = state.previousValue;
  frame.previousOffset = static_cast<int8_t>(progress);
  frame.currentOffset  = static_cast<int8_t>(progress - height);
  frame.active         = true;
}

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

void ui_draw_temperature_fullscreen_animated(const TemperatureType_t temperature, const uint8_t x, const TemperatureAnimationSlot slot) {
  static const uint8_t DegreeSymbol[]       = {0x0E, 0x0A, 0x0E};
  constexpr uint8_t TemperaturePanelWidth  = 80;
  constexpr uint8_t DegreeSymbolOffset     = 70;
  constexpr uint8_t UnitSymbolOffset       = 74;
  TemperatureSlideFrame frame;
  ui_get_temperature_slide_frame(temperature, slot, OLED_HEIGHT, frame);

  OLED::fillArea(x, 0, TemperaturePanelWidth, OLED_HEIGHT, 0);
  drawFullscreenDigitTransition(temperature, x, frame);
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
