"""Author cache layers and USD instances during cook, without disk writes."""

import json
from typing import Any, Sequence, cast

import hou
import loputils
from jiko_bridge_houdini.jb_utils import unpack_piece
from jiko_bridge_houdini.scene.jb_scene_layer_plan import CACHE_ROOT_PRIM, GEOMETRY_PRIM, layer_plan
from pxr import Gf, Sdf, Tf, Usd, UsdGeom


def _layer_metrics(layer: Sdf.Layer) -> None:
    stage = Usd.Stage.Open(layer)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    layer.framesPerSecond = hou.fps()
    layer.timeCodesPerSecond = hou.fps()


def _set_instance_transform(prim: Usd.Prim, values: Sequence[float]) -> None:
    matrix = Gf.Matrix4d(*values)
    xform = UsdGeom.Xformable(prim)
    xform.MakeMatrixXform().Set(matrix)


def _copy_geometry_roots(source: Sdf.Layer, destination: Sdf.Layer, parent: str) -> None:
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


class LayerAssembly:

    def __init__(self, node: hou.LopNode, plan: dict[str, Any], geometry: hou.Geometry) -> None:
        self.node = node
        self.plan = plan
        self.geometry = geometry
        self.layers: dict[str, Sdf.Layer] = {}
        self.stages: dict[str, Usd.Stage] = {}
        self.asset_layers: dict[str, str] = {}
        self.usd_sources: dict[str, Usd.Stage] = {}

    def allocate(self) -> None:
        """Allocate every target before creating references to it."""
        for item in self.plan["layers"]:
            if item["reuse"]:
                stage = Usd.Stage.Open(item["path"])
                if stage is None:
                    raise hou.NodeError(f"Cannot read cached USD: {item['path']}")
                for model in item["models"]:
                    if not stage.GetPrimAtPath(model["prim"]):
                        raise hou.NodeError(
                            f"Cache schema differs for {item['path']}. Enable Override to rebuild it."
                        )
                self.asset_layers[item["asset_id"]] = item["path"]
                continue
            layer = loputils.createPythonLayer(self.node, item["path"])
            _layer_metrics(layer)
            layer.defaultPrim = CACHE_ROOT_PRIM
            stage = Usd.Stage.Open(layer)
            if stage is None:
                raise hou.NodeError(f"Cannot create cache layer: {item['path']}")
            container = f"/{CACHE_ROOT_PRIM}"
            UsdGeom.Xform.Define(stage, container)
            UsdGeom.Xform.Define(stage, f"{container}/{GEOMETRY_PRIM}")
            for model in item["models"]:
                UsdGeom.Xform.Define(stage, model["prim"])
            self.asset_layers[item["asset_id"]] = layer.identifier
            self.layers[item["path"]] = layer
            self.stages[item["path"]] = stage

    def copy_geometry(self, stage: Usd.Stage, model: dict[str, Any]) -> None:
        primitive = next(
            (
                prim
                for prim in self.geometry.prims()
                if prim.stringAttribValue("asset_id") == model["id"]
            ),
            None,
        )
        if primitive is None:
            raise hou.NodeError(f"Prepared geometry is missing for {model['source']}")
        geometry = unpack_piece(self.geometry, primitive, convert_polysoup=False)
        if not geometry.prims() and (not geometry.points()):
            return
        identifier = self.node.addLockedGeometry(model["id"], geometry)
        imported = Usd.Stage.Open(identifier)
        if imported is None:
            raise hou.NodeError(f"Cannot convert geometry to USD: {model['source']}")
        imported.SetEditTarget(imported.GetSessionLayer())
        while True:
            instances = [prim for prim in imported.Traverse() if prim.IsInstance()]
            if not instances:
                break
            for prim in instances:
                prim.SetInstanceable(False)
        flattened = imported.Flatten()
        parent = model["prim"] + "/geometry"
        UsdGeom.Xform.Define(stage, parent)
        destination = stage.GetRootLayer()
        _copy_geometry_roots(flattened, destination, parent)

    def usd_source(self, path: str) -> Usd.Stage:
        if path not in self.usd_sources:
            stage = Usd.Stage.Open(path)
            if stage is None:
                raise hou.NodeError(f"Cannot open USD source: {path}")
            self.usd_sources[path] = stage
        return self.usd_sources[path]

    def reference(
        self, stage: Usd.Stage, path: str, identifier: str, ancestors: tuple[str, ...] = ()
    ) -> Usd.Prim:
        """One reference per asset, however many files the asset holds."""
        if identifier in ancestors:
            raise hou.NodeError(f"Cyclic USD reference at {path}")
        asset = self.plan["assets"][identifier]
        prim = UsdGeom.Xform.Define(stage, path).GetPrim()
        if asset["converted"]:
            target = self.asset_layers[identifier]
            if target == stage.GetRootLayer().identifier:
                prim.GetReferences().AddInternalReference(asset["root"])
            else:
                prim.GetReferences().AddReference(target, asset["root"])
        else:
            prototype = asset["prototype"]
            if not stage.GetRootLayer().GetPrimAtPath(prototype):
                stage.CreateClassPrim("/__JikoPrototypes")
                stage.CreateClassPrim(prototype).SetTypeName("Xform")
                self.author_usd_source(stage, prototype, asset, ancestors + (identifier,))
            prim.GetReferences().AddInternalReference(prototype)
        prim.SetInstanceable(True)
        return prim

    def author_usd_source(
        self, stage: Usd.Stage, path: str, asset: dict[str, Any], ancestors: tuple[str, ...]
    ) -> None:
        """Keep original USD on disk; author replacements as stronger opinions."""
        geometry = f"{path}/{GEOMETRY_PRIM}"
        UsdGeom.Xform.Define(stage, geometry)
        for model in asset["models"]:
            original = self.usd_source(model["file"])
            source_path = geometry + "/" + Sdf.Path(model["prim"]).name
            UsdGeom.Xform.Define(stage, source_path)
            for root in original.GetPseudoRoot().GetChildren():
                if root.GetName() == "HoudiniLayerInfo":
                    continue
                prim = stage.DefinePrim(source_path + "/" + root.GetName())
                prim.GetReferences().AddReference(model["file"], root.GetPath())
            for location in asset["record"]["remove_objects"]:
                target = Sdf.Path(source_path + location)
                for prefix in target.GetPrefixes():
                    prim = stage.GetPrimAtPath(prefix)
                    if prim and prim.IsInstance():
                        prim.SetInstanceable(False)
                stage.OverridePrim(target).SetActive(False)
        self.instances(stage, path, asset["record"], ancestors)

    def instances(
        self, stage: Usd.Stage, parent: str, record: dict[str, Any], ancestors: tuple[str, ...] = ()
    ) -> None:
        for index, instance in enumerate(record["instances"]):
            if not instance.get("replace"):
                continue
            container = parent + "/instances"
            UsdGeom.Xform.Define(stage, container)
            path = f"{container}/instance_{index:04d}"
            prim = self.reference(stage, path, instance["target"], ancestors)
            _set_instance_transform(prim, instance["transform"])

    def author(self) -> None:
        self.allocate()
        for item in self.plan["layers"]:
            if item["reuse"]:
                continue
            stage = self.stages[item["path"]]
            for model in item["models"]:
                self.copy_geometry(stage, model)
            asset = self.plan["assets"][item["asset_id"]]
            self.instances(stage, asset["root"], item["record"], (item["asset_id"],))


