"""Asset export workflow shared by every Jiko Bridge DCC plugin."""

from abc import ABC
from logging import Logger
from pathlib import Path
from typing import Generic, List, cast

from ..api import JbAPI
from ..contracts import (
    JbContainerT,
    JbMaterialT,
    JbMatrixT,
    JbObjectT,
    JbSceneABC,
    JbSettingsABC,
    JbSourceT,
)
from ..logger import get_logger
from ..models import AssetFile, AssetModel


class JbAssetExporterABC(ABC, Generic[JbSourceT, JbMatrixT, JbContainerT, JbObjectT, JbMaterialT]):
    """Base class for asset exporters holding the shared export workflow.

    As in the importer, the source document is constructor-only and the plugin
    only names the collaborators the workflow needs.
    """

    scene_class: type[JbSceneABC[JbSourceT, JbMatrixT, JbContainerT, JbObjectT, JbMaterialT]]
    settings_class: type[JbSettingsABC[JbSourceT, JbContainerT]]

    def __init__(self, source: JbSourceT):
        self.source = source
        self.api = JbAPI()
        self.scene = self.scene_class(source)

    @property
    def logger(self) -> Logger:
        """Logger of the concrete plugin module, so log lines stay traceable."""
        return get_logger(type(self).__module__)

    def export_asset(self) -> None:
        """Exports an asset from the scene into Jiko Bridge."""
        selected_objects, asset_containers = self._collect_data()
        if asset_containers:
            for container in asset_containers:
                self._update_asset(container)
        elif selected_objects:
            self._create_new_asset(selected_objects)
        else:
            self._export_project()

    def export_message(self) -> str:
        """Return a confirmation message based on the current selection and asset containers."""
        selected_objects, asset_containers = self._collect_data()
        if asset_containers:
            return "Update existing assets?\n" f"{len(asset_containers)} asset(s) will be updated"

        if selected_objects:
            return (
                "No asset containers found in selection. "
                f"Create new asset with {len(selected_objects)} object(s)?"
            )

        return "Export project."

    def _collect_data(self) -> tuple[list[JbObjectT | JbContainerT], list[JbContainerT]]:
        selected_objects = cast(List[JbObjectT | JbContainerT], self.scene.get_selection())
        return selected_objects, self.scene.get_containers_from_objects(
            cast(List[JbObjectT], selected_objects)
        )

    def _update_asset(self, container: JbContainerT) -> None:
        asset_model = self.scene.get_asset_data_from_container(container)
        if not asset_model:
            self.logger.error("Invalid asset information")
            return

        asset = self.api.get_asset(asset_model)
        if not asset or not asset.files or not asset.pack_name or not asset.asset_name:
            self.logger.error("Failed to fetch asset '%s'.", asset_model.asset_name)
            return

        file = next(iter(asset.files))
        if not file.filepath:
            self.logger.error(
                "Filepath missing for asset '%s'. Cannot export.",
                asset_model.asset_name,
            )
            return

        ext = Path(file.filepath.lower()).suffix.lstrip(".")
        if not ext:
            self.logger.error(
                "Unable to determine export extension from filepath '%s' for '%s'.",
                file.filepath,
                asset_model.asset_name,
            )
            return

        objects = self.scene.get_children(container)
        if not objects:
            self.logger.error(
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

    def _create_new_asset(self, objects: list[JbObjectT | JbContainerT]) -> None:
        fmt = self.settings_class(self.source).get_export_format()

        filepath = self.scene.export_with_temp(objects, fmt)
        if not filepath:
            self.logger.error("Export failed.")
            return

        asset = self.api.create_asset(AssetModel(files=[AssetFile(filepath=filepath)]))

        if not asset or not asset.files:
            self.logger.error("No asset found for filepath '%s'", filepath)
            return

        for file in asset.files:
            container, _ = self.scene.get_or_create_asset_container(asset, file)
            self.scene.move_objects_to_container(cast(List[JbObjectT], objects), container)
            self.logger.info(
                "Asset '%s' created with type '%s'.", asset.asset_name, file.asset_type
            )

    def _export_project(self) -> None:
        if filepath := self.scene.get_project_filepath():
            self.api.create_asset(AssetModel(files=[AssetFile(filepath=filepath)]))
