"""
Bridge Settings
Code by Semyon Shapoval, 2026
"""

import c4d
from src.jb_protocols import JbSettingsABC

IDC_SETTINGS_COMBO = 3001
IDC_SETTINGS_OK = 3002
IDC_SETTINGS_CANCEL = 3003

COMBO_OPTIONS_EXPORT_FORMAT = [
    "fbx",
    "abc",
]


class JbSettings(JbSettingsABC):
    """Manages plugin settings stored inside the C4D document."""

    _SETTINGS_ID = 1096087
    _SOLO_STACK_ID = 1057892
    _SOLO_STACK_SIZE = 10

    _SETTING_EXPORT_FORMAT = 1057234

    def __init__(self, doc: c4d.documents.BaseDocument):
        self._doc = doc

    def _get_container(self) -> c4d.BaseContainer:
        return self._doc.GetDataInstance().GetContainer(self._SETTINGS_ID)

    def _save_container(self, bc: c4d.BaseContainer) -> None:
        self._doc.GetDataInstance().SetContainer(self._SETTINGS_ID, bc)

    def _entry_to_bc(self, objects: list) -> c4d.BaseContainer:
        bc = c4d.BaseContainer()
        for i, obj in enumerate(objects):
            bc.SetLink(i, obj)
        return bc

    def _bc_to_entry(self, bc: c4d.BaseContainer) -> list:
        return [obj for _, obj in bc if isinstance(obj, c4d.BaseObject) and obj.IsAlive()]

    def get_export_format(self) -> str:
        bc = self._get_container()
        index = bc.GetInt32(self._SETTING_EXPORT_FORMAT, 0)
        return COMBO_OPTIONS_EXPORT_FORMAT[index]

    def set_export_format(self, index: int) -> None:
        """Set export format for exporting"""
        bc = self._get_container()
        bc.SetInt32(self._SETTING_EXPORT_FORMAT, index)
        self._save_container(bc)

    def load_solo_stack(self) -> list[list]:
        root_bc = self._doc.GetDataInstance().GetContainer(self._SOLO_STACK_ID)
        return [
            self._bc_to_entry(root_bc.GetContainer(i))
            for i in range(self._SOLO_STACK_SIZE)
            if root_bc.FindIndex(i) != -1
        ]

    def save_solo_selection(self, containers) -> None:
        stack = self.load_solo_stack()

        if stack:
            previous_selection = stack[0]
            if set(containers) == set(previous_selection):
                return

        stack.insert(0, containers)
        stack = stack[: self._SOLO_STACK_SIZE]

        root_bc = c4d.BaseContainer()
        for i, entry in enumerate(stack):
            root_bc.SetContainer(i, self._entry_to_bc(entry))

        self._doc.GetDataInstance().SetContainer(self._SOLO_STACK_ID, root_bc)

    def pop_solo_selection(self) -> list:
        stack = self.load_solo_stack()
        if len(stack) < 2:
            return []

        _, previous, *rest = stack

        root_bc = c4d.BaseContainer()
        for i, entry in enumerate([previous] + rest):
            root_bc.SetContainer(i, self._entry_to_bc(entry))
        self._doc.GetDataInstance().SetContainer(self._SOLO_STACK_ID, root_bc)

        return previous


# pylint: disable=invalid-name, missing-function-docstring
class JbSettingsDialog(c4d.gui.GeDialog):
    """Dialog with settings jiko bridge."""

    def __init__(self, doc: c4d.documents.BaseDocument):
        super().__init__()
        self._settings = JbSettings(doc)
        self.selected_option = 0

    def CreateLayout(self):
        """Create layout"""
        self.SetTitle("Settings")

        self.GroupBegin(0, c4d.BFH_SCALEFIT, 1, 0, "", 0)
        self.GroupBorderSpace(10, 10, 10, 10)

        self.AddStaticText(0, c4d.BFH_LEFT, name="Export Format:")
        self.AddComboBox(IDC_SETTINGS_COMBO, c4d.BFH_SCALEFIT)
        for i, label in enumerate(COMBO_OPTIONS_EXPORT_FORMAT):
            self.AddChild(IDC_SETTINGS_COMBO, i, label)

        self.GroupEnd()

        self.GroupBegin(0, c4d.BFH_CENTER, 2, 1, "", 0)
        self.GroupBorderSpace(10, 5, 10, 10)
        self.AddButton(IDC_SETTINGS_OK, c4d.BFH_SCALE, name="OK")
        self.AddButton(IDC_SETTINGS_CANCEL, c4d.BFH_SCALE, name="Cancel")
        self.GroupEnd()

        return True

    def InitValues(self):
        index = COMBO_OPTIONS_EXPORT_FORMAT.index(self._settings.get_export_format())
        self.SetInt32(IDC_SETTINGS_COMBO, index)
        return True

    def Command(self, cmd_id, _msg):
        if cmd_id == IDC_SETTINGS_OK:
            self._settings.set_export_format(self.GetInt32(IDC_SETTINGS_COMBO))
            self.Close()
        elif cmd_id == IDC_SETTINGS_CANCEL:
            self.Close()
        return True
