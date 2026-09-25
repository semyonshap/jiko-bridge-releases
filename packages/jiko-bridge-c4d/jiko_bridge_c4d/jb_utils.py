"""
Utility functions for the Jiko Bridge Cinema 4D plugin.
Code by Semyon Shapoval, 2026
"""

import os
import sys
from contextlib import contextmanager
from typing import Callable

import c4d

_JB_RELOAD_HANDLER: Callable[[], bool] | None = None


def set_reload_handler(handler: Callable[[], bool] | None) -> None:
    """Connect the optional source-development reload controller."""
    global _JB_RELOAD_HANDLER  # pylint: disable=global-statement
    _JB_RELOAD_HANDLER = handler


def is_development() -> bool:
    """Whether the development entry point has attached a reload controller."""
    return _JB_RELOAD_HANDLER is not None


def reload_plugin_modules() -> bool:
    """Reload sources in development; the release has no reload controller."""
    return _JB_RELOAD_HANDLER() if _JB_RELOAD_HANDLER is not None else False


def is_headless() -> bool:
    """Headless-режим: c4dpy или Cinema 4D Commandline."""
    executable = sys.argv[0].lower() if sys.argv else ""
    return "c4dpy" in executable


@contextmanager
def busy_cursor(status_text: str = ""):
    """Context manager to show a busy cursor with optional status text."""
    if status_text:
        c4d.StatusSetText(status_text)
    c4d.gui.SetMousePointer(c4d.MOUSE_BUSY)
    try:
        yield
    finally:
        c4d.gui.SetMousePointer(c4d.MOUSE_NORMAL)
        c4d.StatusClear()


def load_arnold_module():
    """Load Arnold module if it exists in the Cinema 4D library path."""
    try:
        arnold_folder = os.path.join(c4d.storage.GeGetC4DPath(c4d.C4D_PATH_LIBRARY), "scripts")
        if os.path.exists(arnold_folder) and arnold_folder not in sys.path:
            sys.path.append(arnold_folder)
    except OSError as e:
        print(f"Failed to load Arnold module: {e}")
