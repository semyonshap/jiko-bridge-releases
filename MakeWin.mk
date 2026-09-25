SHELL := cmd.exe

# Пути к софту
BLENDER_PATH ?= C:\Program Files\Blender Foundation\Blender 5.0\blender.exe
C4D_PATH     ?= C:\Program Files\Maxon Cinema 4D 2023\Cinema 4D.exe
C4D_PYTHON   ?= C:\Program Files\Maxon Cinema 4D 2023\c4dpy.exe


# Специфика окружения
VENV_BIN     := venv\Scripts
PYTHON       := $(VENV_BIN)\python.exe
PIP          := $(VENV_BIN)\pip.exe
VENV_ACTIVATE := $(VENV_BIN)\activate.bat

# Системные пути
DESKTOP      := $(USERPROFILE)\Desktop

# Название аддона для Blender
ADDON_NAME := jiko_bridge_blend
DEV_ADDON_NAME := jiko_bridge_blend_dev

# Путь к папке с аддонами проекта
ROOT_ADDONS_PATH  := $(CURDIR)/plugins/blender
ROOT_DEV_ADDONS_PATH := $(CURDIR)/plugins/blender-dev
C4D_PLUGIN_PATH := $(CURDIR)/plugins/cinema4d
BLENDER_PLUGIN_PATH := $(ROOT_ADDONS_PATH)/addons/$(ADDON_NAME)

