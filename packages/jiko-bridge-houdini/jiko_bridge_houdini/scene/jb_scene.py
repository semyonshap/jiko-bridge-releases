"""Jiko Bridge scene state: one import session over the asset layers."""

from logging import Logger
from typing import cast

import hou
import loputils
from jiko_bridge_client import AssetModel, get_logger
from jiko_bridge_houdini.jb_types import JbContainer, JbSource
from jiko_bridge_houdini.jb_utils import absolute_path, apply_asset, cached_asset
from jiko_bridge_houdini.scene.jb_scene_file import JbSceneFile, asset_layer, scene_output_path
from jiko_bridge_houdini.scene.jb_scene_instance import reference
from jiko_bridge_houdini.scene.jb_scene_temp import JbStage, layer_metrics
from pxr import Tf, Usd, UsdGeom


def assemble_usd(node: hou.LopNode) -> None:
    """Python LOP entry point: reference the container prim of this node's asset."""
    owner = cast(hou.OpNode, node.parent())
    node.editableStage()
    scene = loputils.createPythonLayer(node)
    layer_metrics(scene)
    scene.defaultPrim = "World"
    stage = Usd.Stage.Open(scene)
    UsdGeom.Xform.Define(stage, "/World")
    root = "/World/" + Tf.MakeValidIdentifier(owner.name())
    UsdGeom.Xform.Define(stage, root)
    if owner.evalParm("cached"):
        path = scene_output_path(owner)
        if path:
            prim = stage.DefinePrim(root + "/asset")
            prim.GetReferences().AddReference(path)
            prim.SetInstanceable(True)
    else:
        entry = asset_layer(owner)
        if entry is not None:
            reference(stage, f"{root}/{entry['name']}", entry["path"], entry["root"])
    node.addSubLayer(scene.identifier)


class JbScene(JbSceneFile):
    """Houdini implementation of jb_scene operations."""

    def __init__(self, source: JbSource):
        self._source = source
        self._logger = get_logger(__name__)
        self.stage = JbStage(self.cache_root(), bool(source.evalParm("override")))
        self.convert_units = bool(source.evalParm("convert_units"))
        self.warnings: list[str] = []
        self._import_target: JbContainer | None = None

    @property
    def source(self) -> JbSource:
        """The HDA node this scene belongs to."""
        return self._source

    @property
    def logger(self) -> Logger:
        """Logger of the concrete plugin module."""
        return self._logger

    def cache_root(self) -> str:
        """Expanded directory every asset layer is written under."""
        return absolute_path(str(self.source.evalParm("cache_path")))

    def has_asset(self) -> bool:
        """Whether this node already carries an asset to import."""
        asset = cached_asset(self.source)
        return bool(asset.files)

    def import_with_temp(self, file_path: str, target: JbContainer) -> None:
        """Parse one model file into the given container."""
        previous = self._import_target
        self._import_target = target
        try:
            if not self.import_file(file_path):
                self.logger.warning("Cannot import model: %s", file_path)
        finally:
            self._import_target = previous

    def export_with_temp(self, _src, _ext):
        """Houdini has no asset export yet."""
        self.logger.warning("Houdini asset export is not implemented.")

    def get_project_filepath(self) -> str | None:
        """Path of the current hip file."""
        return hou.hipFile.path()

    def select_asset(self, asset: AssetModel) -> bool:
        """Persist the asset on the HDA before its layers are authored."""
        return apply_asset(self.source, asset)

    def refresh(self) -> None:
        """Force the assembler to cook so the viewport picks up new layers."""
        assembly = self.source.node("assemble_usd")
        if assembly is not None:
            assembly.cook(force=True)

    def report(self) -> str:
        """Everything this session left unresolved, one line per item."""
        return "\n".join(self.warnings)
