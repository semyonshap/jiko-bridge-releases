from abc import ABC, abstractmethod
from logging import Logger
from pathlib import Path
from typing import Generator, Generic, List, Optional, TypeVar, cast

from .api import JbAPI
from .logger import get_logger
from .models import AssetFile, AssetModel

# DCC-supplied types
JbSourceT = TypeVar("JbSourceT")
JbMatrixT = TypeVar("JbMatrixT")
JbContainerT = TypeVar("JbContainerT")
JbObjectT = TypeVar("JbObjectT")
JbMaterialT = TypeVar("JbMaterialT")


class JbSettingsABC(ABC, Generic[JbSourceT, JbContainerT]):
    """Abstract base class for per-scene settings storage.

    Besides the general plugin settings it stores the solo history as opaque
    container lists: the storage is DCC-specific, the semantics are not.
    """

    @abstractmethod
    def __init__(self, source: JbSourceT) -> None: ...

    @abstractmethod
    def get_export_format(self) -> str:
        """Return the current export format (e.g. 'fbx', 'abc')."""

    @abstractmethod
    def load_solo(self) -> list[list[JbContainerT]]:
        """Return the stored solo selections, newest first."""

    @abstractmethod
    def save_solo(self, entries: list[list[JbContainerT]]) -> None:
        """Replace the stored solo selections with the given entries, newest first."""


