import c4d
from jiko_bridge_c4d.commands.jb_asset_exporter import JbAssetExporter
from jiko_bridge_c4d.commands.jb_asset_importer import JbAssetImporter
from jiko_bridge_c4d.commands.jb_asset_solo import JbAssetSolo
from jiko_bridge_c4d.jb_settings import JbSettingsDialog
from jiko_bridge_c4d.jb_types import JbSource

IDC_POPUP_ACTION_IMPORT = 2001
IDC_POPUP_ACTION_EXPORT = 2002
IDC_POPUP_ACTION_SOLO = 2003
IDC_POPUP_ACTION_SETTINGS = 2005


class JbCommandsPopup:
    """icon reference:
    https://developers.maxon.net/docs/py/2024_3_0/modules/c4d.bitmaps/RESOURCEIMAGE.html
    """

    def __init__(self, source: JbSource):
        self.doc = source
        self.asset_import = JbAssetImporter(source)
        self.asset_export = JbAssetExporter(source)
        self.asset_solo = JbAssetSolo(source)
        self._settings_dialog = JbSettingsDialog(source)

    def export_asset(self):
        """Export asset to Jiko Bridge."""
        self.doc.StartUndo()
        try:
            msg = self.asset_export.export_message()
            if c4d.gui.QuestionDialog(msg):
                self.asset_export.export_asset()
        finally:
            self.doc.EndUndo()
            c4d.EventAdd()

    def import_asset(self):
        """Import asset from Jiko Bridge."""
        self.doc.StartUndo()
        try:
            msg = self.asset_import.import_message()
            if c4d.gui.QuestionDialog(msg):
                self.asset_import.import_assets()
        finally:
            self.doc.EndUndo()
            c4d.EventAdd()

    def solo(self):
        """Solo mode with history"""
        self.doc.StartUndo()
        try:
            self.asset_solo.solo()
        finally:
            self.doc.EndUndo()
            c4d.EventAdd()

    def open_settings(self):
        """Открыть диалог настроек."""
        self._settings_dialog.Open(
            dlgtype=c4d.DLG_TYPE_MODAL,
            defaultw=250,
            defaulth=120,
        )

    def show_popup_menu(self):
        """Show the popup menu."""
        bc = c4d.BaseContainer()
        bc.InsData(IDC_POPUP_ACTION_IMPORT, f"Import&i{c4d.ID_MODELING_FLATTEN_TOOL}&")
        bc.InsData(IDC_POPUP_ACTION_EXPORT, f"Export&i{c4d.ID_GLOBALMACHINELIST}&")
        bc.InsData(IDC_POPUP_ACTION_SOLO, f"Solo&i{c4d.RESOURCEIMAGE_EYEACTIVE}&")
        bc.InsData(0, "")
        bc.InsData(IDC_POPUP_ACTION_SETTINGS, f"Settings&i{c4d.RESOURCEIMAGE_PIN}&")

        res = c4d.gui.ShowPopupDialog(cd=None, bc=bc, x=c4d.MOUSEPOS, y=c4d.MOUSEPOS)

        if res == IDC_POPUP_ACTION_IMPORT:
            self.import_asset()
        elif res == IDC_POPUP_ACTION_EXPORT:
            self.export_asset()
        elif res == IDC_POPUP_ACTION_SOLO:
            self.solo()
        elif res == IDC_POPUP_ACTION_SETTINGS:
            self.open_settings()


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
