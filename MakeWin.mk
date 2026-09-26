SHELL := cmd.exe

# Python
VENV_BIN     := venv\Scripts
PYTHON       := $(VENV_BIN)\python.exe
PIP          := $(VENV_BIN)\pip.exe
VENV_ACTIVATE := $(VENV_BIN)\activate.bat

# System
DESKTOP      := $(USERPROFILE)\Desktop

# Blender
BLENDER_PATH ?= C:\Program Files\Blender Foundation\Blender 5.0\blender.exe
ADDON_NAME := jiko_bridge_blend
ROOT_ADDONS_PATH  := $(CURDIR)/plugins/blender
BLENDER_PLUGIN_PATH := $(ROOT_ADDONS_PATH)/addons/$(ADDON_NAME)

# Cinema 4d
C4D_PATH     ?= C:\Program Files\Maxon Cinema 4D 2023\Cinema 4D.exe
C4D_PYTHON   ?= C:\Program Files\Maxon Cinema 4D 2023\c4dpy.exe
C4D_PLUGIN_PATH := $(CURDIR)/dist/cinema4d

