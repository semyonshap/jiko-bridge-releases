"""
Types Jiko Bridge
Code by Semyon Shapoval, 2026
"""

from dataclasses import dataclass, field
import re
from typing import Any, List, Optional


import c4d

JbSource = c4d.documents.BaseDocument
JbMatrix = c4d.Matrix

JbContainer = c4d.BaseObject
JbObject = c4d.BaseObject
JbMaterial = c4d.BaseMaterial

JbData = JbContainer | JbObject | JbMaterial


@dataclass
class AssetFile:
    """Represents a file associated with an asset."""

    filepath: Optional[str] = None
    asset_type: Optional[str] = None
    bridge_type: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict):
        """Create an AssetFile instance from a dictionary."""
        return cls(
            filepath=data.get("filepath", None),
            asset_type=data.get("assetType", None),
            bridge_type=data.get("bridgeType", None),
        )

    def to_dict(self) -> dict:
        """Convert the AssetFile instance to a dictionary."""
        result: dict[str, Any] = {}
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

    database_name: Optional[str] = None
    pack_name: Optional[str] = None
    asset_name: Optional[str] = None
    active_type: Optional[str] = None
    files: List[AssetFile] = field(default_factory=list)

    def __hash__(self):
        return hash((self.database_name, self.pack_name, self.asset_name))

    @classmethod
    def from_string(cls, value: str):
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
    def from_dict(cls, data: dict):
        """Create an AssetModel instance from a dictionary."""
        return cls(
            database_name=data.get("databaseName"),
            pack_name=data.get("packName"),
            asset_name=data.get("assetName"),
            files=[AssetFile.from_dict(f) for f in data.get("files", [])],
        )

    def to_dict(self) -> dict:
        """Convert the AssetModel instance to a dictionary."""
        result: dict[str, Any] = {}

        files = list(self.files)
        if self.active_type:
            files.append(AssetFile(asset_type=self.active_type))

        if self.database_name:
            result["databaseName"] = self.database_name
        if self.pack_name:
            result["packName"] = self.pack_name
        if self.asset_name:
            result["assetName"] = self.asset_name
        if files:
            result["files"] = [f.to_dict() for f in files]
        return result
