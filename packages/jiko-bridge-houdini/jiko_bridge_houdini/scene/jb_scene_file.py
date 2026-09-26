"""Houdini file operations: model parsing, layer paths and the cached scene."""

import math
import os
import re
import struct
from pathlib import Path
from typing import Any, BinaryIO, Optional, Sequence, cast

import hou
from jiko_bridge_client import get_logger
from jiko_bridge_houdini.jb_types import (
    MODEL_EXTENSIONS,
    USD_EXTENSIONS,
    JbModel,
    JbObject,
    Placeholder,
)
from jiko_bridge_houdini.jb_utils import absolute_path, cached_asset, source_path
from jiko_bridge_houdini.scene.jb_scene_container import asset_root, layer_name, prim_name
from jiko_bridge_houdini.scene.jb_scene_instance import stage_placeholders
from jiko_bridge_houdini.scene.jb_scene_temp import JbSceneTemp, cache_file, geometry_stage
from pxr import Usd

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


def _cache_root(owner: hou.OpNode) -> str:
    path = absolute_path(str(owner.evalParm("cache_path")))
    if not path:
        raise hou.Error("Set Cache Path before saving USD.")
    return path


def scene_output_path(owner: hou.OpNode) -> str:
    """Path of the assembled scene USD for the selected asset."""
    if not owner.evalParm("asset_name"):
        return ""
    metadata = {
        "vaultName": owner.evalParm("vault_name"),
        "packName": owner.evalParm("pack_name"),
        "assetName": owner.evalParm("asset_name"),
    }
    asset_path = cache_file(_cache_root(owner), metadata)
    return os.path.splitext(asset_path)[0] + ".scene.usd"


def cache_save_pattern(owner: hou.OpNode) -> str:
    """Glob pattern matching every cached asset file."""
    return '"' + _cache_root(owner).rstrip("/") + '/*"'


def asset_layer(owner: hou.OpNode) -> dict[str, Any] | None:
    """Layer file, prim name and root prim of the asset this node holds."""
    cache_root = absolute_path(str(owner.evalParm("cache_path")))
    asset = {
        "vaultName": owner.evalParm("vault_name"),
        "packName": owner.evalParm("pack_name"),
        "assetName": owner.evalParm("asset_name"),
    }
    if not (cache_root and asset["packName"] and asset["assetName"]):
        return None
    path = cache_file(cache_root, asset)
    if not os.path.isfile(path):
        return None
    return {
        "name": layer_name("", asset),
        "path": path,
        "root": asset_root("", asset),
    }


def layer_plan(owner: hou.OpNode) -> str | None:
    """Path of the cached scene this node assembles, when it works from cache."""
    cache_root = absolute_path(str(owner.evalParm("cache_path")))
    metadata = {
        "vaultName": owner.evalParm("vault_name"),
        "packName": owner.evalParm("pack_name"),
        "assetName": owner.evalParm("asset_name"),
    }
    path = cache_file(cache_root, metadata)
    if not os.path.isfile(path):
        raise hou.NodeError(f"Cached USD does not exist: {path}")
    return path


def _path_key(path: str) -> str:
    return os.path.normcase(os.path.abspath(hou.text.expandString(path)))


def _inside_cache(path: str, root: str) -> bool:
    try:
        return os.path.commonpath((_path_key(path), _path_key(root))) == _path_key(root)
    except ValueError:
        return False


