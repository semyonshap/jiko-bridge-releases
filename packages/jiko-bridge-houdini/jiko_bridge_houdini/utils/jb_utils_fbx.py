import math
import re
import struct
from typing import BinaryIO, Optional

CM_TO_METERS = 0.01
DEFAULT_UNIT_SCALE_FACTOR = 1.0
DEFAULT_METERS_PER_UNIT = DEFAULT_UNIT_SCALE_FACTOR * CM_TO_METERS


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


def fbx_meters_per_unit(path: str) -> float:
    """Meters per FBX file unit; raises ValueError when the header is unreadable."""
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
        raise ValueError(f"Cannot read FBX units from {path}: {error}") from error
