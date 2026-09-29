from typing import Optional

import bpy

from ..jb_types import JbSource
from .jb_scene_temp import JBSceneTemp


class JbScene(JBSceneTemp):
    """High-level operations for the active Blender scene."""

    def __init__(self, source: JbSource):
        super().__init__()
        self._source = source

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
