import c4d
from jiko_bridge_c4d.jb_settings import JbSettings
from jiko_bridge_c4d.jb_types import JbAssetSoloBase, JbContainer
from jiko_bridge_c4d.scene.jb_scene import JbScene


class JbAssetSolo(JbAssetSoloBase):
    """Isolate the selected asset containers."""

    scene: JbScene
    scene_class = JbScene
    settings_class = JbSettings
    history_size = 10

    def _apply_solo(self, containers: list[JbContainer]) -> None:
        root, _ = self.scene.get_or_create_container("Assets")

        self.scene.set_container_visibility(root, 1)

        for child in root.GetChildren():
            self.scene.set_container_visibility(child, 2)

        for container in containers:
            self.scene.set_container_visibility(container, 0)

        c4d.CallCommand(12288)
