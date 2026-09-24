"""
Arnold node material implementation for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

from __future__ import annotations

from src.materials.jb_base_node_material import JbBaseNodeMaterial

ARNOLD_NODESPACE = "com.autodesk.arnold.nodespace"
ARNOLD_END = "com.autodesk.arnold.material"
ARNOLD_STANDARD = "com.autodesk.arnold.shader.standard_surface"
ARNOLD_IMAGE = "com.autodesk.arnold.shader.image"
ARNOLD_COLCORRECT = "com.autodesk.arnold.shader.color_correct"
ARNOLD_DISP = "com.autodesk.arnold.shader.displacement"
ARNOLD_NORMALMAP = "com.autodesk.arnold.shader.normal_map"

# Порты standard_surface
PORT_BASE_COLOR = f"{ARNOLD_STANDARD}.base_color"
PORT_NORMAL = f"{ARNOLD_STANDARD}.normal"
PORT_ROUGHNESS = f"{ARNOLD_STANDARD}.specular_roughness"
PORT_METALNESS = f"{ARNOLD_STANDARD}.metalness"
PORT_EMISSION = f"{ARNOLD_STANDARD}.emission"
PORT_EMIS_COLOR = f"{ARNOLD_STANDARD}.emission_color"
PORT_OPACITY = f"{ARNOLD_STANDARD}.opacity"
PORT_TRANSMISSION = f"{ARNOLD_STANDARD}.transmission"
PORT_TRANS_COLOR = f"{ARNOLD_STANDARD}.transmission_color"

# Порты end node
PORT_SHADER_IN = f"{ARNOLD_END}.shader"
PORT_DISP_IN = f"{ARNOLD_END}.displacement"

# Порты вспомогательных нодов
PORT_CC_INPUT = f"{ARNOLD_COLCORRECT}.input"
PORT_CC_MULTIPLY = f"{ARNOLD_COLCORRECT}.multiply"
PORT_NM_INPUT = f"{ARNOLD_NORMALMAP}.input"
PORT_DISP_MAP = f"{ARNOLD_DISP}.normal_displacement_input"
PORT_IMG_FILE = f"{ARNOLD_IMAGE}.filename"


class JbArnoldNodeMaterial(JbBaseNodeMaterial):
    """Arnold node material implementation."""

    def nodespace_id(self) -> str:
        return ARNOLD_NODESPACE

    @property
    def _surface(self):
        surface, _ = self.find_or_add_node(self._graph, ARNOLD_STANDARD)
        self._connect_port(self.get_output_ports(surface), self._end, PORT_SHADER_IN)
        return surface

    @property
    def _end(self):
        return self.find_or_add_node(self._graph, ARNOLD_END)[0]

    def _make_image_node(self, channel: str, path: str):
        node = self._make_labeled_node(self._graph, ARNOLD_IMAGE, channel)
        port = self.get_input_ports(node, PORT_IMG_FILE)
        if port is not None:
            port.SetDefaultValue(self.path_to_url(path))
        out = self.get_output_ports(node)
        return out

    def _wire_basecolor(self, path) -> None:
        img_out = self._make_image_node("basecolor", path)
        if img_out is None:
            return

        correct = self._make_labeled_node(self._graph, ARNOLD_COLCORRECT, "basecolor_correct")

        self._connect_port(img_out, correct, PORT_CC_INPUT)
        self._connect_port(self.get_output_ports(correct), self._surface, PORT_BASE_COLOR)

    def _wire_normal(self, path) -> None:
        img_out = self._make_image_node("normal", path)
        if img_out is None:
            return
        nm, _ = self.find_or_add_node(self._graph, ARNOLD_NORMALMAP)
        self._connect_port(img_out, nm, PORT_NM_INPUT)
        nm_out = self.get_output_ports(nm)
        if nm_out is not None:
            self._connect_port(nm_out, self._surface, PORT_NORMAL)

    def _wire_roughness(self, path) -> None:
        img_out = self._make_image_node("roughness", path)
        if img_out is None:
            return
        self._connect_port(img_out, self._surface, PORT_ROUGHNESS)

    def _wire_metallic(self, path) -> None:
        img_out = self._make_image_node("metallic", path)
        if img_out is None:
            return
        self._connect_port(img_out, self._surface, PORT_METALNESS)

    def _wire_emissive(self, path) -> None:
        img_out = self._make_image_node("emissive", path)
        if img_out is None:
            return
        self._connect_port(img_out, self._surface, PORT_EMIS_COLOR)
        p = self.get_port(self._surface, PORT_EMISSION)
        if p:
            p.SetDefaultValue(1.0)

    def _wire_opacity(self, path) -> None:
        img_out = self._make_image_node("opacity", path)
        if img_out is None:
            return
        self._connect_port(img_out, self._surface, PORT_OPACITY)

    def _wire_refraction(self, path) -> None:
        img_out = self._make_image_node("refraction", path)
        if img_out is None:
            return
        self._connect_port(img_out, self._surface, PORT_TRANS_COLOR)
        p = self.get_port(self._surface, PORT_TRANSMISSION)
        if p:
            p.SetDefaultValue(1.0)

    def _wire_height(self, path) -> None:
        img_out = self._make_image_node("height", path)
        if img_out is None:
            return
        disp, _ = self.find_or_add_node(self._graph, ARNOLD_DISP)
        self._connect_port(img_out, disp, PORT_DISP_MAP)
        disp_out = self.get_output_ports(disp)
        if disp_out is not None:
            self._connect_port(disp_out, self._end, PORT_DISP_IN)

    def _wire_ao(self, path) -> None:
        self._make_image_node("ao", path)
