"""
Materials module for Jiko Bridge Cinema 4D plugin.
Code by Semyon Shapoval, 2026
"""

from src.materials.jb_base_node_material import JbBaseNodeMaterial

from src.materials.jb_standard_node_material import JbStandardNodeMaterial
from src.materials.jb_redshift_node_material import JbRedshiftNodeMaterial
from src.materials.jb_arnold_node_material import JbArnoldNodeMaterial

__all__ = [
    "JbBaseNodeMaterial",
    "JbRedshiftNodeMaterial",
    "JbArnoldNodeMaterial",
    "JbStandardNodeMaterial",
]
