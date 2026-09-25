"""
Helper class for managing Cinema 4D scenes during integration tests.
Code by Semyon Shapoval, 2026
"""

import os
import importlib
from typing import Optional

import c4d
from tests.integration.scene.base_scene import BaseScene


class Scene(BaseScene):
    """Utility class for Cinema 4D scenes in tests."""

    JIKO_BRIDGE_ID = 1096086

    def __init__(self):
        self._source = c4d.documents.GetActiveDocument()

    @property
    def source(self) -> c4d.documents.BaseDocument:
        return self._source

    def import_module(self, module_name: str):
        """Resolve a logical module name inside the plugin package."""
        return importlib.import_module(f"jiko_bridge_c4d.{module_name}")

    def call_command(self, operator: str):
        try:
            ops = self.import_module("jb_commands")
        except ImportError as e:
            raise RuntimeError("jiko_bridge operator should be registered") from e
        commands = getattr(ops, "JbCommands")(self.source)
        if not hasattr(commands, operator):
            raise RuntimeError(f"Operator {operator} should be defined in JbCommands")
        result = getattr(commands, operator)()
        return result

    def ensure_loaded(self) -> None:
        plugin = c4d.plugins.FindPlugin(self.JIKO_BRIDGE_ID, c4d.PLUGINTYPE_COMMAND)
        if plugin is None:
            raise RuntimeError("Jiko Bridge plugin is not loaded in Cinema 4D.")

    def update(self) -> None:
        c4d.EventAdd()

    def create_scene_object(
        self, name: str, parent: c4d.BaseObject | None = None
    ) -> c4d.BaseObject:
        obj = c4d.BaseObject(c4d.Ocube)
        obj.SetName(name)
        if parent is not None:
            obj.InsertUnder(parent)
        else:
            self._source.InsertObject(obj)
        obj.SetBit(c4d.BIT_ACTIVE)
        c4d.EventAdd()
        return obj

    def create_scene_material(self, name: str) -> c4d.BaseMaterial:
        material = c4d.BaseMaterial(c4d.Mmaterial)
        material.SetName(name)
        self.source.InsertMaterial(material)
        c4d.EventAdd()
        return material

    def get_all_materials(self) -> list[c4d.BaseMaterial]:
        materials = []
        mat = self.source.GetFirstMaterial()
        while mat:
            materials.append(mat)
            mat = mat.GetNext()
        return materials

    def find_container_by_name(self, name: str) -> Optional[c4d.BaseObject]:
        return self._source.SearchObject(name)

    def select_objects(self, objects: list[c4d.BaseObject]) -> None:
        self.clear_selection()

        if not objects:
            return

        for obj in objects:
            obj.SetBit(c4d.BIT_ACTIVE)

        c4d.EventAdd()

    def clear_selection(self) -> None:
        active = self._source.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
        for obj in active:
            obj.DelBit(c4d.BIT_ACTIVE)
        self._source.SetActiveObject(None, c4d.SELECTION_NEW)
        c4d.EventAdd()

    def get_hierarchy(self, container: c4d.BaseObject) -> dict[str, str | None]:
        result: dict[str, str | None] = {}

        def normalize_name(name: str) -> str:
            return name.split(".", 1)[0]

        for obj in container.GetChildren():
            parent = obj.GetUp()
            norm_name = normalize_name(obj.GetName())
            norm_parent = normalize_name(parent.GetName()) if parent else None
            result[norm_name] = norm_parent
        return result

    def get_instance_objects(self) -> list[c4d.BaseObject]:
        result: list[c4d.BaseObject] = []

        obj = self._source.GetFirstObject()

        while obj:
            if obj.CheckType(c4d.Oinstance):
                result.append(obj)
            obj = obj.GetNext()
        return result

    def save_document(self, filename: str) -> Optional[str]:
        logs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "logs"))
        os.makedirs(logs_dir, exist_ok=True)

        if not filename.lower().endswith(".c4d"):
            filename = f"{filename}.c4d"

        path = os.path.normpath(os.path.join(logs_dir, filename))

        result = c4d.documents.SaveDocument(
            self.source,
            path,
            c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST,
            c4d.FORMAT_C4DEXPORT,
        )

        if not result:
            return None

        return path

    # pylint: disable=duplicate-code
    def find_material_by_name(self, name: str) -> Optional[c4d.BaseMaterial]:
        mat = self.source.GetFirstMaterial()
        while mat:
            if mat.GetName() == name:
                return mat
            mat = mat.GetNext()
        return None

    def apply_material_to_object(self, obj: c4d.BaseObject, material: c4d.BaseMaterial) -> bool:
        tag = c4d.BaseTag(c4d.Ttexture)
        tag[c4d.TEXTURETAG_MATERIAL] = material
        obj.InsertTag(tag)
        c4d.EventAdd()
        return True

    def get_children_container(self, container: c4d.BaseObject) -> list[c4d.BaseObject]:
        if not container:
            return []
        result = []
        for child in container.GetChildren():
            result.append(child)
            result.extend(self.get_children_container(child))
        return result

    def reset_scene(self) -> None:
        current = c4d.documents.GetActiveDocument()
        if current is not None:
            c4d.documents.KillDocument(current)
        new_doc = c4d.documents.BaseDocument()
        c4d.documents.InsertBaseDocument(new_doc)
        c4d.documents.SetActiveDocument(new_doc)
        self._source = new_doc
        c4d.EventAdd()

    def set_export_format(self, fmt: str) -> None:
        jb_settings = self.import_module("jb_settings")
        combo_options_export_format = jb_settings.COMBO_OPTIONS_EXPORT_FORMAT
        jb_settings_mod = jb_settings.JbSettings

        if fmt not in combo_options_export_format:
            raise ValueError(f"Unknown format '{fmt}'. Valid: {combo_options_export_format}")
        index = combo_options_export_format.index(fmt)
        jb_settings_mod(self.source).set_export_format(index)
