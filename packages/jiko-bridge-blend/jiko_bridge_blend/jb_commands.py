"""Commands of the Blender plugin: the shared workflows bound to this scene."""

from .jb_settings import JbSettings
from .jb_types import JbAssetExporterBase, JbAssetImporterBase, JbAssetSoloBase
from .materials.jb_material_importer import JbMaterialImporter
from .scene.jb_scene import JbScene


class JbAssetImporter(JbAssetImporterBase):
    """Handles importing assets from Jiko Bridge into scene."""

    scene_class = JbScene
    materials_class = JbMaterialImporter


class JbAssetExporter(JbAssetExporterBase):
    """Export asset class"""

    scene_class = JbScene
    settings_class = JbSettings


class JbAssetSolo(JbAssetSoloBase):
    """Isolate the selected asset collections."""

    scene: JbScene
    scene_class = JbScene
    settings_class = JbSettings
