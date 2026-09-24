"""
Standard renderer node material implementation for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

from __future__ import annotations

from src.materials.jb_base_node_material import JbBaseNodeMaterial

C4D_NODESPACE = "net.maxon.nodespace.standard"
C4D_BSDF = "net.maxon.render.node.bsdf"
C4D_IMAGE = "net.maxon.pattern.node.generator.image"
C4D_END = "net.maxon.render.node.material"

# BSDF node input port IDs (short names)
PORT_BSDF_COLOR = "color"
PORT_BSDF_ROUGHNESS = "roughness"
PORT_BSDF_NORMAL = "normal"
PORT_BSDF_METALNESS = "reflectionstrength"  # closest analog in Standard renderer

# Material end node input port IDs
PORT_MAT_EMISSION = "emission"
PORT_MAT_ALPHA = "alpha"
PORT_MAT_DISPLACEMENT = "displacement"
PORT_MAT_TRANSPARENCY = "transparency"
PORT_MAT_BSDFLAYERS = "bsdflayers"
PORT_MAT_BSDFLAYER = "bsdflayer"


# Image node port IDs
PORT_IMG_URL = "url"
PORT_IMG_RESULT = "result"


class JbStandardNodeMaterial(JbBaseNodeMaterial):
    """C4D Native Standard Renderer — node material."""

    def nodespace_id(self) -> str:
        return C4D_NODESPACE

    @property
    def _bsdf(self):
        bsdf, _ = self.find_or_add_node(self._graph, C4D_BSDF)

        self._connect_port(
            self.get_output_ports(bsdf),
            self._end,
            [PORT_MAT_BSDFLAYERS, 0, PORT_MAT_BSDFLAYER],
        )
        return bsdf

    @property
    def _end(self):
        end, _ = self.find_or_add_node(self._graph, C4D_END)
        return end

    def _make_image_node(self, channel: str, path: str):
        node = self._make_labeled_node(self._graph, C4D_IMAGE, channel)
        port = self.get_input_ports(node, PORT_IMG_URL)
        if port is not None and not port.IsNullValue():
            port.SetDefaultValue(self.path_to_url(path))

        out = self.get_output_ports(node, PORT_IMG_RESULT)
        return out

    def _wire_basecolor(self, path) -> None:
        img_out = self._make_image_node("basecolor", path)
        if img_out is None:
            return
        self._connect_port(img_out, self._bsdf, PORT_BSDF_COLOR)

    def _wire_roughness(self, path) -> None:
        img_out = self._make_image_node("roughness", path)
        if img_out is None:
            return
        self._connect_port(img_out, self._bsdf, PORT_BSDF_ROUGHNESS)

    def _wire_normal(self, path) -> None:
        img_out = self._make_image_node("normal", path)
        if img_out is None:
            return
        self._connect_port(img_out, self._bsdf, PORT_BSDF_NORMAL)

    def _wire_emissive(self, path) -> None:
        img_out = self._make_image_node("emissive", path)
        if img_out is None:
            return
        self._connect_port(img_out, self._end, PORT_MAT_EMISSION)

    def _wire_opacity(self, path) -> None:
        img_out = self._make_image_node("opacity", path)
        if img_out is None:
            return
        self._connect_port(img_out, self._end, PORT_MAT_ALPHA)

    def _wire_height(self, path) -> None:
        img_out = self._make_image_node("height", path)
        if img_out is None:
            return
        self._connect_port(img_out, self._end, PORT_MAT_DISPLACEMENT)

    def _wire_refraction(self, path) -> None:
        img_out = self._make_image_node("refraction", path)
        if img_out is None:
            return
        self._connect_port(img_out, self._end, PORT_MAT_TRANSPARENCY)
