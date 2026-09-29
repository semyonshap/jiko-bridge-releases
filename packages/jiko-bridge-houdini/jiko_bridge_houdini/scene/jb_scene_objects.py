"""Object selection, traversal, copying and transforms."""

import os
from typing import Any, Optional, Sequence

import hou
from jiko_bridge_client import AssetModel
from jiko_bridge_houdini.jb_types import (
    ASSETS_PRIM,
    GEOMETRY_PRIM,
    PLACEHOLDER_NAMES_ATTR,
    PLACEHOLDER_SOURCE_ATTR,
    PLACEHOLDER_TRANSFORM_ATTR,
    JbContainer,
    JbData,
    JbObject,
    JbSceneBase,
)
from jiko_bridge_houdini.jb_settings import JbSettings
from jiko_bridge_houdini.utils.jb_utils_params import node_assets, store_asset
from pxr import Gf, Sdf, Usd, UsdGeom


class JbSceneObjects(JbSceneBase):
    """Houdini implementation of objects operations."""

    node: hou.OpNode
    settings: JbSettings
    _source: Optional[Usd.Stage]

    def copy_geometry_roots(
        self, source: Sdf.Layer, destination: Sdf.Layer, parent: str
    ) -> None:
        """Copy the root prims of a converted geometry, remapping their internal links."""
        roots = [prim for prim in source.rootPrims if prim.name != "HoudiniLayerInfo"]
        mapping = [(prim.path, Sdf.Path(parent).AppendChild(prim.name)) for prim in roots]
        for old, new in mapping:
            if not Sdf.CopySpec(source, old, destination, new):
                raise hou.NodeError(f"Cannot copy imported USD geometry: {old}")

        def remap(path: Sdf.Path) -> Sdf.Path:
            if path.HasPrefix(Sdf.Path(parent)):
                return path
            for old, new in mapping:
                if path.HasPrefix(old):
                    return path.ReplacePrefix(old, new)
            return path

        def fix_links(path: Sdf.Path) -> None:
            spec = destination.GetObjectAtPath(path)
            if spec is None:
                return
            for field in ("targetPaths", "connectionPaths", "inheritPaths", "specializes"):
                if spec.HasInfo(field):
                    values = spec.GetInfo(field)
                    spec.SetInfo(
                        field,
                        Sdf.PathListOp.CreateExplicit(
                            [remap(value) for value in values.GetAppliedItems()]
                        ),
                    )
            if spec.HasInfo("references"):
                values = spec.GetInfo("references").GetAppliedItems()
                spec.SetInfo(
                    "references",
                    Sdf.ReferenceListOp.CreateExplicit(
                        [
                            (
                                Sdf.Reference(
                                    value.assetPath,
                                    remap(value.primPath),
                                    value.layerOffset,
                                    value.customData,
                                )
                                if not value.assetPath
                                else value
                            )
                            for value in values
                        ]
                    ),
                )

        paths: list[Sdf.Path] = []
        destination.Traverse(Sdf.Path(parent), lambda path: paths.append(Sdf.Path(str(path))))
        for path in paths:
            fix_links(path)

    @staticmethod
    def make_explicit(stage: Usd.Stage) -> None:
        """Turn every instance into explicit specs so its contents can be copied."""
        while True:
            instances = [prim for prim in stage.Traverse() if prim.IsInstance()]
            if not instances:
                break
            for prim in instances:
                prim.SetInstanceable(False)

    def _layer(self, path: str, reset: bool) -> Sdf.Layer:
        """Open the cache layer of an asset, creating and resetting its file when needed."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        layer = Sdf.Layer.Find(path)
        if layer is None:
            layer = (
                Sdf.Layer.FindOrOpen(path)
                if os.path.isfile(path)
                else Sdf.Layer.CreateNew(path)
            )
        if layer is None:
            raise hou.NodeError(f"Cannot open asset layer: {path}")
        if reset and (self.settings.override or not layer.rootPrims):
            layer.Clear()
            layer.defaultPrim = ASSETS_PRIM
            self._set_layer_metrics(layer)
        return layer

    def _layer_of(self, container: JbContainer) -> Sdf.Layer:
        """The cache layer of a container, which the session stage sublayers."""
        layer = Sdf.Layer.Find(container.layer)
        if layer is None:
            raise hou.NodeError(f"Cannot open asset layer: {container.layer}")
        return layer

    def _attached(self, path: str) -> bool:
        """Whether a layer is already sublayered into the running import."""
        return path in self.source.GetRootLayer().subLayerPaths

    def _attach(self, container: JbContainer) -> None:
        """Sublayer the layer of a container into the session stage."""
        paths = self.source.GetRootLayer().subLayerPaths
        if container.layer not in paths:
            paths.append(container.layer)

    def container_key(self, container: JbContainer) -> str:
        """A container is identified by the cache layer it is authored into."""
        return container.layer

    def _edit(self, container: JbContainer) -> Usd.Stage:
        """Point the session stage at the layer of one container before authoring."""
        self.source.SetEditTarget(self._layer_of(container))
        return self.source

    def _save_layer(self, path: str) -> None:
        """Write one asset layer to disk, once its contents are explicit."""
        layer = Sdf.Layer.Find(path)
        if layer is None:
            raise hou.NodeError(f"Cannot open asset layer: {path}")
        # Older caches may still carry instanceable opinions inside their containers.
        self.make_explicit(Usd.Stage.Open(layer))
        if not layer.dirty:
            return
        if not layer.Save():
            raise hou.NodeError(f"Cannot save asset layer: {path}")

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
        imageable = UsdGeom.Imageable(self._edit(container).OverridePrim(container.root))
        attribute = imageable.GetVisibilityAttr()
        if visible is None:
            attribute.Clear()
        elif visible:
            imageable.MakeVisible()
        else:
            imageable.MakeInvisible()

    @staticmethod
    def set_instance_transform(prim: Usd.Prim, values: Sequence[float]) -> None:
        """Apply a stored 4x4 transform to a prim."""
        xform = UsdGeom.Xformable(prim)
        xform.MakeMatrixXform().Set(Gf.Matrix4d(*values))

    def recorded_assets(self) -> list[AssetModel]:
        """Every asset the node records, in parameter order."""
        return node_assets(self.node)

    def get_selection(self) -> list[JbData]:
        """One container per complete asset entry of the node."""
        return [
            self.get_or_create_asset_container(asset)[0] for asset in self.recorded_assets()
        ]

    def record_asset(self, asset) -> None:
        """Keep an asset the import was asked for in the fields of the node."""
        store_asset(self.node, asset, enable=True)

    def walk(self, root) -> list[JbData]:
        result = []
        for obj in root:
            result.append(obj)
            if isinstance(obj, JbContainer):
                result.extend(self.get_children(obj))
        return result

    def get_children(self, obj) -> list[JbObject | JbContainer]:
        """The placeholders a container still holds in its layer."""
        if not isinstance(obj, JbContainer):
            return []
        return [JbObject(data, parent=obj) for data in self.placeholders(obj)]

    @staticmethod
    def geometry_path(root: str) -> str:
        """Where the geometry of an asset lives inside its container."""
        return f"{root}/{GEOMETRY_PRIM}"

    def placeholders(self, container: JbContainer) -> list[dict[str, Any]]:
        """The placeholders a container still holds, read back from its layer."""
        parent = self.geometry_path(container.root)
        prim = self.source.GetPrimAtPath(parent)
        if not prim:
            return []
        return [
            self._placeholder(item, parent)
            for item in Usd.PrimRange(prim)
            if item.HasAttribute(PLACEHOLDER_SOURCE_ATTR)
        ]

    def mark_placeholders(
        self, container: JbContainer, source: str, found: list[dict[str, Any]]
    ) -> None:
        """Author every placeholder of one model into the layer of its container."""
        parent = self.geometry_path(container.root)
        stage = self._edit(container)
        for placeholder in found:
            prim = stage.OverridePrim(Sdf.Path(parent + placeholder["object"]))
            self._author(prim, PLACEHOLDER_SOURCE_ATTR, Sdf.ValueTypeNames.String, source)
            names = placeholder.get("names")
            if names:
                self._author(
                    prim, PLACEHOLDER_NAMES_ATTR, Sdf.ValueTypeNames.StringArray, list(names)
                )
            transform = placeholder.get("transform")
            if transform:
                self._author(
                    prim,
                    PLACEHOLDER_TRANSFORM_ATTR,
                    Sdf.ValueTypeNames.DoubleArray,
                    [float(value) for value in transform],
                )

    def drop_placeholder(self, container: JbContainer, location: str) -> None:
        """Turn off the placeholder prim an instance has taken the place of."""
        target = Sdf.Path(self.geometry_path(container.root) + location)
        stage = self._edit(container)
        # An instance proxy cannot be edited, so the placeholders it holds are released first.
        for prefix in target.GetPrefixes():
            prim = stage.GetPrimAtPath(prefix)
            if prim and prim.IsInstance():
                prim.SetInstanceable(False)
        stage.OverridePrim(target).SetActive(False)

    @staticmethod
    def _author(prim: Usd.Prim, name: str, kind: Sdf.ValueTypeName, value: Any) -> None:
        """Write one placeholder attribute on a prim of the container layer."""
        prim.CreateAttribute(name, kind, custom=True).Set(value)

    def _placeholder(self, prim: Usd.Prim, parent: str) -> dict[str, Any]:
        """One authored placeholder, as the importer reads it."""
        transform = prim.GetAttribute(PLACEHOLDER_TRANSFORM_ATTR).Get()
        return {
            "object": str(prim.GetPath())[len(parent) :],
            "source": str(prim.GetAttribute(PLACEHOLDER_SOURCE_ATTR).Get() or ""),
            "names": [str(name) for name in prim.GetAttribute(PLACEHOLDER_NAMES_ATTR).Get() or []],
            "transform": [float(value) for value in transform] if transform else None,
        }

    def get_depth(self, obj) -> int:
        return 0 if isinstance(obj, JbContainer) or obj.parent is None else 1

    def copy_object_transform(self, obj, target_obj) -> None:
        matrix = target_obj.data.get("transform")
        obj.data["transform"] = list(matrix) if matrix is not None else None
        obj.data["object"] = target_obj.data["object"]
        obj.data["names"] = list(target_obj.data.get("names", []))
        obj.data["source"] = target_obj.data["source"]
        obj.data["placeholder"] = target_obj

    def remove_object(self, obj) -> None:
        """Drop a placeholder, turning off the prim its instance takes the place of."""
        parent = obj.parent
        if isinstance(parent, JbContainer) and obj.target is None and obj.data.get("replace"):
            self.drop_placeholder(parent, str(obj.data["object"]))
        obj.parent = None

    def get_materials_from_objects(self, objects):
        """Houdini selects materials by node, not by container contents."""
        return []

    def merge_duplicates_materials(self, material):
        """Houdini imports one material per file, so nothing is merged."""
        self.logger.warning("Houdini material merging is not implemented.")
