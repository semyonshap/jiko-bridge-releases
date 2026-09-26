import bpy

from .jb_types import JbSettingsBase


class JB_PG_SoloEntry(bpy.types.PropertyGroup):  # pylint: disable=invalid-name
    """One entry of the stored solo history (stored per scene)."""

    containers: bpy.props.StringProperty(default="")  # type: ignore[valid-type]

    def set_containers(self, containers: list) -> None:
        """Serialize collection names to string."""
        self.containers = ",".join(c.name for c in containers if c)

    def get_containers(self) -> list:
        """Deserialize collection names back to collections."""
        if not self.containers:
            return []
        return [
            col
            for name in self.containers.split(",")
            if (col := bpy.data.collections.get(name)) is not None
        ]


class JB_PG_SceneSettings(bpy.types.PropertyGroup):  # pylint: disable=invalid-name
    """Per-scene settings stored on bpy.types.Scene."""

    solo: bpy.props.CollectionProperty(type=JB_PG_SoloEntry)  # type: ignore[valid-type]

    export_format: bpy.props.EnumProperty(  # type: ignore[valid-type]
        name="Export Format",
        items=[
            ("fbx", "FBX", "Export as FBX"),
            ("abc", "Alembic", "Export as Alembic"),
        ],
        default="fbx",
    )


class JbSettings(JbSettingsBase):
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
        """Return the configured export format, defaulting to FBX."""
        s = self.scene_settings
        if s is None:
            return "fbx"
        return s.export_format

    def load_solo(self) -> list[list]:
        """Return the stored solo selections, newest first."""
        s = self.scene_settings
        if s is None:
            return []
        return [entry.get_containers() for entry in s.solo if entry.get_containers()]

    def save_solo(self, entries: list[list]) -> None:
        """Replace the stored solo selections with the given entries, newest first."""
        s = self.scene_settings
        if s is None:
            return
        s.solo.clear()
        for entry_containers in entries:
            entry = s.solo.add()
            entry.set_containers(entry_containers)


settings_classes = (
    JB_PG_SoloEntry,
    JB_PG_SceneSettings,
)


def register_settings() -> None:
    """Register Settings"""
    for cls in settings_classes:
        bpy.utils.register_class(cls)
    setattr(bpy.types.Scene, "jb_settings", bpy.props.PointerProperty(type=JB_PG_SceneSettings))


def unregister_settings() -> None:
    """Unregister settings"""
    if hasattr(bpy.types.Scene, "jb_settings"):
        delattr(bpy.types.Scene, "jb_settings")
    for cls in reversed(settings_classes):
        bpy.utils.unregister_class(cls)  # type: ignore[arg-type]
