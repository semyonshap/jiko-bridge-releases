"""Save the assembled stage through the single USD ROP inside this HDA."""

import os
from typing import cast

import hou
from jiko_bridge_client import get_logger
from jiko_bridge_houdini.jb_utils import absolute_path, cached_asset
from jiko_bridge_houdini.scene.jb_scene_layer_plan import cache_file


def _cache_root(owner: hou.OpNode) -> str:
    path = absolute_path(str(owner.evalParm("cache_path")))
    if not path:
        raise hou.Error("Set Cache Path before saving USD.")
    return path


def scene_output_path(owner: hou.OpNode) -> str:
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
    return '"' + _cache_root(owner).rstrip("/") + '/*"'


def _path_key(path: str) -> str:
    return os.path.normcase(os.path.abspath(hou.text.expandString(path)))


def _inside_cache(path: str, root: str) -> bool:
    try:
        return os.path.commonpath((_path_key(path), _path_key(root))) == _path_key(root)
    except ValueError:
        return False


def save_usd(owner: hou.OpNode) -> str:
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
