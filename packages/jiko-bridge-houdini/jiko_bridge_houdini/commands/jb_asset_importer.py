from dataclasses import replace

from jiko_bridge_client import AssetModel
from jiko_bridge_houdini.jb_types import IMPORT_NODE, JbAssetImporterBase
from jiko_bridge_houdini.materials.jb_material_importer import JbMaterialImporter
from jiko_bridge_houdini.scene.jb_scene import JbScene


class JbAssetImporter(JbAssetImporterBase):
    """Shared DCC import workflow with the node parameters as the asset selection."""

    scene_class = JbScene
    materials_class = JbMaterialImporter

    def import_assets(self) -> None:
        """Import every asset the node asks for and record it in its own fields."""
        self._asset_cache = {}
        for asset in self._collect_assets():
            self.scene.record_asset(asset)
            self._import_single(asset)
        self._refresh()

    def _refresh(self) -> None:
        """Re-read the cache layers of the import node after their files were written."""
        node = self.source.node(IMPORT_NODE)
        if node is not None:
            node.cook(force=True)

    def _resolve_asset(self, name: str) -> AssetModel | None:
        """Only geometry participates in this importer, including dependencies."""
        asset = super()._resolve_asset(name)
        return self._model_asset(asset) if asset is not None else None

    @staticmethod
    def _model_asset(asset: AssetModel) -> AssetModel | None:
        """Keep the model files of an asset; None when it has none."""
        files = [file for file in asset.files if file.bridge_type == "model" and file.filepath]
        return replace(asset, files=files) if files else None
