from pathlib import Path

import hou
from jiko_bridge_houdini.jb_settings import JbSettings
from jiko_bridge_houdini.jb_types import USD_EXTENSIONS, JbContainer, JbSource
from jiko_bridge_houdini.jb_utils import source_path
from jiko_bridge_houdini.scene.jb_scene_file import JbSceneFile


class JbScene(JbSceneFile):
    """Houdini implementation of jb_scene operations."""

    def __init__(self, source: JbSource):
        self.node = source
        self.settings = JbSettings(source)
        self._containers = {}
        self._temp = None
        self._temp_layer = None
        self.messages.clear()

    def finish_asset(self, _container: JbContainer) -> None:
        """Write the layers of one finished asset, and of the assets it pulled in."""
        self._save_layers()

    def _save_layers(self) -> None:
        """Write every container the import opened; unchanged layers are skipped."""
        for container in self._containers.values():
            self._save_container(container)

    @property
    def source(self) -> JbSource:
        """The node the running import is driven from."""
        return self.node

    def import_with_temp(self, file_path: str, target: JbContainer) -> None:
        """Import one model file, then author it into the container as a reference."""
        source = source_path(file_path)
        if Path(source).suffix.lower() in USD_EXTENSIONS:
            path = source
        else:
            with self.temp_source(debug=False) as stage:
                if not self.import_file(file_path):
                    self.logger.warning("No objects imported for file: %s", file_path)
                    return
                path = self._save_geometry(stage, target)
        self._reference_source(target, path)

    def export_with_temp(self, _src, _ext):
        """Houdini has no asset export yet."""
        self.logger.warning("Houdini asset export is not implemented.")

    def get_project_filepath(self) -> str | None:
        """Path of the current hip file."""
        return hou.hipFile.path()
