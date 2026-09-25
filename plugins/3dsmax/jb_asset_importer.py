from pymxs import runtime as rt


class JB_AssetImporter:
    def __init__(self, api, material_importer):
        self.api = api
        self.material_importer = material_importer

    def import_asset(self, asset=None) -> bool:
        if not asset:
            return self._import_active_asset()

        return self._create_model(asset)

    def _import_active_asset(self):
        asset = self.api.get_active_asset()
        if not asset:
            print("Could not get active asset")
            return False

        if asset.asset_type == "MODEL":
            return self._create_model(asset)
        elif asset.asset_type == "MATERIAL":
            return self.material_importer.import_material(asset)
        else:
            print(f"Unsupported asset type: {asset.asset_type}")
            return False

    def _create_model(self, asset):
        ext = asset.ext

        if ext == '.fbx':
            return self._import_fbx(asset.asset_path)
        elif ext == '.abc':
            return self._import_alembic(asset.asset_path)
        else:
            print(f"Unsupported file type: {ext}")
            return False

    def _import_fbx(self, file_path: str):
        """Imports an FBX file"""
        try:
            rt.FBXImporterSetParam("Mode", rt.name("merge"))
            rt.FBXImporterSetParam("ScaleConversion", True)
            rt.FBXImporterSetParam("UpAxis", rt.name("Z"))
            rt.FBXImporterSetParam("ConvertUnit", "m")
            rt.FBXImporterSetParam("AxisConversionMethod", rt.name("convertAnimation"))
            rt.FBXImporterSetParam("Animation", True)
            rt.FBXImporterSetParam("Cameras", True)
            rt.FBXImporterSetParam("Lights", True)
            rt.FBXImporterSetParam("Materials", True)
            rt.FBXImporterSetParam("Textures", True)
            rt.FBXImporterSetParam("SmoothingGroups", True)

            rt.importFile(file_path, rt.name("noPrompt"), using=rt.FBXIMP)

        except Exception as e:
            print(f"Error importing FBX: {e}")
            return False

    def _import_alembic(self, file_path: str) -> bool:
        """Imports an Alembic file"""
        try:
            if rt.classof(rt.AlembicImport) != rt.UndefinedClass:
                alembic_importer = rt.AlembicImport()
                alembic_importer.filename = file_path
                result = alembic_importer.importToScene()

                if not result:
                    print(f"Ошибка импорта Alembic файла: {file_path}")
                    return False
            else:
                print("Alembic not available")
                return False

        except Exception as e:
            print(f"Error importing Alembic: {e}")
            return False
