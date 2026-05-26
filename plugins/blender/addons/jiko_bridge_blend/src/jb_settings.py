"""
Settings for plugin management
Code by Semyon Shapoval, 2026
"""

import bpy
from .jb_protocols import JbSettingsABC

ADDON_ID = __package__.split('.', maxsplit=1)[0]
_SOLO_STACK_SIZE = 5


class JB_PG_SoloEntry(bpy.types.PropertyGroup):  # pylint: disable=invalid-name
    """One entry in the solo history stack (stored per scene)."""

    collections: bpy.props.StringProperty(default="")  # type: ignore[valid-type]

    def set_collections(self, collections: list) -> None:
        """Serialize collection names to string."""
        self.collections = ",".join(c.name for c in collections if c)

    def get_collections(self) -> list:
        """Deserialize collection names back to collections."""
        if not self.collections:
            return []
        return [
            col
            for name in self.collections.split(",")
            if (col := bpy.data.collections.get(name)) is not None
        ]


class JB_PG_SceneSettings(bpy.types.PropertyGroup):  # pylint: disable=invalid-name
    """Per-scene settings stored on bpy.types.Scene."""

    solo_stack: bpy.props.CollectionProperty(type=JB_PG_SoloEntry)  # type: ignore[valid-type]

    export_format: bpy.props.EnumProperty(  # type: ignore[valid-type]
        name="Export Format",
        items=[
            ("fbx", "FBX", "Export as FBX"),
            ("abc", "Alembic", "Export as Alembic"),
        ],
        default="fbx",
    )


class JbSettings(JbSettingsABC):
    """Wrapper for accessing Jiko Bridge addon preferences."""

    def __init__(self, context: bpy.types.Context):
        self._context = context

    @property
    def scene_settings(self) -> JB_PG_SceneSettings | None:
        """Scene settings"""
        scene = self._context.scene
        if scene is None:
            return None
        return getattr(scene, "jb_settings", None)

    def get_export_format(self) -> str:
        s = self.scene_settings
        if s is None:
            return "fbx"
        return s.export_format

    def load_solo_stack(self) -> list[list]:
        """Load Solo Stack"""
        s = self.scene_settings
        if s is None:
            return []
        return [entry.get_collections() for entry in s.solo_stack if entry.get_collections()]

    def save_solo_selection(self, containers) -> None:
        s = self.scene_settings
        if s is None:
            return

        entries = [entry.get_collections() for entry in s.solo_stack]

        if entries and set(entries[0]) == set(containers):
            return

        entries.insert(0, containers)
        entries = entries[:_SOLO_STACK_SIZE]
        s.solo_stack.clear()
        for entry_collections in entries:
            entry = s.solo_stack.add()
            entry.set_collections(entry_collections)

    def pop_solo_selection(self) -> list:
        s = self.scene_settings
        if s is None or len(s.solo_stack) < 2:
            return []
        entries = [entry.get_collections() for entry in s.solo_stack]
        previous = entries[1]
        s.solo_stack.clear()
        for entry_collections in entries[1:]:
            entry = s.solo_stack.add()
            entry.set_collections(entry_collections)
        return previous


classes = (
    JB_PG_SoloEntry,
    JB_PG_SceneSettings,
)


def register_settings() -> None:
    """Register Settings"""
    for cls in classes:
        bpy.utils.register_class(cls)
    setattr(bpy.types.Scene, "jb_settings", bpy.props.PointerProperty(type=JB_PG_SceneSettings))


def unregister_settings() -> None:
    """Unregister settings"""
    if hasattr(bpy.types.Scene, "jb_settings"):
        delattr(bpy.types.Scene, "jb_settings")
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)  # type: ignore[arg-type]
