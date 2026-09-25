import bpy

from jiko_bridge_client import get_logger

from .jb_base_node_material import JBBaseNodeMaterial

logger = get_logger(__name__)

NODE_OUTPUT = "ShaderNodeOutputMaterial"
NODE_OUTPUT_NAME = "Material Output"

NODE_BSDF = "ShaderNodeBsdfPrincipled"
NODE_BSDF_NAME = "Principled BSDF"

NODE_TEX_IMAGE = "ShaderNodeTexImage"


class JBStandardMaterial(JBBaseNodeMaterial):
    """Principled BSDF node material for Blender."""

    @property
    def _nodes(self):
        return self._mat.node_tree.nodes

    @property
    def _links(self):
        return self._mat.node_tree.links

    @property
    def _output(self):
        output = self._nodes.get(NODE_OUTPUT_NAME)
        if output is None:
            output = self._nodes.new(NODE_OUTPUT)
            output.name = NODE_OUTPUT_NAME
            output.location = (600, 0)
        return output

    @property
    def _bsdf(self):
        bsdf = self._nodes.get(NODE_BSDF_NAME)
        if bsdf is None:
            bsdf = self._nodes.new(NODE_BSDF)
            self._links.new(bsdf.outputs["BSDF"], self._output.inputs["Surface"])
            bsdf.location = (300, 0)
        return bsdf

    def _make_texture_node(
        self, channel: str, path: str, color_space: str = "sRGB"
    ) -> bpy.types.Node:
        """Find existing texture node for channel or create a new one."""
        node = self._nodes.get(channel)
        if node is None:
            node = self._nodes.new(NODE_TEX_IMAGE)
            node.name = channel
        try:
            img = bpy.data.images.load(path, check_existing=True)
            if color_space != "sRGB":
                img.colorspace_settings.name = "Non-Color"
            node.image = img
        except RuntimeError as e:
            logger.warning("Failed to load texture '%s': %s", path, e)
        return node

    def _wire_basecolor(self, path: str) -> None:
        tex = self._make_texture_node("basecolor", path, "sRGB")
        self._links.new(tex.outputs["Color"], self._bsdf.inputs["Base Color"])

    def _wire_metallic(self, path: str) -> None:
        tex = self._make_texture_node("metallic", path, "Non-Color")
        self._links.new(tex.outputs["Color"], self._bsdf.inputs["Metallic"])

    def _wire_roughness(self, path: str) -> None:
        tex = self._make_texture_node("roughness", path, "Non-Color")
        self._links.new(tex.outputs["Color"], self._bsdf.inputs["Roughness"])

    def _wire_normal(self, path: str) -> None:
        tex = self._make_texture_node("normal", path, "Non-Color")
        normal_map = self._nodes.get("normal_map")
        if normal_map is None:
            normal_map = self._nodes.new("ShaderNodeNormalMap")
            normal_map.name = "normal_map"
        self._links.new(tex.outputs["Color"], normal_map.inputs["Color"])
        self._links.new(normal_map.outputs["Normal"], self._bsdf.inputs["Normal"])

    def _wire_emissive(self, path: str) -> None:
        tex = self._make_texture_node("emissive", path, "sRGB")
        self._links.new(tex.outputs["Color"], self._bsdf.inputs["Emission Color"])
        self._bsdf.inputs["Emission Strength"].default_value = 1.0

    def _wire_opacity(self, path: str) -> None:
        tex = self._make_texture_node("opacity", path, "Non-Color")
        self._links.new(tex.outputs["Color"], self._bsdf.inputs["Alpha"])
        self._mat.blend_method = "HASHED"

    def _wire_height(self, path: str) -> None:
        tex = self._make_texture_node("height", path, "Non-Color")
        disp_node = self._nodes.get("displacement")
        if disp_node is None:
            disp_node = self._nodes.new("ShaderNodeDisplacement")
            disp_node.name = "displacement"
        self._links.new(tex.outputs["Color"], disp_node.inputs["Height"])
        self._links.new(disp_node.outputs["Displacement"], self._output.inputs["Displacement"])

    def _wire_ao(self, path: str) -> None:
        ao_tex = self._make_texture_node("ao", path, "Non-Color")
        base_tex = self._nodes.get("basecolor")
        if base_tex is None:
            return
        mix = self._nodes.get("ao_mix")
        if mix is None:
            mix = self._nodes.new("ShaderNodeMixRGB")
            mix.name = "ao_mix"
        mix.blend_type = "MULTIPLY"
        mix.inputs["Fac"].default_value = 1.0
        self._links.new(base_tex.outputs["Color"], mix.inputs["Color1"])
        self._links.new(ao_tex.outputs["Color"], mix.inputs["Color2"])
        self._links.new(mix.outputs["Color"], self._bsdf.inputs["Base Color"])
