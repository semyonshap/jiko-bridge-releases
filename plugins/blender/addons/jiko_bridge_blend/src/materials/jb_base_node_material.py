"""
Base node material class for Blender.
Code by Semyon Shapoval, 2026
"""

from __future__ import annotations

from collections import defaultdict

import bpy

COL_WIDTH = 300
ROW_HEIGHT = 320


class JBBaseNodeMaterial:
    """Base node material for Blender node graphs."""

    def __init__(self, material: bpy.types.Material):
        self._mat = material

    @property
    def _nodes(self):
        return self._mat.node_tree.nodes

    @property
    def _links(self):
        return self._mat.node_tree.links

    def _wire_channel(self, channel: str, path: str) -> None:
        method = getattr(self, f"_wire_{channel}", None)
        if method is not None:
            method(path)

    def apply_channel(self, channel: str, path: str) -> None:
        """Apply a texture channel to the material."""
        self._wire_channel(channel, path)
        self.clear_orphans()
        self.auto_layout()

    def clear_orphans(self) -> None:
        """Remove nodes with no connected inputs or outputs."""
        to_remove = [
            node
            for node in self._nodes
            if not any(s.is_linked for s in node.inputs)
            and not any(s.is_linked for s in node.outputs)
        ]
        for node in to_remove:
            self._nodes.remove(node)

    def auto_layout(self) -> None:
        """Automatically arranges nodes from left to right based on depth in the graph."""
        if self._mat is None:
            return

        nodes = self._nodes

        def get_depth(node, visited=None):
            if visited is None:
                visited = set()
            if node.name in visited:
                return 0
            visited.add(node.name)
            input_nodes = [link.from_node for socket in node.inputs for link in socket.links]
            if not input_nodes:
                return 0
            return 1 + max(get_depth(n, visited) for n in input_nodes)

        columns: dict[int, list[bpy.types.Node]] = defaultdict(list)
        for node in nodes:
            depth = get_depth(node)
            columns[depth].append(node)

        max_depth = max(columns.keys(), default=0)

        for depth, col_nodes in columns.items():
            x = (depth - max_depth) * COL_WIDTH
            for row, node in enumerate(col_nodes):
                y = -row * ROW_HEIGHT
                node.location = (x, y)
