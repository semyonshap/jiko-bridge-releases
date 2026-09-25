from contextlib import contextmanager

import c4d
from jiko_bridge_c4d.scene.jb_scene_instance import JbSceneInstance


class JbSceneTemp(JbSceneInstance):
    """Scene-level operations: document helpers, geometry transforms."""

    def __init__(self):
        self._temp_source = None

    @contextmanager
    def temp_source(self, objects=None, unit_scale=c4d.DOCUMENT_UNIT_CM, debug=False):
        if objects:
            tmp_doc = c4d.documents.IsolateObjects(self.source, objects)
        else:
            tmp_doc = c4d.documents.BaseDocument()

        self._temp_source = tmp_doc

        unit_scale_data = c4d.UnitScaleData()
        unit_scale_data.SetUnitScale(1, unit_scale)
        tmp_doc[c4d.DOCUMENT_DOCUNIT] = unit_scale_data

        try:
            yield tmp_doc
        finally:
            if debug:
                c4d.documents.InsertBaseDocument(tmp_doc)
                c4d.documents.SetActiveDocument(tmp_doc)
                c4d.EventAdd()
            else:
                c4d.documents.KillDocument(tmp_doc)

            self._temp_source = None

    def _copy_source(
        self,
        src: c4d.documents.BaseDocument,
        dst: c4d.documents.BaseDocument,
        parent: c4d.BaseObject,
    ) -> None:
        mat = src.GetFirstMaterial()
        while mat:
            next_mat = mat.GetNext()
            mat.Remove()
            dst.InsertMaterial(mat)
            mat = next_mat

        objects = src.GetObjects()
        for obj in objects:
            obj.Remove()
            dst.InsertObject(obj)
            obj.InsertUnder(parent)
            obj.SetBit(c4d.BIT_ACTIVE)

    # ------------------------------------------------------------------
    # Geometry transforms
    # ------------------------------------------------------------------

    def _project_scale(self, doc: c4d.documents.BaseDocument, factor: float = 0.01) -> None:
        objects = self.walk(doc.GetObjects())
        for obj in objects:
            if obj.IsInstanceOf(c4d.Opolygon):
                points = obj.GetAllPoints()
                if points:
                    obj.SetAllPoints([p * factor for p in points])
                    obj.Message(c4d.MSG_UPDATE)

            pos = obj.GetRelPos()
            obj.SetRelPos(pos * factor)

        self.logger.debug("Project scale: %s objects", len(objects))

    def _make_editable(self, objects: list[c4d.BaseObject]) -> None:
        """Convert generators to polygons (MCOMMAND_MAKEEDITABLE)."""
        count = 0
        for item in objects:
            if not item.IsAlive():
                continue
            if item.IsInstanceOf(c4d.Opolygon) or item.IsInstanceOf(c4d.Onull):
                continue
            parent = item.GetUp()
            children = list(item.GetChildren())
            result = c4d.utils.SendModelingCommand(
                command=c4d.MCOMMAND_MAKEEDITABLE,
                list=[item],
                mode=c4d.MODELINGCOMMANDMODE_ALL,
                doc=self._temp_source,
            )
            if isinstance(result, list):
                for new_obj in result:
                    count += 1
                    self._temp_source.InsertObject(new_obj)
                    if parent:
                        new_obj.InsertUnder(parent)
                    for child in children:
                        child.Remove()
                        child.InsertUnder(new_obj)

        if count > 0:
            self.logger.debug("Editable: %s objects", count)

    def _remove_unused_materials(
        self,
        doc: c4d.documents.BaseDocument,
    ) -> None:
        used_mats = set()

        objects = self.walk(doc.GetObjects())
        for obj in objects:
            tag = obj.GetFirstTag()
            while tag:
                if tag.GetType() == c4d.Ttexture:
                    mat = tag[c4d.TEXTURETAG_MATERIAL]
                    if mat is not None:
                        used_mats.add(mat)
                tag = tag.GetNext()

        mat = doc.GetFirstMaterial()
        while mat:
            next_mat = mat.GetNext()
            if mat not in used_mats:
                mat.Remove()
            mat = next_mat
