"""
Utility functions for Jiko Bridge Blender plugin.
Code by Semyon Shapoval, 2026
"""

import sys
import logging

import bpy
import addon_utils


def get_logger(name: str) -> logging.Logger:
    """Get a logger."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

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


def reload_plugin_modules(addon_module_name: str = "jiko_bridge_blend") -> None:
    """Reload the addon modules by disabling and enabling the addon."""
    addon_utils.disable(addon_module_name)
    to_remove = [k for k in list(sys.modules) if addon_module_name in k]
    for k in to_remove:
        del sys.modules[k]
    addon_utils.enable(addon_module_name)


addon_keymaps: list = []


def register_keymap():
    """Register keymap"""
    wm = bpy.context.window_manager
    if not wm:
        return

    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.get("3D View")
        if km is None:
            km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")

        for item in km.keymap_items:
            if (
                item.idname == "wm.call_menu_pie"
                and item.properties.get("name", "") == "JB_MT_PIE_MAIN"
            ):
                return

        kmi = km.keymap_items.new(
            "wm.call_menu_pie",
            type="J",
            value="PRESS",
            shift=True,
        )
        kmi.properties.name = "JB_MT_PIE_MAIN"
        addon_keymaps.append((km, kmi))


def unregister_keymap():
    """Unregister keymap"""
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()
