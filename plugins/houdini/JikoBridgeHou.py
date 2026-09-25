from jb_api import JB_API
from jb_importer import JB_Importer


class JikoBridge:
    def __init__(self):
        self.api = JB_API()
        self.importer = JB_Importer()

    def asset_import(self):
        asset = self.api.get_active_asset()

        if asset:
            self.importer.set_selected_asset(asset)
            self.importer.import_asset()
            return asset

        return None
