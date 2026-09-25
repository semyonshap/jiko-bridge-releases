"""
Scene management for Jiko Bridge Blender plugin
Code by Semyon Shapoval, 2026
"""

from logging import Logger
from typing import Optional

import bpy

from ..jb_settings import JbSettings
from ..jb_types import JbSource
from ..jb_utils import get_logger
from .jb_scene_temp import JBSceneTemp


class JbScene(JBSceneTemp):
    """High-level operations for the active Blender scene."""

    def __init__(self, source):
        super().__init__()
        self._logger = get_logger(__name__)
        self._source = source

    @property
    def logger(self) -> Logger:
        return self._logger

    @property
    def source(self) -> JbSource:
        if self._source is not None:
            return self._source
        return bpy.context

    def import_with_temp(self, file_path, target) -> None:
        with self.temp_source(debug=False) as temp:
            with self._view3d_context(temp):
                if not self.import_file(file_path):
                    self.logger.warning("No objects imported for file: %s", file_path)
                    return

            self._copy_source([temp.collection], target)

    def export_with_temp(self, src, ext) -> Optional[str]:
        with self.temp_source(src, debug=False) as temp:
            col = temp.collection
            if not col or not col.objects:
                self.logger.warning("No objects to export.")
                return None
            copies = list(col.objects)
            self.replace_instances_with_placeholders(copies, temp)

            with self._view3d_context(temp):
                return self.export_file(ext)

    def get_project_filepath(self) -> Optional[str]:
        """Get the current Blender project file path."""
        filepath = bpy.data.filepath
        if not filepath:
            self.logger.warning("Current Blender project is not saved.")
            return None
        return filepath

    def solo(self):
        objects = self.get_selection()
        instances = self.get_containers_from_instances(objects)
        containers = self.get_containers_from_objects(objects)
        combine = instances + containers

        settings = JbSettings(self.source)

        if not combine:
            combine = settings.pop_solo_selection()
        else:
            settings.save_solo_selection(combine)

        if not combine:
            return

        root = self.get_or_create_container("Assets")

        # Скрыть root
        self._set_collection_visibility(root, True)

        # Все children -> скрытые
        for child in root.children:
            self._set_collection_visibility(child, False)

        # combine -> видимые
        for col in combine:
            self._set_collection_visibility(col, True)

        bpy.ops.view3d.view_all()
