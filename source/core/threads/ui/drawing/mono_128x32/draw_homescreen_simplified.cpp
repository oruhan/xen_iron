#include "SolderingCommon.h"
#include "ui_drawing.hpp"

#ifdef OLED_128x32

extern uint8_t buttonAF[sizeof(buttonA)];
extern uint8_t buttonBF[sizeof(buttonB)];
extern uint8_t disconnectedTipF[sizeof(disconnectedTip)];

namespace {
constexpr uint8_t CircleWidth       = 56;
constexpr uint8_t SourceGlyphWidth  = 6;
constexpr uint8_t TallGlyphWidth    = 8;
constexpr uint8_t DegreeAndGapWidth = 4;

uint8_t temperaturePlaces(const TemperatureType_t temperature) { return temperature >= 100 ? 3 : (temperature >= 10 ? 2 : 1); }

uint16_t temperatureDivisor(const uint8_t places) { return places == 3 ? 100 : (places == 2 ? 10 : 1); }

int16_t temperatureTextX(const int16_t circleX, const TemperatureType_t temperature) {
  const uint8_t textWidth = temperaturePlaces(temperature) * TallGlyphWidth + DegreeAndGapWidth + TallGlyphWidth;
  return circleX + (CircleWidth - textWidth) / 2;
}

void drawTallSmallGlyph(const int16_t x, const uint8_t *glyph, const int8_t yOffset = 0) {
  static constexpr uint8_t SourceColumns[] = {0, 1, 1, 2, 3, 4, 4, 5};
  constexpr uint8_t StretchedWidth         = sizeof(SourceColumns);
  uint8_t stretchedGlyph[StretchedWidth * 2] = {0};
  for (uint8_t column = 0; column < StretchedWidth; column++) {
    uint16_t stretchedColumn = 0;
    const uint8_t sourceColumn = SourceColumns[column];
    for (uint8_t sourceBit = 0; sourceBit < 7; sourceBit++) {
      if (glyph[sourceColumn] & (1U << sourceBit)) {
        stretchedColumn |= 3U << (sourceBit * 2 + 1);
      }
    }
    stretchedGlyph[column]                  = stretchedColumn & 0xFF;
    stretchedGlyph[column + StretchedWidth] = stretchedColumn >> 8;
  }
  OLED::drawAreaClipped(x, 8 + yOffset, StretchedWidth, 16, stretchedGlyph, 1, 8, 24);
}

void drawTallTemperatureDigits(const int16_t circleX, const TemperatureType_t temperature, const int8_t yOffset) {
  const uint8_t places = temperaturePlaces(temperature);
  int16_t       cursorX = temperatureTextX(circleX, temperature);
  uint16_t      divisor = temperatureDivisor(places);
  for (uint8_t digitIndex = 0; digitIndex < places; digitIndex++) {
    const uint8_t digit = (temperature / divisor) % 10;
    drawTallSmallGlyph(cursorX, FontSectionInfo.font06_start_ptr + digit * SourceGlyphWidth, yOffset);
    cursorX += TallGlyphWidth;
    divisor /= 10;
  }
}

void drawTallTemperatureTransition(const int16_t circleX, const TemperatureType_t temperature, const TemperatureSlideFrame &frame) {
  const uint8_t currentPlaces  = temperaturePlaces(temperature);
  const uint8_t previousPlaces = temperaturePlaces(frame.previousValue);
  if (!frame.active) {
    drawTallTemperatureDigits(circleX, temperature, 0);
    return;
  }
  if (currentPlaces != previousPlaces) {
    drawTallTemperatureDigits(circleX, frame.previousValue, frame.previousOffset);
    drawTallTemperatureDigits(circleX, temperature, frame.currentOffset);
    return;
  }

  int16_t  cursorX         = temperatureTextX(circleX, temperature);
  uint16_t divisor        = temperatureDivisor(currentPlaces);
  for (uint8_t digitIndex = 0; digitIndex < currentPlaces; digitIndex++) {
    const uint8_t previousDigit = (frame.previousValue / divisor) % 10;
    const uint8_t currentDigit  = (temperature / divisor) % 10;
    if (previousDigit == currentDigit) {
      drawTallSmallGlyph(cursorX, FontSectionInfo.font06_start_ptr + currentDigit * SourceGlyphWidth);
    } else {
      drawTallSmallGlyph(cursorX, FontSectionInfo.font06_start_ptr + previousDigit * SourceGlyphWidth, frame.previousOffset);
      drawTallSmallGlyph(cursorX, FontSectionInfo.font06_start_ptr + currentDigit * SourceGlyphWidth, frame.currentOffset);
    }
    cursorX += TallGlyphWidth;
    divisor /= 10;
  }
}

void drawHotTipStatus(const int16_t x, const uint8_t *circle, const TemperatureType_t tipTemp, const bool showTemperature) {
  static const uint8_t DegreeSymbol[] = {0x0E, 0x0A, 0x0E};
  TemperatureSlideFrame frame;
  ui_get_temperature_slide_frame(tipTemp, TemperatureAnimationSlot::Home, 16, frame);

  OLED::drawArea(x, 0, 56, 32, circle);
  // Remove the original button artwork while preserving the circular outline.
  OLED::drawFilledRect(x + 10, 4, x + 46, 8, true);
  OLED::fillArea(x + 8, 8, 40, 16, 0);
  OLED::drawFilledRect(x + 10, 24, x + 46, 28, true);
  // Keep the bottom stroke one pixel inside the physical panel so it is not
  // cropped by the TS101 OLED's last scan line.
  OLED::drawFilledRect(x + 8, 30, x + 48, 32, true);
  OLED::drawFilledRect(x + 13, 30, x + 42, 31, false);
  if (showTemperature) {
    drawTallTemperatureTransition(x, tipTemp, frame);
    const int16_t degreeX = temperatureTextX(x, tipTemp) + temperaturePlaces(tipTemp) * TallGlyphWidth;
    const char *unitSymbol = getSettingValue(SettingsOptions::TemperatureInF) ? SmallSymbolDegF : SmallSymbolDegC;
    OLED::drawArea(degreeX, 8, sizeof(DegreeSymbol), 8, DegreeSymbol);
    drawTallSmallGlyph(degreeX + DegreeAndGapWidth, FontSectionInfo.font06_start_ptr + (unitSymbol[0] - 2) * SourceGlyphWidth);
  }
}
} // namespace

