import json

import hou
from jiko_bridge_houdini.jb_types import JbContainer, JbData, JbObject, JbSceneBase
from jiko_bridge_houdini.jb_utils import (
    add_string_attribs,
    cached_asset,
    node_geometry,
    pack_geometry,
    set_global_attrib,
    unpack_piece,
)
from jiko_bridge_houdini.scene.jb_scene_graph import JbSceneGraph


def clean_geometry(geometry: hou.Geometry, remove_objects: list[str]) -> hou.Geometry:
    """Rebuild only affected packed branches, preserving their placement."""
    removed = set(remove_objects)
    parents: set[str] = set()
    for location in removed:
        parts = location.strip("/").split("/")
        parents.update(("/" + "/".join(parts[:index]) for index in range(1, len(parts))))

    def clean(source: hou.Geometry, prefix: str) -> hou.Geometry:
        result = hou.Geometry()
        result.merge(source)
        discard = []
        replacements = []
        for primitive in source.prims():
            location = f"{prefix}/{primitive.number()}"
            if location in removed:
                discard.append(primitive.number())
            elif location in parents:
                if not isinstance(primitive, hou.PackedPrim):
                    raise hou.NodeError(f"Placeholder hierarchy changed at {location}.")
                nested = clean(unpack_piece(source, primitive), location)
                nested.transform(primitive.fullTransform())
                replacements.append(nested)
                discard.append(primitive.number())
        if discard:
            handles = [prim for prim in map(result.prim, discard) if prim is not None]
            result.deletePrims(handles)
        for nested in replacements:
            result.merge(nested)
        return result

    return clean(geometry, "")


def prepare_geometry(sop: hou.SopNode) -> None:
    """Build one packed geometry per discovered asset model."""
    input_node = sop.inputs()[0]
    if input_node is None:
        raise hou.NodeError("Connect the graph SOP to this node.")
    source = node_geometry(input_node)
    graph = json.loads(str(source.attribValue("jiko_graph")))
    owners = {entry["id"]: asset for asset in graph["assets"] for entry in asset["models"]}
    output = node_geometry(sop)
    output.clear()
    add_string_attribs(output, hou.attribType.Prim, ("asset_id", "source", "name"))
    for primitive in source.prims():
        identifier = primitive.stringAttribValue("asset_id")
        record = owners[identifier]
        geometry = unpack_piece(source, primitive, convert_polysoup=False)
        geometry = clean_geometry(geometry, record["remove_objects"])
        packed = pack_geometry(output, geometry)
        for name in ("asset_id", "source", "name"):
            packed.setAttribValue(name, primitive.stringAttribValue(name))
    set_global_attrib(output, "jiko_graph", json.dumps(graph, ensure_ascii=False))


class JbSceneObjects(JbSceneBase):
    graph: JbSceneGraph
    containers: dict[str, JbContainer]
    _import_target: JbContainer | None
    "Houdini implementation of objects operations."

    def get_selection(self) -> list[JbData]:
        asset = cached_asset(self.source)
        if not (asset.pack_name and asset.asset_name):
            return []
        container, _ = self.get_or_create_asset_container(asset)
        return [container]

    def walk(self, root) -> list[JbData]:
        result = []
        for obj in root:
            result.append(obj)
            if isinstance(obj, JbContainer):
                result.extend(self.get_children(obj))
        return result

    def get_children(self, obj) -> list[JbObject | JbContainer]:
        return list(obj.objects) if isinstance(obj, JbContainer) else []

    def get_depth(self, obj) -> int:
        depth = 0
        while isinstance(obj, (JbObject, JbContainer)) and obj.parent is not None:
            depth += 1
            obj = obj.parent
        return depth

    def copy_object_transform(self, obj, target_obj) -> None:
        matrix = target_obj.data.get("transform")
        obj.data["transform"] = list(matrix) if matrix is not None else None
        obj.data["object"] = target_obj.data["object"]
        obj.data["names"] = list(target_obj.data.get("names", []))

    def remove_object(self, obj) -> None:
        if obj.parent is not None:
            parent = obj.parent
            parent.objects.remove(obj)
            if obj.target is not None:
                parent.record["instances"].remove(obj.data)
            obj.parent = None

    def get_materials_from_objects(self, objects):
        self.logger.warning("Houdini material selection is not implemented.")

    def merge_duplicates_materials(self, material):
        self.logger.warning("Houdini material merging is not implemented.")
