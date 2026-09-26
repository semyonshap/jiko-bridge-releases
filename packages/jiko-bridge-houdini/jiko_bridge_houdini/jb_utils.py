"""Houdini message reporting."""

import json
import logging
import os
from typing import Mapping, Optional, Sequence

import hou
from jiko_bridge_client import AssetModel, get_logger


def report(
    logger: logging.Logger,
    message: Optional[str] = None,
    box: Optional[str] = None,
    severity: hou.EnumValue = hou.severityType.Warning,
) -> None:
    """Report a message: log it, show it in a message box, or both."""
    levels = {
        hou.severityType.Message: logging.INFO,
        hou.severityType.ImportantMessage: logging.INFO,
        hou.severityType.Warning: logging.WARNING,
        hou.severityType.Error: logging.ERROR,
        hou.severityType.Fatal: logging.CRITICAL,
    }
    if message:
        logger.log(levels.get(severity, logging.WARNING), message)
    if box and hou.isUIAvailable():
        hou.ui.displayMessage(box, title="Jiko Bridge", severity=severity)


container_logger = get_logger(__name__)


def apply_asset(node: hou.OpNode, asset: AssetModel) -> bool:
    """Populate the node's user data; the parms below only mirror it."""
    files = asset.files
    if not files:
        report(container_logger, "Asset has no files", "The asset has no files.")
        return False
    node.setUserData("jiko_asset", json.dumps(asset.to_dict(), ensure_ascii=False))
    set_parm(node, "vault_name", asset.vault_name)
    set_parm(node, "pack_name", asset.pack_name)
    set_parm(node, "asset_name", asset.asset_name)
    set_multiparm(
        node,
        "files",
        {
            "filepath": [file.filepath for file in files],
            "asset_type": [file.asset_type for file in files],
            "bridge_type": [file.bridge_type for file in files],
        },
    )
    return True


def cached_asset(node: hou.OpNode) -> AssetModel:
    """The asset stored in the node's user data; the parms only mirror it."""
    payload = node.userData("jiko_asset")
    return AssetModel.from_dict(json.loads(payload)) if payload else AssetModel()


def set_parm(node: hou.OpNode, name: str, value: Optional[str]) -> None:
    """Set a parm if the node has it; None becomes the empty string."""
    parm = node.parm(name)
    if parm is not None:
        parm.set("" if value is None else str(value))


def set_multiparm(
    node: hou.OpNode, name: str, parms: Mapping[str, Sequence[Optional[str]]]
) -> None:
    """Resize a multiparm to the column length and fill every instance of every parm."""
    count = node.parm(name)
    columns = list(parms.values())
    if count is None or not columns:
        return
    count.set(len(columns[0]))
    for parm_name, values in parms.items():
        for index, value in enumerate(values, start=1):
            set_parm(node, f"{parm_name}{index}", value)


def absolute_path(value: str) -> str:
    """Expand Houdini variables and normalise slashes; empty value stays empty."""
    if not value:
        return ""
    return os.path.abspath(hou.text.expandString(value)).replace("\\", "/")


def source_path(path: str | None) -> str:
    """Expand a Houdini source path and normalise its separators."""
    return hou.text.expandString(path or "").replace("\\", "/")
