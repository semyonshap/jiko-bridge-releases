"""Asset containers and their metadata in USD and on the HDA."""

import os
from typing import Any, Mapping, Optional

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
    def container_fields(prim: Usd.Prim) -> dict[str, str]:
        """Identity fields read back from the attributes of a container prim."""
        fields: dict[str, str] = {}
        for key in ASSET_FIELDS:
            attribute = prim.GetAttribute(key)
            if attribute is None:
                continue
            value = attribute.Get()
            if value:
                fields[key] = str(value)
        return fields

    @staticmethod
    def prim_name(source: str) -> str:
        """Prim name of one source file inside an asset container."""
        return Tf.MakeValidIdentifier(os.path.splitext(os.path.basename(source))[0])

    @staticmethod
    def asset_root(identifier: str, asset: Mapping[str, Any]) -> str:
        """Root prim of one asset: the container every layer of that asset owns."""
        name = Tf.MakeValidIdentifier(str(asset.get("assetName") or identifier or "asset"))
        return f"/{name}"

    def author_container(
        self, stage: Usd.Stage, path: str, asset: Optional[Mapping[str, Any]] = None
    ) -> Usd.Prim:
        """Define an asset container prim and stamp its identity attributes."""
        parent = str(Sdf.Path(path).GetParentPath())
        if parent != "/":
            UsdGeom.Xform.Define(stage, parent)
        prim = UsdGeom.Xform.Define(stage, path).GetPrim()
        fields = self.asset_fields(asset or {})
        if fields:
            Usd.ModelAPI(prim).SetKind(ASSET_KIND)
        for key in ASSET_FIELDS:
            attribute = prim.CreateAttribute(key, Sdf.ValueTypeNames.String, custom=True)
            if key in fields:
                attribute.Set(fields[key])
        return prim

    @staticmethod
    def asset_of(fields: Mapping[str, Any]) -> Optional[AssetModel]:
        """The asset a set of container identity fields describes, or None if incomplete."""
        return AssetModel.from_container_fields(
            fields.get("packName"),
            fields.get("assetName"),
            fields.get("assetType"),
            fields.get("vaultName"),
        )

    def get_container(self, asset: AssetModel) -> JbContainer | None:
        """The container of an asset that already has a cache layer on disk."""
        path = asset_cache_file(self.node, asset)
        if self.settings.override or not path or not os.path.isfile(path):
            return None
        return self._open_container(asset)

    def get_or_create_container(self, name: str, parent=None) -> JbContainer:
        """Open the container of a named asset, creating its layer when absent."""
        asset = AssetModel.from_string(name) or AssetModel(asset_name=name)
        return self.get_or_create_asset_container(asset)[0]

    def get_or_create_asset_container(self, asset, file=None) -> tuple[JbContainer, bool]:
        """Record the asset in its entry, then open the layer that entry names."""
        store_asset(self.node, asset)
        container = self._open_container(asset)
        self.set_asset_data(container, asset, file)
        return container, self._has_models(container)

    def set_asset_data(self, container, asset, file=None) -> None:
        """Keep the asset identity on the container prim of its own layer."""
        container.asset.update(asset.to_dict())
        asset_type = file.asset_type if file is not None else asset.active_type
        if asset_type:
            container.asset["assetType"] = asset_type
        self.author_container(self._edit(container), container.root, container.asset)

    def get_asset_data_from_container(self, container) -> AssetModel | None:
        """Read the asset identity back from the container prim of its own layer."""
        prim = self.source.GetPrimAtPath(container.root)
        fields = self.container_fields(prim) if prim is not None else container.asset
        return self.asset_of(fields)

    def copy_asset_data(self, src, dst) -> None:
        """Carry the asset identity over to another container or object."""
        if isinstance(dst, JbContainer):
            dst.asset = dict(src.asset)
            self.author_container(self._edit(dst), dst.root, dst.asset)
        else:
            dst.data["asset"] = dict(src.asset)

    def get_containers_from_objects(self, objects) -> list[JbContainer]:
        """Every container the given objects belong to."""
        result: dict[str, JbContainer] = {}
        for obj in objects:
            container = obj if isinstance(obj, JbContainer) else getattr(obj, "target", None)
            if container is not None:
                result.setdefault(self.container_key(container), container)
        return list(result.values())

    def get_containers_from_instances(self, objects) -> list[JbContainer]:
        """Every container the given instances point at."""
        return self.get_containers_from_objects(
            [obj for obj in objects if isinstance(obj, JbObject) and obj.target is not None]
        )

    def move_objects_to_container(self, objects, container) -> None:
        """Author the given instances into a container; cycles only warn."""
        for obj in objects:
            target = obj.target
            replace = target is not None and obj.data.get("transform") is not None
            cycle = bool(replace and self._is_cycle(container, target))
            obj.data["cycle"] = cycle
            obj.data["replace"] = replace and not cycle
            if cycle and target is not None:
                self.message(f"Cyclic dependency: {container.root} -> {target.root}")
            self.remove_object(obj)
            obj.parent = container
            if obj.data["replace"]:
                self._add_instance(container, obj)
                placeholder = obj.data.get("placeholder")
                if placeholder is not None:
                    placeholder.data["replace"] = True

    def cleanup_container(self, container) -> None:
        """Report the placeholders that stayed unresolved."""
        for obj in self.get_children(container):
            self.message(f"Unresolved placeholder {obj.data['object']} in {container.root}")

    def clear_container(self, container) -> None:
        """Empty a container so its asset can be imported again, only when overriding."""
        if not self.settings.override:
            return
        layer = self._layer_of(container)
        layer.Clear()
        self._set_layer_metrics(layer)
        layer.defaultPrim = Sdf.Path(container.root).name
        self.author_container(self._edit(container), container.root)

    def _has_models(self, container: JbContainer) -> bool:
        """Whether this container already holds geometry of any model."""
        prim = self.source.GetPrimAtPath(self.geometry_path(container.root))
        return bool(prim) and bool(prim.GetChildren())

    def _open_container(self, asset: AssetModel) -> JbContainer:
        """The container of an asset: its cache layer, its prim path and its metadata."""
        metadata = asset.to_dict()
        file = asset_cache_file(self.node, asset)
        if file is None:
            raise hou.NodeError(f"The asset has no cache file: {metadata.get('assetName')!r}")
        container = JbContainer(file, self.asset_root("", metadata), asset=dict(metadata))
        self._layer(file, reset=not self._attached(file), root=Sdf.Path(container.root).name)
        self._attach(container)
        if not self.source.GetPrimAtPath(container.root):
            self.author_container(self._edit(container), container.root)
        return container
