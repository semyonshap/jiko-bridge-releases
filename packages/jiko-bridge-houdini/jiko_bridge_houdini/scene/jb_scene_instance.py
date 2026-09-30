import math
from typing import Any, Optional

import hou
from jiko_bridge_houdini.jb_types import INSTANCES_PRIM, JbObject
from jiko_bridge_houdini.scene.jb_scene_container import JbSceneContainer
from pxr import Gf, Usd, UsdGeom, UsdShade

FBX_TRANSLATION = "primvars:fbx_translation"
FBX_ROTATION = "primvars:fbx_rotation"
FBX_SCALE = "primvars:fbx_scale"
VECTOR_TYPES = (Gf.Vec2f, Gf.Vec3f, Gf.Vec4f, Gf.Vec2d, Gf.Vec3d, Gf.Vec4d)


class JbSceneInstance(JbSceneContainer):
    """Houdini implementation of instance operations."""

    def instances_path(self, root: str) -> str:
        """Where a container keeps the instances of its placeholders."""
        return f"{root}/{INSTANCES_PRIM}"

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

    def placeholder_transform(self, prim: Usd.Prim, time: Usd.TimeCode) -> list[float]:
        """Placement of a placeholder: the FBX point data when present, else its xform."""
        translation = self._primvar(prim, FBX_TRANSLATION, time)
        if translation is None:
            matrix = UsdGeom.XformCache(time).GetLocalToWorldTransform(prim)
            return [float(matrix[row, column]) for row in range(4) for column in range(4)]
        rotation = self._primvar(prim, FBX_ROTATION, time) or (0.0, 0.0, 0.0)
        scale = self._primvar(prim, FBX_SCALE, time) or (1.0, 1.0, 1.0)
        transform = hou.hmath.buildTransform(
            {
                "translate": tuple(float(value) for value in translation),
                "rotate": tuple(math.degrees(float(value)) for value in rotation),
                "scale": tuple(float(value) for value in scale),
            }
        )
        return list(transform.asTuple())

    def get_names_from_placeholder(self, obj) -> list[str]:
        """The asset names a placeholder asks for; a container asks for nothing."""
        if not isinstance(obj, Usd.Prim) or not obj.IsA(UsdGeom.Mesh):
            return []
        time = Usd.TimeCode.Default()
        points = UsdGeom.Mesh(obj).GetPointsAttr().Get(time)
        if points is None or len(points) != 4:
            return []
        names: list[str] = []

        def add(value: str) -> None:
            name = value.rsplit("/", 1)[-1]
            if name and name not in names:
                names.append(name)

        candidates = [obj] + [child for child in obj.GetChildren() if child.IsA(UsdGeom.Subset)]
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
            if candidate != obj:
                add(str(candidate.GetMetadata("displayName") or candidate.GetName()))
        add(str(obj.GetMetadata("displayName") or obj.GetName()))
        return names

    def create_instance(self, container, asset, parent=None, source=None) -> Optional[JbObject]:
        """An instance of an asset container, authored at once into its parent."""
        if parent is None or not source:
            return None
        root = self.container_root(parent)
        location = str(source.GetPath())[len(self.geometry_path(root)) :]
        prim_name = self.instance_name(asset, location)
        instance = UsdGeom.Xform.Define(parent, self.instance_path(root, prim_name)).GetPrim()
        instance.SetInstanceable(False)
        matrix = self.placeholder_transform(source, Usd.TimeCode.Default())
        UsdGeom.Xformable(instance).MakeMatrixXform().Set(Gf.Matrix4d(*matrix))
        instance.GetReferences().AddReference(
            self.container_key(container), self.container_root(container)
        )
        return instance

    def replace_instances_with_placeholders(self, objects, source):
        """Houdini has no placeholder authoring in this direction yet."""
        self.logger.warning("Houdini placeholder export is not implemented.")

    def create_placeholder(self, asset_model, transform, source):
        """Houdini has no placeholder authoring in this direction yet."""
        self.logger.warning("Houdini placeholder export is not implemented.")
