"""Houdini message reporting."""

import json
import logging
import os
from typing import Any, Mapping, Optional, Sequence, cast

import hou
from jiko_bridge_client import AssetModel, get_logger


def report(
    logger: logging.Logger,
    message: Optional[str] = None,
    box: Optional[str] = None,
    severity: hou.EnumValue = hou.severityType.Warning,
) -> None:
    """Report a message: log it, show it in a message box, or both."""
    levels = {
        hou.severityType.Message: logging.INFO,
        hou.severityType.ImportantMessage: logging.INFO,
        hou.severityType.Warning: logging.WARNING,
        hou.severityType.Error: logging.ERROR,
        hou.severityType.Fatal: logging.CRITICAL,
    }
    if message:
        logger.log(levels.get(severity, logging.WARNING), message)
    if box and hou.isUIAvailable():
        hou.ui.displayMessage(box, title="Jiko Bridge", severity=severity)


container_logger = get_logger(__name__)


def apply_asset(node: hou.OpNode, asset: AssetModel) -> bool:
    """Populate the node's user data; the parms below only mirror it."""
    files = asset.files
    if not files:
        report(container_logger, "Asset has no files", "The asset has no files.")
        return False
    node.setUserData("jiko_asset", json.dumps(asset.to_dict(), ensure_ascii=False))
    set_parm(node, "vault_name", asset.vault_name)
    set_parm(node, "pack_name", asset.pack_name)
    set_parm(node, "asset_name", asset.asset_name)
    set_multiparm(
        node,
        "files",
        {
            "filepath": [file.filepath for file in files],
            "asset_type": [file.asset_type for file in files],
            "bridge_type": [file.bridge_type for file in files],
        },
    )
    return True


def cached_asset(node: hou.OpNode) -> AssetModel:
    """The asset stored in the node's user data; the parms only mirror it."""
    payload = node.userData("jiko_asset")
    return AssetModel.from_dict(json.loads(payload)) if payload else AssetModel()


def group_prims(geometry: hou.Geometry, name: str) -> Sequence[hou.Prim]:
    """Primitives a VEX pass collected into a group; no level is rescanned."""
    group = geometry.findPrimGroup(name)
    return tuple(group.prims()) if group is not None else ()


def prim_strings(prim: hou.Prim, name: str) -> list[str]:
    """Read a string array attribute a VEX pass wrote, when that pass wrote one."""
    if prim.geometry().findPrimAttrib(name) is None:
        return []
    return list(cast(Sequence[str], prim.stringListAttribValue(name)))


def prim_matrix(prim: hou.Prim, name: str) -> Optional[hou.Matrix4]:
    """Read a transform attribute a VEX pass wrote, when that pass wrote one."""
    if prim.geometry().findPrimAttrib(name) is None:
        return None
    return _matrix(prim.attribValue(name))


def add_string_attribs(
    geometry: hou.Geometry, attrib_type: hou.EnumValue, names: Sequence[str]
) -> None:
    """Create string attributes with an empty default; existing ones are kept."""
    for name in names:
        geometry.addAttrib(attrib_type, name, "")


def set_global_attrib(geometry: hou.Geometry, name: str, value: str) -> None:
    """Write a global attribute, creating it when the geometry lacks it."""
    if geometry.findGlobalAttrib(name) is None:
        geometry.addAttrib(hou.attribType.Global, name, "")
    geometry.setGlobalAttribValue(name, value)


def _matrix(value: Any) -> Optional[hou.Matrix4]:
    """Read a transform stored either as a matrix or as sixteen floats."""
    if isinstance(value, hou.Matrix4):
        return value
    if isinstance(value, tuple) and len(value) == 16:
        return hou.Matrix4(cast(Sequence[float], value))
    return None


def write_files(node_type: hou.OpNodeType, folder: str, names: tuple[str, ...]):
    """Write the asset's embedded files to disk so VEX can include them."""
    definition = node_type.definition()
    if definition is None:
        raise hou.OperationFailed("This node type has no HDA definition.")
    sections = definition.sections()
    root = hou.text.expandString(folder)
    for name in names:
        section = sections.get(name)
        if section is None:
            continue
        contents = section.contents()
        path = os.path.join(root, *name.split("/"))
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as handle:
                if handle.read() == contents:
                    continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(contents)


def node_geometry(node: hou.Node) -> hou.Geometry:
    """The cooked geometry of a SOP; hou-stubs types the getter as optional."""
    if not isinstance(node, hou.SopNode):
        raise hou.NodeError(f"{node.path()} is not a geometry node.")
    return cast(hou.Geometry, node.geometry())


def unpack_piece(
    geometry: hou.Geometry, primitive: hou.Prim, convert_polysoup: bool = True
) -> hou.Geometry:
    """Copy one primitive out of geometry and unpack it in place."""
    piece = hou.Geometry()
    piece.merge(geometry, prims=hou.Selection((primitive,)))
    return run_verb("unpack", [piece], {"dotransform": False, "convertpolysoup": convert_polysoup})


def pack_geometry(target: hou.Geometry, geometry: hou.Geometry) -> hou.PackedPrim:
    """Store geometry in a packed primitive; hou-stubs lacks this method."""
    return cast(Any, target).createPackedGeometry(geometry)


def set_parm(node: hou.OpNode, name: str, value: Optional[str]) -> None:
    """Set a parm if the node has it; None becomes the empty string."""
    parm = node.parm(name)
    if parm is not None:
        parm.set("" if value is None else str(value))


def set_multiparm(
    node: hou.OpNode, name: str, parms: Mapping[str, Sequence[Optional[str]]]
) -> None:
    """Resize a multiparm to the column length and fill every instance of every parm."""
    count = node.parm(name)
    columns = list(parms.values())
    if count is None or not columns:
        return
    count.set(len(columns[0]))
    for parm_name, values in parms.items():
        for index, value in enumerate(values, start=1):
            set_parm(node, f"{parm_name}{index}", value)


def absolute_path(value: str) -> str:
    """Expand Houdini variables and normalise slashes; empty value stays empty."""
    if not value:
        return ""
    return os.path.abspath(hou.text.expandString(value)).replace("\\", "/")


def sop_verb(node_type: str) -> hou.SopVerb:
    """Get the verb of a SOP type, so its code can run on geometry in memory."""
    verb = hou.sopNodeTypeCategory().nodeVerb(node_type)
    if verb is None:
        raise hou.NodeError(f"The {node_type} SOP type is unavailable.")
    return cast(hou.SopVerb, verb)


def node_verb(node: hou.SopNode) -> hou.SopVerb:
    """Get the verb of an existing node, initialized with its parameters."""
    verb = node.verb()
    if verb is None:
        raise hou.NodeError(f"The {node.type().name()} node type has no verb.")
    verb.loadParmsFromNode(node)
    return verb


def execute_verb(verb: hou.SopVerb, inputs: Sequence[hou.Geometry]) -> hou.Geometry:
    """Run a prepared verb over input geometry and return its output."""
    output = hou.Geometry()
    verb.execute(output, list(inputs))
    return output


def run_verb(
    node_type: str, inputs: Sequence[hou.Geometry], params: Optional[Mapping[str, Any]] = None
) -> hou.Geometry:
    """Run a verb of the given SOP type over input geometry."""
    verb = sop_verb(node_type)
    if params:
        verb.setParms(params)
    return execute_verb(verb, inputs)


def source_path(path: str | None) -> str:
    """Expand a Houdini source path and normalise its separators."""
    return hou.text.expandString(path or "").replace("\\", "/")
