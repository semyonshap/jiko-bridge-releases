"""Houdini temp and layer operations: the session over the asset layers."""

import os
import re
from contextlib import contextmanager
from typing import Any, Iterator, Optional, Sequence

import hou
from jiko_bridge_client import AssetModel
from jiko_bridge_houdini.jb_types import JbContainer, JbObject
from jiko_bridge_houdini.scene.jb_scene_container import (
    author_container,
    asset_root,
    model_path,
    prim_name,
)
from jiko_bridge_houdini.scene.jb_scene_instance import (
    TARGET_LAYER_ATTR,
    TARGET_PRIM_ATTR,
    JbSceneInstance,
    instance_name,
    instance_path,
    instance_targets,
    reference,
    set_instance_transform,
)
from pxr import Sdf, Usd, UsdGeom

SOURCE_ATTR = "jb:source"


def cache_file(cache_root: str, metadata: dict[str, Any]) -> str:
    """Cache path of one asset, validated against invalid name characters."""
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


def layer_metrics(layer: Sdf.Layer) -> None:
    """Set the stage metrics Houdini expects on a layer it authors."""
    stage = Usd.Stage.Open(layer)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    layer.framesPerSecond = hou.fps()
    layer.timeCodesPerSecond = hou.fps()


def copy_geometry_roots(source: Sdf.Layer, destination: Sdf.Layer, parent: str) -> None:
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


def make_explicit(stage: Usd.Stage) -> None:
    """Turn every instance into explicit specs so its contents can be copied."""
    stage.SetEditTarget(stage.GetSessionLayer())
    while True:
        instances = [prim for prim in stage.Traverse() if prim.IsInstance()]
        if not instances:
            break
        for prim in instances:
            prim.SetInstanceable(False)


@contextmanager
def geometry_stage(
    identifier: str, geometry: hou.Geometry, node: Optional[hou.LopNode] = None
) -> Iterator[Usd.Stage]:
    """Stage holding one converted geometry, authored through a node or the module API."""
    if node is not None:
        layer_id = node.addLockedGeometry(identifier, geometry)
        stage = Usd.Stage.Open(layer_id)
        if stage is None:
            raise hou.NodeError(f"Cannot convert geometry to USD: {identifier}")
        yield stage
        return
    layer_id = hou.lop.addLockedGeometry(identifier, geometry)
    try:
        stage = Usd.Stage.CreateInMemory()
        stage.GetRootLayer().subLayerPaths.append(layer_id)
        yield stage
    finally:
        hou.lop.removeLockedGeometry(layer_id)


def geometry_into_layer(
    stage: Usd.Stage,
    model_prim: str,
    identifier: str,
    geometry: hou.Geometry,
    node: Optional[hou.LopNode] = None,
) -> None:
    """Convert one geometry and copy it under the model prim of the target layer."""
    with geometry_stage(identifier, geometry, node) as converted:
        make_explicit(converted)
        flattened = converted.Flatten()
        parent = model_prim + "/geometry"
        UsdGeom.Xform.Define(stage, parent)
        copy_geometry_roots(flattened, stage.GetRootLayer(), parent)


