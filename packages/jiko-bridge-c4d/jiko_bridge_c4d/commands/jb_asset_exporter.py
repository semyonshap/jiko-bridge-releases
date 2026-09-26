from jiko_bridge_c4d.jb_settings import JbSettings
from jiko_bridge_c4d.jb_types import JbAssetExporterBase
from jiko_bridge_c4d.scene.jb_scene import JbScene


class JbAssetExporter(JbAssetExporterBase):
    """Export asset class"""

    scene_class = JbScene
    settings_class = JbSettings
