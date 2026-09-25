"""Source reload controller; imported only by the development entry point."""

import importlib
import sys


def enable_development() -> None:
    """Attach development behavior without importing it into release builds."""
    utils = importlib.import_module("jiko_bridge_c4d.jb_utils")
    utils.set_reload_handler(reload_implementation)


def reload_implementation() -> bool:
    """Replace source modules while preserving the registered C4D command."""
    def owned(name):
        return any(
            name == prefix or name.startswith(prefix + ".")
            for prefix in ("jiko_bridge_c4d", "jiko_bridge_client")
        )

    stable = {__name__, "jiko_bridge_c4d.jb_plugin"}
    previous = {name: mod for name, mod in sys.modules.copy().items() if owned(name)}
    for name in previous:
        if name not in stable:
            sys.modules.pop(name, None)
    importlib.invalidate_caches()
    try:
        package = importlib.import_module("jiko_bridge_c4d")
        commands = importlib.import_module("jiko_bridge_c4d.jb_commands")
        enable_development()
        plugin = sys.modules["jiko_bridge_c4d.jb_plugin"]
        package.jb_plugin = plugin
        package.jb_development = sys.modules[__name__]
        # Commit only after all new imports succeed. Execute() uses this global.
        plugin.JbCommandsPopup = commands.JbCommandsPopup
    except Exception:
        for name in list(sys.modules):
            if owned(name):
                sys.modules.pop(name, None)
        sys.modules.update(previous)
        raise
    print("Jiko Bridge: source modules reloaded.")
    return True
