#include "power.hpp"
#include "ui_drawing.hpp"
#ifdef OLED_128x32

void ui_draw_soldering_basic_status(bool boostModeOn) {
  ui_draw_soldering_fullscreen_status(boostModeOn);
}

#endif
