"""
Redshift node material implementation for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

from __future__ import annotations
from src.materials.jb_base_node_material import JbBaseNodeMaterial

RS_ID = "com.redshift3d.redshift4c4d"
RS_NODESPACE = f"{RS_ID}.class.nodespace"
RS_CORE = f"{RS_ID}.nodes.core"
RS_OUTPUT = f"{RS_ID}.node.output"
RS_MATERIAL = f"{RS_CORE}.material"
RS_TEX = f"{RS_CORE}.texturesampler"
RS_BUMPMAP = f"{RS_CORE}.bumpmap"
RS_DISPLACEMENT = f"{RS_CORE}.displacement"

# Порты RS Material
RS_PORT_SURFACE = f"{RS_OUTPUT}.surface"
RS_PORT_DIFFUSE = f"{RS_MATERIAL}.diffuse_color"
RS_PORT_BUMP = f"{RS_MATERIAL}.bump_input"
RS_PORT_ROUGHNESS = f"{RS_MATERIAL}.refl_roughness"
RS_PORT_EMISSIVE = f"{RS_MATERIAL}.emissive_color"
RS_PORT_METALNESS = f"{RS_MATERIAL}.refl_metalness"
RS_PORT_DISP_OUT = f"{RS_OUTPUT}.displacement"
RS_PORT_DISP_TEX = f"{RS_DISPLACEMENT}.texmap"
RS_PORT_BUMP_IN = f"{RS_BUMPMAP}.input"
RS_PORT_TEX_FILE = f"{RS_TEX}.tex0"
RS_PORT_TEX_PATH_SUB = "path"


class JbRedshiftNodeMaterial(JbBaseNodeMaterial):
    """Redshift for C4D — node material."""

    def nodespace_id(self) -> str:
        return RS_NODESPACE

    @property
    def _material(self):
        node, _ = self.find_or_add_node(self._graph, RS_MATERIAL)

        self._connect_port(self.get_output_ports(node), self._output, RS_PORT_SURFACE)
        return node

    @property
    def _output(self):
        return self.find_or_add_node(self._graph, RS_OUTPUT)[0]

    def _make_texture_node(self, channel: str, path: str):
        node = self._make_labeled_node(self._graph, RS_TEX, channel)
        port = self.get_input_ports(node, [RS_PORT_TEX_FILE, RS_PORT_TEX_PATH_SUB])
        if port is not None:
            port.SetDefaultValue(self.path_to_url(path))
        out = self.get_output_ports(node)
        return out

    def _wire_basecolor(self, path) -> None:
        tex_out = self._make_texture_node("basecolor", path)
        if tex_out is None:
            return
        self._connect_port(tex_out, self._material, RS_PORT_DIFFUSE)

    def _wire_normal(self, path) -> None:
        tex_out = self._make_texture_node("normal", path)
        if tex_out is None:
            return
        bump, _ = self.find_or_add_node(self._graph, RS_BUMPMAP)
        self._connect_port(tex_out, bump, RS_PORT_BUMP_IN)
        bump_out = self.get_output_ports(bump)
        if bump_out is not None:
            self._connect_port(bump_out, self._material, RS_PORT_BUMP)

    def _wire_roughness(self, path) -> None:
        tex_out = self._make_texture_node("roughness", path)
        if tex_out is None:
            return
        self._connect_port(tex_out, self._material, RS_PORT_ROUGHNESS)

    def _wire_metallic(self, path) -> None:
        tex_out = self._make_texture_node("metallic", path)
        if tex_out is None:
            return
        self._connect_port(tex_out, self._material, RS_PORT_METALNESS)

    def _wire_emissive(self, path) -> None:
        tex_out = self._make_texture_node("emissive", path)
        if tex_out is None:
            return
        self._connect_port(tex_out, self._material, RS_PORT_EMISSIVE)

    def _wire_height(self, path) -> None:
        tex_out = self._make_texture_node("height", path)
        if tex_out is None:
            return
        disp, _ = self.find_or_add_node(self._graph, RS_DISPLACEMENT)
        self._connect_port(tex_out, disp, RS_PORT_DISP_TEX)
        disp_out = self.get_output_ports(disp)
        if disp_out is not None:
            self._connect_port(disp_out, self._output, RS_PORT_DISP_OUT)
