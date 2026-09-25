class JB_MaterialImporter:
    def __init__(self):
        pass

    def _create_arnold_material(self, asset):
        print(f"Creating Arnold material for asset: {asset}")
        channels = asset.get_textures()

        for channel in channels:
            print(f" - Channel: {channel}")

    def import_material(self, asset):
        self._create_arnold_material(asset)
