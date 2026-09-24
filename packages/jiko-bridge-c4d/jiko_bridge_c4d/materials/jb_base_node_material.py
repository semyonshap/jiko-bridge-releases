"""
Base node material class for Cinema 4D.
Code by Semyon Shapoval, 2026
"""

from __future__ import annotations
from typing import Optional

import c4d
import maxon
from src.jb_utils import get_logger

logger = get_logger(__name__)

ASSET_ID_ATTR = "net.maxon.node.attribute.assetid"
NODE_NAME_ID = "net.maxon.node.base.name"

PortType = str | int
PortsType = PortType | list[PortType]


class JbBaseNodeMaterial:
    """Base node material."""

    def __init__(self):
        self._graph = None

    def nodespace_id(self) -> Optional[str]:
        """Returns the node space ID for this material type, or None if not applicable."""
        raise NotImplementedError

    @staticmethod
    def path_to_url(path: str) -> maxon.Url:
        """Converts a file path to a maxon.Url."""
        normalized = path.replace("\\", "/")
        if not normalized.startswith("/"):
            normalized = "/" + normalized
        return maxon.Url(f"file://{normalized}")

    @staticmethod
    def ensure_graph(material: c4d.BaseMaterial, nodespace_id: str):
        """Возвращает граф, создавая его если нужно."""
        node_mat = material.GetNodeMaterialReference()
        if node_mat is None:
            return None
        if not node_mat.HasSpace(maxon.Id(nodespace_id)):
            node_mat.AddGraph(maxon.Id(nodespace_id))
        return node_mat.GetGraph(maxon.Id(nodespace_id))

    def _make_labeled_node(self, graph, asset_id: str, label: str):
        """Ищет узел с именем label среди узлов asset_id; создаёт, если не найден."""
        for node in self.find_nodes_by_asset_id(graph, asset_id):
            try:
                if str(node.GetValue(NODE_NAME_ID)) == label:
                    return node
            except (AttributeError, TypeError, RuntimeError):
                pass
        node = self.add_node(graph, asset_id)
        try:
            node.SetValue(NODE_NAME_ID, maxon.String(label))
        except (AttributeError, TypeError, RuntimeError):
            pass
        return node

    @staticmethod
    def find_nodes_by_asset_id(graph, asset_id: str) -> list:
        """Ищет все узлы с данным asset ID через официальный GraphModelHelper.
        При неудаче — fallback через ручной обход дочерних узлов."""
        result: list[object] = []
        try:
            maxon.GraphModelHelper.FindNodesByAssetId(graph, maxon.Id(asset_id), True, result)
        except (RuntimeError, TypeError, AttributeError):
            pass

        if not result:
            for child in graph.GetRoot().GetChildren():
                if not child.IsInner():
                    continue
                try:
                    aid_val = child.GetValue(maxon.Id(ASSET_ID_ATTR))
                    aid = str(aid_val[0]) if aid_val else ""
                    if asset_id in aid:
                        result.append(child)
                except (RuntimeError, TypeError, AttributeError, ValueError):
                    continue

        return result

    @staticmethod
    def find_node(graph, asset_id: str):
        """Возвращает первый узел с данным asset ID или None."""
        result = JbBaseNodeMaterial.find_nodes_by_asset_id(graph, asset_id)
        return result[0] if result else None

    @staticmethod
    def add_node(graph, asset_id: str):
        """Добавляет новый узел в граф."""
        return graph.AddChild(maxon.Id(), maxon.Id(asset_id))

    @staticmethod
    def find_or_add_node(graph, asset_id: str):
        """Ищет узел, создаёт если не найден. Возвращает (node, was_created)."""
        node = JbBaseNodeMaterial.find_node(graph, asset_id)
        if node is not None:
            return node, False
        return JbBaseNodeMaterial.add_node(graph, asset_id), True

    @staticmethod
    def get_port(inputs, port_id: PortType):
        """Возвращает входной порт узла.

        Стратегия:
        1. InternedId — Redshift (порты зарегистрированы в C4D-реестре).
        2. maxon.Id — Arnold и другие сторонние рендеры (оригинальный способ).
        3. Итерация GetChildren() — последний fallback по short ID.
        """

        if isinstance(port_id, int):
            children = inputs.GetChildren()
            return children[port_id] if port_id < len(children) else None

        try:
            port = inputs.FindChild(maxon.InternedId(port_id))
            if port and not port.IsNullValue():
                return port
        except (RuntimeError, TypeError, AttributeError):
            pass

        try:
            port = inputs.FindChild(maxon.Id(port_id))
            if port and not port.IsNullValue():
                return port
        except (RuntimeError, TypeError, AttributeError):
            pass

        # Fallback: поиск по короткому имени порта
        short_id = port_id.rsplit(".", 1)[-1]
        for child in inputs.GetChildren():
            try:
                child_id = str(child.GetId())
                if child_id in (port_id, short_id):
                    return child
            except (RuntimeError, TypeError, AttributeError):
                continue

        return None

    @staticmethod
    def get_ports(inputs, port_ids: PortsType):
        """Traverse node inputs by a chain of port IDs and return the final port."""
        current = inputs

        if isinstance(port_ids, PortType):
            port_ids = [port_ids]

        for port_id in port_ids:
            if current is None:
                return None
            current = JbBaseNodeMaterial.get_port(current, port_id)
            if current is None:
                return None
        return current

    @staticmethod
    def get_input_ports(node, port_ids: PortsType):
        """Return the input port of a node by ID."""
        return JbBaseNodeMaterial.get_ports(node.GetInputs(), port_ids)

    @staticmethod
    def get_output_ports(node, port_ids: PortsType = 0):
        """Return the output port of a node by ID."""
        return JbBaseNodeMaterial.get_ports(node.GetOutputs(), port_ids)

    def _disconnect_all(self, port) -> bool:
        """Disconnects all connections from the given port."""
        if port is None:
            return False
        if port.IsNullValue():
            return False

        port.RemoveConnections(maxon.PORT_DIR.INPUT, maxon.Wires.All())

        return True

    def _connect_port(self, out_port, node, port_ids: PortsType) -> bool:
        """Соединяет out_port с входным портом port_id узла node."""
        if out_port is None or node is None:
            return False
        inp = self.get_input_ports(node, port_ids)
        if inp is None:
            return False

        self._disconnect_all(inp)
        out_port.Connect(inp)
        return True

    def _wire_channel(self, channel: str, path: str) -> None:
        """Подключить канал к нужным портам материала."""
        method = getattr(self, f"_wire_{channel}", None)
        if method is not None:
            method(path)

    def apply_channel(
        self,
        material: c4d.BaseMaterial,
        channel: str,
        path: str,
    ):
        """Apply a texture channel to the material."""
        nodespace = self.nodespace_id()
        if nodespace is None:
            logger.error("Node space ID is not defined for this material type.")
            return

        self._graph = self.ensure_graph(material, nodespace)
        if self._graph is None:
            logger.error("Material does not have the expected node space.")
            return

        with self._graph.BeginTransaction() as t:
            self._wire_channel(channel, path)
            t.Commit()

        material.Update(True, True)