class JbSceneABC(  # pylint: disable=too-many-public-methods
    ABC,
    Generic[JbSourceT, JbMatrixT, JbContainerT, JbObjectT, JbMaterialT],
):
    """Abstract base class for all Jiko Bridge scene operations."""

    # ------------------------------------------------------------------
    # Base
    # ------------------------------------------------------------------

    @abstractmethod
    def __init__(self, source: JbSourceT): ...

    @property
    @abstractmethod
    def source(self) -> JbSourceT:
        """Return the source scene."""

    @property
    @abstractmethod
    def logger(self) -> Logger:
        """Return the logger instance."""

    # ------------------------------------------------------------------
    # Scene Objects
    # ------------------------------------------------------------------

    @abstractmethod
    def walk(
        self,
        root: list[JbObjectT | JbContainerT | JbMaterialT],
    ) -> list[JbObjectT | JbContainerT | JbMaterialT]:
        """Call *fn* for every object in the root hierarchy (pre-order)."""

    @abstractmethod
    def get_materials_from_objects(self, objects: list[JbObjectT]) -> list[JbMaterialT]:
        """Return materials used by the given objects."""

    @abstractmethod
    def get_selection(self) -> list[JbObjectT | JbContainerT | JbMaterialT]:
        """Return the currently selected objects or materials."""

    @abstractmethod
    def copy_object_transform(self, obj: JbObjectT, target_obj: JbObjectT) -> None:
        """Set the transform of the given object."""

    @abstractmethod
    def remove_object(self, obj: JbObjectT) -> None:
        """Remove the given object from the scene."""

    @abstractmethod
    def get_depth(self, obj: JbObjectT | JbContainerT | JbMaterialT) -> int:
        """Return the depth of the given object in the hierarchy."""

    @abstractmethod
    def merge_duplicates_materials(self, material: JbMaterialT) -> None:
        """Replace duplicate materials (.001, .002, ...) with the given base material."""

    # ------------------------------------------------------------------
    # Container
    # ------------------------------------------------------------------

    @abstractmethod
    def get_container(self, asset: AssetModel) -> Optional[JbContainerT]:
        """Get the container associated with the given asset, if it exists."""

    @abstractmethod
    def get_or_create_container(
        self, name: str, parent: Optional[JbContainerT] = None
    ) -> JbContainerT:
        """Get or create a container with the given name under the parent."""

    @abstractmethod
    def get_or_create_asset_container(
        self,
        asset: AssetModel,
        file: Optional[AssetFile] = None,
    ) -> tuple[JbContainerT, bool]:
        """Get or create a container with asset data."""

    @abstractmethod
    def set_asset_data(
        self, container: JbContainerT, asset: AssetModel, file: Optional[AssetFile] = None
    ) -> None:
        """Store asset info in the container's custom properties."""

    @abstractmethod
    def get_asset_data_from_container(self, container: JbContainerT) -> Optional[AssetModel]:
        """Parse asset info from a container's custom properties."""

    @abstractmethod
    def copy_asset_data(self, src: JbContainerT, dst: JbContainerT | JbObjectT) -> None:
        """Copy custom properties from src to dst."""

    @abstractmethod
    def get_containers_from_objects(self, objects: list[JbObjectT]) -> list[JbContainerT]:
        """Return asset containers found among the given objects (via instance Empties)."""

    @abstractmethod
    def get_containers_from_instances(self, objects: list[JbObjectT]) -> list[JbContainerT]:
        """Return asset containers found among the given instances."""

    @abstractmethod
    def move_objects_to_container(self, objects: list[JbObjectT], container: JbContainerT) -> None:
        """Move objects into target collection."""

    @abstractmethod
    def cleanup_container(self, container: JbContainerT) -> None:
        """Remove empty objects that have no children and no data."""

    @abstractmethod
    def clear_container(self, container: JbContainerT) -> None:
        """Remove all objects from the container."""

    @abstractmethod
    def get_children(self, obj: JbObjectT | JbContainerT) -> list[JbObjectT | JbContainerT]:
        """Return the children of the given object or container."""

    # ------------------------------------------------------------------
    # Instance
    # ------------------------------------------------------------------

    @abstractmethod
    def create_instance(self, container: JbContainerT, name: str) -> JbObjectT:
        """Create an instance of the given object."""

    @abstractmethod
    def get_names_from_placeholder(self, obj: JbObjectT) -> List[str]:
        """Extract placeholder info from objects and remove them."""

    @abstractmethod
    def replace_instances_with_placeholders(
        self, objects: list[JbObjectT], source: JbSourceT
    ) -> list[JbObjectT]:
        """Replace instances in the list with placeholders."""

    @abstractmethod
    def create_placeholder(
        self,
        asset_model: AssetModel,
        transform: JbMatrixT,
        source: JbSourceT,
    ) -> JbObjectT:
        """Create a placeholder object in the scene based on the info."""

    # ------------------------------------------------------------------
    # File
    # ------------------------------------------------------------------

    @abstractmethod
    def import_file(self, file_path: str) -> bool:
        """Import a file into the active scene."""

    @abstractmethod
    def _import_fbx(self, file_path: str) -> bool: ...

    @abstractmethod
    def export_file(self, ext: str) -> Optional[str]:
        """Export the active scene to a file and return its path."""

    @abstractmethod
    def _export_fbx(self, file_path: str) -> Optional[str]: ...

    # ------------------------------------------------------------------
    # Temp Scene
    # ------------------------------------------------------------------

    @abstractmethod
    def temp_source(
        self,
        objects: Optional[list[JbObjectT | JbContainerT]] = None,
        unit_scale: float | int = 1.0,
        debug: bool = False,
    ) -> Generator[JbSourceT, None, None]:
        """Context manager for temporary scenes."""

    # ------------------------------------------------------------------
    # Scene (high-level)
    # ------------------------------------------------------------------

    @abstractmethod
    def import_with_temp(self, file_path: str, target: JbContainerT) -> None:
        """Import a file into an isolated scene, then copy to target collection."""

    @abstractmethod
    def export_with_temp(
        self,
        src: list[JbObjectT | JbContainerT],
        ext: str,
    ) -> Optional[str]:
        """Copy objects to isolated scene, replace instances, export."""

    @abstractmethod
    def get_project_filepath(self) -> Optional[str]:
        """Return the current project filepath, if it exists."""


class JbMaterialImporterABC(ABC, Generic[JbSourceT, JbMaterialT]):
    """Abstract base class for Material Importers."""

    @abstractmethod
    def __init__(self, source: JbSourceT) -> None: ...

    @abstractmethod
    def get_material_name(self, material: JbMaterialT) -> str | None:
        """Get the name of a material."""

    @abstractmethod
    def set_material_name(self, material: JbMaterialT, name: str):
        """Set the name of a material."""

    @abstractmethod
    def import_material(self, asset: AssetModel, file: AssetFile) -> Optional[JbMaterialT]:
        """Import a single material file into the scene."""


