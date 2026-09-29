"""Small Houdini UI and path helpers."""

import logging
import os
from typing import Optional

import hou


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


def absolute_path(value: str) -> str:
    """Expand Houdini variables and normalise slashes; empty value stays empty."""
    if not value:
        return ""
    return os.path.abspath(hou.text.expandString(value)).replace("\\", "/")


def source_path(path: str | None) -> str:
    """Expand a Houdini source path and normalise its separators."""
    return absolute_path(path or "")
