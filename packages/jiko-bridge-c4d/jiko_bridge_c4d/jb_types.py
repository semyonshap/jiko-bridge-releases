from typing import TypeAlias

import c4d
from jiko_bridge_client import (
    JbAssetExporterABC,
    JbAssetImporterABC,
    JbAssetSoloABC,
    JbMaterialImporterABC,
    JbSceneABC,
    JbSettingsABC,
)

JbSource: TypeAlias = c4d.documents.BaseDocument
JbMatrix: TypeAlias = c4d.Matrix

JbContainer: TypeAlias = c4d.BaseObject
JbObject: TypeAlias = c4d.BaseObject
JbMaterial: TypeAlias = c4d.BaseMaterial

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
