"""
Cinema 4D types, bound to the shared Jiko Bridge contracts.
Code by Semyon Shapoval, 2026
"""

import c4d

from jiko_bridge_client import (
    JbAssetExporterABC,
    JbAssetImporterABC,
    JbMaterialImporterABC,
    JbSceneABC,
    JbSettingsABC,
)

JbSource = c4d.documents.BaseDocument
JbMatrix = c4d.Matrix

JbContainer = c4d.BaseObject
JbObject = c4d.BaseObject
JbMaterial = c4d.BaseMaterial

JbData = JbContainer | JbObject | JbMaterial

JbSceneBase = JbSceneABC[JbSource, JbMatrix, JbContainer, JbObject, JbMaterial]
JbMaterialImporterBase = JbMaterialImporterABC[JbMaterial]
JbSettingsBase = JbSettingsABC[JbContainer]
JbAssetImporterBase = JbAssetImporterABC[JbContainer, JbObject, JbMaterial]
JbAssetExporterBase = JbAssetExporterABC[JbContainer, JbObject, JbMaterial]
