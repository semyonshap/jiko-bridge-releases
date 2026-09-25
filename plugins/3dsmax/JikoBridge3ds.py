import os
import sys


def load_plugin_modules():
    plugin_dir = os.path.abspath(os.path.dirname(__file__))
    bridge_dir = os.path.abspath(os.path.join(plugin_dir, "..", "bridge"))

    for p in (plugin_dir, bridge_dir):
        if p not in sys.path:
            sys.path.insert(0, p)

    return [plugin_dir, bridge_dir]


python_modules = load_plugin_modules()

from jb_api import JB_API
from jb_asset_importer import JB_AssetImporter
from jb_material_importer import JB_MaterialImporter


class JikoBridge:
    def __init__(self):
        self.api = JB_API()
        self.material_importer = JB_MaterialImporter()
        self.importer = JB_AssetImporter(self.api, self.material_importer)

    def import_asset(self):
        return self.importer.import_asset()


bridge = JikoBridge()
