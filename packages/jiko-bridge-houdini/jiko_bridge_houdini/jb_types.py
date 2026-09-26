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
from pxr import Usd

JbSource: TypeAlias = hou.OpNode
JbMatrix: TypeAlias = hou.Matrix4
JbMaterial: TypeAlias = hou.OpNode


@dataclass(eq=False)
class JbContainer:
    """An asset authored as a container prim inside its own USD layer."""

    layer: str
    root: str
    stage: Usd.Stage
    asset: dict[str, Any] = field(default_factory=dict)
    models: dict[str, "JbModel"] = field(default_factory=dict)
    remove_objects: list[str] = field(default_factory=list)
    pending: list["JbObject"] = field(default_factory=list)


@dataclass(eq=False)
class JbModel:
    """One parsed model file of a container, kept until the layer is authored."""

    source: str
    geometry: Optional[hou.Geometry] = None
    placeholders: list["Placeholder"] = field(default_factory=list)

    @property
    def converted(self) -> bool:
        """Whether the file has to be converted rather than referenced."""
        return self.geometry is not None


@dataclass(eq=False)
class JbObject:
    """A placeholder parsed from a file, or an instance awaiting authoring."""

    data: dict[str, Any]
    parent: Optional["JbContainer"] = None
    target: Optional["JbContainer"] = None


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
