from pathlib import Path

from jiko_bridge_c4d.jb_settings import JbSettings
from jiko_bridge_c4d.jb_types import JbAssetExporterBase, JbSource
from jiko_bridge_c4d.scene.jb_scene import JbScene
from jiko_bridge_client import AssetFile, AssetModel, JbAPI, get_logger

asset_export_logger = get_logger(__name__)


class JbAssetExporter(JbAssetExporterBase):
    """Export asset class"""

    def __init__(self, source: JbSource):
        self.source = source
        self.api = JbAPI()
        self.scene = JbScene(source)

    def export_asset(self) -> None:
        """Export the selected asset or create a new one."""
        selected_objects, asset_containers = self._collect_data()
        if asset_containers:
            for container in asset_containers:
                self._update_asset(container)
        elif selected_objects:
            self._create_new_asset(selected_objects)
        else:
            self._export_project()

    def export_message(self) -> str:
        selected_objects, asset_containers = self._collect_data()
        if asset_containers:
            return "Update existing assets?\n" f"{len(asset_containers)} asset(s) will be updated"

        if selected_objects:
            return (
                "No asset containers found in selection. "
                f"Create new asset with {len(selected_objects)} object(s)?"
            )

        return "Export project."

    def _collect_data(self):
        selected_objects = self.scene.get_selection()
        asset_containers = self.scene.get_containers_from_objects(selected_objects)
        return selected_objects, asset_containers

    def _update_asset(self, container) -> None:
        asset_model = self.scene.get_asset_data_from_container(container)
        if not asset_model:
            asset_export_logger.error("Invalid asset information")
            return

        asset = self.api.get_asset(asset_model)
        if not asset or not asset.files or not asset.pack_name or not asset.asset_name:
            asset_export_logger.error("Failed to fetch asset '%s'.", asset_model.asset_name)
            return

        file = next(iter(asset.files))
        if not file.filepath:
            asset_export_logger.error(
                "Filepath missing for asset '%s'. Cannot export.",
                asset_model.asset_name,
            )
            return

        ext = Path(file.filepath.lower()).suffix.lstrip('.')
        if not ext:
            asset_export_logger.error(
                "Unable to determine export extension from filepath '%s' for '%s'.",
                file.filepath,
                asset_model.asset_name,
            )
            return

        objects = self.scene.get_children(container)
        if not objects:
            asset_export_logger.error(
                "No objects found in container for asset '%s'. Cannot export.",
                asset_model.asset_name,
            )
            return
        filepath = self.scene.export_with_temp(objects, ext)

        if not filepath:
            return

        asset.files = [
            AssetFile(filepath=filepath, asset_type=file.asset_type, bridge_type=file.bridge_type)
        ]

        self.api.update_asset(asset)

    def _create_new_asset(self, objects) -> None:
        fmt = JbSettings(self.source).get_export_format()

        filepath = self.scene.export_with_temp(objects, fmt)
        if not filepath:
            asset_export_logger.error("Export failed.")
            return

        asset = self.api.create_asset(AssetModel(files=[AssetFile(filepath=filepath)]))

        if not asset or not asset.files:
            asset_export_logger.error("No asset found for filepath '%s'", filepath)
            return

        for file in asset.files:
            container, _ = self.scene.get_or_create_asset_container(asset, file)
            self.scene.move_objects_to_container(objects, container)
            asset_export_logger.info(
                "Asset '%s' created with type '%s'.", asset.asset_name, file.asset_type
            )

    def _export_project(self) -> None:
        if filepath := self.scene.get_project_filepath():
            self.api.create_asset(AssetModel(files=[AssetFile(filepath=filepath)]))
