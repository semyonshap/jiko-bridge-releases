import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx
from jb_api import JB_API
from jb_asset_importer import JB_AssetImporter
from maya import OpenMayaUI
from PySide6 import QtCore, QtWidgets
from shiboken6 import wrapInstance


def get_maya_main_window():
    ptr = OpenMayaUI.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)


class JB_CommandsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(JB_CommandsDialog, self).__init__(parent)
        self.api = JB_API()
        self.importer = JB_AssetImporter()

        self.setWindowTitle("JikoBridge Maya UI")
        self.setFixedSize(300, 120)
        layout = QtWidgets.QVBoxLayout(self)

        self.import_button = QtWidgets.QPushButton("Import")

        layout.addWidget(self.import_button)

        self.import_button.clicked.connect(self.import_asset)

    def import_asset(self):
        asset = self.api.get_active_asset()

        if asset:
            self.importer.import_asset(asset)
            print(asset)
            return asset

        return None

    def closeEvent(self, event):
        super(JB_CommandsDialog, self).closeEvent(event)


def show_ui():
    global ui
    try:
        ui.close()
        ui.deleteLater()
    except:
        pass
    ui = JB_CommandsDialog(parent=get_maya_main_window())
    ui.show()


class JikoBridge(OpenMayaMPx.MPxCommand):
    def __init__(self):
        OpenMayaMPx.MPxCommand.__init__(self)

    def doIt(self, args):
        show_ui()


def cmdCreator():
    return OpenMayaMPx.asMPxPtr(JikoBridge())


def initializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    mplugin.registerCommand("JikoBridge", cmdCreator)
    show_ui()


def uninitializePlugin(mobject):
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    mplugin.deregisterCommand("JikoBridge")
