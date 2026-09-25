"""
Jiko Bridge (dev) - load editable sources from this checkout.
Enable only this addon or the bundled one, never both.
"""

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[4] / "packages" / "jiko-bridge-blend"

if not SOURCE_ROOT.is_dir():
    raise RuntimeError(f"Jiko Bridge source directory not found: {SOURCE_ROOT}")

if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

if "jiko_bridge_blend" in sys.modules:
    raise RuntimeError("Jiko Bridge is already loaded. Enable only the development addon.")

bl_info = {
    "name": "Jiko Bridge (dev)",
    "author": "JIKO",
    "version": (1, 0),
    "blender": (5, 0, 1),
    "location": "View3D > Sidebar > Jiko Bridge",
    "description": "Jiko Bridge development build driven by editable sources",
    "category": "3D View",
    "doc_url": "https://with-jiko.com",
    "tracker_url": "https://t.me/withjiko",
}

from .jb_development import register, unregister  # pylint: disable=wrong-import-position
