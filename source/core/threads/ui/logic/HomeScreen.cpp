
#include "Buttons.hpp"
#include "OperatingModes.h"
#include "ui_drawing.hpp"

bool showExitMenuTransition = false;

OperatingMode handleHomeButtons(const ButtonState buttons, guiContext *cxt) {
  if (cxt->scratch_state.state2 != 0) {
    const bool dismissWarning = warnUserWithIcon(translatedString(Tr->WarningTipMissing), buttons);
    if (cxt->scratch_state.state2 == 1) {
      // The long-press event that opened the warning can still be active while
      // its entry frame is rendered. Arm dismissal only after that input has
      // been released so the warning cannot immediately animate back out.
      if (buttons == BUTTON_NONE) {
        cxt->scratch_state.state2 = 2;
      }
    } else if (dismissWarning) {
      cxt->scratch_state.state2 = 0;
      cxt->transitionMode       = TransitionAnimation::Up;
    }
    return OperatingMode::HomeScreen;
  }
  if (buttons != BUTTON_NONE && cxt->scratch_state.state1 == 0) {
    return OperatingMode::HomeScreen; // Ignore button press
  } else {
    cxt->scratch_state.state1 = 1;
  }
  switch (buttons) {
  case BUTTON_NONE:
    // Do nothing
    break;
  case BUTTON_BOTH:
    break;

  case BUTTON_B_LONG:
    cxt->transitionMode = TransitionAnimation::Down;
    return OperatingMode::DebugMenuReadout;
    break;
  case BUTTON_F_LONG:
#ifdef PROFILE_SUPPORT
    if (!isTipDisconnected()) {
      cxt->transitionMode = TransitionAnimation::Left;
      return OperatingMode::SolderingProfile;
    } else {
      cxt->scratch_state.state2 = 1;
      cxt->transitionMode       = TransitionAnimation::Down;
      return OperatingMode::HomeScreen;
    }
#else
    cxt->transitionMode = TransitionAnimation::Left;
    return OperatingMode::TemperatureAdjust;
#endif
    break;
  case BUTTON_F_SHORT:
    if (!isTipDisconnected()) {
      bool detailedView   = getSettingValue(SettingsOptions::DetailedIDLE) && getSettingValue(SettingsOptions::DetailedSoldering);
      cxt->transitionMode = detailedView ? TransitionAnimation::None : TransitionAnimation::Left;
      return OperatingMode::Soldering;
    } else {
      cxt->scratch_state.state2 = 1;
      cxt->transitionMode       = TransitionAnimation::Down;
    }
    break;
  case BUTTON_B_SHORT:
    cxt->transitionMode = TransitionAnimation::Right;
    return OperatingMode::SettingsMenu;
    break;
  default:
    break;
  }
  return OperatingMode::HomeScreen;
}

OperatingMode drawHomeScreen(const ButtonState buttons, guiContext *cxt) {

  currentTempTargetDegC = 0; // ensure tip is off
  getInputVoltageX10(getSettingValue(SettingsOptions::VoltageDiv), 0);
  uint32_t tipTemp = TipThermoModel::getTipInC();

  // Setup LCD Cursor location
  if (OLED::getRotation()) {
    OLED::setCursor(50, 0);
  } else {
    OLED::setCursor(-1, 0);
  }
  if (getSettingValue(SettingsOptions::DetailedIDLE)) {
    ui_draw_homescreen_detailed(tipTemp);
  } else {
    ui_draw_homescreen_simplified(tipTemp, cxt->viewEnterTime);
  }
  return handleHomeButtons(buttons, cxt);
}
