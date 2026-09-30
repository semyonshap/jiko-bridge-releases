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
    _temp_layer: Optional[str]

    @contextmanager
    def temp_source(self, debug: bool = False) -> Generator[Usd.Stage, None, None]:
        """Swap in the isolated in-memory stage one model file is converted in."""
        self._temp = Usd.Stage.CreateInMemory()
        self._temp_layer = None
        try:
            yield self._temp
        finally:
            if not debug and self._temp_layer:
                hou.lop.removeLockedGeometry(self._temp_layer)
            self._temp = None
            self._temp_layer = None

    def _save_geometry(self, converted: Usd.Stage, container: JbContainer) -> str:
        """Write the converted geometry as one usdc next to the layer of its container."""
        converted.SetEditTarget(converted.GetSessionLayer())
        directory = os.path.dirname(container.GetRootLayer().identifier)
        path = os.path.join(directory, GEOMETRY_FILE)
        if not converted.Flatten().Export(path):
            raise hou.NodeError(f"Cannot write asset geometry: {path}")
        return path

    def _reference_source(self, container: JbContainer, source: str) -> None:
        """Keep one USD file on disk as the geometry of a container."""
        parent = self.geometry_path(self.container_root(container))
        self._ensure_prim(container, parent)
        original = Usd.Stage.Open(source)
        if original is None:
            raise hou.NodeError(f"Cannot open USD source: {source}")
        for root in original.GetPseudoRoot().GetChildren():
            if root.GetName() == "HoudiniLayerInfo":
                continue
            prim = container.DefinePrim(f"{parent}/{root.GetName()}")
            prim.GetReferences().AddReference(source, root.GetPath())
