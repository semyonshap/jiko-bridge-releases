"""
Register Jiko Bridge Blender Plugin
Code by Semyon Shapoval, 2026
"""

import os
import sys

root_path = os.path.join(os.path.dirname(__file__))
if root_path not in sys.path:
    sys.path.append(root_path)

bl_info = {
    "name": "Jiko Bridge",
    "author": "JIKO",
    "version": (1, 0),
    "blender": (5, 0, 1),
    "location": "View3D > Sidebar > Jiko Bridge",
    "description": "Jiko Bridge",
    "category": "3D View",
    "doc_url": "https://with-jiko.com",
    "tracker_url": "https://t.me/withjiko",
}

from .jiko_bridge_blend import register, unregister  # pylint: disable=wrong-import-position

if __name__ == "__main__":
    register()
