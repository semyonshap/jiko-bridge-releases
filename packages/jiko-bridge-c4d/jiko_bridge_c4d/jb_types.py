from typing import TypeAlias

import c4d
from jiko_bridge_client import (
    JbAssetExporterABC,
    JbAssetImporterABC,
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
JbMaterialImporterBase: TypeAlias = JbMaterialImporterABC[JbMaterial]
JbSettingsBase: TypeAlias = JbSettingsABC[JbContainer]
JbAssetImporterBase: TypeAlias = JbAssetImporterABC[JbContainer, JbObject, JbMaterial]
JbAssetExporterBase: TypeAlias = JbAssetExporterABC[JbContainer, JbObject, JbMaterial]
