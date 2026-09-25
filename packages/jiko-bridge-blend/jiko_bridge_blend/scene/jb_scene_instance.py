from __future__ import annotations

from typing import List

import bmesh
import bpy

from ..jb_types import JbObject
from .jb_scene_container import JbSceneContainer


class JbSceneInstance(JbSceneContainer):
    """Instance and placeholder management for Blender."""

    def create_instance(self, container, name) -> JbObject:
        empty = bpy.data.objects.new(f"Instance_{name}", None)
        empty.instance_type = "COLLECTION"
        empty.instance_collection = container
        empty["jb_pack_name"] = container.get("jb_pack_name", "")
        empty["jb_asset_name"] = container.get("jb_asset_name", "")
        empty["jb_asset_type"] = container.get("jb_asset_type", "")
        empty["jb_vault_name"] = container.get("jb_vault_name", "")
        scene = self.source.scene
        if scene is not None and scene.collection is not None:
            scene.collection.objects.link(empty)
        return empty

    def create_placeholder(self, asset_model, transform, source) -> JbObject:
        pack_name = asset_model.pack_name
        asset_name = asset_model.asset_name
        name = f"{pack_name}__{asset_name}"

        mesh = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(name, mesh)

        obj["jb_placeholder_pack"] = pack_name
        obj["jb_placeholder_asset"] = asset_name
        obj.matrix_world = transform
        col = source.collection

        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mesh.materials.append(mat)

        if col is not None:
            col.objects.link(obj)

        return obj

    def get_names_from_placeholder(self, obj) -> List[str]:
        names = set()

        if (
            not isinstance(obj, bpy.types.Object)
            or obj.data is None
            or not isinstance(obj.data, bpy.types.Mesh)
            or not hasattr(obj.data, "materials")
            or len(obj.data.vertices) != 4
        ):
            return []

        mat_name = next((m.name for m in obj.data.materials if m), None)
        if mat_name:
            names.add(mat_name)

        return list(names)

    def replace_instances_with_placeholders(self, objects, source) -> list[JbObject]:
        result = []
        for obj in objects:
            if obj.instance_type == "COLLECTION" and obj.instance_collection:
                asset_model = self.get_asset_data_from_container(obj.instance_collection)
                if asset_model:
                    placeholder = self.create_placeholder(
                        asset_model, obj.matrix_world.copy(), source
                    )
                    self.remove_object(obj)
                    result.append(placeholder)
                    continue
            result.append(obj)
        return result
