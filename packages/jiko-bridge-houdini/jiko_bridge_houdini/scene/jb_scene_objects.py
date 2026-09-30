"""Object selection, traversal, copying and transforms."""

import hou
from jiko_bridge_client import AssetModel
from jiko_bridge_houdini.jb_settings import JbSettings
from jiko_bridge_houdini.jb_types import (
    GEOMETRY_PRIM,
    JbContainer,
    JbData,
    JbObject,
    JbSceneBase,
)
from jiko_bridge_houdini.utils.jb_utils_params import node_assets
from pxr import Sdf, Usd, UsdGeom


class JbSceneObjects(JbSceneBase):
    """Houdini implementation of objects operations."""

    node: hou.OpNode
    settings: JbSettings
    _containers: dict[str, Usd.Stage]

    @staticmethod
    def container_root(container: JbContainer) -> str:
        """The root prim of a container, which every path inside it hangs from."""
        return str(container.GetDefaultPrim().GetPath())

    def container_key(self, container: JbContainer) -> str:
        """A container is identified by the cache layer it is authored into."""
        return container.GetRootLayer().identifier

    def _save_container(self, container: JbContainer) -> None:
        """Write the layer of one container to disk when it changed."""
        layer = container.GetRootLayer()
        if not layer.dirty:
            return
        if not layer.Save():
            raise hou.NodeError(f"Cannot save asset layer: {layer.identifier}")

    @staticmethod
    def _set_layer_metrics(layer: Sdf.Layer) -> None:
        """Set the stage metrics Houdini expects on a layer it authors."""
        stage = Usd.Stage.Open(layer)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        layer.framesPerSecond = hou.fps()
        layer.timeCodesPerSecond = hou.fps()

    def set_container_visibility(self, container: JbContainer, visible: bool | None) -> None:
        """Show, hide or release one container in its own layer."""
        imageable = UsdGeom.Imageable(container.OverridePrim(self.container_root(container)))
        attribute = imageable.GetVisibilityAttr()
        if visible is None:
            attribute.Clear()
        elif visible:
            imageable.MakeVisible()
        else:
            imageable.MakeInvisible()

    def recorded_assets(self) -> list[AssetModel]:
        """Every asset the node records, in parameter order."""
        return node_assets(self.node)

    def get_selection(self) -> list[JbData]:
        """One container per complete asset entry of the node."""
        containers: list[JbData] = []
        for asset in self.recorded_assets():
            container = self.get_container(asset)
            containers.append(container if container is not None else self.create_container(asset))
        return containers

    def walk(self, root) -> list[JbData]:
        result = []
        for obj in root:
            result.append(obj)
            if isinstance(obj, JbContainer):
                result.extend(self.get_children(obj))
        return result

    def get_children(self, obj) -> list[JbObject | JbContainer]:
        """Every prim a container holds in its layer."""
        if not isinstance(obj, JbContainer):
            return []
        prim = obj.GetPrimAtPath(self.geometry_path(self.container_root(obj)))
        if not prim:
            return []
        prims = Usd.PrimRange(prim, Usd.TraverseInstanceProxies())
        return [item for item in prims if item != prim]

    @staticmethod
    def geometry_path(root: str) -> str:
        """Where the geometry of an asset lives inside its container."""
        return f"{root}/{GEOMETRY_PRIM}"

    def remove_object(self, obj) -> None:
        """Turn off the prim of the given object in the layer of its own stage."""
        if not obj:
            return
        container = obj.GetStage()
        # An instance proxy cannot be edited, so the placeholders it holds are released first.
        for prefix in obj.GetPath().GetPrefixes():
            prim = container.GetPrimAtPath(prefix)
            if prim and prim.IsInstance():
                prim.SetInstanceable(False)
        container.OverridePrim(obj.GetPath()).SetActive(False)

    def get_materials_from_objects(self, objects):
        """Houdini selects materials by node, not by container contents."""
        return []
