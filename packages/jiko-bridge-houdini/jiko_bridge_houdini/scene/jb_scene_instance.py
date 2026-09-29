import math
from typing import Any, Iterator, cast

import hou
from jiko_bridge_houdini.jb_types import (
    INSTANCES_PRIM,
    TARGET_LAYER_ATTR,
    TARGET_PRIM_ATTR,
    JbContainer,
    JbObject,
    Placeholder,
)
from jiko_bridge_houdini.scene.jb_scene_container import JbSceneContainer
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdShade


FBX_TRANSLATION = "primvars:fbx_translation"
FBX_ROTATION = "primvars:fbx_rotation"
FBX_SCALE = "primvars:fbx_scale"
VECTOR_TYPES = (Gf.Vec2f, Gf.Vec3f, Gf.Vec4f, Gf.Vec2d, Gf.Vec3d, Gf.Vec4d)


class JbSceneInstance(JbSceneContainer):
    """Houdini implementation of instance operations."""

    def instances_path(self, root: str) -> str:
        """Where a container keeps the instances of its placeholders."""
        return f"{root}/{INSTANCES_PRIM}"

    @staticmethod
    def instance_name(name: str, location: str) -> str:
        """Name of one instance, as Cinema 4D and Blender name theirs."""
        part = Tf.MakeValidIdentifier(location.strip("/").replace("/", "_")) or "placeholder"
        return f"Instance_{name}_{part}"

    def instance_path(self, root: str, name: str) -> str:
        """Where one instance prim lives inside a container."""
        return f"{self.instances_path(root)}/{name}"

    def _primvar(self, prim: Usd.Prim, name: str, time: Usd.TimeCode) -> Any:
        """One value of a primvar the FBX conversion wrote: a vector or a vector array."""
        attribute = prim.GetAttribute(name)
        if not attribute:
            return None
        value = attribute.Get(time)
        if value is None or isinstance(value, VECTOR_TYPES + (float, int, str)):
            return value
        values = list(value)
        return values[0] if values else None

    def placeholder_transform(
        self, prim: Usd.Prim, time: Usd.TimeCode, units: float = 1.0
    ) -> list[float]:
        """Placement of a placeholder: the FBX point data when present, else its xform."""
        translation = self._primvar(prim, FBX_TRANSLATION, time)
        if translation is None:
            matrix = UsdGeom.XformCache(time).GetLocalToWorldTransform(prim)
            return [float(value) for row in matrix for value in row]
        rotation = self._primvar(prim, FBX_ROTATION, time) or (0.0, 0.0, 0.0)
        scale = self._primvar(prim, FBX_SCALE, time) or (1.0, 1.0, 1.0)
        transform = hou.hmath.buildTransform(
            {
                "translate": tuple(float(value) * units for value in translation),
                "rotate": tuple(math.degrees(float(value)) for value in rotation),
                "scale": tuple(float(value) for value in scale),
            }
        )
        return list(transform.asTuple())

    def placeholder_names(self, prim: Usd.Prim, time: Usd.TimeCode) -> list[str]:
        """Use material and selection names, as the C4D and Blender importers do."""
        names: list[str] = []

        def add(value: str) -> None:
            name = value.replace("\\", "/").rsplit("/", 1)[-1]
            if name and name not in names:
                names.append(name)

        candidates = [prim] + [child for child in prim.GetChildren() if child.IsA(UsdGeom.Subset)]
        for candidate in candidates:
            material, _ = UsdShade.MaterialBindingAPI(candidate).ComputeBoundMaterial()
            if material:
                material_prim = material.GetPrim()
                add(str(material_prim.GetMetadata("displayName") or material_prim.GetName()))
            # The SOP-to-USD conversion can keep the original material path as a primvar.
            for attribute in ("primvars:shop_materialpath", "shop_materialpath"):
                value = candidate.GetAttribute(attribute).Get(time)
                if isinstance(value, str):
                    add(value)
                elif value is not None:
                    for item in value:
                        if isinstance(item, str):
                            add(item)
            if candidate != prim:
                add(str(candidate.GetMetadata("displayName") or candidate.GetName()))
        add(str(prim.GetMetadata("displayName") or prim.GetName()))
        return names

    def stage_placeholders(self, stage: Usd.Stage, units: float = 1.0) -> Iterator[Placeholder]:
        """Read square placeholder prims from a model file that is a USD stage."""
        time = Usd.TimeCode(hou.frame() * stage.GetTimeCodesPerSecond() / hou.fps())
        for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
            if not prim.IsA(cast(Tf.Type, UsdGeom.Mesh)):
                continue
            mesh = UsdGeom.Mesh(prim)
            points = mesh.GetPointsAttr().Get(time)
            counts = mesh.GetFaceVertexCountsAttr().Get(time)
            indices = mesh.GetFaceVertexIndicesAttr().Get(time)
            if points is None or len(points) != 4 or not counts:
                continue
            if len(set(indices or [])) != 4:
                continue
            yield {
                "object": str(prim.GetPath()),
                "names": self.placeholder_names(prim, time),
                "transform": self.placeholder_transform(prim, time, units),
            }

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

    def _add_instance(self, container: JbContainer, obj: JbObject) -> None:
        """Author one placeholder replacement as an instance prim of the container."""
        if obj.target is None:
            return
        location = str(obj.data.get("object", obj.data["name"]))
        name = self.instance_name(str(obj.data["name"]), location)
        prim = UsdGeom.Xform.Define(
            self._edit(container), self.instance_path(container.root, name)
        ).GetPrim()
        prim.SetInstanceable(False)
        transform = obj.data.get("transform")
        if transform:
            self.set_instance_transform(prim, transform)
        layer = prim.CreateAttribute(TARGET_LAYER_ATTR, Sdf.ValueTypeNames.String)
        layer.Set(obj.target.layer)
        target = prim.CreateAttribute(TARGET_PRIM_ATTR, Sdf.ValueTypeNames.String)
        target.Set(obj.target.root)
        prim.GetReferences().AddReference(obj.target.layer, obj.target.root)

    def _is_cycle(self, container: JbContainer, target: JbContainer) -> bool:
        """Whether making this container depend on the target would close a circle."""
        pending = [target.layer]
        seen: set[str] = set()
        while pending:
            path = pending.pop()
            if path == container.layer:
                return True
            if path in seen:
                continue
            seen.add(path)
            pending.extend((layer for layer, _ in self._targets_of(path)))
        return False

    def _targets_of(self, path: str) -> list[tuple[str, str]]:
        """Instance targets of one layer, taken from the running import or from disk."""
        stage = Usd.Stage.Open(path)
        if stage is None:
            return []
        return [
            (
                str(prim.GetAttribute(TARGET_LAYER_ATTR).Get()),
                str(prim.GetAttribute(TARGET_PRIM_ATTR).Get()),
            )
            for prim in stage.Traverse()
            if prim.GetAttribute(TARGET_LAYER_ATTR).Get()
        ]
