"""
Commands Module
Code by Semyon Shapoval, 2026
"""

import bpy

from .jb_settings import JbSettings


class JB_PT_Commands(bpy.types.Panel):  # pylint: disable=invalid-name
    """Main panel for Jiko Bridge commands."""

    bl_label = "Jiko Bridge"
    bl_idname = "JB_PT_MAIN"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Jiko Bridge"

    def draw(self, context: bpy.types.Context):
        layout = self.layout

        if not layout:
            return

        col = layout.column(align=True)
        col.operator("jiko_bridge.import_asset", text="Import Asset", icon="IMPORT")
        col.operator("jiko_bridge.export_asset", text="Export Asset", icon="EXPORT")
        col.operator("jiko_bridge.solo", text="Solo Asset", icon="ZOOM_SELECTED")

        col.separator()

        col.operator("jiko_bridge.reload", text="Reload Addon", icon="FILE_REFRESH")

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
        layout = self.layout
        if not layout:
            return

        pie = layout.menu_pie()
        pie.operator("jiko_bridge.import_asset", text="Import Asset", icon="IMPORT")
        pie.operator("jiko_bridge.export_asset", text="Export Asset", icon="EXPORT")
        pie.operator("jiko_bridge.solo", text="Solo Asset", icon="ZOOM_SELECTED")
