"""Houdini object operations: selection, walking and transforms over containers."""

from typing import TYPE_CHECKING

from jiko_bridge_houdini.jb_types import JbContainer, JbData, JbObject, JbSceneBase
from jiko_bridge_houdini.jb_utils import cached_asset

if TYPE_CHECKING:
    from jiko_bridge_houdini.scene.jb_scene_temp import JbStage


class JbSceneObjects(JbSceneBase):
    """Houdini implementation of objects operations."""

    stage: "JbStage"
    warnings: list[str]
    convert_units: bool
    _import_target: JbContainer | None

    def get_selection(self) -> list[JbData]:
        """The container of the asset this HDA holds."""
        asset = cached_asset(self.source)
        if not (asset.pack_name and asset.asset_name):
            return []
        return [self.stage.find(asset) or self.stage.open(asset)]

    def walk(self, root) -> list[JbData]:
        """The containers and placeholders the given roots hold."""
        result = []
        for obj in root:
            result.append(obj)
            if isinstance(obj, JbContainer):
                result.extend(self.get_children(obj))
        return result

    def get_children(self, obj) -> list[JbObject | JbContainer]:
        """The placeholders parsed into a container."""
        return list(obj.pending) if isinstance(obj, JbContainer) else []

    def get_depth(self, obj) -> int:
        """Depth of an object: containers are roots, their placeholders sit below."""
        return 0 if isinstance(obj, JbContainer) or obj.parent is None else 1

    def copy_object_transform(self, obj, target_obj) -> None:
        """Carry a placeholder's placement and names onto its instance."""
        matrix = target_obj.data.get("transform")
        obj.data["transform"] = list(matrix) if matrix is not None else None
        obj.data["object"] = target_obj.data["object"]
        obj.data["names"] = list(target_obj.data.get("names", []))

    def remove_object(self, obj) -> None:
        """Drop a placeholder, remembering the spot its instance replaces."""
        parent = obj.parent
        if parent is None:
            return
        if obj.data.get("replace"):
            parent.remove_objects.append(str(obj.data["object"]))
        if obj in parent.pending:
            parent.pending.remove(obj)
        obj.parent = None

    def get_materials_from_objects(self, objects):
        """Houdini selects materials by node, not by container contents."""
        self.logger.warning("Houdini material selection is not implemented.")
        return []

    def merge_duplicates_materials(self, material):
        """Houdini imports one material per file, so nothing is merged."""
        self.logger.warning("Houdini material merging is not implemented.")
