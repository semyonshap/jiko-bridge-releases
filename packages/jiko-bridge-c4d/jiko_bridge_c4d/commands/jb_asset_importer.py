from jiko_bridge_c4d.jb_types import JbAssetImporterBase
from jiko_bridge_c4d.materials.jb_material_importer import JbMaterialImporter
from jiko_bridge_c4d.scene.jb_scene import JbScene


class JbAssetImporter(JbAssetImporterBase):
    """Handles importing assets from Jiko Bridge into scene."""

    scene_class = JbScene
    materials_class = JbMaterialImporter
