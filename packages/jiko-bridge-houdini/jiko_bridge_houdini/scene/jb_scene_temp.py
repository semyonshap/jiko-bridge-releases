"""Temporary scenes used while importing model files."""

import os
from contextlib import contextmanager
from typing import Generator, Optional

import hou
from jiko_bridge_houdini.jb_types import GEOMETRY_FILE, JbContainer
from jiko_bridge_houdini.scene.jb_scene_instance import JbSceneInstance
from pxr import Usd


class JbSceneTemp(JbSceneInstance):
    """Houdini implementation of temp operations."""

    _temp: Optional[Usd.Stage]
    _temp_reference: bool
    _temp_locked: list[str]

    @contextmanager
    def temp_source(self, debug: bool = False) -> Generator[Usd.Stage, None, None]:
        """Swap in the isolated in-memory stage one model file is converted in."""
        previous = (self._temp, self._temp_reference, self._temp_locked)
        locked: list[str] = []
        self._temp = Usd.Stage.CreateInMemory()
        self._temp_reference = False
        self._temp_locked = locked
        try:
            yield self._temp
        finally:
            self._temp, self._temp_reference, self._temp_locked = previous
            if not debug:
                for layer_id in locked:
                    hou.lop.removeLockedGeometry(layer_id)

    def _copy_source(self, src: Usd.Stage, dst: JbContainer, source: str) -> None:
        """Author the temp scene into the container as references to USD files on disk."""
        parent = self.geometry_path(self.container_root(dst))
        self._ensure_prim(dst, parent)
        if self._temp_reference:
            self._reference_source(dst, parent, source)
        else:
            self._reference_source(dst, parent, self._save_geometry(src, dst))

    def _save_geometry(self, converted: Usd.Stage, container: JbContainer) -> str:
        """Write the converted geometry as one usdc next to the layer of its container."""
        converted.SetEditTarget(converted.GetSessionLayer())
        directory = os.path.dirname(container.GetRootLayer().identifier)
        path = os.path.join(directory, GEOMETRY_FILE)
        if not converted.Flatten().Export(path):
            raise hou.NodeError(f"Cannot write asset geometry: {path}")
        return path

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
