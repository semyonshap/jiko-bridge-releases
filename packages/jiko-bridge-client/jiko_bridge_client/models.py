"""
Data models shared by every Jiko Bridge integration.
Code by Semyon Shapoval, 2026
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict


@dataclass
class AssetFile:
    """Represents a file associated with an asset."""

    filepath: Optional[str] = None
    asset_type: Optional[str] = None
    bridge_type: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "AssetFile":
        """Create an AssetFile instance from a dictionary."""
        return cls(
            filepath=data.get("filepath", None),
            asset_type=data.get("assetType", None),
            bridge_type=data.get("bridgeType", None),
        )

    def to_dict(self) -> dict:
        """Convert the AssetFile instance to a dictionary."""
        result: Dict[str, Any] = {}
        if self.filepath:
            result["filepath"] = self.filepath
        if self.asset_type:
            result["assetType"] = self.asset_type
        if self.bridge_type:
            result["bridgeType"] = self.bridge_type

        return result


@dataclass
class AssetModel:
    """Represents a complete asset with its metadata and associated files."""

    vault_name: Optional[str] = None
    pack_name: Optional[str] = None
    asset_name: Optional[str] = None
    active_type: Optional[str] = None
    files: List[AssetFile] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash((self.vault_name, self.pack_name, self.asset_name))

    @classmethod
    def from_string(cls, value: str) -> Optional["AssetModel"]:
        """Parse packName / assetName from a placeholder object/tag name."""
        normalized = re.sub(r"\.\d+$", "", value)
        pattern = re.compile(r"(?P<pack>.+?)__(?P<asset>.+?)$")
        m = pattern.match(normalized)
        if m:
            return cls(
                pack_name=m.group("pack"),
                asset_name=m.group("asset"),
            )
        return None

    @classmethod
    def from_container_fields(
        cls,
        pack_name: Optional[str],
        asset_name: Optional[str],
        active_type: Optional[str] = None,
        vault_name: Optional[str] = None,
    ) -> Optional["AssetModel"]:
        """Build an asset from the fields a container stores, or None if incomplete."""
        if not (pack_name and asset_name):
            return None
        return cls(
            pack_name=pack_name,
            asset_name=asset_name,
            active_type=active_type,
            vault_name=vault_name,
        )

    @classmethod
    def from_dict(cls, data: dict) -> "AssetModel":
        """Create an AssetModel instance from a dictionary."""
        return cls(
            vault_name=data.get("vaultName"),
            pack_name=data.get("packName"),
            asset_name=data.get("assetName"),
            files=[AssetFile.from_dict(f) for f in data.get("files", [])],
        )

    def to_dict(self) -> dict:
        """Convert the AssetModel instance to a dictionary."""
        result: Dict[str, Any] = {}

        files = list(self.files)
        if self.active_type:
            files.append(AssetFile(asset_type=self.active_type))

        if self.vault_name:
            result["vaultName"] = self.vault_name
        if self.pack_name:
            result["packName"] = self.pack_name
        if self.asset_name:
            result["assetName"] = self.asset_name
        if files:
            result["files"] = [f.to_dict() for f in files]
        return result


class JbPlaceholderInfo(TypedDict):
    """Represents information about a placeholder object."""

    asset: AssetModel
    transform: Any
