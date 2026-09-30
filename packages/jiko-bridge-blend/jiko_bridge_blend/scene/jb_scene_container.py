from typing import Optional

import bpy
from jiko_bridge_client import AssetModel

from ..jb_types import JbContainer
from .jb_scene_objects import JbSceneObjects


class JbSceneContainer(JbSceneObjects):
    """Container and asset management: collections, metadata."""

    def get_container(self, asset: AssetModel) -> Optional[JbContainer]:
        """The container collection of an asset, once it already holds its model."""
        collection = bpy.data.collections.get(self.container_name(asset))
        if collection is None or not collection.objects:
            return None
        return collection

    def create_container(self, asset: AssetModel, file=None) -> JbContainer:
        """The container collection of an asset, linked under the Assets root."""
        root = self._ensure_null("Assets")

        container = self._ensure_null(self.container_name(asset), parent=root)
        self.set_asset_data(container, asset, file)
        return container

    def _ensure_null(self, name: str, parent=None) -> JbContainer:
        """The collection of the given name, created and linked under the parent when absent."""
        scene = self.source.scene
        collection = bpy.data.collections.get(name)
        if collection is None:
            collection = bpy.data.collections.new(name)
            collection.color_tag = "COLOR_04"

        if parent is None:
            parent = scene.collection if scene else None
        if parent is not None and name not in {child.name for child in parent.children}:
            try:
                parent.children.link(collection)
            except RuntimeError:
                pass

        return collection

    def apply_solo(self, containers: list[JbContainer]) -> None:
        """Show only the given containers and frame them in the viewport."""
        root = bpy.data.collections.get("Assets")
        if root is None:
            return

        # Hide root
        self.set_container_visibility(root, True)

        # Hide every child
        for child in root.children:
            self.set_container_visibility(child, False)

        # Show the soloed ones
        for container in containers:
            self.set_container_visibility(container, True)

        bpy.ops.view3d.view_all()

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
        return AssetModel.from_container_fields(
            container.get("jb_pack_name", None),
            container.get("jb_asset_name", None),
            container.get("jb_asset_type", None),
            container.get("jb_vault_name", None),
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
