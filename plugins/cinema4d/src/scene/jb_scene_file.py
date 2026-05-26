"""
File import/export layer for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

import os
import tempfile
import time
from pathlib import Path
from typing import Any, MutableMapping, Optional

import c4d
from src.scene.jb_scene_temp import JbSceneTemp


class JbSceneFile(JbSceneTemp):
    """File import/export layer in the scene hierarchy."""

    def __init__(self):
        super().__init__()
        self.cache_path = os.path.join(tempfile.gettempdir(), "jiko-bridge")
        os.makedirs(self.cache_path, exist_ok=True)

    def _find_plugin(self, plugin_id: int, plugin_type: int) -> Optional[c4d.plugins.BasePlugin]:
        plug = c4d.plugins.FindPlugin(plugin_id, plugin_type)
        if not plug:
            self.logger.error("Plugin %d not found", plugin_id)
        return plug

    def _get_imexporter(self, plug: c4d.plugins.BasePlugin) -> Optional[MutableMapping[int, Any]]:
        data: dict[str, Any] = {}
        if not plug.Message(c4d.MSG_RETRIEVEPRIVATEDATA, data):
            self.logger.error("Failed to retrieve private data from plugin")
            return None
        imexporter = data.get("imexporter")
        if not imexporter:
            self.logger.error("imexporter not available in plugin data")
        return imexporter

    def _merge_document(self, file_path: str) -> bool:
        doc = self._temp_source
        if doc is None:
            self.logger.error("No active document for merging")
            return False
        t = time.time()
        result = c4d.documents.MergeDocument(
            doc, file_path, c4d.SCENEFILTER_OBJECTS | c4d.SCENEFILTER_MATERIALS
        )
        self.logger.debug("Import took %.3fs: %s", time.time() - t, file_path)
        return result

    def _save_document(self, file_path: str, format_id: int) -> bool:
        doc = self._temp_source
        if doc is None:
            self.logger.error("No active document for saving")
            return False
        t = time.time()
        result = c4d.documents.SaveDocument(doc, file_path, c4d.SAVEDOCUMENTFLAGS_NONE, format_id)
        self.logger.debug("Export took %.3fs: %s", time.time() - t, file_path)
        return result

    def import_file(self, file_path) -> bool:
        ext = Path(file_path).suffix.lower().lstrip('.')
        handler = {
            "fbx": self._import_fbx,
            "abc": self._import_alembic,
            "obj": self._import_obj,
            "usd": self._import_usd,
        }.get(ext)

        if not handler:
            self.logger.error("Unsupported file extension: %s", ext)
            return False

        return handler(file_path)

    def _import_fbx(self, file_path) -> bool:
        plug = self._find_plugin(c4d.FORMAT_FBX_IMPORT, c4d.PLUGINTYPE_SCENELOADER)
        if not plug:
            return False

        imex = self._get_imexporter(plug)
        if imex:
            imex[c4d.FBXIMPORT_CAMERAS] = True
            imex[c4d.FBXIMPORT_LIGHTS] = True
            imex[c4d.FBXIMPORT_SINGLE_MAT_SELECTIONTAGS] = False

        result = self._merge_document(file_path)
        if not result:
            self.logger.error("FBX import failed: %s", file_path)
        return result

    def _import_alembic(self, file_path: str) -> bool:
        plug = self._find_plugin(c4d.FORMAT_ABCIMPORT, c4d.PLUGINTYPE_SCENELOADER)
        if not plug:
            return False

        imex = self._get_imexporter(plug)
        if imex:
            scale_data = c4d.UnitScaleData()
            scale_data.SetUnitScale(1, c4d.DOCUMENT_UNIT_M)
            imex[c4d.ABCIMPORT_SCALE] = scale_data
            imex[c4d.ABCIMPORT_FACESETS] = True

        result = self._merge_document(file_path)
        if not result:
            self.logger.error("Alembic import failed: %s", file_path)
        return result

    def _import_obj(self, file_path: str) -> bool:
        plug = self._find_plugin(c4d.FORMAT_OBJ2IMPORT, c4d.PLUGINTYPE_SCENELOADER)
        if not plug:
            return False

        result = self._merge_document(file_path)
        if not result:
            self.logger.error("OBJ import failed: %s", file_path)
        return result

    def _import_usd(self, file_path: str) -> bool:
        plug = self._find_plugin(c4d.FORMAT_USDIMPORT, c4d.PLUGINTYPE_SCENELOADER)
        if not plug:
            return False

        result = self._merge_document(file_path)
        if not result:
            self.logger.error("USD import failed: %s", file_path)
        return result

    def _generate_path(self, ext: str) -> str:
        filename = f"tmp_{int(time.time())}.{ext}"
        return os.path.join(self.cache_path, filename)

    def _select_all(self, doc: c4d.documents.BaseDocument) -> None:
        objects = self.walk(doc.GetObjects())
        for obj in objects:
            obj.SetBit(c4d.BIT_ACTIVE)

    def export_file(self, ext) -> Optional[str]:
        file_path = self._generate_path(ext)
        handler = {
            "fbx": self._export_fbx,
            "abc": self._export_alembic,
            "obj": self._export_obj,
            "usd": self._export_usd,
        }.get(ext)

        if not handler:
            self.logger.error("Unsupported export extension: %s", ext)
            return None

        self._select_all(self._temp_source)
        return handler(file_path)

    def _export_fbx(self, file_path) -> Optional[str]:
        self._project_scale(self._temp_source, 0.01)

        plug = self._find_plugin(c4d.FORMAT_FBX_EXPORT, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            return None

        imex = self._get_imexporter(plug)
        if imex:
            imex[c4d.FBXEXPORT_SELECTION_ONLY] = True
            imex[c4d.FBXEXPORT_ASCII] = False
            imex[c4d.FBXEXPORT_SCALE] = 0.01
            imex[c4d.FBXEXPORT_EMBED_TEXTURES] = False

        if not self._save_document(file_path, c4d.FORMAT_FBX_EXPORT):
            self.logger.error("FBX export failed")
            return None

        self.logger.debug("FBX exported: %s", file_path)
        return file_path

    def _export_alembic(self, file_path: str) -> Optional[str]:
        self._project_scale(self._temp_source, 0.01)
        plug = self._find_plugin(c4d.FORMAT_ABCEXPORT, c4d.PLUGINTYPE_SCENESAVER)
        if not plug:
            return None

        imex = self._get_imexporter(plug)
        if imex:
            imex[c4d.ABCEXPORT_SELECTION_ONLY] = True
            scale_data = c4d.UnitScaleData()
            scale_data.SetUnitScale(1, c4d.DOCUMENT_UNIT_M)
            imex[c4d.ABCEXPORT_SCALE] = scale_data

        if not self._save_document(file_path, c4d.FORMAT_ABCEXPORT):
            self.logger.error("Alembic export failed")
            return None

        self.logger.debug("Alembic exported: %s", file_path)
        return file_path

    def _export_obj(self, _file_path: str) -> Optional[str]:
        return None

    def _export_usd(self, _file_path: str) -> Optional[str]:
        return None
