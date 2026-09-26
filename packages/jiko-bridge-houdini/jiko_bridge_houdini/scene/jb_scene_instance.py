"""Houdini instance operations: placeholders read from USD, and their prims."""

import hashlib
import math
from typing import Any, Iterator, Sequence, cast

import hou
from jiko_bridge_houdini.jb_types import JbContainer, JbObject, Placeholder
from jiko_bridge_houdini.scene.jb_scene_container import JbSceneContainer
from pxr import Gf, Tf, Usd, UsdGeom

FBX_TRANSLATION = "primvars:fbx_translation"
FBX_ROTATION = "primvars:fbx_rotation"
FBX_SCALE = "primvars:fbx_scale"
INSTANCES_PRIM = "instances"
TARGET_LAYER_ATTR = "jb:targetLayer"
TARGET_PRIM_ATTR = "jb:targetPrim"


def _primvar(prim: Usd.Prim, name: str, time: Usd.TimeCode) -> Any:
    """The first value of a primvar the FBX conversion wrote, when it wrote one."""
    attribute = prim.GetAttribute(name)
    if not attribute:
        return None
    value = attribute.Get(time)
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def placeholder_transform(prim: Usd.Prim, time: Usd.TimeCode) -> list[float]:
    """Placement of a placeholder: the FBX point data when present, else its xform."""
    translation = _primvar(prim, FBX_TRANSLATION, time)
    if translation is None:
        matrix = UsdGeom.XformCache(time).GetLocalToWorldTransform(prim)
        return [float(value) for row in matrix for value in row]
    rotation = _primvar(prim, FBX_ROTATION, time) or (0.0, 0.0, 0.0)
    scale = _primvar(prim, FBX_SCALE, time) or (1.0, 1.0, 1.0)
    transform = hou.hmath.buildTransform(
        {
            "translate": tuple(float(value) for value in translation),
            "rotate": tuple(math.degrees(float(value)) for value in rotation),
            "scale": tuple(float(value) for value in scale),
        }
    )
    return list(transform.asTuple())


def stage_placeholders(stage: Usd.Stage) -> Iterator[Placeholder]:
    """Read square placeholder prims from a model file that is a USD stage."""
    time = Usd.TimeCode(hou.frame() * stage.GetTimeCodesPerSecond() / hou.fps())
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
        yield {
            "object": str(prim.GetPath()),
            "names": [prim.GetPath().name],
            "transform": placeholder_transform(prim, time),
        }


def instances_path(root: str) -> str:
    """Where a container keeps the instances of its placeholders."""
    return f"{root}/{INSTANCES_PRIM}"


def instance_name(target: str, location: str) -> str:
    """Stable prim name of one instance, derived from its target and location."""
    digest = hashlib.sha1(f"{target}|{location}".encode("utf-8")).hexdigest()[:10]
    return f"instance_{digest}"


def instance_path(root: str, name: str) -> str:
    """Where one instance prim lives inside a container."""
    return f"{instances_path(root)}/{name}"


def reference(stage: Usd.Stage, path: str, layer_path: str, prim: str) -> Usd.Prim:
    """Reference a container prim of another layer, written or not."""
    primitive = UsdGeom.Xform.Define(stage, path).GetPrim()
    primitive.GetReferences().AddReference(layer_path, prim)
    primitive.SetInstanceable(True)
    return primitive


def set_instance_transform(prim: Usd.Prim, values: Sequence[float]) -> None:
    """Apply a stored 4x4 transform to a prim."""
    xform = UsdGeom.Xformable(prim)
    xform.MakeMatrixXform().Set(Gf.Matrix4d(*values))


def instance_targets(container: JbContainer) -> list[tuple[str, str]]:
    """Every ``(layer, prim)`` an instance of this container points at."""
    root = container.stage.GetPrimAtPath(instances_path(container.root))
    if not root:
        return []
    targets = []
    for prim in Usd.PrimRange(root):
        layer = prim.GetAttribute(TARGET_LAYER_ATTR).Get()
        target = prim.GetAttribute(TARGET_PRIM_ATTR).Get()
        if layer and target:
            targets.append((str(layer), str(target)))
    return targets


class JbSceneInstance(JbSceneContainer):
    """Houdini implementation of instance operations."""

    def get_names_from_placeholder(self, obj) -> list[str]:
        """The asset names a placeholder asks for."""
        if not isinstance(obj, JbObject) or obj.target is not None:
            return []
        return list(obj.data.get("names", []))

    def create_instance(self, container, name) -> JbObject:
        """An instance of a container; it is authored once it has a parent."""
        return JbObject({"name": name, "transform": None}, target=container)

    def replace_instances_with_placeholders(self, objects, source):
        """Houdini has no placeholder authoring in this direction yet."""
        self.logger.warning("Houdini placeholder export is not implemented.")

    def create_placeholder(self, asset_model, transform, source):
        """Houdini has no placeholder authoring in this direction yet."""
        self.logger.warning("Houdini placeholder export is not implemented.")
