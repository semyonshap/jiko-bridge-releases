"""Deferred Houdini features implementing the shared contract."""

from jiko_bridge_client import get_logger
from jiko_bridge_houdini.jb_types import JbMaterialImporterBase, JbSource


class JbMaterialImporter(JbMaterialImporterBase):
    """Placeholder until this feature is implemented for Houdini."""

    def __init__(self, source: JbSource):
        self.source = source
        self.logger = get_logger(__name__)

    def get_material_name(self, material):
        """Reserved by the common DCC interface."""
        self.logger.warning("Houdini JbMaterialImporter.get_material_name is not implemented.")
        pass

    def set_material_name(self, material, name):
        """Reserved by the common DCC interface."""
        self.logger.warning("Houdini JbMaterialImporter.set_material_name is not implemented.")
        pass

    def import_material(self, asset, file):
        """Reserved by the common DCC interface."""
        self.logger.warning("Houdini JbMaterialImporter.import_material is not implemented.")
        pass
