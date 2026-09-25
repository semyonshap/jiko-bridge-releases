from typing import Optional

import bpy
from jiko_bridge_client import AssetFile, AssetModel, get_logger

from ..jb_types import JbMaterialImporterBase
from .jb_standard_material import JBStandardMaterial

material_import_logger = get_logger(__name__)


class JbMaterialImporter(JbMaterialImporterBase):
    """Material importer that handles Blender materials."""

    def __init__(self, source):
        self.source = source

    def get_material_name(self, material):
        return material.name if material else None

    def set_material_name(self, material, name):
        if material:
            material.name = name

    def import_material(self, asset: AssetModel, file: AssetFile) -> Optional[bpy.types.Material]:
        """Import a single material file into the scene."""
        if file.asset_type is None or file.filepath is None:
            material_import_logger.error("Material file is missing type or path")
            return None

        channel = file.asset_type.lower()
        path = file.filepath
        material_name = f"{asset.pack_name}__{asset.asset_name}"

        material = bpy.data.materials.get(material_name)
        if not material:
            material = bpy.data.materials.new(name=material_name)

        if material is None:
            material_import_logger.error("Failed to create material: %s", material_name)
            return None

        standard = JBStandardMaterial(material)
        standard.apply_channel(channel, path)

        return material
