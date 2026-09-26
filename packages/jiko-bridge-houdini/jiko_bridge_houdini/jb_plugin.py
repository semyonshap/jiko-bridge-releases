"""Entry points the HDA PythonModule calls."""

import hou
from jiko_bridge_houdini.jb_commands import JbCommands


def active_asset(node: hou.OpNode) -> None:
    """HDA Active button callback."""
    JbCommands(node).active_asset()


def import_asset(node: hou.OpNode) -> None:
    """HDA Import button callback."""
    JbCommands(node).import_asset()
