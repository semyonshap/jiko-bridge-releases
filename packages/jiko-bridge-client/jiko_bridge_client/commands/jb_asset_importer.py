"""Asset import workflow shared by every Jiko Bridge DCC plugin."""

from abc import ABC
from logging import Logger
from typing import Generic, List, cast

from ..api import JbAPI
from ..contracts import (
    JbContainerT,
    JbMaterialImporterABC,
    JbMaterialT,
    JbMatrixT,
    JbObjectT,
    JbSceneABC,
    JbSourceT,
)
from ..logger import get_logger
from ..models import AssetFile, AssetModel


class JbAssetImporterABC(ABC, Generic[JbSourceT, JbMatrixT, JbContainerT, JbObjectT, JbMaterialT]):
    """Base class for asset importers holding the shared import workflow.

    A plugin names ``scene_class`` and ``materials_class`` and, when it has to
    deviate, overrides the matching hook below: the selection, lookup and
    instance rules are implemented once here. The source document is taken by
    ``__init__`` and is deliberately not part of the interface.
    """

    scene_class: type[JbSceneABC[JbSourceT, JbMatrixT, JbContainerT, JbObjectT, JbMaterialT]]
    materials_class: type[JbMaterialImporterABC[JbSourceT, JbMaterialT]]

    def __init__(self, source: JbSourceT):
        self.source = source
        self.api = JbAPI()
        self.scene = self.scene_class(source)
        self.materials = self.materials_class(source)
        self._asset_cache: dict[str, AssetModel | None] = {}

    @property
    def logger(self) -> Logger:
        """Logger of the concrete plugin module, so log lines stay traceable."""
        return get_logger(type(self).__module__)

    def import_assets(self) -> None:
        """Imports assets by selection."""
        self._asset_cache = {}
        for asset in self._collect_assets():
            self._import_single(asset)

    def import_message(self) -> str:
        """Return a confirmation message based on the current selection."""
        materials, containers = self._collect_data()
        if materials:
            return (
                "Import assets for materials?\n"
                f"{len(materials)} material(s) with asset info found in selection."
            )
        if containers:
            return (
                "Import assets for asset containers?\n"
                f"{len(containers)} asset container(s) found in selection."
            )
        return "Import active asset from Jiko Bridge."

    def _collect_data(self) -> tuple[list[JbMaterialT], list[JbContainerT]]:
        objects = cast(List[JbObjectT], self.scene.get_selection())
        return (
            self.scene.get_materials_from_objects(objects),
            self.scene.get_containers_from_objects(objects),
        )

    def _collect_assets(self) -> list[AssetModel]:
        assets: list[AssetModel] = []
        materials, containers = self._collect_data()
        if materials:
            for material in materials:
                name = self.materials.get_material_name(material)
                if not name:
                    continue
                asset = self._resolve_asset(name)
                if asset is None:
                    continue
                assets.append(asset)
                if not AssetModel.from_string(name):
                    self.materials.set_material_name(
                        material, f"{asset.pack_name}__{asset.asset_name}"
                    )
        elif containers:
            for container in containers:
                asset = self._asset_from_container(container)
                if asset:
                    assets.append(asset)
        else:
            asset = self.api.get_active_asset()
            if asset:
                assets.append(asset)
        return assets

    def _asset_from_container(self, container: JbContainerT) -> AssetModel | None:
        """Re-read the asset of a container that is about to be imported into."""
        asset_model = self.scene.get_asset_data_from_container(container)
        if not asset_model:
            return None
        asset_model.active_type = None
        asset = self.api.get_asset(asset_model)
        if asset is not None:
            self.scene.clear_container(container)
        return asset

    def _import_single(self, asset: AssetModel) -> None:
        container: JbContainerT | None = None
        for file in asset.files:
            match file.bridge_type:
                case "model":
                    container = self._create_model(asset, file)
                    self._convert_to_instances(container)
                case "material":
                    material = self.materials.import_material(asset, file)
                    if material:
                        self.scene.merge_duplicates_materials(material)
                case _:
                    self.logger.warning("Unsupported bridge type: %s", file.bridge_type)
        if container is not None:
            self.scene.finish_asset(container)

    def _create_model(self, asset: AssetModel, file: AssetFile) -> JbContainerT:
        container = self.scene.get_container(asset)
        if container is None:
            container = self.scene.create_container(asset, file)
            self.scene.import_with_temp(cast(str, file.filepath), container)
        else:
            self.scene.create_instance(container, cast(str, asset.asset_name))
        return container

    def _convert_to_instances(self, container: JbContainerT) -> None:
        queue = [container]
        visited: set[str] = set()
        while queue:
            current = queue.pop(0)
            key = self.scene.container_key(current)
            if key in visited:
                continue
            visited.add(key)
            for obj in cast(List[JbObjectT], self.scene.walk([current])):
                asset_model = None
                for name in self.scene.get_names_from_placeholder(obj):
                    asset_model = self._resolve_asset(name)
                    if asset_model:
                        break
                if not asset_model:
                    continue
                asset_container = self._resolve_placeholder(obj, current, asset_model)
                if asset_container:
                    queue.append(asset_container)
            self.scene.cleanup_container(current)

    def _resolve_asset(self, name: str) -> AssetModel | None:
        """Resolve an asset by bundled name or by search, caching misses too."""
        if name in self._asset_cache:
            return self._asset_cache[name]
        query = AssetModel.from_string(name)
        asset = self.api.get_asset(query) if query else None
        if asset is None:
            asset = self.api.get_asset_by_search(name)
        self._asset_cache[name] = asset
        return asset

    def _resolve_placeholder(
        self, obj: JbObjectT, container: JbContainerT, asset_model: AssetModel
    ) -> JbContainerT | None:
        asset_container = self.scene.get_container(asset_model)
        created = False
        if not asset_container:
            for file in asset_model.files:
                asset_container = self.scene.create_container(asset_model, file)
                if self.scene.get_container(asset_model) is None:
                    self.scene.import_with_temp(cast(str, file.filepath), asset_container)
            created = True
        if asset_container is None:
            return None
        self.scene.create_instance(
            asset_container,
            cast(str, asset_model.asset_name),
            parent=container,
            source=obj,
        )
        self.scene.remove_object(obj)
        return asset_container if created else None
