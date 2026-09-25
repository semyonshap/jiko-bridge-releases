from typing import List

import c4d

from jiko_bridge_c4d.scene.jb_scene_container import JbSceneContainer
from jiko_bridge_c4d.jb_types import JbObject


class JbSceneInstance(JbSceneContainer):
    """Instance and placeholder management for Cinema 4D."""

    def create_instance(self, container, name):
        instance = c4d.BaseObject(c4d.Oinstance)
        instance.SetName(f"Instance_{name}")
        instance[c4d.INSTANCEOBJECT_LINK] = container
        instance[c4d.INSTANCEOBJECT_RENDERINSTANCE_MODE] = 1
        for key, bc in container.GetUserDataContainer():
            self._set_user_data(instance, bc[c4d.DESC_NAME], container[key])
        self.source.InsertObject(instance)
        instance.SetBit(c4d.BIT_ACTIVE)
        return instance

    def get_names_from_placeholder(self, obj) -> List[str]:
        names = set()

        if not obj.IsInstanceOf(c4d.Opolygon) and obj.GetType() != 1028083:
            return []

        if obj.IsInstanceOf(c4d.Opolygon) and obj.GetPointCount() != 4:
            return []

        for tag in obj.GetTags():
            if tag.CheckType(c4d.Ttexture):
                material = tag[c4d.TEXTURETAG_MATERIAL] if tag.GetType() == c4d.Ttexture else None
                if material:
                    names.add(material.GetName())

            elif tag.GetType() == 1036433:
                name = tag.GetName()
                if name:
                    names.add(name)

            elif tag.CheckType(c4d.Tpolygonselection):
                selection_name = tag.GetName()
                if selection_name:
                    names.add(selection_name)

        return list(names)

    def replace_instances_with_placeholders(self, objects, source) -> list[JbObject]:
        if not objects:
            return []

        new_objects = []

        for obj in objects:
            if not obj.CheckType(c4d.Oinstance):
                continue
            info = self.get_asset_data_from_container(obj)
            if not info:
                continue
            placeholder = self.create_placeholder(
                info,
                obj.GetMg(),
                source,
            )
            source.InsertObject(placeholder)
            new_objects.append(placeholder)

            obj.Remove()

        return new_objects

    def create_placeholder(self, asset_model, transform, source) -> JbObject:
        pack_name = asset_model.pack_name
        asset_name = asset_model.asset_name

        name = f"{pack_name}__{asset_name}"

        material = c4d.BaseMaterial(c4d.Mmaterial)
        material.SetName(name)

        source.InsertMaterial(material)

        prim = c4d.BaseObject(c4d.Oplane)
        prim[c4d.PRIM_PLANE_WIDTH] = 100
        prim[c4d.PRIM_PLANE_HEIGHT] = 100
        prim[c4d.PRIM_PLANE_SUBW] = 1
        prim[c4d.PRIM_PLANE_SUBH] = 1

        obj = c4d.utils.SendModelingCommand(
            command=c4d.MCOMMAND_CURRENTSTATETOOBJECT,
            list=[prim],
            mode=c4d.MODELINGCOMMANDMODE_ALL,
            doc=self.source,
        )

        if obj and len(obj) > 0:
            obj = obj[0]
        else:
            obj = prim

        obj.SetMg(transform)
        obj.SetName(name)

        stag = obj.MakeTag(c4d.Tpolygonselection)
        stag.SetName(name)

        bs = stag.GetBaseSelect()
        bs.Select(0)

        mtag = obj.MakeTag(c4d.Ttexture)
        mtag[c4d.TEXTURETAG_MATERIAL] = material

        return obj
