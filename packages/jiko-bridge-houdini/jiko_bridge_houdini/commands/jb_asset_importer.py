"""Common asset import workflow implemented through Houdini scene operations."""

from collections import deque
from typing import Any

import hou
from jiko_bridge_client import AssetFile, AssetModel, get_logger
from jiko_bridge_houdini.jb_types import (
    JbAssetImporterBase,
    JbContainer,
    JbMaterial,
    JbObject,
    JbSource,
)
from jiko_bridge_houdini.jb_utils import cached_asset
from jiko_bridge_houdini.materials.jb_material_importer import JbMaterialImporter
from jiko_bridge_houdini.scene.jb_scene import JbScene

asset_import_logger = get_logger(__name__)


class JbAssetImporter(JbAssetImporterBase):
    """Use the same selection, lookup and instance rules as other DCC plugins."""

    scene: JbScene
    scene_class = JbScene
    materials_class = JbMaterialImporter

    def __init__(self, source: JbSource):
        super().__init__(source)
        self._visited: set[str] = set()

    def import_assets(self) -> None:
        self._asset_cache = {}
        for asset in self._collect_assets():
            if self.scene.select_asset(asset):
                self.scene.refresh()
                asset_import_logger.info("Imported asset %s", asset.asset_name)

    def _collect_data(self) -> tuple[list[JbMaterial], list[JbContainer]]:
        return ([], self.scene.get_containers_from_objects(self.scene.get_selection()))

    def _asset_from_container(self, container: JbContainer) -> AssetModel | None:
        query = self.scene.get_asset_data_from_container(container)
        if query is None:
            return None
        query.active_type = None
        return self.api.get_asset(query)

    def _import_single(self, asset: AssetModel) -> None:
        containers = []
        for file in asset.files:
            match file.bridge_type:
                case "model":
                    if not file.filepath:
                        asset_import_logger.warning("Model file has no path: %s", asset.asset_name)
                        continue
                    container = self._create_model(asset, file)
                    if container not in containers:
                        containers.append(container)
                case "material":
                    self.materials.import_material(asset, file)
                case _:
                    asset_import_logger.warning("Unsupported bridge type: %s", file.bridge_type)
        for container in containers:
            self._convert_to_instances(container)

    def _create_model(self, asset: AssetModel, file: AssetFile) -> JbContainer:
        container, exists = self.scene.get_or_create_asset_container(asset, file)
        if not exists and file.filepath:
            self.scene.import_with_temp(file.filepath, container)
        return container

    def _convert_to_instances(self, container: JbContainer) -> None:
        queue = deque([container])
        while queue:
            if hou.updateProgressAndCheckForInterrupt():
                raise hou.NodeError("Asset import cancelled.")
            current = queue.popleft()
            identifier = current.record["id"]
            if identifier in self._visited:
                continue
            self._visited.add(identifier)
            for obj in self.scene.walk([current]):
                if not isinstance(obj, JbObject) or obj.target is not None:
                    continue
                asset = None
                for name in self.scene.get_names_from_placeholder(obj):
                    asset = self._resolve_asset(name)
                    if asset:
                        break
                target = self._resolve_placeholder(obj, current, asset) if asset else None
                if target is not None:
                    queue.append(target)
                elif obj.parent is current:
                    self.scene.graph.warnings.append(
                        f"Unresolved placeholder {obj.data['object']} in {identifier}"
                    )
            self.scene.cleanup_container(current)

    def _resolve_placeholder(self, obj, container, asset_model) -> JbContainer | None:
        target = self.scene.get_container(asset_model)
        if target is None or not target.record["models"]:
            for file in asset_model.files:
                if file.bridge_type == "model" and file.filepath:
                    target = self._create_model(asset_model, file)
        if target is None or not target.record["models"]:
            return None
        instance = self.scene.create_instance(target, asset_model.asset_name or "asset")
        self.scene.copy_object_transform(instance, obj)
        self.scene.move_objects_to_container([instance], container)
        self.scene.remove_object(obj)
        return target

    def build_graph(self, geometry: hou.Geometry) -> dict[str, Any]:
        """Run the importer in the discovery SOP cook."""
        self._asset_cache = {}
        self._visited = set()
        self.scene.reset_graph(geometry)
        asset = cached_asset(self.scene.source)
        self._import_single(asset)
        root = self.scene.get_container(asset)
        return self.scene.graph_data([root] if root else [])
