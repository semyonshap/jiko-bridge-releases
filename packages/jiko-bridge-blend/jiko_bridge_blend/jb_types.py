from typing import TypeAlias

import bpy
import mathutils
from jiko_bridge_client import (
    JbAssetExporterABC,
    JbAssetImporterABC,
    JbAssetSoloABC,
    JbMaterialImporterABC,
    JbSceneABC,
    JbSettingsABC,
)

JbSource: TypeAlias = bpy.types.Context
JbMatrix: TypeAlias = mathutils.Matrix

JbContainer: TypeAlias = bpy.types.Collection
JbObject: TypeAlias = bpy.types.Object
JbMaterial: TypeAlias = bpy.types.Material

JbData: TypeAlias = JbContainer | JbObject | JbMaterial

JbSceneBase: TypeAlias = JbSceneABC[JbSource, JbMatrix, JbContainer, JbObject, JbMaterial]
JbMaterialImporterBase: TypeAlias = JbMaterialImporterABC[JbSource, JbMaterial]
JbSettingsBase: TypeAlias = JbSettingsABC[JbSource, JbContainer]
JbAssetImporterBase: TypeAlias = JbAssetImporterABC[
    JbSource, JbMatrix, JbContainer, JbObject, JbMaterial
]
JbAssetExporterBase: TypeAlias = JbAssetExporterABC[
    JbSource, JbMatrix, JbContainer, JbObject, JbMaterial
]
JbAssetSoloBase: TypeAlias = JbAssetSoloABC[JbSource, JbMatrix, JbContainer, JbObject, JbMaterial]