def save_usd(owner: hou.OpNode) -> str:
    """Assemble the stage and write it through the HDA's USD ROP."""
    output = scene_output_path(owner)
    if not output or (not owner.evalParm("cached") and (not cached_asset(owner).files)):
        raise hou.Error("Select an asset before saving USD.")
    root = _cache_root(owner)
    override = bool(owner.evalParm("override"))
    if os.path.isfile(output) and (not override):
        raise hou.Error(f"Scene already exists. Enable Override to overwrite it:\n{output}")
    assembly = cast(hou.LopNode, owner.node("assemble_usd"))
    rop = owner.node("usd_rop")
    if assembly is None or rop is None:
        raise hou.Error("Rebuild the HDA to add the USD assembly and USD ROP nodes.")
    assembly.cook(force=True)
    stage = assembly.stage()
    if stage is None or assembly.errors():
        raise hou.Error("USD assembly failed:\n" + "\n".join(assembly.errors()))
    if not stage.GetPrimAtPath("/World"):
        raise hou.Error("The assembled stage has no /World primitive to save.")
    paths = {_path_key(output): output}
    for layer in stage.GetUsedLayers():
        if layer.realPath and _path_key(layer.realPath) == _path_key(output):
            raise hou.Error(f"The scene output is also a referenced source file:\n{output}")
        info = layer.GetPrimAtPath("/HoudiniLayerInfo")
        path = info.customData.get("HoudiniSavePath") if info else None
        if not path:
            continue
        path = hou.text.expandString(path)
        if not _inside_cache(path, root):
            continue
        if _path_key(path) == _path_key(output):
            raise hou.Error(f"Scene output collides with an asset layer:\n{output}")
        if os.path.isfile(path) and (not override):
            raise hou.Error(
                f"A writable cache layer already exists. Import or enable Override:\n{path}"
            )
        paths[_path_key(path)] = path
    for path in paths.values():
        os.makedirs(os.path.dirname(path), exist_ok=True)
    cast(hou.Parm, rop.parm("execute")).pressButton()
    if rop.errors():
        raise hou.Error("USD save failed:\n" + "\n".join(rop.errors()))
    missing = [path for path in paths.values() if not os.path.isfile(path)]
    if missing:
        raise hou.Error("USD ROP did not write these files:\n" + "\n".join(missing))
    get_logger(__name__).info("Saved USD scene: %s", output)
    return output


class JbSceneFile(JbSceneTemp):
    """Houdini implementation of file operations."""

    def import_file(self, file_path: str) -> bool:
        """Parse one model file into the container that is being imported."""
        container = self._import_target
        if container is None:
            raise hou.NodeError("A model import needs an asset container.")
        source = source_path(file_path)
        if self.stage.has_model(container, source):
            return True
        model = self._read_model(source)
        if model is None:
            return False
        container.models[source] = model
        known = {obj.data["object"] for obj in container.pending}
        for placeholder in model.placeholders:
            if placeholder["object"] not in known:
                container.pending.append(JbObject(dict(placeholder), container))
                known.add(placeholder["object"])
        return True

    def _import_fbx(self, file_path: str) -> bool:
        """Import one FBX source through the common model path."""
        return self.import_file(file_path)

    def export_file(self, _ext):
        """Houdini has no asset export yet."""
        self.logger.warning("Houdini file export is not implemented.")

    def _export_fbx(self, _file_path):
        """Houdini has no FBX export yet."""
        self.logger.warning("Houdini FBX export is not implemented.")

    def _read_model(self, source: str) -> JbModel | None:
        """Parse one model file: its geometry when converted, its placeholders."""
        suffix = Path(source).suffix.lower()
        if suffix not in MODEL_EXTENSIONS:
            self.warnings.append(
                f"Cannot import {source}: {suffix or 'no extension'} is not a model format"
            )
            return None
        if suffix in USD_EXTENSIONS:
            stage = Usd.Stage.Open(source)
            if stage is None:
                self.warnings.append(f"Cannot open USD source: {source}")
                return None
            return JbModel(source, None, list(stage_placeholders(stage)))
        loaded = hou.Geometry()
        loaded.loadFromFile(source)
        units = (
            self._convert_units(source, loaded) if self.convert_units and suffix == ".fbx" else 1.0
        )
        with geometry_stage(prim_name(source), loaded) as converted:
            found: list[Placeholder] = list(stage_placeholders(converted))
        self._scale_placeholders(found, units)
        return JbModel(source, loaded, found)

    def _convert_units(self, source: str, loaded: hou.Geometry) -> float:
        """Scale an FBX source from file units to meters and return the factor."""
        units = fbx_meters_per_unit(source)
        if units is None:
            units = DEFAULT_METERS_PER_UNIT
            self.warnings.append(
                f"Cannot read FBX units from {source}, assuming {units} meters per unit"
            )
        if units != 1.0:
            loaded.transform(hou.hmath.buildScale(units, units, units))
        return units

    @staticmethod
    def _scale_placeholders(found: Sequence[Placeholder], units: float) -> None:
        """Scale the placement of the placeholders, which the geometry transform skips."""
        if units == 1.0:
            return
        for placeholder in found:
            matrix = placeholder["transform"]
            if matrix is not None:
                matrix[12:15] = [value * units for value in matrix[12:15]]
