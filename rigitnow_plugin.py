"""Load in Maya Plug-in Manager; enable Auto load to restore the shelf."""
import os
import sys
import maya.api.OpenMaya as om
from maya import cmds

def maya_useNewAPI():
    pass

class RigitnowCommand(om.MPxCommand):
    def doIt(self, args):
        import rigitnow
        rigitnow.show()

def initializePlugin(obj):
    plugin = om.MFnPlugin(obj,'rigitnow','1.0.0','Any')
    path = plugin.loadPath()
    if path not in sys.path: sys.path.insert(0,path)
    plugin.registerCommand('rigitnow',RigitnowCommand)
    if not cmds.about(batch=True):
        cmds.evalDeferred('import rigitnow; rigitnow.install_shelf()')

def uninitializePlugin(obj):
    om.MFnPlugin(obj).deregisterCommand('rigitnow')
    if cmds.window('rigitnow_window',exists=True): cmds.deleteUI('rigitnow_window')
