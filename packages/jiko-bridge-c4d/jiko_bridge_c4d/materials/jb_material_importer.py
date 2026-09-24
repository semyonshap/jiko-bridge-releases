"""
Material importer for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

from typing import Optional

import c4d
from src.jb_types import AssetModel, AssetFile, JbSource
from src.materials import (
    JbRedshiftNodeMaterial,
    JbArnoldNodeMaterial,
    JbStandardNodeMaterial,
)
from src.jb_protocols import JbMaterialImporterABC
from src.jb_utils import get_logger

ARNOLD_ID = 1029988
REDSHIFT_ID = c4d.VPrsrenderer
VIEWPORT_ID = 300001061

logger = get_logger(__name__)


class JbMaterialImporter(JbMaterialImporterABC):
    """Material importer that handles different renderers."""

    def __init__(self, source: JbSource):
        self._redshift = JbRedshiftNodeMaterial()
        self._arnold = JbArnoldNodeMaterial()
        self._standard = JbStandardNodeMaterial()
        self._source = source

    @property
    def source(self) -> JbSource:
        """Return the active document."""
        return self._source or c4d.documents.GetActiveDocument()

    def find_existing(self, name: str):
        """Find an existing material by name."""
        mat = self.source.GetFirstMaterial()
        while mat:
            if mat.GetName() == name:
                return mat
            mat = mat.GetNext()
        return None

    def get_material_name(self, material: c4d.BaseMaterial) -> str | None:
        return material.GetName() if material else None

    def set_material_name(self, material: c4d.BaseMaterial, name: str):
        if material:
            material.SetName(name)

    def _get_material_renderer(self):
        render_id = self.source.GetActiveRenderData()[c4d.RDATA_RENDERENGINE]
        if render_id == REDSHIFT_ID:
            return self._redshift
        if render_id == ARNOLD_ID:
            return self._arnold
        if render_id == VIEWPORT_ID:
            return self._standard
        return self._standard

    def import_material(self, asset: AssetModel, file: AssetFile) -> Optional[c4d.BaseMaterial]:
        """Import a single material file into the scene."""
        if file.asset_type is None or file.filepath is None:
            logger.error("Material file is missing type or path")
            return None

        renderer = self._get_material_renderer()
        channel = file.asset_type.lower()
        path = file.filepath

        material_name = f"{asset.pack_name}__{asset.asset_name}"

        material = self.find_existing(material_name)
        if not material:
            material = c4d.BaseMaterial(c4d.Mmaterial)
            material.SetName(material_name)
            self.source.InsertMaterial(material)

        renderer.apply_channel(material, channel, path)

        c4d.EventAdd()

        return material
