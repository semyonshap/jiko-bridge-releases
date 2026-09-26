"""Deferred Houdini features implementing the shared contract."""

from jiko_bridge_houdini.jb_settings import JbSettings
from jiko_bridge_houdini.jb_types import JbAssetSoloBase, JbContainer
from jiko_bridge_houdini.scene.jb_scene import JbScene


class JbAssetSolo(JbAssetSoloBase):
    """Placeholder until this feature is implemented for Houdini."""

    scene: JbScene
    scene_class = JbScene
    settings_class = JbSettings

    def _apply_solo(self, _containers: list[JbContainer]) -> None:
        self.logger.warning("Houdini solo mode is not implemented.")
