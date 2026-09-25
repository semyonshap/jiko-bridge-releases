import hou
from jb_asset_model import AssetModel


class JB_Importer:
    def __init__(self):
        self.selected_asset = None

    def set_selected_asset(self, asset: AssetModel):
        """Set the currently selected asset"""
        self.selected_asset = asset

    def import_asset(self):
        """Import selected asset into LOP context by creating file node with USD path"""
        if not self.selected_asset:
            hou.ui.displayMessage("No asset selected for import")
            return False

        try:
            usd_path = self.selected_asset.asset_path

            if not usd_path:
                hou.ui.displayMessage(
                    f"USD file not found for asset: {self.selected_asset.asset_name}",
                    severity=hou.severityType.Warning,
                )
                return False

            lop_context = self.get_or_default_lop_context()

            if not lop_context:
                hou.ui.displayMessage(
                    "Failed to access or create LOP context", severity=hou.severityType.Error
                )
                return False

            file_node = self.create_sublayer_node(lop_context, usd_path)

            if file_node:
                self.navigate_to_lop_context(lop_context)
                return True

            return False

        except Exception as e:
            hou.ui.displayMessage(
                f"Error importing asset: {str(e)}", severity=hou.severityType.Error
            )
            return False

    def get_or_default_lop_context(self):
        """Get active LOP context or add directly to /stage"""
        try:
            network_editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
            if network_editor:
                current_node = network_editor.pwd()
                if current_node and current_node.childTypeCategory().name() == "Lop":
                    return current_node

            selected_nodes = hou.selectedNodes()
            if selected_nodes:
                for node in selected_nodes:
                    if node.type().category().name() == "Lop":
                        return node.parent()

            stage_context = hou.node("/stage")
            return stage_context

        except Exception as e:
            print(f"Error accessing LOP context: {e}")
            return hou.node("/stage")

    def create_sublayer_node(self, lop_context, usd_path):
        """Create file node in LOP context with USD path"""
        try:
            file_node = lop_context.createNode(
                "sublayer", f"{self.selected_asset.asset_name}_import"
            )

            file_node.parm("filepath1").set(str(usd_path))

            file_node.moveToGoodPosition()

            file_node.setDisplayFlag(True)

            file_node.setSelected(True, clear_all_selected=True)

            return file_node

        except Exception as e:
            print(f"Error creating file node: {e}")
            hou.ui.displayMessage(
                f"Error creating file node: {str(e)}", severity=hou.severityType.Error
            )
            return None

    def navigate_to_lop_context(self, lop_context):
        """Navigate network view to specific LOP context"""
        try:
            network_editor = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
            if network_editor:
                network_editor.setPwd(lop_context)
                return True
        except Exception as e:
            print(f"Error navigating to LOP context: {e}")
            return False
