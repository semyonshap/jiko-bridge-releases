from typing import TypeAlias

import bpy
import mathutils

from jiko_bridge_client import (
    JbAssetExporterABC,
    JbAssetImporterABC,
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
JbMaterialImporterBase: TypeAlias = JbMaterialImporterABC[JbMaterial]
JbSettingsBase: TypeAlias = JbSettingsABC[JbContainer]
JbAssetImporterBase: TypeAlias = JbAssetImporterABC[JbContainer, JbObject, JbMaterial]
JbAssetExporterBase: TypeAlias = JbAssetExporterABC[JbContainer, JbObject, JbMaterial]
