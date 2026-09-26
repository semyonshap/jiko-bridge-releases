"""The discovery SOP: run the asset importer and publish the graph."""

import json
from typing import Any

import hou
from jiko_bridge_houdini.commands.jb_asset_importer import JbAssetImporter
from jiko_bridge_houdini.jb_commands import JbCommands
from jiko_bridge_houdini.jb_utils import (
    add_string_attribs,
    cached_asset,
    node_geometry,
    set_global_attrib,
)
from jiko_bridge_houdini.scene.jb_scene_instance import plan_instances


def discover_assets(sop: hou.SopNode, owner: hou.OpNode) -> None:
    """Expose the imported asset graph as JSON on the OUT_GRAPH detail geometry."""
    geometry = node_geometry(sop)
    add_string_attribs(geometry, hou.attribType.Prim, ("asset_id", "source", "name"))
    graph: dict[str, Any] = {"version": 1, "roots": [], "assets": [], "warnings": []}
    asset = cached_asset(owner)
    if owner.evalParm("cached"):
        graph["mode"] = "cached"
        graph["cache_root"] = owner.evalParm("cache_path")
        graph["asset"] = {
            "vault_name": asset.vault_name,
            "pack_name": asset.pack_name,
            "asset_name": asset.asset_name,
        }
    elif asset.files:
        importer = JbAssetImporter(owner)
        with hou.InterruptableOperation("Import Jiko Bridge assets"):
            graph = importer.build_graph(geometry)
        plan_instances(graph)
    set_global_attrib(geometry, "jiko_graph", json.dumps(graph, ensure_ascii=False))
    if graph["warnings"]:
        raise hou.NodeWarning("\n".join(graph["warnings"][:20]))


def active_asset(node: hou.OpNode) -> None:
    """HDA Active button callback."""
    JbCommands(node).active_asset()


def import_asset(node: hou.OpNode) -> None:
    """HDA Import button callback."""
    JbCommands(node).import_asset()
