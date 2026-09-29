"""Commands shared by HDA callbacks and scripted use."""

from jiko_bridge_houdini.commands.jb_asset_exporter import JbAssetExporter
from jiko_bridge_houdini.commands.jb_asset_importer import JbAssetImporter
from jiko_bridge_houdini.commands.jb_asset_solo import JbAssetSolo
from jiko_bridge_houdini.jb_types import JbSource
from jiko_bridge_houdini.jb_utils import report


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