# Asset contracts


class JbAssetImporterABC(ABC, Generic[JbSourceT, JbMatrixT, JbContainerT, JbObjectT, JbMaterialT]):
    """Base class for asset importers holding the shared import workflow.

    A plugin names ``scene_class`` and ``materials_class`` and, when it has to
    deviate, overrides the matching hook below: the selection, lookup and
    instance rules are implemented once here. The source document is taken by
    ``__init__`` and is deliberately not part of the interface.
    """

    scene_class: type[JbSceneABC[JbSourceT, JbMatrixT, JbContainerT, JbObjectT, JbMaterialT]]
    materials_class: type[JbMaterialImporterABC[JbSourceT, JbMaterialT]]

    def __init__(self, source: JbSourceT):
        self.source = source
        self.api = JbAPI()
        self.scene = self.scene_class(source)
        self.materials = self.materials_class(source)
        self._asset_cache: dict[str, AssetModel | None] = {}

    @property
    def logger(self) -> Logger:
        """Logger of the concrete plugin module, so log lines stay traceable."""
        return get_logger(type(self).__module__)

    def import_assets(self) -> None:
        """Imports assets by selection."""
        self._asset_cache = {}
        for asset in self._collect_assets():
            self._import_single(asset)

    def import_message(self) -> str:
        """Return a confirmation message based on the current selection."""
        materials, containers = self._collect_data()
        if materials:
            return (
                "Import assets for materials?\n"
                f"{len(materials)} material(s) with asset info found in selection."
            )
        if containers:
            return (
                "Import assets for asset containers?\n"
                f"{len(containers)} asset container(s) found in selection."
            )
        return "Import active asset from Jiko Bridge."

    def _collect_data(self) -> tuple[list[JbMaterialT], list[JbContainerT]]:
        objects = cast(List[JbObjectT], self.scene.get_selection())
        return (
            self.scene.get_materials_from_objects(objects),
            self.scene.get_containers_from_objects(objects),
        )

    def _collect_assets(self) -> list[AssetModel]:
        assets: list[AssetModel] = []
        materials, containers = self._collect_data()
        if materials:
            for material in materials:
                name = self.materials.get_material_name(material)
                if not name:
                    continue
                asset = self._resolve_asset(name)
                if asset is None:
                    continue
                assets.append(asset)
                if not AssetModel.from_string(name):
                    self.materials.set_material_name(
                        material, f"{asset.pack_name}__{asset.asset_name}"
                    )
        elif containers:
            for container in containers:
                asset = self._asset_from_container(container)
                if asset:
                    assets.append(asset)
        else:
            asset = self.api.get_active_asset()
            if asset:
                assets.append(asset)
        return assets

    def _asset_from_container(self, container: JbContainerT) -> AssetModel | None:
        """Re-read the asset of a container that is about to be imported into."""
        self.scene.clear_container(container)
        asset_model = self.scene.get_asset_data_from_container(container)
        if not asset_model:
            return None
        asset_model.active_type = None
        return self.api.get_asset(asset_model)

    def _import_single(self, asset: AssetModel) -> None:
        for file in asset.files:
            match file.bridge_type:
                case "model":
                    container = self._create_model(asset, file)
                    self._convert_to_instances(container)
                case "material":
                    material = self.materials.import_material(asset, file)
                    if material:
                        self.scene.merge_duplicates_materials(material)
                case _:
                    self.logger.warning("Unsupported bridge type: %s", file.bridge_type)

    def _create_model(self, asset: AssetModel, file: AssetFile) -> JbContainerT:
        container, exists = self.scene.get_or_create_asset_container(asset, file)
        if exists:
            self.scene.create_instance(container, cast(str, asset.asset_name))
        else:
            self.scene.import_with_temp(cast(str, file.filepath), container)
        return container

    def _convert_to_instances(self, container: JbContainerT) -> None:
        queue = [container]
        visited: set[int] = set()
        while queue:
            current = queue.pop(0)
            if id(current) in visited:
                continue
            visited.add(id(current))
            for obj in cast(List[JbObjectT], self.scene.walk([current])):
                asset_model = None
                for name in self.scene.get_names_from_placeholder(obj):
                    asset_model = self._resolve_asset(name)
                    if asset_model:
                        break
                if not asset_model:
                    continue
                asset_container = self._resolve_placeholder(obj, current, asset_model)
                if asset_container:
                    queue.append(asset_container)
            self.scene.cleanup_container(current)

    def _resolve_asset(self, name: str) -> AssetModel | None:
        """Resolve an asset by bundled name or by search, caching misses too."""
        if name in self._asset_cache:
            return self._asset_cache[name]
        query = AssetModel.from_string(name)
        asset = self.api.get_asset(query) if query else self.api.get_asset_by_search(name)
        self._asset_cache[name] = asset
        return asset

    def _resolve_placeholder(
        self, obj: JbObjectT, container: JbContainerT, asset_model: AssetModel
    ) -> JbContainerT | None:
        asset_container = self.scene.get_container(asset_model)
        created = False
        if not asset_container:
            for file in asset_model.files:
                asset_container, exists = self.scene.get_or_create_asset_container(
                    asset_model, file
                )
                if not exists:
                    self.scene.import_with_temp(cast(str, file.filepath), asset_container)
            created = True
        if asset_container is None:
            return None
        instance = self.scene.create_instance(asset_container, cast(str, asset_model.asset_name))
        self.scene.copy_object_transform(instance, obj)
        self.scene.move_objects_to_container([instance], container)
        self.scene.remove_object(obj)
        return asset_container if created else None


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


