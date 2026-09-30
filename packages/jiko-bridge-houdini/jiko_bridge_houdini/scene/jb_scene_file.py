"""Houdini file operations: model import and the assembled stage."""

from pathlib import Path

import hou
from jiko_bridge_houdini.jb_types import MODEL_EXTENSIONS, USD_EXTENSIONS
from jiko_bridge_houdini.jb_utils import source_path
from jiko_bridge_houdini.scene.jb_scene_instance import FBX_TRANSLATION, VECTOR_TYPES
from jiko_bridge_houdini.scene.jb_scene_temp import JbSceneTemp
from jiko_bridge_houdini.utils.jb_utils_fbx import DEFAULT_METERS_PER_UNIT, fbx_meters_per_unit
from pxr import Usd


class JbSceneFile(JbSceneTemp):
    """Houdini implementation of file operations."""

    def import_file(self, file_path: str) -> bool:
        """Import one model file into the scene the import is running in."""
        stage = self._temp
        if stage is None:
            raise hou.NodeError("A model import needs a temporary scene.")
        source = source_path(file_path)
        suffix = Path(source).suffix.lower()
        if suffix not in MODEL_EXTENSIONS:
            self.message(
                f"Cannot import {source}: {suffix or 'no extension'} is not a model format"
            )
            return False
        if suffix in USD_EXTENSIONS:
            # The container references the source file instead of copying its geometry.
            self._temp_reference = True
            stage.GetRootLayer().subLayerPaths.append(source)
            return True
        geometry = hou.Geometry()
        geometry.loadFromFile(source)
        units = self._file_units(source, suffix)
        if units != 1.0:
            geometry.transform(hou.hmath.buildScale(units, units, units))
        layer_id = hou.lop.addLockedGeometry(self.prim_name(source), geometry)
        self._temp_locked.append(layer_id)
        stage.GetRootLayer().subLayerPaths.append(layer_id)
        self._scale_translations(stage, units)
        return True

    def _scale_translations(self, stage: Usd.Stage, units: float) -> None:
        """Bake the source units into the FBX translations of one converted geometry."""
        if units == 1.0:
            return
        for prim in stage.Traverse():
            attribute = prim.GetAttribute(FBX_TRANSLATION)
            value = attribute.Get() if attribute else None
            if value is None:
                continue
            if isinstance(value, VECTOR_TYPES):
                attribute.Set(value * units)
            else:
                attribute.Set([item * units for item in value])

    def _import_fbx(self, file_path: str) -> bool:
        """Import one FBX source through the common model path."""
        return self.import_file(file_path)

    def export_file(self, _ext):
        """Houdini has no asset export yet."""
        self.logger.warning("Houdini file export is not implemented.")

    def _export_fbx(self, _file_path):
        """Houdini has no FBX export yet."""
        self.logger.warning("Houdini FBX export is not implemented.")

    def _file_units(self, source: str, suffix: str) -> float:
        """Meters per unit of one model file, read from the FBX header when it has one."""
        if not (self.settings.convert_units and suffix == ".fbx"):
            return 1.0
        try:
            return fbx_meters_per_unit(source)
        except ValueError as error:
            self.message(f"{error}, assuming {DEFAULT_METERS_PER_UNIT} meters per unit")
            return DEFAULT_METERS_PER_UNIT
