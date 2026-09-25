"""
Scene container management for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

from typing import Optional

import c4d

from jiko_bridge_c4d.jb_types import JbContainer
from jiko_bridge_c4d.scene.jb_scene_objects import JbSceneObjects
from jiko_bridge_client import AssetModel


class JbSceneContainer(JbSceneObjects):
    """Container and asset management: null objects, user data, collections."""

    def get_container(self, asset):
        doc = self.source
        name = f"Asset_{asset.pack_name}_{asset.asset_name}"
        return doc.SearchObject(name)

    def get_or_create_container(self, name, parent=None) -> tuple[JbContainer, bool]:
        doc = self.source
        obj = doc.SearchObject(name)
        existed = obj is not None

        if not existed:
            obj = c4d.BaseObject(c4d.Onull)
            if parent is not None:
                obj.InsertUnder(parent)
            else:
                doc.InsertObject(obj)

        obj.SetName(name)
        obj[c4d.ID_BASELIST_ICON_FILE] = "12499"
        obj[c4d.ID_BASELIST_ICON_COLORIZE_MODE] = c4d.ID_BASELIST_ICON_COLORIZE_MODE_CUSTOM
        obj[c4d.ID_BASELIST_ICON_COLOR] = c4d.Vector(0.071, 0.949, 0.85)

        return obj, existed

    def get_or_create_asset_container(self, asset, file=None) -> tuple[JbContainer, bool]:
        """Get or create an asset container null with user data from the asset and file."""
        root_null, _ = self.get_or_create_container("Assets")
        self._set_protection_tag(root_null)

        asset_null, asset_existed = self.get_or_create_container(
            f"Asset_{asset.pack_name}_{asset.asset_name}", parent=root_null
        )

        self._set_protection_tag(asset_null)

        self._set_user_data(asset_null, "databaseName", asset.database_name)
        self._set_user_data(asset_null, "packName", asset.pack_name)
        self._set_user_data(asset_null, "assetName", asset.asset_name)
        if file:
            self._set_user_data(asset_null, "assetType", file.asset_type)

        if len(asset_null.GetChildren()) == 0:
            asset_existed = False

        return asset_null, asset_existed

    def set_asset_data(self, container, asset, file=None) -> None:
        self._set_user_data(container, "databaseName", asset.database_name)
        self._set_user_data(container, "packName", asset.pack_name)
        self._set_user_data(container, "assetName", asset.asset_name)
        if file:
            self._set_user_data(container, "assetType", file.asset_type)

    def get_asset_data_from_container(self, container) -> Optional[AssetModel]:
        pack_name = asset_name = asset_type = database_name = None

        for key, bc in container.GetUserDataContainer() or []:
            bc_name = bc[c4d.DESC_NAME]
            if bc_name == "packName":
                pack_name = container[key]
            elif bc_name == "assetName":
                asset_name = container[key]
            elif bc_name == "assetType":
                asset_type = container[key] or None
            elif bc_name == "databaseName":
                database_name = container[key] or None

        if not (pack_name and asset_name):
            return None

        return AssetModel(
            pack_name=pack_name,
            asset_name=asset_name,
            active_type=asset_type,
            database_name=database_name,
        )

    def copy_asset_data(self, src, dst) -> None:
        for key, bc in src.GetUserDataContainer():
            name = bc[c4d.DESC_NAME]
            value = src[key]
            self._set_user_data(dst, name, value)

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

    def move_objects_to_container(self, objects, container) -> None:
        """Unified API: re-parents objects under asset null."""
        for obj in objects:
            obj.Remove()
            obj.InsertUnder(container)

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
