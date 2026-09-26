from ..jb_settings import JbSettings
from ..jb_types import JbAssetExporterBase
from ..scene.jb_scene import JbScene


class JbAssetExporter(JbAssetExporterBase):
    """Export asset class"""

    scene_class = JbScene
    settings_class = JbSettings
