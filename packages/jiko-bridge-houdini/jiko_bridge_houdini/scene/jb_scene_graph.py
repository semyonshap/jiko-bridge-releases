from pathlib import Path
from typing import Any

import hou
from jiko_bridge_client import AssetModel


class JbSceneGraph:
    """Import every file of an asset and follow its placeholders to other assets."""

    def __init__(self, geometry: hou.Geometry, convert_units: bool) -> None:
        self.geometry = geometry
        self.convert_units = convert_units
        self.records: dict[tuple[Any, ...], dict[str, Any]] = {}
        self.edges: dict[str, set[str]] = {}
        self.warnings: list[str] = []

    def register(self, asset: AssetModel) -> dict[str, Any]:
        """One record per asset; every file of it is imported inside the record."""
        key = self._key(asset)
        if key not in self.records:
            identifier = f"asset_{len(self.records)}"
            record = {
                "id": identifier,
                "asset": asset.to_dict(),
                "files": [
                    {
                        "id": f"{identifier}_f{index}",
                        "source": hou.text.expandString(str(file.filepath)).replace("\\", "/"),
                        "format": Path(file.filepath).suffix.lower(),
                        "bridge_type": file.bridge_type,
                    }
                    for index, file in enumerate(asset.files)
                    if file.filepath
                ],
                "models": [],
                "instances": [],
                "unresolved": [],
            }
            self.records[key] = record
            self.edges[identifier] = set()
        return self.records[key]

    def _key(self, asset: AssetModel) -> tuple[Any, ...]:
        """Assets are identified by name; a nameless one by the set of its files."""
        names = (asset.vault_name, asset.pack_name, asset.asset_name)
        if any(names):
            return names
        return (*names, tuple(sorted((str(file.filepath) for file in asset.files))))

    def is_cycle(self, parent: str, target: str) -> bool:
        """Whether an edge from parent to target would close a dependency circle."""
        pending, seen = ([target], set())
        while pending:
            current = pending.pop()
            if current == parent:
                return True
            if current not in seen:
                seen.add(current)
                pending.extend(self.edges[current])
        return False
