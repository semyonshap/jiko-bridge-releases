"""
Utility functions for the Jiko Bridge Cinema 4D plugin.
Code by Semyon Shapoval, 2026
"""

import os
import sys
import logging
import importlib
from pathlib import Path
from contextlib import contextmanager

import c4d

JB_ENV = os.getenv("JB_ENV", "production")


def get_logger(name: str) -> logging.Logger:
    """Get a logger."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    if JB_ENV == "production":
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "[Jiko Bridge] %(levelname)s [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)
    logger.addHandler(console)
    logger.propagate = False

    return logger


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


def reload_plugin_modules() -> None:
    """Reload plugin modules to ensure the latest code is used."""
    importlib.invalidate_caches()
    plugin_dir = Path(os.path.abspath(os.path.dirname(__file__))).parent

    plugin_modules = {}
    for name, mod in list(sys.modules.items()):
        mod_file = getattr(mod, "__file__", None)
        if mod_file is not None and Path(mod_file).resolve().is_relative_to(plugin_dir.resolve()):
            plugin_modules[name] = mod

    module_names = sorted(plugin_modules, key=lambda name: name.count("."))
    for name in reversed(module_names):
        sys.modules.pop(name, None)

    for name in module_names:
        try:
            importlib.import_module(name)
        except (ImportError, ModuleNotFoundError, RuntimeError, SyntaxError) as e:
            print(f"Failed to import {name!r}: {e}")

    if JB_ENV != "production":
        print(f"{len(plugin_modules)} modules reloaded.")


def load_arnold_module():
    """Load Arnold module if it exists in the Cinema 4D library path."""
    try:
        arnold_folder = os.path.join(c4d.storage.GeGetC4DPath(c4d.C4D_PATH_LIBRARY), "scripts")
        if os.path.exists(arnold_folder) and arnold_folder not in sys.path:
            sys.path.append(arnold_folder)
    except OSError as e:
        print(f"Failed to load Arnold module: {e}")
