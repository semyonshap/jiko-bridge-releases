"""
Universal protocol for Jiko Bridge.
Code by Semyon Shapoval, 2026
"""

from abc import ABC, abstractmethod
from logging import Logger
from typing import Protocol, Generator, Optional, TypedDict, List

from .jb_types import (
    AssetFile,
    AssetModel,
    JbData,
    JbContainer,
    JbMaterial,
    JbMatrix,
    JbObject,
    JbSource,
)


class JbPlaceholderInfo(TypedDict):
    """Represents information about a placeholder object."""

    asset: AssetModel
    transform: JbMatrix


class JbSceneABC(ABC):  # pylint: disable=too-many-public-methods
    """Abstract base class for all Jiko Bridge scene operations."""

    # ------------------------------------------------------------------
    # Base
    # ------------------------------------------------------------------

    @abstractmethod
    def __init__(self, source: JbSource): ...

    @property
    @abstractmethod
    def source(self) -> JbSource:
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
        root: list[JbData],
    ) -> list[JbData]:
        """Call *fn* for every object in the root hierarchy (pre-order)."""

    @abstractmethod
    def get_materials_from_objects(self, objects: list[JbObject]) -> list[JbMaterial]:
        """Return materials used by the given objects."""

    @abstractmethod
    def get_selection(self) -> list[JbData]:
        """Return the currently selected objects or materials."""

    @abstractmethod
    def copy_object_transform(self, obj: JbObject, target_obj: JbObject) -> None:
        """Set the transform of the given object."""

    @abstractmethod
    def remove_object(self, obj: JbObject) -> None:
        """Remove the given object from the scene."""

    @abstractmethod
    def get_depth(self, obj: JbData) -> int:
        """Return the depth of the given object in the hierarchy."""

    @abstractmethod
    def merge_duplicates_materials(self, material: JbMaterial) -> None:
        """Replace duplicate materials (.001, .002, ...) with the given base material."""

    # ------------------------------------------------------------------
    # Container
    # ------------------------------------------------------------------

    @abstractmethod
    def get_container(self, asset: AssetModel) -> Optional[JbContainer]:
        """Get the container associated with the given asset, if it exists."""

    @abstractmethod
    def get_or_create_container(
        self, name: str, parent: Optional[JbContainer] = None
    ) -> JbContainer:
        """Get or create a container with the given name under the parent."""

    @abstractmethod
    def get_or_create_asset_container(
        self,
        asset: AssetModel,
        file: Optional[AssetFile] = None,
    ) -> tuple[JbContainer, bool]:
        """Get or create a container with asset data."""

    @abstractmethod
    def set_asset_data(
        self, container: JbContainer, asset: AssetModel, file: Optional[AssetFile] = None
    ) -> None:
        """Store asset info in the container's custom properties."""

    @abstractmethod
    def get_asset_data_from_container(self, container: JbContainer) -> Optional[AssetModel]:
        """Parse asset info from a container's custom properties."""

    @abstractmethod
    def copy_asset_data(self, src: JbContainer, dst: JbContainer | JbObject) -> None:
        """Copy custom properties from src to dst."""

    @abstractmethod
    def get_containers_from_objects(self, objects: list[JbObject]) -> list[JbContainer]:
        """Return asset containers found among the given objects (via instance Empties)."""

    @abstractmethod
    def get_containers_from_instances(self, objects: list[JbObject]) -> list[JbContainer]:
        """Return asset containers found among the given instances."""

    @abstractmethod
    def move_objects_to_container(self, objects: list[JbObject], container: JbContainer) -> None:
        """Move objects into target collection."""

    @abstractmethod
    def cleanup_container(self, container: JbContainer) -> None:
        """Remove empty objects that have no children and no data."""

    @abstractmethod
    def clear_container(self, container: JbContainer) -> None:
        """Remove all objects from the container."""

    @abstractmethod
    def get_children(self, obj: JbObject | JbContainer) -> list[JbObject | JbContainer]:
        """Return the children of the given object or container."""

    # ------------------------------------------------------------------
    # Instance
    # ------------------------------------------------------------------

    @abstractmethod
    def create_instance(self, container: JbContainer, name: str) -> JbObject:
        """Create an instance of the given object."""

    @abstractmethod
    def get_names_from_placeholder(self, obj: JbObject) -> List[str]:
        """Extract placeholder info from objects and remove them."""

    @abstractmethod
    def replace_instances_with_placeholders(
        self, objects: list[JbObject], source: JbSource
    ) -> list[JbObject]:
        """Replace instances in the list with placeholders."""

    @abstractmethod
    def create_placeholder(
        self,
        asset_model: AssetModel,
        transform: JbMatrix,
        source: JbSource,
    ) -> JbObject:
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
        objects: Optional[list[JbObject | JbContainer]] = None,
        unit_scale: float | int = 1.0,
        debug: bool = False,
    ) -> Generator[JbSource, None, None]:
        """Context manager for temporary scenes."""

    # ------------------------------------------------------------------
    # Scene (high-level)
    # ------------------------------------------------------------------

    @abstractmethod
    def import_with_temp(self, file_path: str, target: JbContainer) -> None:
        """Import a file into an isolated scene, then copy to target collection."""

    @abstractmethod
    def export_with_temp(
        self,
        src: list[JbObject | JbContainer],
        ext: str,
    ) -> Optional[str]:
        """Copy objects to isolated scene, replace instances, export."""

    @abstractmethod
    def get_project_filepath(self) -> Optional[str]:
        """Return the current project filepath, if it exists."""

    @abstractmethod
    def solo(self):
        """Solo mode with history"""


