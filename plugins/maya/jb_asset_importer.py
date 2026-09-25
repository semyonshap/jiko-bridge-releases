import os

import maya.cmds as cmds
from jb_asset_model import AssetModel


class JB_AssetImporter:
    def import_asset(self, asset: AssetModel) -> bool:
        file_ext = os.path.splitext(asset.asset_path)[1].lower()

        try:
            if file_ext in ['.fbx']:
                return self.import_fbx(asset.asset_path)
            elif file_ext in ['.abc']:
                return self.import_alembic(asset.asset_path)
            else:
                print(f"Неподдерживаемый тип файла: {file_ext}")
                return False

        except Exception as e:
            print(f"Ошибка при импорте: {e}")
            return False

    def import_fbx(self, file_path: str) -> bool:
        """Импортирует FBX файл"""
        try:
            cmds.file(
                file_path,
                i=True,
                type="FBX",
                ignoreVersion=True,
                ra=True,
                mergeNamespacesOnClash=False,
                options="fbx",
                pr=True,
            )
            print(f"Import FBX: {file_path}")
            return True
        except Exception as e:
            print(f"Ошибка импорта FBX: {e}")
            return False

    def import_alembic(self, file_path: str) -> bool:
        """Импортирует Alembic файл"""
        try:
            cmds.AbcImport(file_path, mode="import")
            print(f"Импортирован Alembic: {file_path}")
            return True
        except Exception as e:
            print(f"Ошибка импорта Alembic: {e}")
            return False
