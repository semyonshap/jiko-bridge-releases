"""
Base integration test flows for Jiko Bridge.
Code by Semyon Shapoval, 2026
"""

import os
import sys
import uuid
import unittest
import importlib.util
from typing import Any
from unittest.mock import patch

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, root_dir)

# pylint: disable=wrong-import-position disable=import-error

from tests.integration.scene.base_scene import BaseScene
from tests.integration.utils import get_logger, make_injected_create_asset, file_exists

if importlib.util.find_spec("c4d") is not None:
    from tests.integration.scene.c4d_scene import Scene
elif importlib.util.find_spec("bpy") is not None:
    from tests.integration.scene.blend_scene import Scene  # type: ignore[assignment]
else:
    raise ImportError("Environment not supported.")


if importlib.util.find_spec("c4d") is not None:
    from plugins.cinema4d.src.jb_types import AssetModel, AssetFile
elif importlib.util.find_spec("bpy") is not None:
    from plugins.blender.addons.jiko_bridge_blend.src.jb_types import (  # type: ignore[assignment]
        AssetModel,
        AssetFile,
    )
else:
    raise ImportError("Environment not supported.")

log = get_logger(__name__)


class BaseJikoBridgeTests(unittest.TestCase):
    """Abstract base class with all shared Jiko Bridge test flows."""

    @property
    def _suffix(self) -> str:
        return uuid.uuid4().hex[:6]

    def _make_scene(self) -> BaseScene:
        return Scene()

    def _make_asset(
        self,
        asset_name: str | None = None,
        asset_type="model",
        bridge_type="model",
    ):
        return AssetModel(
            database_name="test-local",
            pack_name="test",
            asset_name=f"test_{self._suffix}" if asset_name is None else asset_name,
            files=[AssetFile(asset_type=asset_type, bridge_type=bridge_type)],
        )

    def setUp(self) -> None:
        log.info("Setting up Jiko Bridge integration test.")
        self.scene = self._make_scene()
        self.scene.reset_scene()
        self.scene.ensure_loaded()

        self.asset_1 = self._make_asset()
        self.asset_2 = self._make_asset()
        self.asset_3 = self._make_asset()
        self.asset_mat_1 = self._make_asset(
            asset_name="test_mat", asset_type="basecolor", bridge_type="material"
        )

    def exist_files(self, asset: AssetModel):
        """Wait for files on disk system."""
        asset_updated = self.get_asset(asset)
        if asset_updated:
            for f in asset_updated.files:
                if f.filepath:
                    self.assertTrue(
                        file_exists(f.filepath),
                        f"Updated asset file should appear on disk: {f.filepath}",
                    )

    def tearDown(self) -> None:
        try:
            path = self.scene.save_document("test_flows_teardown")
            if not path:
                log.error("Failed to save during tearDown.")
                return
            log.info("Saved for diagnostics: %s", path)
        except RuntimeError as exc:
            log.error("Failed to save tearDown: %s", exc)

    def export_flow(self, asset_model: Any) -> Any:
        """Export new asset."""
        api_module = self.scene.import_module("jb_api")
        self.assertIsNotNone(api_module)

        original_create_asset = api_module.JbAPI.create_asset
        asset_capture, injected_create_asset = make_injected_create_asset(
            asset_model, original_create_asset
        )

        with patch.object(
            api_module.JbAPI,
            "create_asset",
            autospec=True,
            side_effect=injected_create_asset,
        ):
            self.scene.call_command("export_asset")

        return asset_capture

    def update_flow(self, container: Any) -> None:
        """Update existing asset."""
        self.scene.select_objects([container])

        exporter_module = self.scene.import_module("jb_asset_exporter")
        exporter = exporter_module.JbAssetExporter(self.scene.source)
        export_message = exporter.export_message()
        self.assertIn("update", export_message.lower())

        self.scene.call_command("export_asset")

    def import_active_asset(self, asset_model: Any, count: int = 1):
        """Import active asset"""
        self.scene.clear_selection()

        self.check_import_message("active asset")

        api_module = self.scene.import_module("jb_api")

        def injected_active_asset(*_args: Any, **_kwargs: Any) -> Any:
            return api_module.JbAPI().get_asset(asset_model)

        with patch.object(
            api_module.JbAPI,
            "get_active_asset",
            autospec=True,
            side_effect=injected_active_asset,
        ) as patch_obj:
            for _ in range(count):
                self.scene.call_command("import_asset")

        self.scene.update()
        return patch_obj

    def reimport_flow(self, container: Any) -> None:
        """Reimport asset."""
        self.scene.select_objects([container])
        self.scene.call_command("import_asset")

    def instancing(self, asset_model: Any, count: int = 5):
        """Instance by importing the same asset multiple times."""
        patch_obj = self.import_active_asset(asset_model=asset_model, count=count)
        instances = self.scene.get_instance_objects()
        self.assertEqual(len(instances), count)
        return instances, patch_obj

    def get_asset(self, asset: AssetModel) -> AssetModel:
        """Get asset from api."""
        api_module = self.scene.import_module("jb_api")
        asset = api_module.JbAPI().get_asset(asset)
        self.assertIsNotNone(asset, "Asset should be found")
        return asset

    def check_import_message(self, value: str) -> str:
        """Get import message."""
        importer_module = self.scene.import_module("jb_asset_importer")
        importer = importer_module.JbAssetImporter(self.scene.source)
        msg = importer.import_message()

        self.assertIn(value, msg.lower())

        return msg

    def import_material(self, asset: AssetModel) -> None:
        """Import by selected objects"""

        asset = self.get_asset(asset)
        for f in asset.files:
            if f.filepath:
                self.assertTrue(
                    f.filepath.endswith("_1k.png"),
                    f"Material filepath should end with _1k.png, got: {f.filepath}",
                )

        self.check_import_message("material")

        self.scene.call_command("import_asset")

    def test_full_flow(self) -> None:
        """Test the full flow of Jiko Bridge"""

        self.import_active_asset(self.asset_mat_1)
        mat = self.scene.find_material_by_asset(self.asset_mat_1)
        assert mat is not None, "Material should be imported successfully"

        materials = self.scene.get_all_materials()
        assert (
            len(materials) == 1
        ), f"Active import should remove duplicates material ({len(materials)} found)"

        parent = self.scene.create_scene_object("ExportParent")
        self.scene.create_scene_object("ExportChild", parent=parent)

        self.scene.apply_material_to_object(parent, mat)
        self.scene.select_objects([parent])

        asset_capture = self.export_flow(self.asset_1)
        self.assertIn("asset", asset_capture)

        self.exist_files(self.asset_1)

        asset_container = self.scene.find_container_by_asset(self.asset_1)
        assert asset_container is not None, "Exported asset container should be found in the scene"

        self.scene.create_scene_object("UpdateChild", parent=parent)
        expected_hierarchy = self.scene.get_hierarchy(asset_container)

        self.update_flow(asset_container)

        self.exist_files(self.asset_1)

        self.reimport_flow(asset_container)
        self.assertEqual(self.scene.get_hierarchy(asset_container), expected_hierarchy)

        instances, patch_obj = self.instancing(self.asset_1)
        self.assertEqual(patch_obj.call_count, 5)

        self.scene.select_objects(instances)
        self.export_flow(self.asset_2)

        self.exist_files(self.asset_2)

        instances, patch_obj = self.instancing(self.asset_2, count=3)
        self.assertEqual(patch_obj.call_count, 3)

        self.scene.select_objects(instances)
        self.scene.set_export_format("abc")

        self.export_flow(self.asset_3)

        self.exist_files(self.asset_3)

        self.scene.reset_scene()

        self.import_active_asset(asset_model=self.asset_3)
        container_1 = self.scene.find_container_by_asset(self.asset_1)
        self.assertIsNotNone(container_1)
        self.assertEqual(len(self.scene.get_children_container(container_1)), 3)

        container_2 = self.scene.find_container_by_asset(self.asset_2)
        self.assertIsNotNone(container_2)
        self.assertEqual(len(self.scene.get_children_container(container_2)), 5)

        container_3 = self.scene.find_container_by_asset(self.asset_3)
        self.assertIsNotNone(container_3)
        self.assertEqual(len(self.scene.get_children_container(container_3)), 3)

        objects = self.scene.get_children_container(container_1)
        self.scene.select_objects(objects)

        self.import_material(self.asset_mat_1)
        mat = self.scene.find_material_by_asset(self.asset_mat_1)
        assert mat is not None, "Material should be imported successfully after full flow"


if __name__ == "__main__":
    unittest.main(argv=["tests_flows"], exit=True)
