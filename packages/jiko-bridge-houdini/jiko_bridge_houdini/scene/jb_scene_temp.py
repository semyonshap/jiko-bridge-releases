from contextlib import contextmanager

from jiko_bridge_houdini.scene.jb_scene_instance import JbSceneInstance


class JbSceneTemp(JbSceneInstance):
    """Houdini implementation of temp operations."""

    @contextmanager
    def temp_source(self, objects=None, unit_scale=1.0, debug=False):
        yield self.source
