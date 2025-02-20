#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: Quick_skin_2025.py
@date: 2025/2/20 20:07
@desc: 
"""
from __future__ import print_function
import maya.OpenMayaUI as omui
import maya.OpenMaya as om
import maya.cmds as cmds
import shiboken6
import maya.mel as mel
from PySide6 import QtWidgets, QtGui


def getScenePos():
    view = omui.M3dView.active3dView()
    view_height = view.portHeight()
    QWidget_view = shiboken6.wrapInstance(int(view.widget()), QtWidgets.QWidget)
    global_pos = QtGui.QCursor.pos()
    local_pos = QWidget_view.mapFromGlobal(global_pos)
    return local_pos.x(), view_height - local_pos.y()


def getFaceIDbyMouseCursor( mesh_name ):
    if not cmds.objExists(mesh_name):
        cmds.warning("Mesh '{}' does not exist.".format(mesh_name))
        return None

    view = omui.M3dView.active3dView()
    scene_pos = getScenePos()
    pos = om.MPoint()
    direction = om.MVector()
    view.viewToWorld(int(scene_pos[0]), int(scene_pos[1]), pos, direction)
    pos2 = om.MFloatPoint(pos.x, pos.y, pos.z)

    selection_list = om.MSelectionList()
    selection_list.add(mesh_name)
    dag_path = om.MDagPath()
    selection_list.getDagPath(0, dag_path)
    fn_mesh = om.MFnMesh(dag_path)

    hit_point = om.MFloatPoint()
    hit_face_util = om.MScriptUtil()
    hit_face_ptr = hit_face_util.asIntPtr()

    intersection = fn_mesh.closestIntersection(
        pos2,
        om.MFloatVector(direction),
        None, None, False,
        om.MSpace.kWorld,
        99999.0,
        False,
        None,
        hit_point,
        None,
        hit_face_ptr,
        None, None, None
    )

    if not intersection:
        cmds.warning('No intersection found with mesh.')
        return None

    hit_face = hit_face_util.getInt(hit_face_ptr)
    return "{}.f[{}]".format(mesh_name, hit_face)


def getMaxInfluenceByFace( face_id, skin_name ):
    vertex_list = cmds.polyListComponentConversion(face_id, ff=True, tv=True)
    vertex_list_fl = cmds.ls(vertex_list, fl=True)
    if not vertex_list_fl:
        return None

    influences_dict = {}
    for vertex in vertex_list_fl:
        influences = cmds.skinPercent(skin_name, vertex, query=True, transform=None)
        weights = cmds.skinPercent(skin_name, vertex, query=True, value=True)
        if weights:
            max_value = max(weights)
            max_influence = influences[weights.index(max_value)]
            influences_dict[max_influence] = max(influences_dict.get(max_influence, 0), max_value)

    return max(influences_dict, key=influences_dict.get) if influences_dict else None


def editSkinWeightTools():
    current_context = cmds.currentCtx()
    if current_context != 'artAttrSkinContext':
        mel.eval('ArtPaintSkinWeightsToolOptions')

    paint_operation = cmds.artAttrSkinPaintCtx('artAttrSkinContext', query=True, sao=True)
    if paint_operation == 'additive':
        cmds.artAttrSkinPaintCtx('artAttrSkinContext', edit=True, sao='absolute', value=1.0)
    elif paint_operation == 'absolute':
        cmds.artAttrSkinPaintCtx('artAttrSkinContext', edit=True, sao='additive', value=0.025)


def callPaintListWindowWithSetInfluence( max_inf ):
    if max_inf:
        mel.eval('artSkinInflListChanging "{}" 1'.format(max_inf))
        mel.eval('artSkinInflListChanged artAttrSkinPaintCtx')
        cmds.headsUpMessage('{}'.format(max_inf), time=1)


def UseInfluenceSetSkinList( mesh_name ):
    face_id = getFaceIDbyMouseCursor(mesh_name)
    if not face_id:
        return

    skin = mel.eval('findRelatedSkinCluster("{}");'.format(mesh_name))
    if not skin:
        cmds.warning("No skin cluster found for '{}'".format(mesh_name))
        return

    max_inf = getMaxInfluenceByFace(face_id, skin)
    if not max_inf:
        cmds.warning("Could not determine max influence for face '{}'".format(face_id))
        return

    editSkinWeightTools()
    callPaintListWindowWithSetInfluence(max_inf)
    mel.eval('artSkinRevealSelected artAttrSkinPaintCtx')


def mainFunc():
    selected_meshes = cmds.ls(selection=True, type='transform')
    if not selected_meshes:
        cmds.warning('No mesh selected.')
        return

    mesh = selected_meshes[0]
    if '.' not in mesh and cmds.nodeType(cmds.listRelatives(mesh, shapes=True, noIntermediate=True)) == 'mesh':
        UseInfluenceSetSkinList(mesh)
    else:
        name = mesh.split('.')[0]
        if cmds.objExists(name):
            UseInfluenceSetSkinList(name)


mainFunc()
