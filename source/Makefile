ifndef model
model:=TS101
endif

ALL_MODELS=TS101
ALL_MINIWARE_MODELS=$(ALL_MODELS)

ifneq ($(model),$(filter $(model),$(ALL_MODELS)))
$(error Invalid model '$(model)', valid options are: $(ALL_MODELS))
endif

# Output folder
HEXFILE_DIR=hexfile

# Temporary objects folder
OUTPUT_DIR_BASE=objects
OUTPUT_DIR=objects/ts101

ALL_LANGUAGES=DE EN ES FR JA_JP RU TR

LANGUAGE_GROUP_CJK_LANGS=EN JA_JP
LANGUAGE_GROUP_CJK_NAME=Chinese+Japanese

ifdef custom_multi_langs
RUN_SHELL_CMD:=$(shell rm -Rf {core/gen,$(OUTPUT_DIR)/core/gen,$(HEXFILE_DIR)/*_Custom.*})
LANGUAGE_GROUP_CUSTOM_LANGS=$(custom_multi_langs)
LANGUAGE_GROUP_CUSTOM_NAME=Custom
endif

LANGUAGE_GROUP_CYRILLIC_LANGS=EN RU
LANGUAGE_GROUP_CYRILLIC_NAME=Belarusian+Bulgarian+Russian+Serbian+Ukrainian

LANGUAGE_GROUP_EUR_LANGS=EN $(filter-out $(LANGUAGE_GROUP_CJK_LANGS) $(LANGUAGE_GROUP_CYRILLIC_LANGS),$(ALL_LANGUAGES))
LANGUAGE_GROUP_EUR_NAME=European

LANGUAGE_GROUPS=CUSTOM CJK CYRILLIC EUR

# Define for host Python
ifndef HOST_PYTHON
HOST_PYTHON:=python3
endif

# Defines for host tools
ifeq ($(HOST_CC),)
HOST_CC:=gcc
endif

HOST_OUTPUT_DIR=objects/host

# DFU packing address to use
DEVICE_DFU_ADDRESS=0x08000000
DEVICE_DFU_VID_PID=0x28E9:0x0189


# Enumerate all of the include directories (HAL source dirs are used for clang-format only)
APP_INC_DIR=./core/inc
MIDDLEWARES_DIR=./middlewares
BSP_INC_DIR=./core/bsp
THREADS_DIR=./core/threads
SOURCE_CORE_DIR=./core/src
BRIEFLZ_DIR=./core/brieflz
DRIVERS_DIR=./core/drivers
PD_DRIVER_DIR=./core/drivers/usb-pd
# Exclude USB-PD tests
PD_DRIVER_TESTS_DIR=./core/drivers/usb-pd/tests


# Excludes for clang-format

ALL_INCLUDES_EXCEPT:=-path $(PD_DRIVER_DIR) -o -not -name "configuration.h"
ALL_SOURCE_EXCEPT:=-path $(PD_DRIVER_DIR)
# Find-all's used for formatting; have to exclude external modules
ALL_INCLUDES=$(shell find  ./core -type d \( $(ALL_INCLUDES_EXCEPT) \) -prune -false -o \( -type f \( -name '*.h' -o -name '*.hpp' \) \) )
ALL_SOURCE=$(shell find    ./core -type d \( $(ALL_SOURCE_EXCEPT)   \) -prune -false -o \( -type f \( -name '*.c' -o -name '*.cpp' \) \) )

# Device dependent settings
ifeq ($(model),$(filter $(model),$(ALL_MINIWARE_MODELS)))
$(info Building for Miniware )
DEVICE_BSP_DIR=./core/bsp/miniware
LDSCRIPT=./core/bsp/miniware/stm32f103.ld

# 128K, but logo must be at 99K so their broken ass DFU can flash it
flash_size=98k
bootldr_size=0x8000
DEVICE_DFU_ADDRESS=0x08008000

DEV_GLOBAL_DEFS=-D STM32F103T8Ux       \
                -D STM32F1             \
                -D STM32               \
                -D USE_HAL_DRIVER      \
                -D STM32F103xB         \
                -D USE_RTOS_SYSTICK    \
                -D GCC_ARMCM3          \
                -D ARM_MATH_CM3        \
                -D STM32F10X_MD        \
                -finline-limit=9999999

DEV_LDFLAGS=-Wl,--wrap=printf  -Wl,--no-wchar-size-warning
DEV_AFLAGS=
DEV_CFLAGS=-D VECT_TAB_OFFSET=$(bootldr_size)U
DEV_CXXFLAGS=
CPUFLAGS=-mcpu=cortex-m3  \
         -mthumb          \
         -mfloat-abi=soft

DEVICE_DFU_VID_PID=0x1209:0xDB42
endif # ALL_MINIWARE_MODELS

DEVICE_BSP_INCLUDE_DIRS:= ${shell find ${DEVICE_BSP_DIR} -type d -print}
THREADS_INCLUDE_DIRS:= ${shell find ${THREADS_DIR} -type d -print}
DRIVERS_INCLUDE_DIRS:= ${shell find ${DRIVERS_DIR} -type d -print}
BRIEFLZ_INCLUDE_DIRS:= ${shell find ${BRIEFLZ_DIR} -type d -print}
MIDDLEWARES_INCLUDE_DIRS:= ${shell find ${MIDDLEWARES_DIR} -type d -print}


INCLUDES=-I$(APP_INC_DIR)                              \
         -I$(BSP_INC_DIR)                              \
          ${patsubst %,-I%,${DEVICE_BSP_INCLUDE_DIRS}} \
          ${patsubst %,-I%,${THREADS_INCLUDE_DIRS}}    \
          ${patsubst %,-I%,${DRIVERS_INCLUDE_DIRS}}    \
          ${patsubst %,-I%,${BRIEFLZ_INCLUDE_DIRS}}    \
          ${patsubst %,-I%,${MIDDLEWARES_INCLUDE_DIRS}}

ASM_INC=$(INCLUDES)


SOURCE:=$(shell find ${THREADS_DIR}            -type f -name '*.c') \
        $(shell find ${SOURCE_CORE_DIR}        -type f -name '*.c') \
        $(shell find ${DRIVERS_DIR}            -type f -name '*.c') \
        $(shell find ${DEVICE_BSP_DIR}         -type f -name '*.c') \
        $(shell find ${MIDDLEWARES_DIR}        -type f -name '*.c') \
        $(BRIEFLZ_DIR)/depack.c

# We exclude the USB-PD stack tests $(PD_DRIVER_TESTS_DIR)
SOURCE_CPP:=$(shell find ${THREADS_DIR}      -type f -name '*.cpp') \
            $(shell find ${SOURCE_CORE_DIR}  -type f -name '*.cpp') \
            $(shell find ${DRIVERS_DIR}      -type f -name '*.cpp' -not -path "${PD_DRIVER_TESTS_DIR}/*" ) \
            $(shell find ${DEVICE_BSP_DIR}   -type f -name '*.cpp') \
            $(shell find ${MIDDLEWARES_DIR}  -type f -name '*.cpp')


S_SRCS:=$(shell find $(DEVICE_BSP_DIR) -type f -name '*.S')


# Code optimisation ------------------------------------------------------------
OPTIM=-Os                             \
      -fno-jump-tables                \
      -foptimize-strlen               \
      -faggressive-loop-optimizations \
      -fdevirtualize-at-ltrans        \
      -fmerge-all-constants           \
      -fshort-wchar                   \
      -flto=auto                      \
      -finline-small-functions        \
      -finline-functions              \
      -findirect-inlining             \
      -fdiagnostics-color             \
      -ffunction-sections             \
      -fdata-sections                 \
      -fshort-enums                   \
      -fsingle-precision-constant     \
      -fno-common                     \
      -fno-math-errno                 \
      -ffast-math                     \
      -ffinite-math-only              \
      -fno-signed-zeros               \
      -fsingle-precision-constant

# Global defines ---------------------------------------------------------------
GLOBAL_DEFINES+=$(DEV_GLOBAL_DEFS) -D USE_RTOS_SYSTICK -D MODEL_$(model) -D VECT_TAB_OFFSET=$(bootldr_size)U -fshort-wchar

ifdef swd_enable
GLOBAL_DEFINES+=-DSWD_ENABLE
endif

# Libs -------------------------------------------------------------------------
LIBS=

# Compilers --------------------------------------------------------------------
COMPILER=gcc

COMPILER_PREFIX=arm-none-eabi

# Programs ---------------------------------------------------------------------
CC=$(COMPILER_PREFIX)-gcc
CPP=$(COMPILER_PREFIX)-g++
OBJCOPY=$(COMPILER_PREFIX)-objcopy
SIZE=$(COMPILER_PREFIX)-size
OBJDUMP=$(COMPILER_PREFIX)-objdump

# Use gcc in assembler mode so we can use defines etc in assembly
AS=$(COMPILER_PREFIX)-gcc -x assembler-with-cpp

# Linker flags -----------------------------------------------------------------
LINKER_FLAGS=-Wl,--gc-sections                             \
             -Wl,--wrap=malloc                             \
             -Wl,--wrap=free                               \
             -Wl,--undefined=vTaskSwitchContext            \
             -Wl,--undefined=pxCurrentTCB                  \
             -Wl,--defsym=__FLASH_SIZE__=$(flash_size)     \
             -Wl,--defsym=__BOOTLDR_SIZE__=$(bootldr_size) \
             -Wl,--print-memory-usage                      \
                 --specs=nosys.specs                       \
                 --specs=nano.specs                        \
             $(DEV_LDFLAGS)

# Compiler flags ---------------------------------------------------------------
CHECKOPTIONS=-Wtrigraphs                  \
             -Wuninitialized              \
             -Wmissing-braces             \
             -Wfloat-equal                \
             -Wunreachable-code           \
             -Wswitch-default             \
             -Wreturn-type                \
             -Wundef                      \
             -Wparentheses                \
             -Wnonnull                    \
             -Winit-self                  \
             -Wmissing-include-dirs       \
             -Wsequence-point             \
             -Wswitch                     \
             -Wformat                     \
             -Wsign-compare               \
             -Waddress                    \
             -Waggregate-return           \
             -Wmissing-field-initializers \
             -Wshadow                     \
             -Wno-unused-parameter        \
             -Wno-undef                   \
             -Wdouble-promotion

CHECKOPTIONS_C=$(CHECKOPTIONS) -Wbad-function-cast

CXXFLAGS=$(DEV_CXXFLAGS)        \
         $(CPUFLAGS)            \
         $(INCLUDES)            \
         $(GLOBAL_DEFINES)      \
       -D${COMPILER}            \
       -MMD                     \
         $(CHECKOPTIONS)        \
       -std=c++17               \
         $(OPTIM)               \
       -fno-rtti                \
       -fno-exceptions          \
       -fno-non-call-exceptions \
       -fno-use-cxa-atexit      \
       -fno-strict-aliasing     \
       -fno-threadsafe-statics  \
       -T$(LDSCRIPT)

CFLAGS=$(DEV_CFLAGS)     \
       $(CPUFLAGS)       \
       $(INCLUDES)       \
       $(CHECKOPTIONS_C) \
       $(GLOBAL_DEFINES) \
     -D${COMPILER}       \
     -MMD                \
     -std=gnu11          \
     -g3                 \
       $(OPTIM)          \
     -T$(LDSCRIPT)       \
     -c

AFLAGS=$(CPUFLAGS)       \
       $(DEV_AFLAGS)     \
       $(GLOBAL_DEFINES) \
       $(OPTIM)          \
       $(ASM_INC)        \
       $(INCLUDES)

OBJS=$(SOURCE:.c=.o)
OBJS_CPP=$(SOURCE_CPP:.cpp=.o)
OBJS_S=$(S_SRCS:.S=.o)

OUT_OBJS=$(addprefix $(OUTPUT_DIR)/,$(OBJS))
OUT_OBJS_CPP=$(addprefix $(OUTPUT_DIR)/,$(OBJS_CPP))
OUT_OBJS_S=$(addprefix $(OUTPUT_DIR)/,$(OBJS_S))

default: firmware-EN

firmware-%: $(HEXFILE_DIR)/$(model)_%.hex $(HEXFILE_DIR)/$(model)_%.bin $(HEXFILE_DIR)/$(model)_%.dfu
	@true

# Targets for binary files

%.hex: %.elf Makefile
	$(OBJCOPY) $< -O ihex $@

%.bin: %.elf Makefile
	$(OBJCOPY) $< -O binary $@
	$(SIZE) $<

%.dfu: %.bin Makefile
	$(HOST_PYTHON) dfuse-pack.py -b $(DEVICE_DFU_ADDRESS)@0:$< -D $(DEVICE_DFU_VID_PID) $@

$(HEXFILE_DIR)/$(model)_%.elf: \
		$(OUT_OBJS_S) $(OUT_OBJS) $(OUT_OBJS_CPP)    \
		$(OUTPUT_DIR)/core/gen/Translation.%.o       \
		$(OUTPUT_DIR)/core/lang_support/lang_single.o \
		Makefile $(LDSCRIPT)
	@test -d $(@D) || mkdir -p $(@D)
	@echo Linking $@
	@$(CPP) $(CXXFLAGS) $(OUT_OBJS_S) $(OUT_OBJS) $(OUT_OBJS_CPP) \
		$(OUTPUT_DIR)/core/gen/Translation.$*.o      \
		$(OUTPUT_DIR)/core/lang_support/lang_single.o \
		$(LIBS) $(LINKER_FLAGS) -o$@ -Wl,-Map=$@.map

$(HEXFILE_DIR)/$(model)_string_compressed_%.elf: \
		$(OUT_OBJS_S) $(OUT_OBJS) $(OUT_OBJS_CPP)      \
		$(OUTPUT_DIR)/core/gen/Translation_brieflz.%.o \
		$(OUTPUT_DIR)/core/lang_support/lang_single.o   \
		Makefile $(LDSCRIPT)
	@test -d $(@D) || mkdir -p $(@D)
	@echo Linking $@
	@$(CPP) $(CXXFLAGS) $(OUT_OBJS_S) $(OUT_OBJS) $(OUT_OBJS_CPP) \
		$(OUTPUT_DIR)/core/gen/Translation_brieflz.$*.o \
		$(OUTPUT_DIR)/core/lang_support/lang_single.o    \
		$(LIBS) $(LINKER_FLAGS) -o$@ -Wl,-Map=$@.map

$(HEXFILE_DIR)/$(model)_font_compressed_%.elf: \
		$(OUT_OBJS_S) $(OUT_OBJS) $(OUT_OBJS_CPP)           \
		$(OUTPUT_DIR)/core/gen/Translation_brieflz_font.%.o \
		$(OUTPUT_DIR)/core/lang_support/lang_single.o        \
		Makefile $(LDSCRIPT)
	@test -d $(@D) || mkdir -p $(@D)
	@echo Linking $@
	@$(CPP) $(CXXFLAGS) $(OUT_OBJS_S) $(OUT_OBJS) $(OUT_OBJS_CPP) \
		$(OUTPUT_DIR)/core/gen/Translation_brieflz_font.$*.o  \
		$(OUTPUT_DIR)/core/lang_support/lang_single.o          \
		$(LIBS) $(LINKER_FLAGS) -o$@ -Wl,-Map=$@.map

$(OUT_OBJS): $(OUTPUT_DIR)/%.o: %.c Makefile
	@test -d $(@D) || mkdir -p $(@D)
	@$(CC) -c $(CFLAGS) $< -o $@

$(OUTPUT_DIR)/%.o: %.cpp Makefile
	@test -d $(@D) || mkdir -p $(@D)
	@$(CPP) -c $(CXXFLAGS) $< -o $@

$(OUT_OBJS_S): $(OUTPUT_DIR)/%.o: %.S Makefile
	@test -d $(@D) || mkdir -p $(@D)
	@echo 'Building file: $<'
	@$(AS) -c $(AFLAGS) $< -o $@

core/gen/Translation.%.cpp $(OUTPUT_DIR)/core/gen/translation.files/%.pickle: ../translations/translation_%.json \
		../translations/make_translation.py           \
		../translations/translations_definitions.json \
		../translations/font_tables.py                \
		Makefile ../translations/wqy-bitmapsong/wenquanyi_9pt.bdf \
		core/gen/macros.txt
	@test -d core/gen || mkdir -p core/gen
	@test -d $(OUTPUT_DIR)/core/gen/translation.files || mkdir -p $(OUTPUT_DIR)/core/gen/translation.files
	@echo 'Generating translations for language $*'
	@$(HOST_PYTHON) ../translations/make_translation.py \
		--macros "$(CURDIR)/core/gen/macros.txt"      \
		-o "$(CURDIR)/core/gen/Translation.$*.cpp"    \
		--output-pickled "$(OUTPUT_DIR)/core/gen/translation.files/$*.pickle" \
		$*

core/gen/macros.txt: Makefile
	@test -d "$(CURDIR)/core/gen" || mkdir -p "$(CURDIR)/core/gen"
	echo "#include <configuration.h>" | $(CC) -dM -E $(CFLAGS) -MF "$(CURDIR)/core/gen/macros.tmp" - > "$(CURDIR)/core/gen/macros.txt"

# The recipes to produce compressed translation data

$(OUTPUT_DIR)/core/gen/translation.files/%.o: core/gen/Translation.%.cpp
	@test -d $(@D) || mkdir -p $(@D)
	@echo Generating $@
	@$(CPP) -c $(filter-out -flto=auto ,$(CXXFLAGS)) $< -o $@

$(OUTPUT_DIR)/core/gen/translation.files/multi.%.o: core/gen/Translation_multi.%.cpp
	@test -d $(@D) || mkdir -p $(@D)
	@echo Generating $@
	@$(CPP) -c $(filter-out -flto=auto ,$(CXXFLAGS)) $< -o $@

$(HOST_OUTPUT_DIR)/brieflz/libbrieflz.so: core/brieflz/brieflz.c core/brieflz/depack.c
	@test -d $(@D) || mkdir -p $(@D)
	@echo Building host brieflz shared library $@
	@$(HOST_CC) -fPIC -shared -DBLZ_DLL -DBLZ_DLL_EXPORTS -O $^ -o $@

core/gen/Translation_brieflz.%.cpp: $(OUTPUT_DIR)/core/gen/translation.files/%.o $(OUTPUT_DIR)/core/gen/translation.files/%.pickle $(HOST_OUTPUT_DIR)/brieflz/libbrieflz.so core/gen/macros.txt
	@test -d $(@D) || mkdir -p $(@D)
	@echo Generating BriefLZ compressed translation for $*
	@OBJCOPY=$(OBJCOPY) $(HOST_PYTHON) ../translations/make_translation.py \
		--macros "$(CURDIR)/core/gen/macros.txt"           \
		-o "$(CURDIR)/core/gen/Translation_brieflz.$*.cpp" \
		--input-pickled "$(OUTPUT_DIR)/core/gen/translation.files/$*.pickle" \
		--strings-obj "$(OUTPUT_DIR)/core/gen/translation.files/$*.o"        \
		$*

core/gen/Translation_brieflz_font.%.cpp: $(OUTPUT_DIR)/core/gen/translation.files/%.pickle $(HOST_OUTPUT_DIR)/brieflz/libbrieflz.so core/gen/macros.txt
	@test -d $(@D) || mkdir -p $(@D)
	@echo Generating BriefLZ compressed translation font for $*
	@$(HOST_PYTHON) ../translations/make_translation.py        \
		--macros $(PWD)/core/gen/macros.txt                \
		-o $(PWD)/core/gen/Translation_brieflz_font.$*.cpp \
		--input-pickled $(OUTPUT_DIR)/core/gen/translation.files/$*.pickle \
		--compress-font \
		$*

# The recipes to produce multi-language firmwares:

# Usage: $(eval $(call multi_lang_rule,$(1)=group_code,$(2)=group_name,$(3)=lang_codes))
define multi_lang_rule

$(HEXFILE_DIR)/$(model)_multi_$(2).elf: \
		$(OUT_OBJS_S) $(OUT_OBJS) $(OUT_OBJS_CPP)       \
		$(OUTPUT_DIR)/core/gen/Translation_multi.$(1).o \
		$(OUTPUT_DIR)/core/lang_support/lang_multi.o     \
		Makefile $(LDSCRIPT)
	@test -d $$(@D) || mkdir -p $$(@D)
	@echo Linking $$@
	@$(CPP) $(CXXFLAGS) $(OUT_OBJS_S) $(OUT_OBJS) $(OUT_OBJS_CPP) \
		$(OUTPUT_DIR)/core/gen/Translation_multi.$(1).o       \
		$(OUTPUT_DIR)/core/lang_support/lang_multi.o           \
		$(LIBS) $(LINKER_FLAGS) -o$$@ -Wl,-Map=$$@.map

$(HEXFILE_DIR)/$(model)_multi_compressed_$(2).elf: \
		$(OUT_OBJS_S) $(OUT_OBJS) $(OUT_OBJS_CPP)               \
		$(OUTPUT_DIR)/core/gen/Translation_brieflz_multi.$(1).o \
		$(OUTPUT_DIR)/core/lang_support/lang_multi.o             \
		Makefile $(LDSCRIPT)
	@test -d $$(@D) || mkdir -p $$(@D)
	@echo Linking $$@
	@$(CPP) $(CXXFLAGS) $(OUT_OBJS_S) $(OUT_OBJS) $(OUT_OBJS_CPP)   \
		$(OUTPUT_DIR)/core/gen/Translation_brieflz_multi.$(1).o \
		$(OUTPUT_DIR)/core/lang_support/lang_multi.o             \
		$(LIBS) $(LINKER_FLAGS) -o$$@ -Wl,-Map=$$@.map

core/gen/Translation_multi.$(1).cpp: $(patsubst %,../translations/translation_%.json,$(3)) \
		../translations/make_translation.py           \
		../translations/translations_definitions.json \
		../translations/font_tables.py                \
		Makefile ../translations/wqy-bitmapsong/wenquanyi_9pt.bdf \
		core/gen/macros.txt
	@test -d core/gen || mkdir -p core/gen
	@test -d $(OUTPUT_DIR)/core/gen/translation.files || mkdir -p $(OUTPUT_DIR)/core/gen/translation.files
	@echo 'Generating translations for multi-language $(2)'
	@$(HOST_PYTHON) ../translations/make_translation.py   \
		--macros "$(CURDIR)/core/gen/macros.txt"           \
		-o "$(CURDIR)/core/gen/Translation_multi.$(1).cpp" \
		--output-pickled "$(OUTPUT_DIR)/core/gen/translation.files/multi.$(1).pickle" \
		$(3)

$(OUTPUT_DIR)/core/gen/translation.files/multi.$(1).pickle: core/gen/Translation_multi.$(1).cpp

core/gen/Translation_brieflz_multi.$(1).cpp: $(OUTPUT_DIR)/core/gen/translation.files/multi.$(1).o $(OUTPUT_DIR)/core/gen/translation.files/multi.$(1).pickle $(HOST_OUTPUT_DIR)/brieflz/libbrieflz.so core/gen/macros.txt
	@test -d $$(@D) || mkdir -p $$(@D)
	@echo Generating BriefLZ compressed translation for multi-language $(2)
	@OBJCOPY=$(OBJCOPY) $(HOST_PYTHON) ../translations/make_translation.py \
		--macros "$(CURDIR)/core/gen/macros.txt"                   \
		-o "$(CURDIR)/core/gen/Translation_brieflz_multi.$(1).cpp" \
		--input-pickled "$(OUTPUT_DIR)/core/gen/translation.files/multi.$(1).pickle" \
		--strings-obj "$(OUTPUT_DIR)/core/gen/translation.files/multi.$(1).o"        \
		--compress-font \
		$(3)

endef # multi_lang_rule

# Add multi-language firmware rules:
$(foreach group_code,$(LANGUAGE_GROUPS),$(eval $(call multi_lang_rule,$(group_code),$(LANGUAGE_GROUP_$(group_code)_NAME),$(LANGUAGE_GROUP_$(group_code)_LANGS))))

# Clean up targets

clean:
	rm -Rf core/gen
	rm -Rf $(OUTPUT_DIR_BASE)
	rm -Rf $(HEXFILE_DIR)/*
	rm -Rf ../translations/__pycache__

clean-all: clean
	rm -Rf $(HEXFILE_DIR)

# Style formatting helper targets

# Overwrite source files in your local repo copy according to IronOS code style rules (source/.clang-format) WITHOUT A WARNING!
# Use `git diff` or your favorite diff tool via `git difftool` before commit to make sure there are no false-negative changes.
# If so, report an issue, please.
style:
	@for src in $(ALL_SOURCE) $(ALL_INCLUDES); do echo "Formatting $$src" ; clang-format -i "$$src" ; done;
	@echo "Done! Please, check the changes before commit."

# Code style checks using clang-format:
# - show output in gcc-like error compatible format for IDEs/editors;
# - external variables for debug purposes (can be used at the same time, i.e. STOP=1 LIST=1 ...):
#   * call `make check-style STOP=1` to exit after first failed file;
#   * call `make check-style LIST=1` to show failed file names only;
# - here we process only list of files;
# - per-file check happens in scripts/deploy.sh : check_style_file - since shell commands involved, the check logic moved to shell script for better maintainance outside of makefile syntax crossing.
# - $? / error / STOP conditional logic needed to:
#   * check errors in formatting from deploy.sh
#   * process STOP env variable
check-style:
	@error=0; export LIST=$$LIST; for src in $(ALL_SOURCE) $(ALL_INCLUDES) ; do \
		../scripts/deploy.sh  check_style_file  "$$src" ; \
		test "$${?}" -eq 1 && export error=1 ; \
		test "$${error}" -eq 1 && test -n "$${STOP}" && break; \
	done; \
	if [ $$error -eq 0 ] ; then  echo "" && echo "" && echo "Style check: PASS" && echo "" && echo "" && exit 0 ; \
	else  echo "" && echo "" && echo "Style check: FAIL! Please, check the log above for the details." && echo "If there is a false-negative trigger, please, report an issue attaching the log or link to the log!" && echo "" && echo "" && exit 1 ; \
	fi;

.PHONY: style  check-style  all  clean  default  clean-all
.SECONDARY:

# Pull in dependency info for *existing* .o files
-include $(OUT_OBJS:.o=.d)
-include $(OUT_OBJS_CPP:.o=.d)
-include $(OUTPUT_DIR)/core/gen/Translation.*.d
-include $(OUTPUT_DIR)/core/gen/Translation_*.d
-include $(OUTPUT_DIR)/core/gen/translation.files/*.d
