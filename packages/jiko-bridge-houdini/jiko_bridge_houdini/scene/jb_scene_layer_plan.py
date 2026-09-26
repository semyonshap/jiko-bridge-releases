"""Map discovered models to USD prims and cache files without writing to disk."""

import hashlib
import os
import re
from typing import Any

import hou
from jiko_bridge_houdini.jb_types import CONVERTED_EXTENSIONS
from jiko_bridge_houdini.jb_utils import absolute_path
from pxr import Tf

CACHE_ROOT_PRIM = "Asset"
GEOMETRY_PRIM = "geometry"


def cache_file(cache_root: str, metadata: dict[str, Any]) -> str:
    if not cache_root:
        raise hou.NodeError("Set Cache Path before assembling USD layers.")
    names = []
    for key in ("vaultName", "packName", "assetName"):
        value = metadata.get(key, "")
        if not value or value in (".", "..") or re.search('[<>:"/\\\\|?*\\x00-\\x1f]', value):
            raise hou.NodeError(f"Invalid or missing {key} for the cache path: {value!r}")
        if value.endswith((".", " ")):
            raise hou.NodeError(f"Invalid {key} for the cache path: {value!r}")
        names.append(value)
    return os.path.join(cache_root, *names, names[-1] + ".usd").replace("\\", "/")


def prim_name(source: str) -> str:
    """Stable prim name of one source file inside an asset container."""
    source = os.path.normcase(os.path.normpath(source))
    return f"{_base_name(source)}_{hashlib.sha1(source.encode('utf-8')).hexdigest()[:10]}"


def _base_name(source: str) -> str:
    return Tf.MakeValidIdentifier(os.path.splitext(os.path.basename(source))[0])


def model_prim_path(source: str) -> str:
    """Where one file's geometry lives inside its asset container."""
    return f"/{CACHE_ROOT_PRIM}/{GEOMETRY_PRIM}/{prim_name(source)}"


def prototype_path(record: dict[str, Any]) -> str:
    """Prototype holding a USD-sourced asset in the layer that references it."""
    sources = "|".join((entry["source"] for entry in record["files"]))
    digest = hashlib.sha1(sources.encode("utf-8")).hexdigest()[:10]
    name = str(record["asset"].get("assetName") or record["id"])
    return f"/__JikoPrototypes/{Tf.MakeValidIdentifier(name)}_{digest}"


def layer_plan(owner: hou.OpNode, graph: dict[str, Any]) -> dict[str, Any]:
    """Turn the asset graph into cache layers and one container per asset."""
    cache_root = absolute_path(str(owner.evalParm("cache_path")))
    if graph.get("mode") == "cached":
        metadata = {
            "vaultName": owner.evalParm("vault_name"),
            "packName": owner.evalParm("pack_name"),
            "assetName": owner.evalParm("asset_name"),
        }
        path = cache_file(cache_root, metadata)
        if not os.path.isfile(path):
            raise hou.NodeError(f"Cached USD does not exist: {path}")
        return {"mode": "cached", "path": path, "assets": {}, "layers": []}
    assets: dict[str, dict] = {}
    layers: dict[str, dict] = {}
    paths: dict[str, tuple] = {}
    for record in graph["assets"]:
        models: list[dict] = []
        for entry in record["models"]:
            converted = entry["format"] in CONVERTED_EXTENSIONS
            models.append(
                {
                    "id": entry["id"],
                    "record": record,
                    "source": entry["source"],
                    "format": entry["format"],
                    "converted": converted,
                    "file": (
                        cache_file(cache_root, record["asset"])
                        if converted
                        else os.path.abspath(entry["source"]).replace("\\", "/")
                    ),
                    "prim": model_prim_path(entry["source"]),
                }
            )
        if not models:
            continue
        formats = {model["converted"] for model in models}
        if len(formats) > 1:
            raise hou.NodeError(
                "An asset mixes converted and USD model files: "
                + ", ".join((model["source"] for model in models))
            )
        asset = {
            "id": record["id"],
            "record": record,
            "converted": formats.pop(),
            "root": f"/{CACHE_ROOT_PRIM}",
            "prototype": prototype_path(record),
            "models": models,
        }
        assets[record["id"]] = asset
        if not asset["converted"]:
            continue
        path = models[0]["file"]
        key = os.path.normcase(os.path.abspath(path))
        identity = tuple(
            (record["asset"].get(name) for name in ("vaultName", "packName", "assetName"))
        )
        if key in paths and paths[key] != identity:
            raise hou.NodeError(f"Different assets resolve to the same cache file: {path}")
        paths[key] = identity
        layer = layers.setdefault(
            key,
            {
                "path": path,
                "reuse": os.path.isfile(path) and (not owner.evalParm("override")),
                "asset_id": record["id"],
                "record": record,
                "models": [],
            },
        )
        layer["models"].extend(models)
    sources = {
        os.path.normcase(os.path.abspath(model["file"]))
        for asset in assets.values()
        for model in asset["models"]
        if not model["converted"]
    }
    if sources.intersection(layers):
        raise hou.NodeError(
            "A cache destination matches an original USD source. Choose a separate Cache Path."
        )
    return {"mode": "build", "assets": assets, "layers": list(layers.values())}
