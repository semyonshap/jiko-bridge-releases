"""
Import and export file handling for Jiko Bridge in Blender.
Code by Semyon Shapoval, 2026
"""

import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import bpy

from .jb_scene_instance import JbSceneInstance


class JbSceneFile(JbSceneInstance):
    """File import/export layer in the scene hierarchy."""

    def __init__(self):
        self.cache_path = os.path.join(tempfile.gettempdir(), "jiko-bridge")
        os.makedirs(self.cache_path, exist_ok=True)

    def get_temp_path(self, ext: str) -> str:
        """Generate a unique temporary file path with the given extension."""
        filename = f"tmp_{uuid.uuid4().hex}.{ext}"
        return os.path.join(self.cache_path, filename)

    def import_file(self, file_path) -> bool:
        if not os.path.exists(file_path):
            self.logger.error("Import file not found: %s", file_path)
            return False

        ext = Path(file_path).suffix.lower().lstrip(".")
        handler = {
            "fbx": self._import_fbx,
            "abc": self._import_alembic,
            "obj": self._import_obj,
            "usd": self._import_usd,
            "usda": self._import_usd,
            "usdc": self._import_usd,
            "glb": self._import_gltf,
            "gltf": self._import_gltf,
        }.get(ext)

        if not handler:
            self.logger.error("Unsupported file extension: %s", ext)
            return False

        return handler(file_path)

    def _import_fbx(self, file_path) -> bool:
        self.logger.debug("Importing FBX asset: %s", file_path)
        try:
            bpy.ops.import_scene.fbx(
                filepath=file_path,
                use_image_search=False,
                automatic_bone_orientation=True,
            )
        except Exception as e:
            self.logger.error("FBX import failed: %s", e)
            return False
        return True

    def _import_alembic(self, file_path: str) -> bool:
        try:
            bpy.ops.wm.alembic_import(filepath=file_path, as_background_job=False)
        except Exception as e:
            self.logger.error("Alembic import failed: %s", e)
            return False
        return True

    def _import_obj(self, file_path: str) -> bool:
        try:
            bpy.ops.wm.obj_import(filepath=file_path)
        except Exception as e:
            self.logger.error("OBJ import failed: %s", e)
            return False
        return True

    def _import_usd(self, file_path: str) -> bool:
        try:
            bpy.ops.wm.usd_import(filepath=file_path)
        except Exception as e:
            self.logger.error("USD import failed: %s", e)
            return False
        return True

    def _import_gltf(self, file_path: str) -> bool:
        try:
            bpy.ops.import_scene.gltf(filepath=file_path)
        except Exception as e:
            self.logger.error("GLTF import failed: %s", e)
            return False
        return True

    def export_file(self, ext) -> Optional[str]:
        """Exports the current Blender scene to a file."""
        file_path = self.get_temp_path(ext)
        handler = {
            "fbx": self._export_fbx,
            "abc": self._export_alembic,
            "glb": self._export_gltf,
            "obj": self._export_obj,
            "usd": self._export_usd,
        }.get(ext)

        if not handler:
            self.logger.error("Unsupported export extension: %s", ext)
            return None

        return handler(file_path)

    def _export_fbx(self, file_path) -> Optional[str]:
        try:
            bpy.ops.export_scene.fbx(
                filepath=file_path,
                use_selection=False,
                apply_scale_options="FBX_SCALE_UNITS",
                global_scale=1,
                path_mode="COPY",
                embed_textures=False,
                bake_space_transform=False,
                axis_up="Y",
                axis_forward="-Z",
            )
            self.logger.info("FBX exported: %s", file_path)
            return file_path
        except Exception as e:
            self.logger.error("FBX export failed: %s", e)
            return None

    def _export_alembic(self, file_path: str) -> Optional[str]:
        try:
            bpy.ops.wm.alembic_export(
                filepath=file_path,
                selected=False,
                face_sets=True,
            )
            self.logger.info("Alembic exported: %s", file_path)
            return file_path
        except Exception as e:
            self.logger.error("Alembic export failed: %s", e)
            return None

    def _export_gltf(self, file_path: str) -> Optional[str]:
        try:
            bpy.ops.export_scene.gltf(
                filepath=file_path,
                use_selection=False,
                export_format="GLB",
            )
            self.logger.info("GLTF exported: %s", file_path)
            return file_path
        except Exception as e:
            self.logger.error("GLTF export failed: %s", e)
            return None

    def _export_obj(self, _file_path: str):
        self.logger.warning("OBJ export not implemented yet")

    def _export_usd(self, _file_path: str):
        self.logger.warning("USD export not implemented yet")
