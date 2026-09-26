import bpy

from ..jb_settings import JbSettings
from ..jb_types import JbAssetSoloBase, JbContainer
from ..scene.jb_scene import JbScene


class JbAssetSolo(JbAssetSoloBase):
    """Isolate the selected asset collections."""

    scene: JbScene
    scene_class = JbScene
    settings_class = JbSettings

    def _apply_solo(self, containers: list[JbContainer]) -> None:
        root = self.scene.get_or_create_container("Assets")

        # Hide root
        self.scene.set_container_visibility(root, True)

        # Hide every child
        for child in root.children:
            self.scene.set_container_visibility(child, False)

        # Show the soloed ones
        for container in containers:
            self.scene.set_container_visibility(container, True)

        bpy.ops.view3d.view_all()
