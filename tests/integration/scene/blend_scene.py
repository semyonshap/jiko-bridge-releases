import os
import importlib
from typing import Optional


import bpy
from tests.integration.scene.base_scene import BaseScene


class Scene(BaseScene):
    """Helper class for managing Blender scene state in integration tests."""

    ADDON_NAME = "jiko_bridge_blend"

    def __init__(self):
        self._source = bpy.context

    @property
    def source(self) -> bpy.types.Context:
        return self._source

    def import_plugin(self):
        """Return the enabled add-on bundle."""
        return importlib.import_module(self.ADDON_NAME)

    def call_command(self, operator: str):
        jiko_ops = getattr(bpy.ops, "jiko_bridge", None)
        if jiko_ops is None:
            raise RuntimeError("jiko_bridge operator should be registered in bpy.ops")
        result = getattr(jiko_ops, operator)()
        if result != {"FINISHED"}:
            raise RuntimeError(f"Operator {operator} should finish successfully.")

    @property
    def _view_layer(self) -> bpy.types.ViewLayer:
        view_layer = self.source.view_layer
        if view_layer is None:
            raise RuntimeError("No active view layer found in the current Blender context.")
        return view_layer

    def _find_layer_collection(self, layer_collection, name):
        if layer_collection.collection.name == name:
            return layer_collection
        for child in layer_collection.children:
            found = self._find_layer_collection(child, name)
            if found:
                return found
        return None

    def update(self):
        view_layer = bpy.context.view_layer
        if view_layer:
            view_layer.update()

    def create_scene_object(
        self, name: str, parent: Optional[bpy.types.Object] = None
    ) -> bpy.types.Object:
        bpy.ops.object.select_all(action="DESELECT")

        existing_objects = set(bpy.data.objects)
        bpy.ops.mesh.primitive_cube_add(size=2.0, enter_editmode=False, align="WORLD")

        obj = next((o for o in bpy.data.objects if o not in existing_objects), None)
        if obj is None:
            obj = bpy.context.object
        if obj is None:
            raise RuntimeError("Failed to create cube primitive")

        obj.name = name

        if parent is not None:
            if parent.users_collection:
                for col in parent.users_collection:
                    if obj.name not in col.objects:
                        col.objects.link(obj)

            obj.parent = parent
            obj.parent_type = "OBJECT"
            obj.matrix_parent_inverse = parent.matrix_world.inverted()

        obj.select_set(True)
        self.update()

        return obj

    def create_scene_material(self, name: str) -> bpy.types.Material:
        material = bpy.data.materials.new(name=name)
        return material

    def get_all_materials(self) -> list[bpy.types.Material]:
        return list(bpy.data.materials)

    def find_material_by_name(self, name) -> Optional[bpy.types.Material]:
        return bpy.data.materials.get(name)

    def find_container_by_name(self, name) -> Optional[bpy.types.Collection]:
        return bpy.data.collections.get(name)

    def clear_selection(self):
        bpy.ops.object.select_all(action="DESELECT")

        self._view_layer.objects.active = None
        self._view_layer.active_layer_collection = self._view_layer.layer_collection

        self.update()

    def ensure_loaded(self) -> None:
        addon_name = self.ADDON_NAME
        try:
            importlib.import_module(addon_name)
        except ImportError as exc:
            raise RuntimeError("Addon is not found in the system.") from exc

    def reset_scene(self) -> None:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.preferences.addon_enable(module=self.ADDON_NAME)

    def save_document(self, filename: str) -> str:
        logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
        os.makedirs(logs_dir, exist_ok=True)
        path = os.path.join(logs_dir, f"{filename}.blend")
        bpy.ops.wm.save_mainfile(filepath=path)
        return path

    def select_objects(self, objects: list[bpy.types.Object | bpy.types.Collection]):
        self.clear_selection()

        for obj in objects:
            if isinstance(obj, bpy.types.Object):
                obj.select_set(True)
            if isinstance(obj, bpy.types.Collection):
                layer_collection = self._find_layer_collection(
                    self._view_layer.layer_collection,
                    obj.name,
                )

                self._view_layer.active_layer_collection = layer_collection

        self.update()

    def apply_material_to_object(self, obj: bpy.types.Object, material: bpy.types.Material) -> bool:
        if isinstance(obj.data, bpy.types.Mesh):
            obj.data.materials.append(material)
            return True
        return False

    def get_hierarchy(self, container: bpy.types.Collection):
        hierarchy = {}
        for obj in container.objects:
            norm_name = obj.name.split(".", 1)[0]
            norm_parent = obj.parent.name.split(".", 1)[0] if obj.parent else None
            hierarchy[norm_name] = norm_parent

        return hierarchy

    def get_instance_objects(self) -> list[bpy.types.Object]:
        if not (scene := bpy.context.scene) or not (collection := scene.collection):
            return []

        objects = collection.objects

        return [
            obj
            for obj in objects
            if obj.instance_type == "COLLECTION" and obj.instance_collection is not None
        ]

    def get_children_container(self, container: bpy.types.Collection) -> list[bpy.types.Object]:
        return list(container.objects)

    def set_export_format(self, fmt: str) -> None:
        s = self.source.scene
        if s is None:
            raise RuntimeError("No active scene.")
        jb_settings = getattr(s, "jb_settings", None)
        if jb_settings is None:
            raise RuntimeError("jb_settings are not registered on the scene.")
        jb_settings.export_format = fmt