class JbAssetSoloABC(ABC, Generic[JbSourceT, JbMatrixT, JbContainerT, JbObjectT, JbMaterialT]):
    """Base class for the solo command holding the shared solo workflow.

    The workflow picks the containers to isolate, keeps the history on the
    settings, and leaves only the DCC-specific visibility work to
    ``_apply_solo``.
    """

    scene_class: type[JbSceneABC[JbSourceT, JbMatrixT, JbContainerT, JbObjectT, JbMaterialT]]
    settings_class: type[JbSettingsABC[JbSourceT, JbContainerT]]

    history_size = 5

    def __init__(self, source: JbSourceT):
        self.source = source
        self.scene = self.scene_class(source)

    @property
    def logger(self) -> Logger:
        """Logger of the concrete plugin module, so log lines stay traceable."""
        return get_logger(type(self).__module__)

    def solo(self) -> None:
        """Isolate the selection, or the previous selection when it is empty."""
        containers = self._solo_selection()
        if containers:
            self._apply_solo(containers)

    def _solo_selection(self) -> list[JbContainerT]:
        objects = cast(List[JbObjectT], self.scene.get_selection())
        combine = self.scene.get_containers_from_instances(
            objects
        ) + self.scene.get_containers_from_objects(objects)
        settings = self.settings_class(self.source)
        if combine:
            self._remember(settings, combine)
            return combine
        return self._forget(settings)

    def _remember(
        self, settings: JbSettingsABC[JbSourceT, JbContainerT], containers: list[JbContainerT]
    ) -> None:
        """Push a selection onto the history, ignoring a repeat of the newest entry."""
        entries = settings.load_solo()
        if entries and set(entries[0]) == set(containers):
            return
        settings.save_solo([containers, *entries][: self.history_size])

    def _forget(self, settings: JbSettingsABC[JbSourceT, JbContainerT]) -> list[JbContainerT]:
        """Drop the newest entry and return the one before it."""
        entries = settings.load_solo()
        if len(entries) < 2:
            return []
        settings.save_solo(entries[1:])
        return entries[1]

    @abstractmethod
    def _apply_solo(self, containers: list[JbContainerT]) -> None:
        """Show the given containers and hide everything else."""
