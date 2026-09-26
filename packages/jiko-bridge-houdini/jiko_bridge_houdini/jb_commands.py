"""Commands shared by HDA callbacks and scripted use."""

from jiko_bridge_houdini.commands.jb_asset_exporter import JbAssetExporter
from jiko_bridge_houdini.commands.jb_asset_importer import JbAssetImporter
from jiko_bridge_houdini.jb_types import JbSource
from jiko_bridge_houdini.jb_utils import report


class JbCommands:
    """Run commands against the supplied HDA node."""

    def __init__(self, source: JbSource):
        self.asset_import = JbAssetImporter(source)
        self.asset_export = JbAssetExporter(source)
        self.scene = self.asset_import.scene

    def import_asset(self) -> None:
        """Import the container asset, or the active asset for an empty HDA."""
        self.asset_import.import_assets()

    def active_asset(self) -> None:
        """Select the active Bridge asset without cooking its files yet."""
        asset = self.asset_import.api.get_active_asset()
        scene = self.asset_import.scene
        if asset is None:
            report(
                scene.logger,
                "Jiko Bridge returned no active asset",
                "Jiko Bridge did not return an active asset.",
            )
            return
        scene.select_asset(asset)

    def export_asset(self) -> None:
        """Invoke the exporter placeholder."""
        self.asset_export.export_asset()

    def solo(self) -> None:
        """Invoke the solo placeholder."""
        self.scene.solo()
