"""Commands shared by HDA callbacks and scripted use."""

from jiko_bridge_houdini.commands.jb_asset_exporter import JbAssetExporter
from jiko_bridge_houdini.commands.jb_asset_importer import JbAssetImporter
from jiko_bridge_houdini.commands.jb_asset_solo import JbAssetSolo
from jiko_bridge_houdini.jb_types import JbSource
from jiko_bridge_houdini.jb_utils import report


class JbCommands:
    """Run commands against the supplied HDA node."""

    def __init__(self, source: JbSource):
        self.asset_import = JbAssetImporter(source)
        self.asset_export = JbAssetExporter(source)
        self.asset_solo = JbAssetSolo(source)

    def import_asset(self) -> None:
        """Import the active asset and refresh the assembled stage."""
        scene = self.asset_import.scene
        if not scene.has_asset():
            asset = self.asset_import.api.get_active_asset()
            if asset is not None:
                scene.select_asset(asset)
        self.asset_import.import_assets()
        scene.refresh()
        if scene.warnings:
            report(scene.logger, scene.report())

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
        self.asset_solo.solo()
