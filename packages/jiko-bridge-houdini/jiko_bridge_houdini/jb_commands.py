"""Commands of the Houdini plugin: the shared workflows bound to this node."""

from jiko_bridge_houdini.jb_settings import JbSettings
from jiko_bridge_houdini.jb_types import (
    JbAssetExporterBase,
    JbAssetImporterBase,
    JbAssetSoloBase,
    JbSource,
)
from jiko_bridge_houdini.jb_utils import report
from jiko_bridge_houdini.materials.jb_material_importer import JbMaterialImporter
from jiko_bridge_houdini.scene.jb_scene import JbScene


class JbAssetImporter(JbAssetImporterBase):
    """Handles importing assets from Jiko Bridge into the node."""

    scene_class = JbScene
    materials_class = JbMaterialImporter


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


class JbAssetSolo(JbAssetSoloBase):
    """Placeholder until this feature is implemented for Houdini."""

    scene_class = JbScene
    settings_class = JbSettings

    def solo(self) -> None:
        self.logger.warning("Houdini solo mode is not implemented.")


class JbCommands:
    """Single entry point of the plugin: HDA callbacks and scripted use."""

    def __init__(self, source: JbSource):
        self.source = source
        self.asset_import = JbAssetImporter(source)
        self.asset_export = JbAssetExporter(source)
        self.asset_solo = JbAssetSolo(source)

    def import_assets(self) -> None:
        """Import every asset of this node and expose it in the assembled stage."""
        scene = self.asset_import.scene
        self.asset_import.import_assets()
        if scene.messages:
            report(scene.logger, scene.report())

    def export_asset(self) -> None:
        """Invoke the exporter placeholder."""
        self.asset_export.export_asset()

    def solo(self) -> None:
        """Invoke the solo placeholder."""
        self.asset_solo.solo()
