"""Deferred Houdini features implementing the shared contract."""

from jiko_bridge_houdini.jb_settings import JbSettings
from jiko_bridge_houdini.jb_types import JbAssetExporterBase
from jiko_bridge_houdini.scene.jb_scene import JbScene


class JbAssetExporter(JbAssetExporterBase):
    """Placeholder until this feature is implemented for Houdini."""

    scene_class = JbScene
    settings_class = JbSettings

    def export_asset(self):
        """Reserved by the common DCC interface."""
        self.logger.warning("Houdini JbAssetExporter.export_asset is not implemented.")

    def export_message(self):
        """Reserved by the common DCC interface."""
        self.logger.warning("Houdini JbAssetExporter.export_message is not implemented.")

    def _collect_data(self):
        """Reserved by the common DCC interface."""
        self.logger.warning("Houdini JbAssetExporter._collect_data is not implemented.")

    def _update_asset(self, container):
        """Reserved by the common DCC interface."""
        self.logger.warning("Houdini JbAssetExporter._update_asset is not implemented.")

    def _create_new_asset(self, objects):
        """Reserved by the common DCC interface."""
        self.logger.warning("Houdini JbAssetExporter._create_new_asset is not implemented.")
