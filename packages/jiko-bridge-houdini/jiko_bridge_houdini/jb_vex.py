"""The VEX layer: every program the asset runs on geometry, and the runner."""

import hou
from jiko_bridge_houdini.jb_utils import run_verb

VEX_FILES = "$HOUDINI_TEMP_DIR/jiko/jiko_bridge"
VEX_RUN_OVER = {"detail": 0, "prim": 1, "point": 2, "vertex": 3, "number": 4}
PLACEHOLDER_GROUP = "jiko_placeholders"
_PLACEHOLDER_VEX = """
string names[] = {};
matrix transform;
if (JB_EXTRACT(0, @primnum, names, transform)) {
    s[]@jiko_names = names;
    4@jiko_transform = transform;
    @group_jiko_placeholders = 1;
}
"""


def marker_vex(extract_function: str) -> str:
    """VEX marker that collects placeholders through an embedded library call."""
    return _PLACEHOLDER_VEX.replace("JB_EXTRACT", extract_function)


FBX_VEX = marker_vex("jb_fbx_extract_placeholder")
ABC_VEX = marker_vex("jb_abc_extract_placeholder")


def vex_snippet(body: str, library: str = "lib.vfl") -> str:
    """Prefix VEX code with the include of the asset's embedded VEX library."""
    return f'#include "{VEX_FILES}/{library}"\n\n{body}'


def run_vex(geometry: hou.Geometry, body: str, run_over: str = "point") -> hou.Geometry:
    """Run a VEX snippet on geometry in memory, without a node in the scene."""
    return run_verb(
        "attribvop",
        [geometry],
        {"vexsrc": 3, "vexsnippet": vex_snippet(body), "bindclass": VEX_RUN_OVER[run_over]},
    )
