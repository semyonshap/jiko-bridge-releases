import json
import math
from typing import Any, Iterator, Sequence, cast

import hou
from jiko_bridge_houdini.jb_types import JbObject, Placeholder
from jiko_bridge_houdini.jb_utils import (
    add_string_attribs,
    group_prims,
    node_geometry,
    prim_matrix,
    prim_strings,
    set_global_attrib,
)
from jiko_bridge_houdini.jb_vex import ABC_VEX, FBX_VEX, PLACEHOLDER_GROUP, run_vex
from jiko_bridge_houdini.scene.jb_scene_container import JbSceneContainer
from pxr import Tf, Usd, UsdGeom

MARKERS = {".abc": ABC_VEX, ".fbx": FBX_VEX}


def sop_placeholders(geometry: hou.Geometry, extension: str) -> Iterator[Placeholder]:
    """Read the placeholders the marker of a source format collected."""
    marker = MARKERS.get(extension)
    if marker is None:
        raise hou.NodeError(f"Cannot read placeholders from a {extension} source.")
    marked = run_vex(geometry, marker, run_over="prim")
    for primitive in group_prims(marked, PLACEHOLDER_GROUP):
        transform = prim_matrix(primitive, "jiko_transform")
        names = prim_strings(primitive, "jiko_names")
        yield {
            "object": f"/{primitive.number()}",
            "names": names,
            "transform": list(transform.asTuple()) if transform is not None else None,
        }


def usd_placeholders(path: str) -> Iterator[Placeholder]:
    """Read square placeholder prims from a USD asset file."""
    stage = Usd.Stage.Open(path)
    if stage is None:
        raise hou.NodeError(f"Cannot open USD asset: {path}")
    time = Usd.TimeCode(hou.frame() * stage.GetTimeCodesPerSecond() / hou.fps())
    transforms = UsdGeom.XformCache(time)
    for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
        if not prim.IsA(cast(Tf.Type, UsdGeom.Mesh)):
            continue
        mesh = UsdGeom.Mesh(prim)
        points = mesh.GetPointsAttr().Get(time)
        counts = mesh.GetFaceVertexCountsAttr().Get(time)
        indices = mesh.GetFaceVertexIndicesAttr().Get(time)
        if points is None or len(points) != 4 or list(counts or []) != [4]:
            continue
        if len(set(indices or [])) != 4:
            continue
        transform = transforms.GetLocalToWorldTransform(prim)
        yield {
            "object": str(prim.GetPath()),
            "names": [prim.GetPath().name],
            "transform": [
                float(cast(Sequence[float], transform.GetRow(row))[col])
                for row in range(4)
                for col in range(4)
            ],
        }


def plan_instances(graph: dict[str, Any]) -> None:
    """Remove a source object only if all of its replacements can be placed."""
    for asset in graph["assets"]:
        objects: dict[str, list] = {}
        for instance in asset["instances"]:
            objects.setdefault(instance["object"], []).append(instance)
        asset["remove_objects"] = []
        for location, instances in objects.items():
            ready = True
            for instance in instances:
                matrix = instance.get("transform")
                valid = (
                    matrix is not None
                    and len(matrix) == 16
                    and all((math.isfinite(value) for value in matrix))
                )
                if not valid:
                    label = asset["asset"].get("assetName") or asset["id"]
                    graph["warnings"].append(
                        f"No exact transform for {location} in {label}; placeholder retained."
                    )
                ready = ready and valid and (not instance["cycle"])
            for instance in instances:
                instance["replace"] = ready
            if ready:
                asset["remove_objects"].append(location)


def instance_points(sop: hou.SopNode) -> None:
    """Write one point per replaceable instance into the output SOP."""
    input_node = sop.inputs()[0]
    if input_node is None:
        raise hou.NodeError("Connect the graph SOP to this node.")
    input_geometry = node_geometry(input_node)
    graph = json.loads(str(input_geometry.attribValue("jiko_graph")))
    output = node_geometry(sop)
    output.clear()
    add_string_attribs(
        output, hou.attribType.Point, ("source_asset", "target_asset", "source_object")
    )
    output.addAttrib(hou.attribType.Point, "transform", hou.Matrix4(1).asTuple())
    for asset in graph["assets"]:
        for instance in asset["instances"]:
            if not instance["replace"]:
                continue
            matrix = hou.Matrix4(instance["transform"])
            point = output.createPoint()
            point.setPosition(cast(Sequence[float], hou.Vector3(0, 0, 0) * matrix))
            point.setAttribValue("transform", matrix.asTuple())
            point.setAttribValue("source_asset", asset["id"])
            point.setAttribValue("target_asset", instance["target"])
            point.setAttribValue("source_object", instance["object"])
    set_global_attrib(output, "jiko_graph", json.dumps(graph, ensure_ascii=False))


class JbSceneInstance(JbSceneContainer):
    """Houdini implementation of instance operations."""

    def get_names_from_placeholder(self, obj) -> list[str]:
        if not isinstance(obj, JbObject) or obj.target is not None:
            return []
        return list(obj.data.get("names", []))

    def create_instance(self, container, name) -> JbObject:
        return JbObject(
            {"name": name, "target": container.record["id"], "cycle": False}, target=container
        )

    def replace_instances_with_placeholders(self, objects, source):
        self.logger.warning("Houdini placeholder export is not implemented.")

    def create_placeholder(self, asset_model, transform, source):
        self.logger.warning("Houdini placeholder export is not implemented.")