void ui_draw_homescreen_simplified(TemperatureType_t tipTemp) {
  bool tempOnDisplay          = false;
  bool tipDisconnectedDisplay = false;
  if (OLED::getRotation()) {
    OLED::drawArea(68, 0, 56, 32, buttonAF);
    OLED::drawArea(12, 0, 56, 32, buttonBF);
    OLED::setCursor(0, 0);
    ui_draw_power_source_icon();
  } else {
    OLED::drawArea(0, 0, 56, 32, buttonA);
    OLED::drawArea(58, 0, 56, 32, buttonB);
    OLED::setCursor(116, 0);
    ui_draw_power_source_icon();
  }
  if (tipTemp > 55) {
    tempOnDisplay = true;
  } else if (tipTemp < 45) {
    tempOnDisplay = false;
  }
  if (isTipDisconnected()) {
    tempOnDisplay          = false;
    tipDisconnectedDisplay = true;
  }
  if (tipDisconnectedDisplay) {
    if (OLED::getRotation()) {
      OLED::fillArea(68, 0, 56, 32, 0);
      OLED::drawArea(54, 0, 56, 32, disconnectedTipF);
    } else {
      OLED::fillArea(0, 0, 56, 32, 0);
      OLED::drawArea(0, 0, 56, 32, disconnectedTip);
    }
  } else if (tempOnDisplay) {
    const bool blinkTemperature = getSettingValue(SettingsOptions::CoolingTempBlink) && (xTaskGetTickCount() % 1000 < 300);
    const int16_t warningX      = OLED::getRotation() ? 68 : 0;
    const uint8_t *circle       = OLED::getRotation() ? buttonAF : buttonA;
    drawHotTipStatus(warningX, circle, getTipTemp(), !blinkTemperature);
  }
}

#endif
