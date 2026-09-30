"""Asset containers and their metadata in USD and on the HDA."""

import os
from typing import Any, Mapping

import hou
from jiko_bridge_client import AssetModel
from jiko_bridge_houdini.jb_types import (
    ASSET_KIND,
    JbContainer,
    JbObject,
)
from jiko_bridge_houdini.scene.jb_scene_objects import JbSceneObjects
from jiko_bridge_houdini.utils.jb_utils_params import asset_cache_file, store_asset
from pxr import Sdf, Tf, Usd, UsdGeom

ASSET_FIELDS = ("vaultName", "packName", "assetName", "assetType")


class JbSceneContainer(JbSceneObjects):
    """Houdini implementation of asset container operations."""

    @staticmethod
    def asset_fields(asset: Mapping[str, Any]) -> dict[str, str]:
        """Identity of an asset as the plain strings a container prim stores."""
        return {key: str(asset[key]) for key in ASSET_FIELDS if asset.get(key)}

    @staticmethod
    def prim_name(source: str) -> str:
        """Prim name of one source file inside an asset container."""
        return Tf.MakeValidIdentifier(os.path.splitext(os.path.basename(source))[0])

    def asset_root(self, asset: AssetModel) -> str:
        """Root prim of one asset: the container every layer of that asset owns."""
        return f"/{Tf.MakeValidIdentifier(self.container_name(asset))}"

    def set_asset_data(self, container, asset, file=None) -> None:
        """Keep the asset identity on the container prim of its own layer."""
        fields = asset.to_dict()
        asset_type = file.asset_type if file is not None else asset.active_type
        if asset_type:
            fields["assetType"] = asset_type
        prim = self._ensure_prim(container, self.container_root(container))
        values = self.asset_fields(fields)
        if values:
            Usd.ModelAPI(prim).SetKind(ASSET_KIND)
        for key in ASSET_FIELDS:
            attribute = prim.CreateAttribute(key, Sdf.ValueTypeNames.String, custom=True)
            if key in values:
                attribute.Set(values[key])

    def _ensure_prim(self, stage: Usd.Stage, path: str) -> Usd.Prim:
        """The prim at the given path, defined as an xform when it is missing."""
        prim = stage.GetPrimAtPath(path)
        if prim and prim.IsValid():
            return prim
        return UsdGeom.Xform.Define(stage, path).GetPrim()

    def get_container(self, asset) -> JbContainer | None:
        path = asset_cache_file(self.node, asset)
        if self.settings.override or not path or not os.path.isfile(path):
            return None
        container = self._container_stage(asset)
        return container if self._has_models(container) else None

    def create_container(self, asset, file=None) -> JbContainer:
        store_asset(self.node, asset)
        container = self._container_stage(asset)
        self.set_asset_data(container, asset, file)
        return container

    def get_asset_data_from_container(self, container) -> AssetModel | None:
        prim = container.GetPrimAtPath(self.container_root(container))
        fields: dict[str, str] = {}
        if prim:
            for key in ASSET_FIELDS:
                attribute = prim.GetAttribute(key)
                value = attribute.Get() if attribute else None
                if value:
                    fields[key] = str(value)

        return AssetModel.from_container_fields(
            fields.get("packName"),
            fields.get("assetName"),
            fields.get("assetType"),
            fields.get("vaultName"),
        )

    def copy_asset_data(self, src, dst) -> None:
        if not isinstance(dst, JbContainer):
            return
        asset = self.get_asset_data_from_container(src)
        if asset is None:
            return
        self.set_asset_data(dst, asset)

    def get_containers_from_objects(self, objects) -> list[JbContainer]:
        result: dict[str, JbContainer] = {}
        for obj in objects:
            if isinstance(obj, JbContainer):
                result.setdefault(self.container_key(obj), obj)
        return list(result.values())

    def get_containers_from_instances(self, objects) -> list[JbContainer]:
        result: dict[str, JbContainer] = {}
        for obj in objects:
            if not isinstance(obj, JbObject) or not obj:
                continue
            stage = obj.GetStage()
            if stage is None:
                continue
            references = obj.GetMetadata("references")
            if references is None:
                continue
            for reference in references.GetAppliedItems():
                if not reference.assetPath:
                    continue
                layer = Sdf.Layer.FindOrOpenRelativeToLayer(
                    stage.GetRootLayer(), reference.assetPath
                )
                if layer is None:
                    continue
                container = Usd.Stage.Open(layer)
                result.setdefault(self.container_key(container), container)
                break
        return list(result.values())

    def cleanup_container(self, _container) -> None:
        """Report the placeholders that stayed unresolved."""

    def clear_container(self, container) -> None:
        if not self.settings.override:
            return
        root = self.container_root(container)
        layer = container.GetRootLayer()
        layer.Clear()
        self._set_layer_metrics(layer)
        container.SetDefaultPrim(self._ensure_prim(container, root))

    def _has_models(self, container: JbContainer) -> bool:
        """Whether this container already holds geometry of any model."""
        geometry = self.geometry_path(self.container_root(container))
        prim = container.GetPrimAtPath(geometry)
        return bool(prim) and bool(prim.GetChildren())

    def _container_stage(self, asset: AssetModel) -> JbContainer:
        """The stage of the cache layer of an asset, its root prim authored.

        The layer file is created when absent, and cleared when the import is
        overriding or when nothing was ever written into it.
        """
        path = asset_cache_file(self.node, asset)
        if path is None:
            raise hou.NodeError(f"The asset has no cache file: {asset.asset_name!r}")
        container = self._containers.get(path)
        if container is None:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            layer = Sdf.Layer.Find(path)
            if layer is None:
                layer = (
                    Sdf.Layer.FindOrOpen(path)
                    if os.path.isfile(path)
                    else Sdf.Layer.CreateNew(path)
                )
            if layer is None:
                raise hou.NodeError(f"Cannot open asset layer: {path}")
            if self.settings.override or not layer.rootPrims:
                layer.Clear()
                self._set_layer_metrics(layer)
            container = Usd.Stage.Open(layer)
            self._containers[path] = container
        prim = self._ensure_prim(container, self.asset_root(asset))
        if container.GetDefaultPrim() != prim:
            container.SetDefaultPrim(prim)
        return container
