import importlib
import sys
import traceback

import c4d

JIKO_BRIDGE_DEV_ID = 1096087
JIKO_BRIDGE_DEV_NAME = "Jiko Bridge Reload (dev)"

_OWNED_PREFIXES = ("jiko_bridge_c4d", "jiko_bridge_client")
# This controller and the registered release command must survive a reload.
_STABLE_MODULES = (__name__, "jiko_bridge_c4d.jb_plugin")


def _owned(module_name: str) -> bool:
    """Whether a module belongs to the reloadable Jiko Bridge sources."""
    return any(
        module_name == prefix or module_name.startswith(prefix + ".")
        for prefix in _OWNED_PREFIXES
    )


class JikoBridgeDevReload(c4d.plugins.CommandData):  # pylint: disable=invalid-name
    """Reload the editable Jiko Bridge sources from this checkout."""

    def GetScriptName(self):  # pylint: disable=invalid-name
        """Return a stable script name."""
        return JIKO_BRIDGE_DEV_NAME

    def Execute(self, _doc):  # pylint: disable=invalid-name
        """Reload the source modules and refresh Cinema 4D."""
        try:
            reload_implementation()
        except Exception:  # pylint: disable=broad-except
            traceback.print_exc()
            c4d.gui.MessageDialog(
                "Jiko Bridge: reload failed. Previous modules restored. See Python Console."
            )
        c4d.EventAdd()
        return True


def register_reload_command() -> None:
    """Register the reload command once per Cinema 4D session."""
    if c4d.plugins.FindPlugin(JIKO_BRIDGE_DEV_ID, c4d.PLUGINTYPE_COMMAND):
        return

    try:
        c4d.plugins.RegisterCommandPlugin(
            id=JIKO_BRIDGE_DEV_ID,
            str=JIKO_BRIDGE_DEV_NAME,
            info=0,
            help="Reload Jiko Bridge source modules from the development checkout",
            dat=JikoBridgeDevReload(),
            icon=None,
        )
    except (TypeError, RuntimeError, ValueError) as e:
        print(f"Failed to register Jiko Bridge reload command: {e}")


def reload_implementation() -> bool:
    """Replace source modules while preserving the registered C4D commands."""
    stable = set(_STABLE_MODULES)
    previous = {name: mod for name, mod in sys.modules.items() if _owned(name)}
    for name in previous:
        if name not in stable:
            sys.modules.pop(name, None)
    importlib.invalidate_caches()
    try:
        package = importlib.import_module("jiko_bridge_c4d")
        commands = importlib.import_module("jiko_bridge_c4d.jb_commands")
        # Commit only after all new imports succeed. Execute() uses this global.
        plugin = importlib.import_module("jiko_bridge_c4d.jb_plugin")
        package.jb_plugin = plugin  # type: ignore[attr-defined]
        plugin.JbCommandsPopup = commands.JbCommandsPopup  # type: ignore[attr-defined]
    except Exception:
        for name in list(sys.modules):
            if _owned(name):
                sys.modules.pop(name, None)
        sys.modules.update(previous)
        raise
    print("Jiko Bridge: source modules reloaded.")
    return True
