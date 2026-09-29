"""Temporary scenes used while importing model files."""

from contextlib import contextmanager
from typing import Generator, Optional

import hou
from jiko_bridge_houdini.jb_types import JbContainer, JbSource
from jiko_bridge_houdini.scene.jb_scene_instance import JbSceneInstance
from pxr import Usd, UsdGeom


class JbSceneTemp(JbSceneInstance):
    """Houdini implementation of temp operations."""

    _temp: Optional[Usd.Stage]
    _temp_units: float
    _temp_reference: bool
    _temp_locked: list[str]

    @contextmanager
    def temp_source(self, debug: bool = False) -> Generator[JbSource, None, None]:
        """Swap in the isolated in-memory stage one model file is converted in."""
        previous = (self._temp, self._temp_units, self._temp_reference, self._temp_locked)
        locked: list[str] = []
        self._temp = Usd.Stage.CreateInMemory()
        self._temp_units = 1.0
        self._temp_reference = False
        self._temp_locked = locked
        try:
            yield self._temp
        finally:
            self._temp, self._temp_units, self._temp_reference, self._temp_locked = previous
            if not debug:
                for layer_id in locked:
                    hou.lop.removeLockedGeometry(layer_id)

    def _copy_source(self, src: Usd.Stage, dst: JbContainer, source: str) -> None:
        """Author the temp scene into the container: as a reference, or as its geometry."""
        parent = self.geometry_path(dst.root)
        stage = self._edit(dst)
        UsdGeom.Xform.Define(stage, parent)
        if self._temp_reference:
            self._reference_source(stage, parent, source)
        else:
            self._geometry_into_layer(dst, src)
        found = list(self.stage_placeholders(src, self._temp_units))
        self.mark_placeholders(dst, source, found)

    def _geometry_into_layer(self, container: JbContainer, converted: Usd.Stage) -> None:
        """Copy the root prims of one converted geometry into the layer of its container."""
        converted.SetEditTarget(converted.GetSessionLayer())
        self.make_explicit(converted)
        parent = self.geometry_path(container.root)
        self.copy_geometry_roots(converted.Flatten(), self._layer_of(container), parent)

    def _reference_source(self, stage: Usd.Stage, path: str, source: str) -> None:
        """Keep the original USD file on disk; author replacements as opinions."""
        original = Usd.Stage.Open(source)
        if original is None:
            raise hou.NodeError(f"Cannot open USD source: {source}")
        for root in original.GetPseudoRoot().GetChildren():
            if root.GetName() == "HoudiniLayerInfo":
                continue
            prim = stage.DefinePrim(f"{path}/{root.GetName()}")
            prim.GetReferences().AddReference(source, root.GetPath())
