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

uint8_t homeIconFrame(const TickType_t viewEnterTime) {
  TickType_t step = TICKS_100MS * 3;
  switch (getSettingValue(SettingsOptions::AnimationSpeed)) {
  case settingOffSpeed_t::FAST:
    step = TICKS_100MS;
    break;
  case settingOffSpeed_t::MEDIUM:
    step = TICKS_100MS * 2;
    break;
  default:
    break;
  }

  return ((xTaskGetTickCount() - viewEnterTime) / step) % HOME_ICON_FRAME_COUNT;
}

void drawAnimatedHomePart(const int16_t buttonX, const uint8_t localX, const int16_t y, const uint8_t width, const uint8_t height, const uint8_t *frame,
                          const uint8_t *clearMask, const bool mirrored) {
  const int16_t drawX = buttonX + (mirrored ? CircleWidth - localX - width : localX);
  uint8_t mirroredFrame[HOME_SETTINGS_SLIDERS_WIDTH * 3];
  uint8_t mirroredMask[HOME_SETTINGS_SLIDERS_WIDTH * 3];
  const uint8_t pages = (height + 7) / 8;
  if (mirrored) {
    for (uint8_t page = 0; page < pages; page++) {
      for (uint8_t x = 0; x < width; x++) {
        mirroredFrame[page * width + x] = frame[page * width + (width - 1 - x)];
        if (clearMask) {
          mirroredMask[page * width + x] = clearMask[page * width + (width - 1 - x)];
        }
      }
    }
    frame     = mirroredFrame;
    clearMask = clearMask ? mirroredMask : nullptr;
  }

  if (clearMask) {
    // Clear only pixels occupied by an animation frame. A rectangular clear
    // can erase neighbouring static artwork, such as the cartridge tip.
    OLED::clearAreaMasked(drawX, y, width, height, clearMask);
  } else {
    // Clear one display page at a time. drawFilledRect's height accounting is
    // page-based, so splitting keeps an unaligned 24px region exact.
    const int16_t clearEnd = y + height;
    for (int16_t clearY = y; clearY < clearEnd;) {
      const int16_t nextPage = (clearY & ~7) + 8;
      const int16_t clearTo  = nextPage < clearEnd ? nextPage : clearEnd;
      OLED::drawFilledRect(drawX, clearY, drawX + width, clearTo, true);
      clearY = clearTo;
    }
  }
  OLED::drawAreaClipped(drawX, y, width, height, frame, 1, y, y + height);
}

void drawAnimatedHomeIcons(const TickType_t viewEnterTime) {
  const bool    mirrored  = OLED::getRotation();
  const int16_t solderX   = mirrored ? 68 : 0;
  const int16_t settingsX = mirrored ? 12 : 58;

  if (getSettingValue(SettingsOptions::AnimationSpeed) == settingOffSpeed_t::OFF) {
    return;
  }
  const uint8_t frame = homeIconFrame(viewEnterTime);
  drawAnimatedHomePart(solderX, 7, 10, HOME_SOLDER_HEAT_WIDTH, HOME_SOLDER_HEAT_HEIGHT, HomeSolderHeatFrames[frame], HomeSolderHeatMask, mirrored);
  drawAnimatedHomePart(settingsX, 16, 4, HOME_SETTINGS_SLIDERS_WIDTH, HOME_SETTINGS_SLIDERS_HEIGHT, HomeSettingsSlidersFrames[frame], nullptr, mirrored);
}

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

void drawHomeButtonOutline(const int16_t x) {
  // Every button state uses this single, horizontally and vertically
  // symmetric pixel contour. Do not patch individual edges at runtime: that
  // makes the normal, hot, disconnected and pressed states diverge.
  OLED::drawAreaClipped(x, 0, CircleWidth, OLED_HEIGHT, HomeButtonOutline, 1, 0, OLED_HEIGHT);
}

void drawHotTipStatus(const int16_t x, const TemperatureType_t tipTemp, const bool showTemperature) {
  TemperatureSlideFrame frame;
  ui_get_temperature_slide_frame(tipTemp, TemperatureAnimationSlot::Home, 16, frame);

  // Remove all original soldering artwork. The canonical outline is restored
  // after the dynamic content is drawn, so its corners cannot be clipped.
  OLED::drawFilledRect(x + 4, 0, x + 52, OLED_HEIGHT, true);
  if (showTemperature) {
    drawTallTemperatureTransition(x, tipTemp, frame);
    const int16_t degreeX = temperatureTextX(x, tipTemp) + temperaturePlaces(tipTemp) * TallGlyphWidth;
    const char *unitSymbol = getSettingValue(SettingsOptions::TemperatureInF) ? SmallSymbolDegF : SmallSymbolDegC;
    OLED::drawArea(degreeX, 8, sizeof(DegreeSymbol), 8, DegreeSymbol);
    drawTallSmallGlyph(degreeX + DegreeAndGapWidth, FontSectionInfo.font06_start_ptr + (unitSymbol[0] - 2) * SourceGlyphWidth);
  }
}
} // namespace

void ui_draw_homescreen_simplified(TemperatureType_t tipTemp, TickType_t viewEnterTime) {
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
  drawAnimatedHomeIcons(viewEnterTime);
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
      OLED::drawArea(68, 0, 56, 32, disconnectedTipF);
    } else {
      OLED::fillArea(0, 0, 56, 32, 0);
      OLED::drawArea(0, 0, 56, 32, disconnectedTip);
    }
  } else if (tempOnDisplay) {
    const bool blinkTemperature = getSettingValue(SettingsOptions::CoolingTempBlink) && (xTaskGetTickCount() % 1000 < 300);
    const int16_t warningX      = OLED::getRotation() ? 68 : 0;
    drawHotTipStatus(warningX, getTipTemp(), !blinkTemperature);
  }

  const int16_t solderX   = OLED::getRotation() ? 68 : 0;
  const int16_t settingsX = OLED::getRotation() ? 12 : 58;
  drawHomeButtonOutline(solderX);
  drawHomeButtonOutline(settingsX);

  // Give immediate tactile feedback while the physical button is held. XOR
  // only the rounded button interior so the surrounding screen stays
  // unchanged, then restore the canonical white contour over the inversion.
  if (getButtonA()) {
    OLED::invertAreaMasked(solderX, 0, CircleWidth, OLED_HEIGHT, HomeButtonMask);
    drawHomeButtonOutline(solderX);
  }
  if (getButtonB()) {
    OLED::invertAreaMasked(settingsX, 0, CircleWidth, OLED_HEIGHT, HomeButtonMask);
    drawHomeButtonOutline(settingsX);
  }
}

#endif
