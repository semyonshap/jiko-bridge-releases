"""Deferred Houdini features implementing the shared contract."""

from jiko_bridge_client import get_logger
from jiko_bridge_houdini.jb_types import JbSettingsBase, JbSource


class JbSettings(JbSettingsBase):
    """Placeholder until this feature is implemented for Houdini."""

    def __init__(self, source: JbSource):
        self.source = source
        self.logger = get_logger(__name__)

    def get_export_format(self):
        """Reserved by the common DCC interface."""
        self.logger.warning("Houdini JbSettings.get_export_format is not implemented.")
        pass

    def load_solo_stack(self):
        """Reserved by the common DCC interface."""
        self.logger.warning("Houdini JbSettings.load_solo_stack is not implemented.")
        pass

    def save_solo_selection(self, containers):
        """Reserved by the common DCC interface."""
        self.logger.warning("Houdini JbSettings.save_solo_selection is not implemented.")
        pass

    def pop_solo_selection(self):
        """Reserved by the common DCC interface."""
        self.logger.warning("Houdini JbSettings.pop_solo_selection is not implemented.")
        pass
