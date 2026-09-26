"""Houdini container operations, backed by the prims of an asset layer."""

import hashlib
import os
from typing import Any, Mapping, Optional

from jiko_bridge_client import AssetModel
from jiko_bridge_houdini.jb_types import JbContainer, JbObject
from jiko_bridge_houdini.jb_utils import source_path
from jiko_bridge_houdini.scene.jb_scene_objects import JbSceneObjects
from pxr import Tf, Usd, UsdGeom

GEOMETRY_PRIM = "geometry"
ASSET_KIND = "component"


def _base_name(source: str) -> str:
    return Tf.MakeValidIdentifier(os.path.splitext(os.path.basename(source))[0])


def prim_name(source: str) -> str:
    """Stable prim name of one source file inside an asset container."""
    source = os.path.normcase(os.path.normpath(source))
    return f"{_base_name(source)}_{hashlib.sha1(source.encode('utf-8')).hexdigest()[:10]}"


def model_path(root: str, source: str) -> str:
    """Where one model file's geometry lives inside a container."""
    return f"{root}/{GEOMETRY_PRIM}/{prim_name(source)}"


def asset_root(identifier: str, asset: dict[str, Any]) -> str:
    """Root prim of an asset layer: its asset name, or its identifier."""
    return "/" + Tf.MakeValidIdentifier(str(asset.get("assetName") or identifier or "asset"))


def layer_name(identifier: str, asset: dict[str, Any]) -> str:
    """Prim name of one asset inside the assembled scene."""
    names = [asset.get(key) for key in ("vaultName", "packName", "assetName")]
    joined = "_".join(str(name) for name in names if name)
    return Tf.MakeValidIdentifier(joined or str(identifier))


def author_container(
    stage: Usd.Stage, path: str, asset: Optional[Mapping[str, Any]] = None
) -> Usd.Prim:
    """Define an asset container prim and stamp its asset info dictionary."""
    prim = UsdGeom.Xform.Define(stage, path).GetPrim()
    if asset:
        model = Usd.ModelAPI(prim)
        model.SetKind(ASSET_KIND)
        model.SetAssetInfo({str(key): str(value) for key, value in asset.items() if value})
    return prim


def asset_of(container: JbContainer) -> Optional[AssetModel]:
    """The asset a container prim describes, read back from its asset info."""
    prim = container.stage.GetPrimAtPath(container.root)
    if not prim:
        return None
    info = Usd.ModelAPI(prim).GetAssetInfo()
    return AssetModel.from_container_fields(
        info.get("packName"), info.get("assetName"), None, info.get("vaultName")
    )


class JbSceneContainer(JbSceneObjects):
    """Houdini implementation of container operations."""

    def get_container(self, asset: AssetModel) -> JbContainer | None:
        """The container of an asset whose layer is already on disk."""
        container = self.stage.find(asset)
        if container is None:
            return None
        stored = asset_of(container)
        if stored is None:
            return None
        names = (stored.vault_name, stored.pack_name, stored.asset_name)
        if names != (asset.vault_name, asset.pack_name, asset.asset_name):
            return None
        return container

    def get_or_create_container(self, name: str, parent=None) -> JbContainer:
        """Open the container of a named asset, creating its layer when absent."""
        asset = AssetModel.from_string(name) or AssetModel(asset_name=name)
        return self.get_or_create_asset_container(asset)[0]

    def get_or_create_asset_container(self, asset, file=None) -> tuple[JbContainer, bool]:
        """Open the asset layer; the flag tells whether the work is already done."""
        container = self.stage.open(asset)
        if file is None or not file.filepath:
            return container, self.stage.has_models(container)
        return container, self.stage.has_model(container, source_path(file.filepath))

    def set_asset_data(self, container, asset, file=None) -> None:
        """Keep the asset identity on the container prim."""
        container.asset.update(asset.to_dict())
        if file is not None:
            container.asset["assetType"] = file.asset_type
        author_container(container.stage, container.root, container.asset)

    def get_asset_data_from_container(self, container) -> AssetModel | None:
        """Read the asset identity back from the container prim."""
        return asset_of(container)

    def copy_asset_data(self, src, dst) -> None:
        """Carry the asset identity over to another container or object."""
        if isinstance(dst, JbContainer):
            dst.asset = dict(src.asset)
            author_container(dst.stage, dst.root, dst.asset)
        else:
            dst.data["asset"] = dict(src.asset)

    def get_containers_from_objects(self, objects) -> list[JbContainer]:
        """Every container the given objects belong to."""
        result = []
        for obj in objects:
            container = obj if isinstance(obj, JbContainer) else getattr(obj, "target", None)
            if container is not None and container not in result:
                result.append(container)
        return result

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
            cycle = bool(replace and self.stage.is_cycle(container, target))
            obj.data["cycle"] = cycle
            obj.data["replace"] = replace and not cycle
            if cycle and target is not None:
                self.warnings.append(f"Cyclic dependency: {container.root} -> {target.root}")
            self.remove_object(obj)
            obj.parent = container
            if obj.data["replace"]:
                self.stage.add_object(container, obj)

    def cleanup_container(self, container) -> None:
        """Author every parsed model, write the layer, report what stayed open."""
        for obj in container.pending:
            if obj.target is None:
                self.warnings.append(
                    f"Unresolved placeholder {obj.data['object']} in {container.root}"
                )
        self.stage.finish(container)
        container.pending.clear()

    def clear_container(self, container) -> None:
        """Empty a container so its asset can be imported again."""
        self.stage.clear(container)
