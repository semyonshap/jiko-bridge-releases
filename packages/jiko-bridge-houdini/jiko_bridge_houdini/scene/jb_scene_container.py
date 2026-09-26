from jiko_bridge_client import AssetModel
from jiko_bridge_houdini.jb_types import JbContainer, JbObject
from jiko_bridge_houdini.jb_utils import source_path
from jiko_bridge_houdini.scene.jb_scene_objects import JbSceneObjects


class JbSceneContainer(JbSceneObjects):
    """Houdini implementation of container operations."""

    def get_container(self, asset: AssetModel) -> JbContainer | None:
        for container in self.containers.values():
            stored = AssetModel.from_dict(container.record["asset"])
            if (stored.vault_name, stored.pack_name, stored.asset_name) == (
                asset.vault_name,
                asset.pack_name,
                asset.asset_name,
            ):
                return container
        return None

    def get_or_create_container(self, name: str, parent=None) -> JbContainer:
        for container in self.containers.values():
            if container.record.get("name") == name and container.parent is parent:
                return container
        container, _ = self.get_or_create_asset_container(AssetModel(asset_name=name))
        container.record["name"] = name
        container.parent = parent
        return container

    def get_or_create_asset_container(self, asset, file=None) -> tuple[JbContainer, bool]:
        record = self.graph.register(asset)
        container = self.containers.setdefault(record["id"], JbContainer(record))
        if file is None:
            exists = bool(record["models"])
        else:
            exists = any(
                (entry["source"] == source_path(file.filepath) for entry in record["models"])
            )
        return (container, exists)

    def set_asset_data(self, container, asset, file=None) -> None:
        container.record["asset"] = asset.to_dict()
        if file is not None:
            container.record["asset_type"] = file.asset_type

    def get_asset_data_from_container(self, container) -> AssetModel | None:
        asset = AssetModel.from_dict(container.record["asset"])
        return asset if asset.pack_name and asset.asset_name else None

    def copy_asset_data(self, src, dst) -> None:
        metadata = dict(src.record["asset"])
        if isinstance(dst, JbContainer):
            dst.record["asset"] = metadata
        else:
            dst.data["asset"] = metadata

    def get_containers_from_objects(self, objects) -> list[JbContainer]:
        result = []
        for obj in objects:
            container = obj if isinstance(obj, JbContainer) else getattr(obj, "target", None)
            if container is not None and container not in result:
                result.append(container)
        return result

    def get_containers_from_instances(self, objects) -> list[JbContainer]:
        return self.get_containers_from_objects(
            [obj for obj in objects if isinstance(obj, JbObject) and obj.target is not None]
        )

    def move_objects_to_container(self, objects, container) -> None:
        for obj in objects:
            self.remove_object(obj)
            obj.parent = container
            container.objects.append(obj)
            if obj.target is not None:
                parent_id, target_id = (container.record["id"], obj.target.record["id"])
                obj.data["cycle"] = self.graph.is_cycle(parent_id, target_id)
                if obj.data["cycle"]:
                    self.graph.warnings.append(f"Cyclic dependency: {parent_id} -> {target_id}")
                else:
                    self.graph.edges[parent_id].add(target_id)
                container.record["instances"].append(obj.data)

    def cleanup_container(self, container) -> None:
        container.record["unresolved"] = [
            obj.data for obj in container.objects if obj.target is None
        ]

    def clear_container(self, container) -> None:
        identifiers = {entry["id"] for entry in container.record["models"]}
        geometry = self.graph.geometry
        geometry.deletePrims(
            [prim for prim in geometry.prims() if prim.stringAttribValue("asset_id") in identifiers]
        )
        container.objects.clear()
        for name in ("models", "instances", "unresolved"):
            container.record[name].clear()
        self.graph.edges[container.record["id"]].clear()
