import os
import sys
from contextlib import contextmanager

import c4d


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
