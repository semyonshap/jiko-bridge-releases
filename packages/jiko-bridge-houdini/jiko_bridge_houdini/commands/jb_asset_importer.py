from jiko_bridge_houdini.jb_types import JbAssetImporterBase, JbSource
from jiko_bridge_houdini.materials.jb_material_importer import JbMaterialImporter
from jiko_bridge_houdini.scene.jb_scene import JbScene


class JbAssetImporter(JbAssetImporterBase):

    scene: JbScene
    scene_class = JbScene
    materials_class = JbMaterialImporter

    def __init__(self, source: JbSource):
        super().__init__(source)