class JbStage:
    """Own the asset layers one import session authors."""

    def __init__(self, cache_root: str, override: bool = False) -> None:
        self.cache_root = cache_root
        self.override = override
        self.containers: dict[str, JbContainer] = {}

    def open(self, asset: AssetModel) -> JbContainer:
        """Open the asset layer, creating the container prim when it is absent."""
        metadata = asset.to_dict()
        path = cache_file(self.cache_root, metadata)
        container = self.containers.get(path)
        if container is not None:
            return container
        stage = self._stage(path)
        container = JbContainer(path, asset_root("", metadata), stage, asset=dict(metadata))
        author_container(stage, container.root, container.asset)
        self.containers[path] = container
        return container

    def find(self, asset: AssetModel) -> Optional[JbContainer]:
        """The container of an asset whose layer is already on disk."""
        path = cache_file(self.cache_root, asset.to_dict())
        if not os.path.isfile(path):
            return None
        return self.open(asset)

    def save(self, container: JbContainer) -> None:
        """Write one layer back to disk once its container is complete."""
        container.stage.GetRootLayer().Save()

    def clear(self, container: JbContainer) -> None:
        """Empty the container, keeping the file and its asset info."""
        layer = container.stage.GetRootLayer()
        layer.Clear()
        layer_metrics(layer)
        layer.defaultPrim = container.root.lstrip("/")
        author_container(container.stage, container.root, container.asset)
        container.pending.clear()

    def has_model(self, container: JbContainer, source: str) -> bool:
        """Whether this container already holds the geometry of one model file."""
        if source in container.models:
            return True
        return bool(container.stage.GetPrimAtPath(model_path(container.root, source)))

    def has_models(self, container: JbContainer) -> bool:
        """Whether this container already holds geometry of any model."""
        if container.models:
            return True
        path = f"{container.root}/geometry"
        prim = container.stage.GetPrimAtPath(path)
        return bool(prim) and bool(prim.GetChildren())

    def finish(self, container: JbContainer) -> None:
        """Author every parsed model of a container, then write its layer."""
        for model in container.models.values():
            self.add_model(container, model.source, model.geometry, container.remove_objects)
        container.models.clear()
        self.save(container)

    def add_model(
        self,
        container: JbContainer,
        source: str,
        geometry: Optional[hou.Geometry] = None,
        remove_objects: Sequence[str] = (),
    ) -> None:
        """Author one model file: converted geometry, or a reference to the source USD."""
        path = model_path(container.root, source)
        if geometry is not None:
            geometry_into_layer(container.stage, path, prim_name(source), geometry)
            self._drop_placeholders(container.stage, f"{path}/geometry", remove_objects)
        else:
            self._reference_source(container.stage, path, source, remove_objects)
        prim = container.stage.OverridePrim(path)
        prim.CreateAttribute(SOURCE_ATTR, Sdf.ValueTypeNames.String).Set(source)

    @staticmethod
    def _drop_placeholders(stage: Usd.Stage, parent: str, remove_objects: Sequence[str]) -> None:
        """Deactivate the placeholder prims the instances of a container replace."""
        for location in remove_objects:
            stage.OverridePrim(Sdf.Path(parent + location)).SetActive(False)

    def add_object(self, container: JbContainer, obj: JbObject) -> None:
        """Author one placeholder replacement as an instance prim of the container."""
        if obj.target is None:
            return
        name = instance_name(obj.target.root, str(obj.data.get("object", obj.data["name"])))
        prim = reference(
            container.stage, instance_path(container.root, name), obj.target.layer, obj.target.root
        )
        transform = obj.data.get("transform")
        if transform:
            set_instance_transform(prim, transform)
        layer = prim.CreateAttribute(TARGET_LAYER_ATTR, Sdf.ValueTypeNames.String)
        layer.Set(obj.target.layer)
        target = prim.CreateAttribute(TARGET_PRIM_ATTR, Sdf.ValueTypeNames.String)
        target.Set(obj.target.root)

    def is_cycle(self, container: JbContainer, target: JbContainer) -> bool:
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
        """Instance targets of one layer, read from the session or from disk."""
        holder = next((item for item in self.containers.values() if item.layer == path), None)
        if holder is not None:
            return instance_targets(holder)
        if not os.path.isfile(path):
            return []
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

    def _stage(self, path: str) -> Usd.Stage:
        """Open the layer of an asset, creating or emptying it as required."""
        if os.path.isfile(path):
            stage = Usd.Stage.Open(path)
            if stage is None:
                raise hou.NodeError(f"Cannot open asset layer: {path}")
            if self.override:
                stage.GetRootLayer().Clear()
            return stage
        layer = Sdf.Layer.CreateNew(path)
        stage = Usd.Stage.Open(layer)
        if stage is None:
            raise hou.NodeError(f"Cannot create asset layer: {path}")
        layer_metrics(layer)
        return stage

    def _reference_source(
        self,
        stage: Usd.Stage,
        path: str,
        source: str,
        remove_objects: Sequence[str],
    ) -> None:
        """Keep the original USD file on disk; author replacements as opinions."""
        UsdGeom.Xform.Define(stage, path)
        original = Usd.Stage.Open(source)
        if original is None:
            raise hou.NodeError(f"Cannot open USD source: {source}")
        for root in original.GetPseudoRoot().GetChildren():
            if root.GetName() == "HoudiniLayerInfo":
                continue
            prim = stage.DefinePrim(f"{path}/{root.GetName()}")
            prim.GetReferences().AddReference(source, root.GetPath())
        for location in remove_objects:
            target = Sdf.Path(path + location)
            for prefix in target.GetPrefixes():
                prim = stage.GetPrimAtPath(prefix)
                if prim and prim.IsInstance():
                    prim.SetInstanceable(False)
            stage.OverridePrim(target).SetActive(False)


class JbSceneTemp(JbSceneInstance):
    """Houdini implementation of temp operations."""

    @contextmanager
    def temp_source(self, objects=None, unit_scale=1.0, debug=False):
        yield self.source
