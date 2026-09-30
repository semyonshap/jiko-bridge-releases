from typing import Optional

import c4d
from jiko_bridge_c4d.jb_types import JbContainer
from jiko_bridge_c4d.scene.jb_scene_objects import JbSceneObjects
from jiko_bridge_client import AssetModel


class JbSceneContainer(JbSceneObjects):
    """Container and asset management: null objects, user data, collections."""

    def get_container(self, asset: AssetModel) -> Optional[JbContainer]:
        """The container null of an asset, once it already holds its model."""
        container = self.source.SearchObject(self.container_name(asset))
        if container is None or not container.GetChildren():
            return None
        return container

    def create_container(self, asset: AssetModel, file=None) -> JbContainer:
        """The container null of an asset, created under the protected Assets root."""
        root = self._ensure_collection("Assets")
        self._set_protection_tag(root)

        container = self._ensure_collection(self.container_name(asset), parent=root)
        self._set_protection_tag(container)
        self.set_asset_data(container, asset, file)
        return container

    def _ensure_collection(self, name: str, parent=None) -> JbContainer:
        """The null object of the given name, created under the parent when absent."""
        doc = self.source
        obj = doc.SearchObject(name)
        if obj is None:
            obj = c4d.BaseObject(c4d.Onull)
            if parent is not None:
                obj.InsertUnder(parent)
            else:
                doc.InsertObject(obj)

        obj.SetName(name)
        obj[c4d.ID_BASELIST_ICON_FILE] = "12499"
        obj[c4d.ID_BASELIST_ICON_COLORIZE_MODE] = c4d.ID_BASELIST_ICON_COLORIZE_MODE_CUSTOM
        obj[c4d.ID_BASELIST_ICON_COLOR] = c4d.Vector(0.071, 0.949, 0.85)

        return obj

    def set_asset_data(self, container, asset, file=None) -> None:
        self._set_user_data(container, "vaultName", asset.vault_name)
        self._set_user_data(container, "packName", asset.pack_name)
        self._set_user_data(container, "assetName", asset.asset_name)
        if file:
            self._set_user_data(container, "assetType", file.asset_type)

    def get_asset_data_from_container(self, container) -> Optional[AssetModel]:
        fields: dict = {}

        for key, bc in container.GetUserDataContainer() or []:
            name = bc[c4d.DESC_NAME]
            fields[name] = (container[key] or None) if name == "assetType" else container[key]

        return AssetModel.from_container_fields(
            fields.get("packName"),
            fields.get("assetName"),
            fields.get("assetType"),
            fields.get("vaultName"),
        )

    def copy_asset_data(self, src, dst) -> None:
        for key, bc in src.GetUserDataContainer():
            name = bc[c4d.DESC_NAME]
            value = src[key]
            self._set_user_data(dst, name, value)

    def apply_solo(self, containers: list[JbContainer]) -> None:
        """Show only the given containers and frame them in the viewport."""
        root = self.source.SearchObject("Assets")
        if root is None:
            return

        self.set_container_visibility(root, False)

        for child in root.GetChildren():
            self.set_container_visibility(child, None)

        for container in containers:
            self.set_container_visibility(container, True)

        c4d.CallCommand(12288)

    def get_containers_from_objects(self, objects) -> list[JbContainer]:
        return [
            obj
            for obj in objects
            if obj.CheckType(c4d.Onull) and self.get_asset_data_from_container(obj) is not None
        ]

    def get_containers_from_instances(self, objects) -> list[JbContainer]:
        containers = []
        for obj in objects:
            if not obj.CheckType(c4d.Oinstance):
                continue
            linked = obj[c4d.INSTANCEOBJECT_LINK]
            if linked is None or not linked.IsAlive():
                continue
            if self.get_asset_data_from_container(linked) is not None:
                containers.append(linked)
        return containers

    def cleanup_container(self, container) -> None:
        count = 0
        objects = self.walk(container.GetChildren())
        for obj in objects:
            if obj.GetType() == c4d.Onull and len(obj.GetChildren()) == 0:
                count += 1
                obj.Remove()

            elif obj.GetType() == c4d.Oalembicgenerator and len(obj.GetChildren()) == 0:
                has_geometry = obj[c4d.ALEMBIC_UPDATE_GEOMETRY]

                if not has_geometry:
                    count += 1
                    obj.Remove()

        if count > 0:
            self.logger.debug('Cleanup empty nulls: %s', count)

        c4d.CallCommand(12168)

    def clear_container(self, container) -> None:
        """Unified API: remove all children from asset null."""
        for child in container.GetChildren():
            child.Remove()
