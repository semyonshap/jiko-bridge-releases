from typing import Any, Sequence

from jiko_bridge_houdini.jb_types import MODEL_EXTENSIONS, USD_EXTENSIONS, Placeholder
from jiko_bridge_houdini.jb_utils import pack_geometry, source_path
from jiko_bridge_houdini.scene.jb_scene_instance import sop_placeholders, usd_placeholders

"Read FBX file units without loading meshes or requiring the FBX SDK."
import math
import re
import struct
from pathlib import Path
from typing import BinaryIO, Optional

import hou
from jiko_bridge_client import get_logger
from jiko_bridge_houdini.jb_types import JbObject
from jiko_bridge_houdini.scene.jb_scene_temp import JbSceneTemp

CM_TO_METERS = 0.01
DEFAULT_UNIT_SCALE_FACTOR = 1.0
DEFAULT_METERS_PER_UNIT = DEFAULT_UNIT_SCALE_FACTOR * CM_TO_METERS
units_logger = get_logger(__name__)


def _fbx_read(stream: BinaryIO, size: int) -> bytes:
    value = stream.read(size)
    if len(value) != size:
        raise ValueError("Truncated FBX metadata")
    return value


def _fbx_property(stream: BinaryIO):
    kind = _fbx_read(stream, 1)
    formats = {b"Y": "<h", b"C": "<?", b"I": "<i", b"L": "<q", b"F": "<f", b"D": "<d"}
    if kind in formats:
        fmt = formats[kind]
        return struct.unpack(fmt, _fbx_read(stream, struct.calcsize(fmt)))[0]
    if kind == b"S":
        size = struct.unpack("<I", _fbx_read(stream, 4))[0]
        return _fbx_read(stream, size).decode("utf-8")
    raise ValueError("Unsupported FBX unit property")


def _fbx_binary_units(stream: BinaryIO, version: int) -> Optional[float]:
    fmt = "<QQQB" if version >= 7500 else "<IIIB"
    size = struct.calcsize(fmt)
    stream.seek(0, 2)
    file_end = stream.tell()
    stream.seek(27)

    def scan(end: int, parents: tuple[str, ...]) -> Optional[float]:
        while stream.tell() + size <= end:
            stop, count, length, name_size = struct.unpack(fmt, _fbx_read(stream, size))
            if stop == 0:
                return None
            name = _fbx_read(stream, name_size).decode("utf-8")
            property_end = stream.tell() + length
            if not property_end <= stop <= end:
                raise ValueError("Invalid FBX metadata offsets")
            path = parents + (name,)
            if path == ("GlobalSettings", "Properties70", "P") and count:
                if _fbx_property(stream) == "UnitScaleFactor":
                    values = [_fbx_property(stream) for _ in range(count - 1)]
                    return float(values[-1])
            elif path in (("GlobalSettings",), ("GlobalSettings", "Properties70")):
                stream.seek(property_end)
                value = scan(stop, path)
                if value is not None:
                    return value
            stream.seek(stop)
        return None

    return scan(file_end, ())


def fbx_meters_per_unit(path: str) -> Optional[float]:
    """UnitScaleFactor is centimeters per file unit; None when the header is unreadable."""
    try:
        with open(path, "rb") as stream:
            header = stream.read(27)
            if header.startswith(b"Kaydara FBX Binary  \x00\x1a\x00"):
                version = struct.unpack("<I", header[23:27])[0]
                factor = _fbx_binary_units(stream, version)
            else:
                stream.seek(0)
                factor = None
                in_settings = False
                depth = 0
                for raw in stream:
                    line = raw.decode("utf-8", errors="replace")
                    if not in_settings:
                        if not re.match("\\s*GlobalSettings\\s*:", line):
                            continue
                        in_settings = True
                    depth += line.count("{") - line.count("}")
                    match = re.match(
                        '\\s*P\\s*:\\s*"UnitScaleFactor"\\s*,.*?,\\s*([-+0-9.eE]+)\\s*$', line
                    )
                    if match:
                        factor = float(match.group(1))
                        break
                    if depth == 0:
                        break
        factor = DEFAULT_UNIT_SCALE_FACTOR if factor is None else factor
        if not math.isfinite(factor) or factor <= 0:
            raise ValueError("Invalid FBX UnitScaleFactor")
        return factor * CM_TO_METERS
    except (OSError, ValueError, struct.error) as error:
        units_logger.warning("Cannot read FBX units from %s: %s", path, error)
        return None


class JbSceneFile(JbSceneTemp):
    """Houdini implementation of file operations."""

    def import_file(self, file_path: str) -> bool:
        if self._import_target is None:
            raise hou.NodeError("A model import needs an asset container.")
        record = self._import_target.record
        source = source_path(file_path)
        entry = next((item for item in record["files"] if item["source"] == source), None)
        if entry is None:
            entry = {
                "id": f"{record['id']}_f{len(record['files'])}",
                "source": source,
                "format": Path(source).suffix.lower(),
                "bridge_type": "model",
            }
            record["files"].append(entry)
        if entry in record["models"]:
            return True
        found = self._import_model(record, entry)
        known = {obj.data["object"] for obj in self._import_target.objects}
        for placeholder in found:
            if placeholder["object"] not in known:
                self._import_target.objects.append(JbObject(dict(placeholder), self._import_target))
                known.add(placeholder["object"])
        return entry in record["models"]

    def _import_fbx(self, file_path: str) -> bool:
        return self.import_file(file_path)

    def export_file(self, ext):
        self.logger.warning("Houdini file export is not implemented.")
        pass

    def _export_fbx(self, file_path):
        self.logger.warning("Houdini FBX export is not implemented.")
        pass

    def _import_model(self, record: dict[str, Any], entry: dict[str, Any]) -> Sequence[Placeholder]:
        """Import one model file: read its placeholders and pack its geometry."""
        source = entry["source"]
        if entry["format"] not in MODEL_EXTENSIONS:
            self.graph.warnings.append(
                f"Cannot import {source}: {entry['format'] or 'no extension'} is not a model format"
            )
            return []
        record["models"].append(entry)
        if entry["format"] in USD_EXTENSIONS:
            return list(usd_placeholders(source))
        loaded = hou.Geometry()
        loaded.loadFromFile(source)
        found = list(sop_placeholders(loaded, entry["format"]))
        if entry["format"] == ".fbx" and self.graph.convert_units:
            self._convert_units(entry, loaded, found)
        primitive = pack_geometry(self.graph.geometry, loaded)
        primitive.setAttribValue("asset_id", entry["id"])
        primitive.setAttribValue("source", source)
        primitive.setAttribValue("name", record["asset"].get("assetName") or record["id"])
        return found

    def _convert_units(
        self, entry: dict[str, Any], loaded: hou.Geometry, found: Sequence[Placeholder]
    ) -> None:
        """Scale an FBX source and its placements from file units to meters."""
        source = entry["source"]
        units = fbx_meters_per_unit(source)
        if units is None:
            units = DEFAULT_METERS_PER_UNIT
            self.graph.warnings.append(
                f"Cannot read FBX units from {source}, assuming {units} meters per unit"
            )
        entry["meters_per_source_unit"] = units
        if units == 1.0:
            return
        loaded.transform(hou.hmath.buildScale(units, units, units))
        for placeholder in found:
            matrix = placeholder["transform"]
            if matrix is not None:
                matrix[12:15] = [value * units for value in matrix[12:15]]
