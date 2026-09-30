"""Types and file formats specific to Houdini."""

from typing import TypeAlias

import hou
from jiko_bridge_client import (
    JbAssetExporterABC,
    JbAssetImporterABC,
    JbAssetSoloABC,
    JbMaterialImporterABC,
    JbSceneABC,
    JbSettingsABC,
)
from pxr import Usd

JbObject: TypeAlias = Usd.Prim
JbContainer: TypeAlias = Usd.Stage
JbSource: TypeAlias = hou.OpNode
JbMatrix: TypeAlias = hou.Matrix4
JbMaterial: TypeAlias = hou.OpNode

JbData: TypeAlias = JbContainer | JbObject | JbMaterial

JbSceneBase: TypeAlias = JbSceneABC[JbSource, JbMatrix, JbContainer, JbObject, JbMaterial]

JbAssetImporterBase: TypeAlias = JbAssetImporterABC[
    JbSource, JbMatrix, JbContainer, JbObject, JbMaterial
]
JbAssetExporterBase: TypeAlias = JbAssetExporterABC[
    JbSource, JbMatrix, JbContainer, JbObject, JbMaterial
]
JbAssetSoloBase: TypeAlias = JbAssetSoloABC[JbSource, JbMatrix, JbContainer, JbObject, JbMaterial]
JbMaterialImporterBase: TypeAlias = JbMaterialImporterABC[JbSource, JbMaterial]
JbSettingsBase: TypeAlias = JbSettingsABC[JbSource, JbContainer]
USD_EXTENSIONS = (".usd", ".usda", ".usdc", ".usdz")
CONVERTED_EXTENSIONS = (".fbx", ".abc")
MODEL_EXTENSIONS = CONVERTED_EXTENSIONS + USD_EXTENSIONS


GEOMETRY_PRIM = "geometry"
GEOMETRY_FILE = "geo.usdc"
INSTANCES_PRIM = "instances"
ASSETS_PRIM = "assets"
ASSETS_PARM = "assets"
ASSET_KIND = "component"
