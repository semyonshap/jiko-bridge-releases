from typing import Optional

import bpy
from jiko_bridge_client import AssetModel

from ..jb_types import JbContainer
from .jb_scene_objects import JbSceneObjects


class JbSceneContainer(JbSceneObjects):
    """Container and asset management: collections, metadata."""

    def get_container(self, asset) -> Optional[JbContainer]:
        root = self.get_or_create_container("Assets")
        name = f"Asset_{asset.pack_name}_{asset.asset_name}"

        for col in root.children:
            if isinstance(col, bpy.types.Collection) and col.name == name:
                return col

        return None

    def get_or_create_container(self, name, parent=None) -> JbContainer:
        ctx = self.source
        col = bpy.data.collections.get(name)
        if not col:
            col = bpy.data.collections.new(name)
            if parent is not None:
                parent.children.link(col)
            else:
                scene = ctx.scene
                if scene:
                    root_col = scene.collection
                    if root_col is not None:
                        root_col.children.link(col)

            col.color_tag = "COLOR_04"

        return col

    def get_or_create_asset_container(self, asset, file=None) -> tuple[JbContainer, bool]:
        root = self.get_or_create_container("Assets")
        name = f"Asset_{asset.pack_name}_{asset.asset_name}"

        col = self.get_or_create_container(name, parent=root)
        self.set_asset_data(col, asset, file)

        if name not in [c.name for c in root.children]:
            try:
                root.children.link(col)
            except RuntimeError:
                pass

        existed = True
        if len(col.objects) == 0:
            existed = False

        return col, existed

    def get_containers_from_objects(self, objects) -> list[JbContainer]:
        containers: set[JbContainer] = set()
        for obj in objects:
            if isinstance(obj, bpy.types.Collection):
                if self.get_asset_data_from_container(obj):
                    containers.add(obj)

        return list(containers)

    def get_containers_from_instances(self, objects) -> list[JbContainer]:
        containers: set[JbContainer] = set()
        for obj in objects:
            if not isinstance(obj, bpy.types.Object):
                continue
            if obj.instance_type != 'COLLECTION':
                continue
            collection = obj.instance_collection
            if collection is None:
                continue
            if self.get_asset_data_from_container(collection):
                containers.add(collection)

        return list(containers)

    def set_asset_data(self, container, asset, file=None) -> None:
        container["jb_pack_name"] = asset.pack_name or ""
        container["jb_asset_name"] = asset.asset_name or ""
        container["jb_asset_type"] = file.asset_type or "" if file else ""
        container["jb_vault_name"] = asset.vault_name or ""

    def get_asset_data_from_container(self, container) -> Optional[AssetModel]:
        pack_name = container.get("jb_pack_name", None)
        asset_name = container.get("jb_asset_name", None)
        asset_type = container.get("jb_asset_type", None)
        vault_name = container.get("jb_vault_name", None)
        if not (pack_name and asset_name):
            return None
        return AssetModel(
            pack_name=pack_name,
            asset_name=asset_name,
            active_type=asset_type,
            vault_name=vault_name,
        )

    def copy_asset_data(self, src, dst) -> None:
        for key in ("jb_pack_name", "jb_asset_name", "jb_asset_type", "jb_vault_name"):
            if key in src:
                dst[key] = src[key]

    def clear_container(self, container) -> None:
        for obj in list(container.objects):
            container.objects.unlink(obj)
            bpy.data.objects.remove(obj, do_unlink=True)

    def cleanup_container(self, container) -> None:
        for obj in list(container.objects):
            if obj.type == "EMPTY" and obj.instance_type != "COLLECTION" and not obj.children:
                bpy.data.objects.remove(obj, do_unlink=True)
        for child in container.children:
            self.cleanup_container(child)

    def move_objects_to_container(self, objects, container) -> None:
        moved = set()
        objects = self.walk(objects)

        for obj in objects:
            if isinstance(obj, bpy.types.Object):
                if obj in moved:
                    continue
                moved.add(obj)
                for col in list(obj.users_collection):
                    col.objects.unlink(obj)
                if container not in obj.users_collection:
                    container.objects.link(obj)
