"""
Jiko Bridge client.

Shared models, HTTP API client and integration contracts used by every
Jiko Bridge DCC plugin (Blender, Cinema 4D, Maya, Houdini).

    from jiko_bridge_client import JbAPI, AssetModel, AssetFile

Code by Semyon Shapoval, 2026
"""

from .api import DEFAULT_PORT, JbAPI
from .commands import JbAssetExporterABC, JbAssetImporterABC, JbAssetSoloABC
from .contracts import (
    JbContainerT,
    JbMaterialImporterABC,
    JbMaterialT,
    JbMatrixT,
    JbObjectT,
    JbSceneABC,
    JbSettingsABC,
    JbSourceT,
)
from .logger import JB_ENV, get_logger
from .models import AssetFile, AssetModel, JbPlaceholderInfo

__version__ = "1.0.0"

__all__ = [
    # release
    "__version__",
    # models
    "AssetFile",
    "AssetModel",
    # client
    "JbAPI",
    "DEFAULT_PORT",
    # logging
    "get_logger",
    "JB_ENV",
    # contracts
    "JbSceneABC",
    "JbMaterialImporterABC",
    "JbSettingsABC",
    # commands
    "JbAssetImporterABC",
    "JbAssetExporterABC",
    "JbAssetSoloABC",
    "JbPlaceholderInfo",
    # DCC-supplied type parameters
    "JbSourceT",
    "JbMatrixT",
    "JbContainerT",
    "JbObjectT",
    "JbMaterialT",
]
