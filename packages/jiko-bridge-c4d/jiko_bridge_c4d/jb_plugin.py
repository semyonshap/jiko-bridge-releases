"""
Cinema 4D plugin entry point: CommandData class and registration.
"""

import importlib

import c4d

from jiko_bridge_c4d.jb_utils import reload_plugin_modules

JIKO_BRIDGE_ID = 1096086
JIKO_BRIDGE_NAME = "Jiko Bridge"
JIKO_BRIDGE_HELP = "Jiko Bridge help to improve your workflow"


class JikoBridge(c4d.plugins.CommandData):
    """Main command plugin class for Jiko Bridge."""

    def GetScriptName(self):  # pylint: disable=invalid-name
        """Return a stable script name."""
        return JIKO_BRIDGE_NAME

    def Execute(self, doc):  # pylint: disable=invalid-name
        """Show the Jiko Bridge commands popup menu."""
        mod = importlib.import_module("jiko_bridge_c4d.jb_commands")
        mod.JbCommandsPopup(doc).show_popup_menu()
        return True


def registerJikoBridge() -> None:  # pylint: disable=invalid-name
    """Reload the plugin modules and register the command plugin in Cinema 4D.

    Called once by the ``jiko_bridge_c4d.pyp`` entry point on plugin load.
    """
    reload_plugin_modules()

    if c4d.plugins.FindPlugin(JIKO_BRIDGE_ID, c4d.PLUGINTYPE_COMMAND):
        return

    try:
        c4d.plugins.RegisterCommandPlugin(
            id=JIKO_BRIDGE_ID,
            str=JIKO_BRIDGE_NAME,
            info=0,
            help=JIKO_BRIDGE_HELP,
            dat=JikoBridge(),
            icon=None,
        )
    except (TypeError, RuntimeError, ValueError) as e:
        print(f"Failed to register Jiko Bridge plugin: {e}")
