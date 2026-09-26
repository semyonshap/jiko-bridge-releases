from logging import Logger
from typing import Any

import hou
from jiko_bridge_client import AssetModel, get_logger
from jiko_bridge_houdini.jb_types import JbContainer, JbSource
from jiko_bridge_houdini.jb_utils import add_string_attribs, apply_asset
from jiko_bridge_houdini.scene.jb_scene_file import JbSceneFile
from jiko_bridge_houdini.scene.jb_scene_graph import JbSceneGraph


class JbScene(JbSceneFile):
    """Houdini implementation of jb_scene operations."""

    def __init__(self, source: JbSource):
        self._source = source
        self._logger = get_logger(__name__)
        self.containers: dict[str, JbContainer] = {}
        self.reset_graph(hou.Geometry())

    @property
    def source(self) -> JbSource:
        return self._source

    @property
    def logger(self) -> Logger:
        return self._logger

    def reset_graph(self, geometry: hou.Geometry) -> None:
        """Begin a new cook with independent records and source geometry."""
        self.containers.clear()
        add_string_attribs(geometry, hou.attribType.Prim, ("asset_id", "source", "name"))
        self.graph = JbSceneGraph(geometry, bool(self.source.evalParm("convert_units")))
        self._import_target: JbContainer | None = None

    def import_with_temp(self, file_path: str, target: JbContainer) -> None:
        previous = self._import_target
        self._import_target = target
        try:
            if not self.import_file(file_path):
                self.logger.warning("Cannot import model: %s", file_path)
        finally:
            self._import_target = previous

    def export_with_temp(self, _src, _ext):
        self.logger.warning("Houdini asset export is not implemented.")

    def get_project_filepath(self) -> str | None:
        return hou.hipFile.path()

    def select_asset(self, asset: AssetModel) -> bool:
        """Persist the asset on the HDA before its procedural cook."""
        return apply_asset(self.source, asset)

    def refresh(self) -> None:
        """Force the discovery SOP to cook so the graph picks up changes."""
        scan = self.source.node("geometry/discover_assets")
        if scan is not None:
            scan.cook(force=True)

    def graph_data(self, roots: list[JbContainer]) -> dict[str, Any]:
        """Serialize the asset graph for the geometry SOPs."""
        return {
            "version": 1,
            "roots": [c.record["id"] for c in roots if c.record["models"]],
            "assets": list(self.graph.records.values()),
            "warnings": self.graph.warnings,
        }
