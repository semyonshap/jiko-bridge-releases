import re
from typing import Generator, Optional

import bpy

from ..jb_types import JbContainer, JbData, JbMaterial, JbObject, JbSceneBase


class JbSceneObjects(JbSceneBase):
    """Object operations for Scene."""

    @property
    def _outliner(self) -> Optional[tuple[bpy.types.Area, bpy.types.Region]]:
        ctx = self.source
        if not ctx.screen:
            return None
        for area in ctx.screen.areas:
            if area.type == "OUTLINER":
                for region in area.regions:
                    if region.type == "WINDOW":
                        return area, region
        return None

    def walk(self, root) -> list[JbData]:
        if not root:
            return []

        return list(self._walk(root))

    def _walk(self, root: list[JbData]) -> Generator[JbData, None, None]:
        seen: set[JbData] = set()

        def walk_object(obj: bpy.types.Object):
            if obj in seen:
                return
            seen.add(obj)
            yield obj
            for child in obj.children:
                yield from walk_object(child)

        def walk_collection(collection: bpy.types.Collection):
            if collection in seen:
                return
            seen.add(collection)
            yield collection
            for obj in collection.objects:
                yield from walk_object(obj)
            for child_col in collection.children:
                yield from walk_collection(child_col)

        for item in root:
            if isinstance(item, bpy.types.Object):
                yield from walk_object(item)
            elif isinstance(item, bpy.types.Collection):
                yield from walk_collection(item)
            elif isinstance(item, bpy.types.Material):
                if item not in seen:
                    seen.add(item)
                    yield item

    def get_selection(self) -> list[JbData]:
        ctx = self.source
        data: list[JbData] = []

        outliner = self._outliner
        if outliner:
            area, region = outliner
            with ctx.temp_override(area=area, region=region):
                selected = ctx.selected_ids
                if selected:
                    for item in selected:
                        if isinstance(
                            item, (bpy.types.Object, bpy.types.Collection, bpy.types.Material)
                        ):
                            data.append(item)

        if not data:
            if not (view_layer := ctx.view_layer):
                return []
            if view_layer.objects:
                data = list(view_layer.objects.selected)
            if (
                not data
                and (active_layer := view_layer.active_layer_collection)
                and (collection := active_layer.collection)
            ):
                data = [collection]

        return data

    def get_materials_from_objects(self, objects) -> list[JbMaterial]:
        materials: set[JbMaterial] = set()
        for obj in objects:
            if isinstance(obj, bpy.types.Material):
                materials.add(obj)
                continue
            if not isinstance(obj, bpy.types.Object):
                continue
            if (data := obj.data) is None:
                continue
            materials.update(mat for mat in getattr(data, "materials", ()) if mat is not None)
        return list(materials)

    def copy_object_transform(self, obj, target_obj) -> None:
        obj.matrix_world = target_obj.matrix_world.copy()

    def remove_object(self, obj) -> None:
        bpy.data.objects.remove(obj, do_unlink=True)

    def get_children(self, obj) -> list[JbObject | JbContainer]:
        if isinstance(obj, bpy.types.Object):
            return list(obj.children)
        if isinstance(obj, bpy.types.Collection):
            return list(obj.objects) + list(obj.children)
        return []

    def get_depth(self, obj) -> int:
        depth = 0
        if isinstance(obj, (bpy.types.Object)):
            current = obj.parent
        else:
            return depth

        while current:
            depth += 1
            current = current.parent
        return depth

    def merge_duplicates_materials(self, material) -> None:
        pattern = re.compile(r"^" + re.escape(material.name) + r"\.\d+$")
        duplicates = [m for m in bpy.data.materials if pattern.match(m.name)]
        for dup in duplicates:
            dup.user_remap(material)
            bpy.data.materials.remove(dup)

    def _find_layer_collection(self, layer_col, collection) -> bpy.types.LayerCollection | None:
        if layer_col.collection == collection:
            return layer_col
        for child in layer_col.children:
            result = self._find_layer_collection(child, collection)
            if result:
                return result
        return None

    def _set_collection_visibility(self, collection, visible: bool) -> None:
        view_layer = self.source.view_layer
        if not view_layer:
            return
        layer_col = self._find_layer_collection(view_layer.layer_collection, collection)
        if layer_col:
            layer_col.hide_viewport = not visible
