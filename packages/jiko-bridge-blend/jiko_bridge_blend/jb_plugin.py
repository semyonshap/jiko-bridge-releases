import bpy

from .jb_commands import JbAssetExporter, JbAssetImporter, JbAssetSolo
from .jb_settings import JbSettings, register_settings, unregister_settings
from .jb_utils import register_keymap, unregister_keymap


class JB_PT_Commands(bpy.types.Panel):  # pylint: disable=invalid-name
    """Main panel for Jiko Bridge commands."""

    bl_label = "Jiko Bridge"
    bl_idname = "JB_PT_MAIN"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Jiko Bridge"

    def draw(self, context: bpy.types.Context):
        """Draw the main panel."""
        layout = self.layout

        if not layout:
            return

        col = layout.column(align=True)
        col.operator("jiko_bridge.import_asset", text="Import Asset", icon="IMPORT")
        col.operator("jiko_bridge.export_asset", text="Export Asset", icon="EXPORT")
        col.operator("jiko_bridge.solo", text="Solo Asset", icon="ZOOM_SELECTED")

        col.separator()

        settings = JbSettings(context).scene_settings
        if settings is not None:
            box = col.box()
            box.label(text="Settings", icon="PREFERENCES")
            box.prop(settings, "export_format", text="Export Format")


class JB_MT_PIE_AssetActions(bpy.types.Menu):  # pylint: disable=invalid-name
    """Circular pie menu for asset import/export."""

    bl_idname = "JB_MT_PIE_MAIN"
    bl_label = "Jiko Bridge"

    def draw(self, _context: bpy.types.Context):
        """Draw the pie menu."""
        layout = self.layout
        if not layout:
            return

        pie = layout.menu_pie()
        pie.operator("jiko_bridge.import_asset", text="Import Asset", icon="IMPORT")
        pie.operator("jiko_bridge.export_asset", text="Export Asset", icon="EXPORT")
        pie.operator("jiko_bridge.solo", text="Solo Asset", icon="ZOOM_SELECTED")


class JB_OT_AssetImport(bpy.types.Operator):  # pylint: disable=invalid-name
    """Import asset from Jiko Bridge."""

    bl_idname = "jiko_bridge.import_asset"
    bl_label = "Import Asset"
    bl_description = "Import active asset from Jiko Bridge"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        """Show a confirmation dialog before importing."""
        importer = JbAssetImporter(context)
        msg = importer.import_message()
        return context.window_manager.invoke_confirm(self, event, message=msg)

    def execute(self, context):
        """Import the active asset."""
        importer = JbAssetImporter(context)
        importer.import_assets()
        return {"FINISHED"}


class JB_OT_AssetExport(bpy.types.Operator):  # pylint: disable=invalid-name
    """Export asset to Jiko Bridge."""

    bl_idname = "jiko_bridge.export_asset"
    bl_label = "Export Asset"
    bl_description = "Export selected objects as a new asset or update existing"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        """Show a confirmation dialog before exporting."""
        exporter = JbAssetExporter(context)
        msg = exporter.export_message()
        return context.window_manager.invoke_confirm(self, event, message=msg)

    def execute(self, context):
        """Export the selected objects."""
        exporter = JbAssetExporter(context)
        exporter.export_asset()
        return {"FINISHED"}


class JB_OT_Solo(bpy.types.Operator):  # pylint: disable=invalid-name
    """Solo selected asset."""

    bl_idname = "jiko_bridge.solo"
    bl_label = "Solo Asset"
    bl_description = "Isolate selected asset collections"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        """Solo the selected asset."""
        JbAssetSolo(context).solo()
        return {"FINISHED"}


operator_classes = [
    JB_PT_Commands,
    JB_OT_Solo,
    JB_OT_AssetExport,
    JB_OT_AssetImport,
    JB_MT_PIE_AssetActions,
]


def register():
    """Register addon classes."""
    for cls in operator_classes:
        bpy.utils.register_class(cls)

    register_keymap()
    register_settings()


def unregister():
    """Unregister addon classes."""
    for cls in reversed(operator_classes):
        bpy.utils.unregister_class(cls)

    unregister_keymap()
    unregister_settings()
