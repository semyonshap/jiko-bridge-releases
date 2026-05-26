"""
Base scene helper interface for integration tests.
Code by Semyon Shapoval, 2026
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseScene(ABC):
    """Abstract base class for scene helper wrappers used in integration tests."""

    @property
    @abstractmethod
    def source(self) -> Any:
        """Return the current scene or context object."""
        raise NotImplementedError

    @abstractmethod
    def import_module(self, module_name: str) -> Any:
        """Import a module from the target application's plugin package."""
        raise NotImplementedError

    @abstractmethod
    def call_command(self, operator: str) -> Any:
        """Call a Jiko Bridge operator in the current scene context."""
        raise NotImplementedError

    @abstractmethod
    def ensure_loaded(self) -> None:
        """Ensure the target application plugin or addon is loaded."""
        raise NotImplementedError

    @abstractmethod
    def update(self) -> None:
        """Trigger an update or refresh of the scene state."""
        raise NotImplementedError

    @abstractmethod
    def create_scene_object(self, name: str, parent: Optional[Any] = None) -> Any:
        """Create a new object in the scene."""
        raise NotImplementedError

    @abstractmethod
    def create_scene_material(self, name: str) -> Any:
        """Create a new material in the scene."""
        raise NotImplementedError

    @abstractmethod
    def get_all_materials(self) -> list[Any]:
        """Return a list of all materials in the current scene."""
        raise NotImplementedError

    @abstractmethod
    def find_container_by_name(self, name: str) -> Optional[Any]:
        """Find a scene container by name."""
        raise NotImplementedError

    def find_container_by_asset(self, asset: Any) -> Optional[Any]:
        "Find scene container by asset model"
        name = f"Asset_{asset.pack_name}_{asset.asset_name}"
        return self.find_container_by_name(name)

    @abstractmethod
    def find_material_by_name(self, name: str) -> Optional[Any]:
        """Find material in the current scene by name."""
        raise NotImplementedError

    def find_material_by_asset(self, asset: Any) -> Optional[Any]:
        "Find material by asset model"
        name = f"{asset.pack_name}__{asset.asset_name}"
        return self.find_material_by_name(name)

    @abstractmethod
    def select_objects(self, objects: list[Any]) -> None:
        """Select the given objects or collections in the scene."""
        raise NotImplementedError

    @abstractmethod
    def clear_selection(self) -> None:
        """Clear the current selection in the scene."""
        raise NotImplementedError

    @abstractmethod
    def get_hierarchy(self, container: Any) -> dict[str, Optional[str]]:
        """Return a parent map for objects inside the given container."""
        raise NotImplementedError

    @abstractmethod
    def get_instance_objects(self) -> list[Any]:
        """Return instance objects created in the scene."""
        raise NotImplementedError

    @abstractmethod
    def save_document(self, filename: str) -> Optional[str]:
        """Save the current document or scene file."""
        raise NotImplementedError

    @abstractmethod
    def apply_material_to_object(self, obj: Any, material: Any) -> bool:
        """Apply a material to a given scene object."""
        raise NotImplementedError

    @abstractmethod
    def reset_scene(self) -> None:
        """Reset the scene to a clean state."""
        raise NotImplementedError

    @abstractmethod
    def get_children_container(self, container: Any) -> list[Any]:
        """Return a list of child objects for the given container."""
        raise NotImplementedError

    @abstractmethod
    def set_export_format(self, fmt: str) -> None:
        """Set the export format (e.g. 'fbx', 'abc') in the plugin settings."""
        raise NotImplementedError
