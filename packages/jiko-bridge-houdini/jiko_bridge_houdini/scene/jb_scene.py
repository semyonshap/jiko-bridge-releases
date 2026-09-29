import hou
from jiko_bridge_houdini.jb_settings import JbSettings
from jiko_bridge_houdini.jb_types import JbContainer, JbSource
from jiko_bridge_houdini.jb_utils import source_path
from jiko_bridge_houdini.scene.jb_scene_file import JbSceneFile
from pxr import Usd


class JbScene(JbSceneFile):
    """Houdini implementation of jb_scene operations."""

    def __init__(self, source: JbSource):
        self.node = source
        self.settings = JbSettings(source)
        self._source = None
        self.messages.clear()

    def finish_asset(self, _container: JbContainer) -> None:
        """Write the layers of one finished asset, and of the assets it pulled in."""
        self._save_layers()

    def _save_layers(self) -> None:
        """Write every asset layer the import sublayered; unchanged layers are skipped."""
        if self._source is None:
            return
        for path in self._source.GetRootLayer().subLayerPaths:
            self._save_layer(path)

    @property
    def source(self) -> Usd.Stage:
        """The in-memory stage every container of the running import is authored into."""
        if self._source is None:
            self._source = Usd.Stage.CreateInMemory()
        return self._source

    def import_with_temp(self, file_path: str, target: JbContainer) -> None:
        """Import one model file in an isolated scene, then author it into the container."""
        with self.temp_source(debug=False) as tmp_stage:
            if not self.import_file(file_path):
                self.logger.warning("No objects imported for file: %s", file_path)
                return
            self._copy_source(tmp_stage, target, source_path(file_path))

    def export_with_temp(self, _src, _ext):
        """Houdini has no asset export yet."""
        self.logger.warning("Houdini asset export is not implemented.")

    def get_project_filepath(self) -> str | None:
        """Path of the current hip file."""
        return hou.hipFile.path()
