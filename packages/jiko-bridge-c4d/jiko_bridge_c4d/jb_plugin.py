import c4d
from jiko_bridge_c4d.jb_commands import JbAssetExporter, JbAssetImporter, JbAssetSolo
from jiko_bridge_c4d.jb_settings import JbSettingsDialog
from jiko_bridge_c4d.jb_types import JbSource

JIKO_BRIDGE_ID = 1096086
JIKO_BRIDGE_NAME = "Jiko Bridge"
JIKO_BRIDGE_HELP = "Jiko Bridge help to improve your workflow"

IDC_POPUP_ACTION_IMPORT = 2001
IDC_POPUP_ACTION_EXPORT = 2002
IDC_POPUP_ACTION_SOLO = 2003
IDC_POPUP_ACTION_SETTINGS = 2005


class JbCommandsPopup:
    """Popup menu of the plugin, with one entry per command."""

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
        """Open the settings dialog."""
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


class JikoBridge(c4d.plugins.CommandData):
    """Main command plugin class for Jiko Bridge."""

    def GetScriptName(self):  # pylint: disable=invalid-name
        """Return a stable script name."""
        return JIKO_BRIDGE_NAME

    def Execute(self, doc):  # pylint: disable=invalid-name
        """Show the Jiko Bridge commands popup menu."""
        JbCommandsPopup(doc).show_popup_menu()
        return True


def registerJikoBridge() -> None:  # pylint: disable=invalid-name
    """Register the stable command plugin once in Cinema 4D.

    Called once by the ``jiko_bridge_c4d.pyp`` entry point on plugin load.
    """
    if c4d.plugins.FindPlugin(JIKO_BRIDGE_ID, c4d.PLUGINTYPE_COMMAND):
        return

    try:
        c4d.plugins.RegisterCommandPlugin(
            id=JIKO_BRIDGE_ID,
            str=JIKO_BRIDGE_NAME,
            info=0,
            help=JIKO_BRIDGE_HELP,
            dat=JikoBridge(),
            icon=None,
        )
    except (TypeError, RuntimeError, ValueError) as e:
        print(f"Failed to register Jiko Bridge plugin: {e}")
