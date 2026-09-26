"""The VEX layer: every program the asset runs on geometry, and the runner."""

import hou
from jiko_bridge_houdini.jb_utils import run_verb

VEX_FILES = "$HOUDINI_TEMP_DIR/jiko/jiko_bridge"
VEX_RUN_OVER = {"detail": 0, "prim": 1, "point": 2, "vertex": 3, "number": 4}
PLACEHOLDER_GROUP = "jiko_placeholders"
FBX_VEX = "\nstring names[] = {};\nmatrix transform;\nif (jb_fbx_extract_placeholder(0, @primnum, names, transform)) {\n    s[]@jiko_names = names;\n    4@jiko_transform = transform;\n    @group_jiko_placeholders = 1;\n}\n"
ABC_VEX = "\nstring names[] = {};\nmatrix transform;\nif (jb_abc_extract_placeholder(0, @primnum, names, transform)) {\n    s[]@jiko_names = names;\n    4@jiko_transform = transform;\n    @group_jiko_placeholders = 1;\n}\n"


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
