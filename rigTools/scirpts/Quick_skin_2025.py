#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: Quick_skin_2025.py
@date: 2025/2/20 20:07
@desc:
    根据鼠标位置在视口中射线检测(mesh)，找到命中的多边形(face)，
    通过 skinPercent 查询该面上权重最大的骨骼(influence)，
    自动切换 Paint Skin Weights 工具的绘制骨骼，
    并在该骨骼屏幕位置显示 HUD（绿色小圆点 + 骨骼名 + 笔刷模式）。

    特性：
    - HUD 永远只有一个实例（Single HUD Instance，Qt 层做强制清理）；
    - 每次运行只更新位置和内容，1.2 秒后自动隐藏（QTimer 控制）；
    - 支持组件选择模式（Component Selection）：face / vertex / edge 等。
"""

from __future__ import print_function
import maya.OpenMayaUI as omui
import maya.OpenMaya as om
import maya.cmds as cmds
import maya.mel as mel

import shiboken6
from PySide6 import QtWidgets, QtGui, QtCore

# ----------------------------------------------------------------------
# 全局 HUD 单例 & 计时器
# ----------------------------------------------------------------------
_hud_instance = None      # InfluenceHUD 单例 (single HUD widget)
_hud_timer = None         # QTimer 控制 HUD 自动隐藏 (auto-hide timer)


# ----------------------------------------------------------------------
# 视口鼠标位置 (Viewport mouse position)
# ----------------------------------------------------------------------
def getScenePos():
    """
    返回鼠标在当前 3D 视图中的坐标（视口坐标系）
    M3dView 原点：左下
    """
    view = omui.M3dView.active3dView()
    view_height = view.portHeight()
    QWidget_view = shiboken6.wrapInstance(int(view.widget()), QtWidgets.QWidget)
    global_pos = QtGui.QCursor.pos()
    local_pos = QWidget_view.mapFromGlobal(global_pos)
    return local_pos.x(), view_height - local_pos.y()


# ----------------------------------------------------------------------
# RayCast: 根据鼠标位置获取 faceID
# ----------------------------------------------------------------------
def getFaceIDbyMouseCursor(mesh_name):
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

    # transform -> shape（保险）
    if dag_path.apiType() == om.MFn.kTransform:
        dag_path.extendToShape()

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


# ----------------------------------------------------------------------
# 根据 face 查询最大影响骨骼 (Max influence by face via skinPercent)
# ----------------------------------------------------------------------
def getMaxInfluenceByFace(face_id, skin_name):
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
            # 多个点时取该骨骼在这些点上的最大权重作为比较依据
            influences_dict[max_influence] = max(influences_dict.get(max_influence, 0), max_value)

    return max(influences_dict, key=influences_dict.get) if influences_dict else None


# ----------------------------------------------------------------------
# 计算骨骼在屏幕上的位置 (bone world pos -> screen pos)
# ----------------------------------------------------------------------
def getBoneScreenPos(joint_name):
    """
    返回骨骼在屏幕上的全局坐标 (screen_x, screen_y)
    使用 OpenMaya API1.0 的 M3dView.worldToView(MPoint, short&, short&)
    """
    try:
        sel = om.MSelectionList()
        sel.add(joint_name)
        dag = om.MDagPath()
        sel.getDagPath(0, dag)
    except:
        return None

    try:
        fn_trans = om.MFnTransform(dag)
    except:
        return None

    world_vec = fn_trans.translation(om.MSpace.kWorld)
    world_point = om.MPoint(world_vec.x, world_vec.y, world_vec.z)

    view = omui.M3dView.active3dView()

    # 使用 short 指针，符合 API 签名
    util_x = om.MScriptUtil()
    util_x.createFromInt(0)
    x_ptr = util_x.asShortPtr()

    util_y = om.MScriptUtil()
    util_y.createFromInt(0)
    y_ptr = util_y.asShortPtr()

    view.worldToView(world_point, x_ptr, y_ptr)

    x = om.MScriptUtil(x_ptr).asShort()
    y = om.MScriptUtil(y_ptr).asShort()

    widget = shiboken6.wrapInstance(int(view.widget()), QtWidgets.QWidget)
    # worldToView 的 y 原点在左下，Qt 在左上
    global_pos = widget.mapToGlobal(QtCore.QPoint(int(x), widget.height() - int(y)))
    return global_pos.x(), global_pos.y()


# ----------------------------------------------------------------------
# HUD 类：绿色圆点 + 文本标签（单实例，无动画）
# ----------------------------------------------------------------------
class InfluenceHUD(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(InfluenceHUD, self).__init__(parent)

        # 关键：设置固定 objectName，方便跨脚本版本清理旧实例
        self.setObjectName("GG_QuickSkinInfluenceHUD")

        # 无边框 & 置顶 & 透明背景
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.ToolTip
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)

        # 布局：左边预留小绿点，右边文本
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(20, 14, 8, 10)

        self.label = QtWidgets.QLabel()
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 220);
                border-radius: 6px;
                padding: 8px 10px;
                font-family: Segoe UI, Arial;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.label)

    def showInfo(self, bone_name, mode_text, screen_x, screen_y):
        """
        在给定屏幕位置显示 HUD
        :param bone_name: 骨骼名（会自动取短名）
        :param mode_text: 笔刷模式文本（例如 REPLACE(1.0) / ADD(0.025)）
        :param screen_x: 屏幕 X
        :param screen_y: 屏幕 Y
        """
        short_name = bone_name.split('|')[-1]

        html = (
            u"<div style='font-weight:bold; font-size:16px; color:#FFDD55;'>{bone}</div>"
            u"<div style='font-weight:600; font-size:13px; color:#66CCFF; margin-top:2px;'>{mode}</div>"
        ).format(bone=short_name, mode=mode_text)

        self.label.setText(html)
        self.adjustSize()

        # 让左侧绿点大致对齐到骨骼所在屏幕位置
        self.move(int(screen_x - 16), int(screen_y - 16))
        self.show()

    def paintEvent(self, event):
        # 先画左侧小绿点，再交给父类绘制 label
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        painter.setBrush(QtGui.QBrush(QtGui.QColor(0, 255, 0)))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(QtCore.QPoint(10, 14), 5, 5)  # 小圆点

        super(InfluenceHUD, self).paintEvent(event)


# ----------------------------------------------------------------------
# 内部工具：确保全局只存在一个 HUD（清理旧的残留窗口）
# ----------------------------------------------------------------------
def _get_or_create_hud():
    """
    保证 Qt 层只存在一个 GG_QuickSkinInfluenceHUD：
    - 先扫描所有 topLevelWidgets，关闭并 deleteLater 掉旧的；
    - 然后创建/复用当前脚本的 _hud_instance 与 _hud_timer。
    """
    global _hud_instance, _hud_timer

    app = QtWidgets.QApplication.instance()
    if app:
        for w in app.topLevelWidgets():
            try:
                if w.objectName() == "GG_QuickSkinInfluenceHUD":
                    # 如果是旧脚本残留的 HUD，先关掉
                    w.close()
                    w.deleteLater()
            except:
                pass

    view = omui.M3dView.active3dView()
    parent = shiboken6.wrapInstance(int(view.widget()), QtWidgets.QWidget)

    # 创建新的 HUD 实例（当前脚本持有的单例）
    if _hud_instance is None:
        _hud_instance = InfluenceHUD(parent)
    else:
        # 运行中重载脚本时，旧 _hud_instance 可能已失效
        if not shiboken6.isValid(_hud_instance):
            _hud_instance = InfluenceHUD(parent)
        else:
            if _hud_instance.parent() is not parent:
                _hud_instance.setParent(parent)

    # 创建 / 复用计时器
    if _hud_timer is None or not shiboken6.isValid(_hud_timer):
        _hud_timer = QtCore.QTimer(_hud_instance)
        _hud_timer.setSingleShot(True)
        _hud_timer.timeout.connect(_hud_instance.hide)

    return _hud_instance, _hud_timer


# ----------------------------------------------------------------------
# 显示 HUD：骨骼位置 + 笔刷模式（单例 + QTimer 控制）
# ----------------------------------------------------------------------
def showInfluenceHud(max_inf, paint_operation):
    """
    根据骨骼名和笔刷模式，在视口中对应骨骼位置显示 HUD：
    - Qt 级别清理所有旧 HUD；
    - 使用当前脚本的单例 HUD + QTimer；
    - 多次点击只会刷新同一个 UI，不会出现第二个。
    """
    hud, hud_timer = _get_or_create_hud()

    # 计算骨骼屏幕位置
    screen_pos = getBoneScreenPos(max_inf)
    if not screen_pos:
        # 若获取失败，退化到鼠标位置（保证不崩）
        x, y = getScenePos()
        view = omui.M3dView.active3dView()
        widget = shiboken6.wrapInstance(int(view.widget()), QtWidgets.QWidget)
        global_pos = widget.mapToGlobal(QtCore.QPoint(int(x), widget.height() - int(y)))
        screen_pos = (global_pos.x(), global_pos.y())

    screen_x, screen_y = screen_pos

    # 将 paint_operation 转为更友好的文本
    if paint_operation == 'absolute':
        mode_text = u"REPLACE (1.0)"
    elif paint_operation in ('additive', 'add'):
        mode_text = u"ADD (0.025)"
    else:
        mode_text = u"MODE: {}".format(paint_operation)

    # 显示/刷新 HUD（单实例）
    hud.showInfo(max_inf, mode_text, screen_x, screen_y)

    # QTimer 控制隐藏：重复点击只会重置计时
    hud_timer.stop()
    hud_timer.start(1200)  # 1.2 秒后隐藏


# ----------------------------------------------------------------------
# Paint Skin Weights 工具模式切换
# ----------------------------------------------------------------------
def editSkinWeightTools():
    """
    打开或切换到 Paint Skin Weights 工具，并在 absolute/additive 之间切换。
    返回切换后的模式字符串：'absolute' 或 'additive'
    """
    current_context = cmds.currentCtx()
    if current_context != 'artAttrSkinContext':
        # 使用 Options 版本，可以保证 context 被创建
        mel.eval('ArtPaintSkinWeightsToolOptions')

    paint_operation = cmds.artAttrSkinPaintCtx('artAttrSkinContext', query=True, sao=True)
    new_operation = paint_operation

    if paint_operation == 'additive':
        cmds.artAttrSkinPaintCtx('artAttrSkinContext', edit=True, sao='absolute', value=1.0)
        new_operation = 'absolute'
    elif paint_operation == 'absolute':
        cmds.artAttrSkinPaintCtx('artAttrSkinContext', edit=True, sao='additive', value=0.025)
        new_operation = 'additive'

    return new_operation


# ----------------------------------------------------------------------
# 更新 ArtSkinInfluence 列表并显示 HUD
# ----------------------------------------------------------------------
def callPaintListWindowWithSetInfluence(max_inf, paint_operation):
    if max_inf:
        mel.eval('artSkinInflListChanging "{}" 1'.format(max_inf))
        mel.eval('artSkinInflListChanged artAttrSkinPaintCtx')
        # 用我们自己的 HUD 替代 headsUpMessage
        showInfluenceHud(max_inf, paint_operation)


# ----------------------------------------------------------------------
# 主逻辑：根据鼠标点击设置当前绘制骨骼
# ----------------------------------------------------------------------
def UseInfluenceSetSkinList(mesh_name):
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

    # 切换/设置 Paint Skin Weights 工具 & 模式
    new_mode = editSkinWeightTools()
    # 更新影响列表 & 显示 HUD
    callPaintListWindowWithSetInfluence(max_inf, new_mode)
    # 原功能：高亮选中影响
    mel.eval('artSkinRevealSelected artAttrSkinPaintCtx')


# ----------------------------------------------------------------------
# 入口：处理选择并调用（支持组件模式）
# ----------------------------------------------------------------------
def mainFunc():
    """
    支持两种选择方式：
    1）Transform / Mesh 物体模式；
    2）组件模式（面 / 点 / 边），内部自动解析其所属 mesh。
    """
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning('No selection.')
        return

    # objectsOnly=True 可以从组件选择中得到对应 transform/shape
    objs = cmds.ls(selection=True, objectsOnly=True) or []

    # 优先使用 objectsOnly 的结果，保证组件模式可用
    target = objs[0] if objs else sel[0]

    node_type = cmds.nodeType(target)
    mesh_name = None

    if node_type == 'transform':
        # transform -> 查有没有 mesh shape
        shapes = cmds.listRelatives(target, shapes=True, noIntermediate=True, fullPath=True) or []
        if shapes and cmds.nodeType(shapes[0]) == 'mesh':
            mesh_name = target
    elif node_type == 'mesh':
        # shape -> 找到它的 transform
        parents = cmds.listRelatives(target, parent=True, fullPath=True) or []
        mesh_name = parents[0] if parents else target
    else:
        # 兜底：可能是 "pSphere1.f[10]" 这种字符串
        base = target.split('.')[0]
        if cmds.objExists(base):
            mesh_name = base

    if not mesh_name:
        cmds.warning('Selection is not a skinned mesh.')
        return

    UseInfluenceSetSkinList(mesh_name)


# ----------------------------------------------------------------------
# 执行
# ----------------------------------------------------------------------
mainFunc()