class JbMaterialImporterABC(ABC):
    """Abstract base class for Material Importers."""

    @abstractmethod
    def get_material_name(self, material: JbMaterial) -> str | None:
        """Get the name of a material."""

    @abstractmethod
    def set_material_name(self, material: JbMaterial, name: str):
        """Set the name of a material."""

    @abstractmethod
    def import_material(self, asset: AssetModel, file: AssetFile) -> Optional[JbMaterial]:
        """Import a single material file into the scene."""


class JbSettingsABC(ABC):
    """Abstract base class for per-scene settings storage."""

    @abstractmethod
    def get_export_format(self) -> str:
        """Return the current export format (e.g. 'fbx', 'abc')."""

    @abstractmethod
    def load_solo_stack(self) -> list[list]:
        """Return the full solo-mode history as a list of container lists."""

    @abstractmethod
    def save_solo_selection(self, containers: list[JbContainer]) -> None:
        """Push a new solo selection onto the history stack.

        No-op if the selection is identical to the most recent entry.
        """

    @abstractmethod
    def pop_solo_selection(self) -> list:
        """Remove the current selection and return the previous one.

        Returns an empty list if there is no previous entry.
        """


# Asset Protocols


class JbAssetImporterProtocol(Protocol):
    """Protocol for Asset Importers."""

    def __init__(self, _source: JbSource): ...
    def import_assets(self) -> None:
        """Imports assets by selection."""

    def import_message(self) -> str:
        """Return a confirmation message based on the current selection."""

    def _collect_data(self) -> tuple[list[JbMaterial], list[JbContainer]]: ...
    def _collect_assets(self) -> list[AssetModel]: ...
    def _import_single(self, asset: AssetModel) -> None: ...
    def _create_model(self, asset: AssetModel, file: AssetFile) -> JbContainer: ...
    def _convert_to_instances(self, container: JbContainer) -> None: ...
    def _resolve_placeholder(
        self, obj: JbObject, container: JbContainer, asset_model: AssetModel
    ) -> JbContainer | None: ...


class JbAssetExporterProtocol(Protocol):
    """Protocol for Asset Exporters."""

    def __init__(self, source: JbSource): ...
    def export_asset(self) -> None:
        """Exports an asset from the scene into Jiko Bridge."""

    def export_message(self) -> str:
        """Return a confirmation message based on the current selection and asset containers."""

    def _collect_data(
        self,
    ) -> tuple[list[JbContainer | JbObject | JbMaterial], list[JbContainer]]: ...
    def _update_asset(self, container: JbContainer) -> None: ...
    def _create_new_asset(self, objects: list[JbObject]) -> None: ...


class JbAPIProtocol(Protocol):
    """Protocol for Jiko Bridge API interactions."""

    def get_active_asset(self) -> Optional[AssetModel]:
        """Get the currently active asset based on selection or context."""

    def get_asset_by_search(self, search_key: str) -> Optional[AssetModel]:
        """Search for an Asset by a free-form key."""

    def get_asset(self, asset: AssetModel) -> Optional[AssetModel]:
        """Get Asset by an AssetModel object."""

    def create_asset(self, asset: AssetModel) -> Optional[AssetModel]:
        """Create a new Asset with the given files and optional metadata."""

    def update_asset(self, asset: AssetModel) -> Optional[AssetModel]:
        """Update an existing Asset's files and metadata."""
