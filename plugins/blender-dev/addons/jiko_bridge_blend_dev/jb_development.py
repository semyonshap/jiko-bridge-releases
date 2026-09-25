"""Source reload controller for the development Blender addon.

Assign a hotkey to the operator "jiko_bridge.dev_reload" to refresh the
editable sources without restarting Blender.
"""

import importlib
import sys
import traceback

import bpy

_OWNED_PREFIXES = ("jiko_bridge_blend",)
# This controller module and its addon package must survive a reload.
_STABLE_MODULES = (__name__,)


def _owned(module_name: str) -> bool:
    """Whether a module belongs to the reloadable Jiko Bridge sources."""
    return any(
        module_name == prefix or module_name.startswith(prefix + ".") for prefix in _OWNED_PREFIXES
    )


def install_sources() -> None:
    """Import the current sources and register their addon classes."""
    plugin = importlib.import_module("jiko_bridge_blend.jb_plugin")
    plugin.register()


def uninstall_sources() -> None:
    """Unregister the addon classes of the currently imported sources."""
    plugin = sys.modules.get("jiko_bridge_blend.jb_plugin")
    if plugin is not None:
        plugin.unregister()


def reload_implementation() -> None:
    """Replace source modules while preserving this registered addon."""
    uninstall_sources()
    previous = {name: module for name, module in sys.modules.items() if _owned(name)}
    for name in previous:
        if name not in _STABLE_MODULES:
            sys.modules.pop(name, None)
    importlib.invalidate_caches()
    try:
        # Commit only after all new imports succeed.
        install_sources()
    except Exception:
        for name in list(sys.modules):
            if _owned(name):
                sys.modules.pop(name, None)
        sys.modules.update(previous)
        install_sources()
        raise
    print("Jiko Bridge: source modules reloaded.")


class JB_OT_DevReload(bpy.types.Operator):  # pylint: disable=invalid-name
    """Reload the editable Jiko Bridge sources from this checkout."""

    bl_idname = "jiko_bridge.dev_reload"
    bl_label = "Reload Jiko Bridge (dev)"

    def execute(self, _context):
        try:
            reload_implementation()
        except Exception:  # pylint: disable=broad-except
            traceback.print_exc()
            self.report({"ERROR"}, "Jiko Bridge: reload failed. Previous modules restored.")
            return {"CANCELLED"}
        return {"FINISHED"}


def register() -> None:
    """Register the reload operator and the addon sources."""
    bpy.utils.register_class(JB_OT_DevReload)
    install_sources()


def unregister() -> None:
    """Unregister the addon sources and the reload operator."""
    uninstall_sources()
    bpy.utils.unregister_class(JB_OT_DevReload)
