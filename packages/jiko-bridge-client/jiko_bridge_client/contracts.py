from abc import ABC, abstractmethod
from contextlib import contextmanager
from logging import Logger
from typing import Any, Generator, Generic, List, Optional, TypeVar

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
    def __init__(self, source: JbSourceT) -> None: ...

    @property
    @abstractmethod
    def source(self) -> JbSourceT:
        """Return the source scene."""

    @property
    def logger(self) -> Logger:
        """Return the logger instance."""
        return get_logger(type(self).__module__)

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
    def remove_object(self, obj: JbObjectT) -> None:
        """Remove the given object from the scene."""

    @abstractmethod
    def get_depth(self, obj: JbObjectT | JbContainerT | JbMaterialT) -> int:
        """Return the depth of the given object in the hierarchy."""

    @abstractmethod
    def merge_duplicates_materials(self, material: JbMaterialT) -> None:
        """Replace duplicate materials (.001, .002, ...) with the given base material."""

    def set_container_visibility(self, container: JbContainerT, visible: bool | None) -> None:
        """Show, hide or release one container; None lets it inherit from its parent.

        The default leaves the scene as it is.
        """

    def apply_solo(self, containers: list[JbContainerT]) -> None:
        """Show the given containers and hide every other one of the scene.

        The default leaves the scene as it is.
        """

    # ------------------------------------------------------------------
    # Container
    # ------------------------------------------------------------------

    def container_key(self, container: JbContainerT) -> str:
        """Stable key of one container, unique inside the scene."""
        return str(id(container))

    @staticmethod
    def container_name(asset: AssetModel) -> str:
        """Name the scene gives to the container that holds the contents of an asset."""
        return f"Asset_{asset.pack_name}_{asset.asset_name}"

    @abstractmethod
    def get_container(self, asset: AssetModel) -> Optional[JbContainerT]:
        """Get the container of the given asset, once it already holds its model."""

    @abstractmethod
    def create_container(
        self,
        asset: AssetModel,
        file: Optional[AssetFile] = None,
    ) -> JbContainerT:
        """Create the container of the given asset and store its asset data."""

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
    def create_instance(
        self,
        container: JbContainerT,
        name: str,
        parent: Optional[JbContainerT] = None,
        source: Optional[JbObjectT] = None,
    ) -> Optional[JbObjectT]:
        """Create an instance of an asset container, placed under the given parent."""

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

    @contextmanager
    @abstractmethod
    def temp_source(self) -> Generator[Any, None, None]:
        """Context manager for the isolated scene the import works in."""
        yield

    # ------------------------------------------------------------------
    # Scene (high-level)
    # ------------------------------------------------------------------

    @abstractmethod
    def import_with_temp(self, file_path: str, target: JbContainerT) -> None:
        """Import a file into an isolated scene, then copy to target collection."""

    def finish_asset(self, container: JbContainerT) -> None:
        """Persist the work of one asset once it is fully imported.

        Called by the shared import workflow after every file of an asset and
        its placeholders have been resolved, so a scene can flush what it keeps
        in memory per asset instead of once per session. The default keeps the
        scene in memory and does nothing.
        """

    _messages: list[str]

    @property
    def messages(self) -> list[str]:
        """Everything the last import left unresolved, oldest first."""
        if not hasattr(self, "_messages"):
            self._messages = []
        return self._messages

    def message(self, text: str) -> None:
        """Record one thing this session could not resolve."""
        self.messages.append(text)

    def report(self) -> str:
        """Everything the last import left unresolved, one line per item."""
        return "\n".join(self.messages)

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
