"""
Temporary scene helpers for Jiko Bridge Blender plugin
Code by Semyon Shapoval, 2026
"""

from contextlib import contextmanager

import bpy

from ..jb_types import JbContainer, JbData
from .jb_scene_file import JbSceneFile


class JBSceneTemp(JbSceneFile):
    """Scene-level operations: temporary scene contexts."""

    @contextmanager
    def temp_source(self, objects=None, unit_scale=1.0, debug=False):
        temp = bpy.data.scenes.new("_jb_temp_scene")

        if not isinstance(temp, bpy.types.Scene):
            raise TypeError("temp must be a Scene")

        settings = temp.unit_settings
        if settings is not None:
            settings.system = "METRIC"
            settings.scale_length = unit_scale

        try:
            with self.source.temp_override(scene=temp):
                col = temp.collection
                if objects is not None and col is not None:
                    self._copy_source(objects, col)
                yield temp
        finally:
            if not debug:
                try:
                    if temp.name in bpy.data.scenes:
                        bpy.data.scenes.remove(temp, do_unlink=True)
                        bpy.data.orphans_purge(do_recursive=True)
                except RuntimeError:
                    pass

    @contextmanager
    def _view3d_context(self, scene):
        """Provides a valid VIEW_3D context override required by certain bpy operators."""
        ctx = self.source
        wm = getattr(ctx, "window_manager", None)

        if not wm or not wm.windows:
            raise RuntimeError("No active window manager or windows found")

        window = wm.windows[0]
        window.scene = scene

        screen = window.screen
        if not screen or not screen.areas:
            raise RuntimeError("Active window has no screens or areas configured")

        area = next((a for a in screen.areas if a.type == "VIEW_3D"), screen.areas[0])
        region = next((r for r in area.regions if r.type == "WINDOW"), None)

        with ctx.temp_override(window=window, area=area, region=region):
            print("after", bpy.context.scene)
            yield

    def _copy_source(
        self,
        src: list[JbData],
        dst: JbContainer,
    ) -> None:
        orig_to_new: dict[bpy.types.Object, bpy.types.Object] = {}

        objects = self.walk(src)

        if not objects:
            self.logger.warning("No objects found in source")
            return

        for obj in sorted(objects, key=self.get_depth):
            if isinstance(obj, bpy.types.Collection):
                continue

            if isinstance(obj, bpy.types.Object):
                new_obj = obj.copy()
                dst.objects.link(new_obj)

                if obj.parent and obj.parent in orig_to_new:
                    new_obj.parent = orig_to_new[obj.parent]
                    new_obj.parent_type = obj.parent_type
                    new_obj.parent_bone = obj.parent_bone
                    new_obj.matrix_parent_inverse = obj.matrix_parent_inverse.copy()
                orig_to_new[obj] = new_obj
