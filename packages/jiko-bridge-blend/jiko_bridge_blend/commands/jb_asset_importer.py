from ..jb_types import JbAssetImporterBase
from ..materials.jb_material_importer import JbMaterialImporter
from ..scene.jb_scene import JbScene


class JbAssetImporter(JbAssetImporterBase):
    """Handles importing assets from Jiko Bridge into scene."""

    scene_class = JbScene
    materials_class = JbMaterialImporter