def assemble_usd(node: hou.LopNode) -> None:
    owner = cast(hou.OpNode, node.parent())
    graph: dict[str, Any] = {"mode": "cached"}
    geometry = None
    if not owner.evalParm("cached"):
        source = cast(hou.SopNode, owner.node("geometry/OUT_GEOMETRY"))
        geometry = source.geometry()
        graph = json.loads(str(cast(hou.Geometry, geometry).attribValue("jiko_graph")))
    plan = layer_plan(owner, graph)
    node.editableStage()
    if plan["mode"] != "cached" and (not graph["roots"]):
        return
    scene = loputils.createPythonLayer(node)
    _layer_metrics(scene)
    scene.defaultPrim = "World"
    stage = Usd.Stage.Open(scene)
    UsdGeom.Xform.Define(stage, "/World")
    root = "/World/" + Tf.MakeValidIdentifier(owner.name())
    UsdGeom.Xform.Define(stage, root)
    if plan["mode"] == "cached":
        prim = stage.DefinePrim(root + "/asset")
        prim.GetReferences().AddReference(plan["path"])
        prim.SetInstanceable(True)
    else:
        assembly = LayerAssembly(node, plan, cast(hou.Geometry, geometry))
        assembly.author()
        for index, identifier in enumerate(graph["roots"]):
            assembly.reference(stage, f"{root}/model_{index:04d}", identifier)
    node.addSubLayer(scene.identifier)
