"""Types and file formats specific to Houdini."""

from dataclasses import dataclass, field
from typing import Any, List, Optional, TypeAlias, TypedDict

import hou
from jiko_bridge_client import (
    JbAssetExporterABC,
    JbAssetImporterABC,
    JbAssetSoloABC,
    JbMaterialImporterABC,
    JbSceneABC,
    JbSettingsABC,
)

JbSource: TypeAlias = hou.OpNode
JbMatrix: TypeAlias = hou.Matrix4
JbMaterial: TypeAlias = hou.OpNode


@dataclass(eq=False)
class JbContainer:
    """An asset container authored into USD after SOP discovery."""

    record: dict[str, Any]
    objects: list["JbObject"] = field(default_factory=list)
    parent: Optional["JbContainer"] = None


@dataclass(eq=False)
class JbObject:
    """A source placeholder or a pending USD instance."""

    data: dict[str, Any]
    parent: Optional[JbContainer] = None
    target: Optional[JbContainer] = None


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


class Placeholder(TypedDict):
    """A source object and the names and placement used to resolve its asset."""

    object: str
    names: List[str]
    transform: Optional[List[float]]
