import re

import c4d
from jiko_bridge_c4d.jb_types import JbData, JbMaterial, JbObject, JbSceneBase


class JbSceneObjects(JbSceneBase):
    """Traversal and querying of Cinema 4D object hierarchies."""

    def get_selection(self) -> list[JbObject | JbMaterial]:
        result = []
        materials = self.source.GetActiveMaterials()
        if materials:
            result.extend(materials)
        objects = self.source.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
        if objects:
            result.extend(objects)

        return result

    def walk(self, root) -> list[JbData]:
        if not root:
            return []
        return list(self._walk(root))

    def _walk(self, root: list[JbData]):
        if root is None:
            return

        def walk_objects(obj):
            yield obj
            child = obj.GetDown()
            while child:
                yield from walk_objects(child)
                child = child.GetNext()

        for item in root:
            if isinstance(item, c4d.BaseObject):
                yield from walk_objects(item)
            elif isinstance(item, c4d.BaseMaterial):
                yield item

    def get_materials_from_objects(self, objects) -> list[JbMaterial]:
        materials = []

        for obj in objects:
            if isinstance(obj, c4d.BaseMaterial):
                materials.append(obj)
                continue

            if not obj.IsInstanceOf(c4d.Opolygon):
                continue

            for tag in obj.GetTags():
                if not tag.CheckType(c4d.Ttexture):
                    continue

                material = tag[c4d.TEXTURETAG_MATERIAL]
                if material:
                    materials.append(material)

        return materials

    def get_children(self, obj) -> list[JbObject]:
        return obj.GetChildren() or []

    def copy_object_transform(self, obj, target_obj) -> None:
        obj.SetMg(target_obj.GetMg())

    def remove_object(self, obj) -> None:
        obj.Remove()

    def get_depth(self, obj) -> int:
        depth = 0
        current = obj
        while current.GetUp():
            depth += 1
            current = current.GetUp()
        return depth

    def _set_protection_tag(self, obj: c4d.BaseObject) -> None:
        if obj is None:
            return

        if obj.GetTags() is not None:
            for tag in obj.GetTags():
                try:
                    if tag.GetType() == c4d.Tprotection:
                        tag[c4d.PROTECTION_ALLOW_DUPLICATION] = True
                        return
                except (AttributeError, TypeError):
                    continue

        try:
            protection_tag = c4d.BaseTag(c4d.Tprotection)
            if protection_tag is not None:
                protection_tag[c4d.PROTECTION_ALLOW_DUPLICATION] = True
                obj.InsertTag(protection_tag)
        except (AttributeError, TypeError):
            pass

    def _set_user_data(
        self,
        obj: c4d.BaseObject,
        name: str,
        value: str | None,
    ) -> None:
        if value is None:
            value = ""

        for key, bc in obj.GetUserDataContainer() or []:
            if bc[c4d.DESC_NAME] == name:
                obj[key] = value
                return

        bc = c4d.GetCustomDatatypeDefault(c4d.DTYPE_STRING)
        bc[c4d.DESC_NAME] = name
        bc[c4d.DESC_SHORT_NAME] = name
        bc[c4d.DESC_DEFAULT] = value

        element = obj.AddUserData(bc)
        if element is not None:
            obj[element] = value

    def set_container_visibility(self, obj: c4d.BaseObject, mode: int) -> None:
        """Set the editor and render visibility mode of the container."""
        obj[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = mode
        obj[c4d.ID_BASEOBJECT_VISIBILITY_RENDER] = mode

    def merge_duplicates_materials(self, material: c4d.BaseMaterial) -> None:
        pattern = re.compile(r"^" + re.escape(material.GetName()) + r"\.\d+$")

        duplicates = set()
        mat = self.source.GetFirstMaterial()
        while mat:
            if pattern.match(mat.GetName()):
                duplicates.add(mat)
            mat = mat.GetNext()

        if not duplicates:
            return

        for obj in self.walk(self.source.GetObjects()):
            while obj:
                tag = obj.GetFirstTag()
                while tag:
                    if tag.GetType() == c4d.Ttexture:
                        if tag[c4d.TEXTURETAG_MATERIAL] in duplicates:
                            tag[c4d.TEXTURETAG_MATERIAL] = material
                    tag = tag.GetNext()

        for dup in duplicates:
            dup.Remove()
