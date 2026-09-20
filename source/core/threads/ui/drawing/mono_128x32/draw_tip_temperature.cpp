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
constexpr uint8_t    TemperaturePanelWidth         = 80;
constexpr uint8_t    FullscreenGlyphWidth          = 24;
constexpr uint8_t    FullscreenGlyphVisibleWidth   = 22;
constexpr uint8_t    FullscreenGlyphLeftPadding    = 2;
constexpr uint8_t    FullscreenGlyphVerticalOffset = 2;
constexpr uint8_t    DegreeWidth                   = sizeof(DegreeSymbol);
constexpr uint8_t    UnitVisibleWidth              = 4;
constexpr uint8_t    SymbolGap                     = 1;

struct FullscreenTemperatureLayout {
  int16_t digitX;
  int16_t degreeX;
  int16_t unitX;
};

uint8_t easeInOutPosition(const TickType_t elapsed, const TickType_t duration, const uint8_t distance) {
  // Rounded integer smoothstep: slow at both ends and fastest halfway through.
  if (duration == 0 || elapsed >= duration) {
    return distance;
  }
  const uint32_t denominator = uint32_t(duration) * duration * duration;
  const uint32_t numerator   = uint32_t(distance) * elapsed * elapsed * (3U * duration - 2U * elapsed);
  return (numerator + denominator / 2U) / denominator;
}

uint8_t temperaturePlaces(const TemperatureType_t temperature) { return temperature >= 100 ? 3 : (temperature >= 10 ? 2 : 1); }

uint16_t temperatureDivisor(const uint8_t places) { return places == 3 ? 100 : (places == 2 ? 10 : 1); }

void fullscreenTemperatureLayout(const TemperatureType_t temperature, const int16_t panelX, FullscreenTemperatureLayout &layout) {
  const uint8_t places            = temperaturePlaces(temperature);
  const uint8_t digitsVisualWidth = (places - 1) * FullscreenGlyphWidth + FullscreenGlyphVisibleWidth;
  const uint8_t contentWidth      = digitsVisualWidth + SymbolGap + DegreeWidth + SymbolGap + UnitVisibleWidth;
  const int16_t visibleStart      = panelX + (TemperaturePanelWidth - contentWidth) / 2;
  layout.digitX                 = visibleStart - FullscreenGlyphLeftPadding;
  layout.degreeX                = visibleStart + digitsVisualWidth + SymbolGap;
  layout.unitX                  = visibleStart + digitsVisualWidth + SymbolGap + DegreeWidth + SymbolGap;
}

void drawFullscreenDigit(const uint8_t digit, const int16_t x, const int8_t yOffset) {
  constexpr uint8_t SourceGlyphWidth  = 12;
  constexpr uint8_t SourceGlyphHeight = 16;
  OLED::drawAreaClipped(x, FullscreenGlyphVerticalOffset + yOffset, SourceGlyphWidth, SourceGlyphHeight, FontSectionInfo.font12_start_ptr + digit * 24, 2, 0,
                        OLED_HEIGHT);
}

void drawFullscreenUnit(const int16_t x) {
  static constexpr uint8_t UnitColumns[] = {0, 1, 3, 4};
  const char               *unitSymbol   = getSettingValue(SettingsOptions::TemperatureInF) ? SmallSymbolDegF : SmallSymbolDegC;
  const uint8_t            *source       = FontSectionInfo.font06_start_ptr + (unitSymbol[0] - 2) * 6;
  uint8_t                   compactUnit[sizeof(UnitColumns)];
  for (uint8_t column = 0; column < sizeof(UnitColumns); column++) {
    compactUnit[column] = source[UnitColumns[column]];
  }
  OLED::drawArea(x, FullscreenGlyphVerticalOffset, sizeof(compactUnit), 8, compactUnit);
}

void drawFullscreenDigits(const TemperatureType_t temperature, const int16_t x, const int8_t yOffset) {
  const uint8_t places = temperaturePlaces(temperature);
  FullscreenTemperatureLayout layout;
  fullscreenTemperatureLayout(temperature, x, layout);
  int16_t  cursorX = layout.digitX;
  uint16_t divisor = temperatureDivisor(places);
  for (uint8_t digitIndex = 0; digitIndex < places; digitIndex++) {
    const uint8_t digit = (temperature / divisor) % 10;
    drawFullscreenDigit(digit, cursorX, yOffset);
    cursorX += FullscreenGlyphWidth;
    divisor /= 10;
  }
}

void drawFullscreenDigitTransition(const TemperatureType_t temperature, const int16_t x, const TemperatureSlideFrame &frame) {
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

  FullscreenTemperatureLayout layout;
  fullscreenTemperatureLayout(temperature, x, layout);
  int16_t  cursorX         = layout.digitX;
  uint16_t divisor         = temperatureDivisor(currentPlaces);
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
  const uint8_t progress = easeInOutPosition(elapsed, TemperatureAnimationDuration, height);
  frame.previousValue = state.previousValue;
  if (state.currentValue > state.previousValue) {
    // Natural counter motion: increasing values roll upward, with the new
    // digit entering from below.
    frame.previousOffset = -static_cast<int8_t>(progress);
    frame.currentOffset  = static_cast<int8_t>(height - progress);
  } else {
    // Decreasing values reverse the same motion instead of rolling down again.
    frame.previousOffset = static_cast<int8_t>(progress);
    frame.currentOffset  = static_cast<int8_t>(progress - height);
  }
  frame.active = true;
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
  FullscreenTemperatureLayout layout;
  fullscreenTemperatureLayout(temperature, x, layout);
  drawFullscreenDigits(temperature, x, 0);
  OLED::drawArea(layout.degreeX, FullscreenGlyphVerticalOffset, DegreeWidth, 8, DegreeSymbol);
  drawFullscreenUnit(layout.unitX);
}

void ui_draw_temperature_fullscreen_animated(const TemperatureType_t temperature, const uint8_t x, const TemperatureAnimationSlot slot) {
  TemperatureSlideFrame frame;
  ui_get_temperature_slide_frame(temperature, slot, OLED_HEIGHT, frame);

  OLED::fillArea(x, 0, TemperaturePanelWidth, OLED_HEIGHT, 0);
  drawFullscreenDigitTransition(temperature, x, frame);
  FullscreenTemperatureLayout layout;
  fullscreenTemperatureLayout(temperature, x, layout);
  OLED::drawArea(layout.degreeX, FullscreenGlyphVerticalOffset, DegreeWidth, 8, DegreeSymbol);
  drawFullscreenUnit(layout.unitX);
}

void ui_draw_temperature_small(const TemperatureType_t temperature, const uint8_t x, const uint8_t y) {
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
