"""Commands of the Cinema 4D plugin: the shared workflows bound to this document."""

from jiko_bridge_c4d.jb_settings import JbSettings
from jiko_bridge_c4d.jb_types import (
    JbAssetExporterBase,
    JbAssetImporterBase,
    JbAssetSoloBase,
    JbSource,
)
from jiko_bridge_c4d.materials.jb_material_importer import JbMaterialImporter
from jiko_bridge_c4d.scene.jb_scene import JbScene


class JbAssetImporter(JbAssetImporterBase):
    """Handles importing assets from Jiko Bridge into scene."""

    scene_class = JbScene
    materials_class = JbMaterialImporter


class JbAssetExporter(JbAssetExporterBase):
    """Export asset class"""

    scene_class = JbScene
    settings_class = JbSettings


class JbAssetSolo(JbAssetSoloBase):
    """Isolate the selected asset containers."""

    scene: JbScene
    scene_class = JbScene
    settings_class = JbSettings
    history_size = 10


class JbCommands:
    """Main command for headless execution."""

    def __init__(self, source: JbSource):
        self.asset_import = JbAssetImporter(source)
        self.asset_export = JbAssetExporter(source)

    def export_asset(self) -> None:
        """Export asset to Jiko Bridge."""
        return self.asset_export.export_asset()

    def import_asset(self) -> None:
        """Import asset from Jiko Bridge."""
        return self.asset_import.import_assets()
