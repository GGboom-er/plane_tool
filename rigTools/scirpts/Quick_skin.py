import maya.OpenMayaUI as omui
import maya.OpenMaya as om
import maya.cmds as cmds
import shiboken2
import maya.mel as mel
from PySide2 import QtWidgets
from PySide2 import QtGui


def getScenePos():
    view = omui.M3dView.active3dView()
    view_height = view.portHeight()
    QWidget_view = shiboken2.wrapInstance(int(view.widget()), QtWidgets.QWidget)
    global_pos = QtGui.QCursor.pos()
    local_pos = QWidget_view.mapFromGlobal(global_pos)
    return local_pos.x(), view_height - local_pos.y()


def getFaceIDbyMouseCursor( mesh_name ):
    if cmds.objExists(mesh_name):
        scenes_pos = getScenePos()

        pos = om.MPoint()
        dir = om.MVector()

        hitpoint = om.MFloatPoint()
        omui.M3dView().active3dView().viewToWorld(int(scenes_pos[0]), int(scenes_pos[1]), pos, dir)
        pos2 = om.MFloatPoint(pos.x, pos.y, pos.z)

        unit = om.MScriptUtil()
        int_ptr = unit.asIntPtr()

        selectionList = om.MSelectionList()
        selectionList.add(mesh_name)
        dagPath = om.MDagPath()
        selectionList.getDagPath(0, dagPath)
        fnMesh = om.MFnMesh(dagPath)
        intersection = fnMesh.closestIntersection(om.MFloatPoint(pos2), om.MFloatVector(dir), None, None, False,
                                                  om.MSpace.kWorld,
                                                  99999,
                                                  False,
                                                  None,
                                                  hitpoint,
                                                  None,  # hitRayParam
                                                  int_ptr,  # hitFace
                                                  None,
                                                  None,
                                                  None)
        if intersection:
            face_id = unit.getInt(int_ptr)
            return mesh_name + '.f[{0}]'.format(face_id)
        else:
            face_id = None
            cmds.warning('No mesh')



def getMaxInfluenceByFace( face_id, skin_name ):
    vertex_list = cmds.polyListComponentConversion(face_id, ff=True, tv=True)
    vertex_list_fl = cmds.ls(vertex_list, fl=True)
    max_inf = []
    influence = cmds.skinPercent(skin_name, face_id, query=True, t=None)
    for ii in range(len(vertex_list_fl)):
        value = cmds.skinPercent(skin_name, vertex_list_fl[ii], query=True, v=1)
        max_inf.append(influence[value.index(max(value))])
    return list(set(max_inf))[0]
def editSkinWeightTools():
    currentContext = cmds.currentCtx()
    if currentContext != 'artAttrSkinContext':
       mel.eval('ArtPaintSkinWeightsToolOptions')
    paintOperation = cmds.artAttrSkinPaintCtx('artAttrSkinContext', query=True, sao=True)
    if paintOperation=='additive':
        cmds.artAttrSkinPaintCtx('artAttrSkinContext',e =1, sao='absolute')
        cmds.artAttrSkinPaintCtx('artAttrSkinContext',e =1, val=1.0)
    elif paintOperation=='absolute':
        cmds.artAttrSkinPaintCtx('artAttrSkinContext',e =1, sao='additive')
        cmds.artAttrSkinPaintCtx('artAttrSkinContext',e =1, val=0.025)
def callPaintListWindowWithSetInfluence( max_inf ):
    mel.eval('artSkinInflListChanging "{0}" 1'.format(max_inf))
    mel.eval('artSkinInflListChanged artAttrSkinPaintCtx')
    cmds.headsUpMessage('{0}'.format(max_inf), t=1)

def UseInfluenceSetSkinList( mesh_name ):
    face_id = getFaceIDbyMouseCursor(mesh_name)
    if face_id:
        skin = mel.eval('findRelatedSkinCluster("{0}");'.format(mesh_name))
        if skin:
            max_inf = getMaxInfluenceByFace(face_id, skin)
            if cmds.treeView('theSkinClusterInflList', q=True, ex=True) == False:
                editSkinWeightTools()
                callPaintListWindowWithSetInfluence(max_inf)
            else:
                if cmds.treeView('theSkinClusterInflList', q=True, io=True) == True:
                    editSkinWeightTools()
                    callPaintListWindowWithSetInfluence(max_inf)
                    mel.eval('artSkinRevealSelected artAttrSkinPaintCtx')

                else:
                    editSkinWeightTools()
                    callPaintListWindowWithSetInfluence(max_inf)
                    mel.eval('artSkinRevealSelected artAttrSkinPaintCtx')


def mainFunc():
    mesh = cmds.ls(sl=True)
    if mesh:
        if '.' not in mesh[0] and cmds.nodeType(cmds.listRelatives(mesh[0],s =1,ni =1)) == 'mesh':
            UseInfluenceSetSkinList(mesh[0])
        else:
            name = mesh[0].split('.')[0]
            if cmds.objExists(name):
                UseInfluenceSetSkinList(name)


mainFunc()