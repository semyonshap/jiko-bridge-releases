import bpy

from .jb_asset_exporter import JbAssetExporter
from .jb_asset_importer import JbAssetImporter
from .jb_commands import JB_MT_PIE_AssetActions, JB_PT_Commands
from .jb_settings import register_settings, unregister_settings
from .jb_utils import register_keymap, unregister_keymap
from .scene.jb_scene import JbScene


class JB_OT_AssetImport(bpy.types.Operator):  # pylint: disable=invalid-name
    """Import asset from Jiko Bridge."""

    bl_idname = "jiko_bridge.import_asset"
    bl_label = "Import Asset"
    bl_description = "Import active asset from Jiko Bridge"
    bl_options = {"REGISTER", "UNDO"}

    def invoke(self, context, event):
        importer = JbAssetImporter(context)
        msg = importer.import_message()
        return context.window_manager.invoke_confirm(self, event, message=msg)

    def execute(self, context):
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
        exporter = JbAssetExporter(context)
        msg = exporter.export_message()
        return context.window_manager.invoke_confirm(self, event, message=msg)

    def execute(self, context):
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
        JbScene(context).solo()
        return {"FINISHED"}


classes = [
    JB_PT_Commands,
    JB_OT_Solo,
    JB_OT_AssetExport,
    JB_OT_AssetImport,
    JB_MT_PIE_AssetActions,
]


def register():
    """Register addon classes."""
    for cls in classes:
        bpy.utils.register_class(cls)

    register_keymap()
    register_settings()


def unregister():
    """Unregister addon classes."""
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    unregister_keymap()
    unregister_settings()
