#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@desc:
    Quick Skin Picker + 关节屏幕标记 + 相机旋转枢轴 (Tumble Pivot) 对齐

    - 基于 Quick_skin_2025 原逻辑：射线选面 + skinCluster 权重查询
    - 权重查询使用 API2.0 MFnSkinCluster.getWeights 高性能实现
    - 新增：
        * 小绿点 + 悬浮标签，标记骨骼屏幕位置
        * 相机 Alt 旋转围绕该骨骼旋转（通过 Tumble Pivot）
"""

from __future__ import print_function

import sys

# --- API 1.0：视图 / 相机 / 射线 -------------------------------------------
import maya.OpenMayaUI as omui
import maya.OpenMaya as om

# --- API 2.0：高性能权重 / 世界坐标 / 屏幕坐标 -------------------------------
import maya.api.OpenMaya as om2
import maya.api.OpenMayaUI as omui2
import maya.api.OpenMayaAnim as oma2

import maya.cmds as cmds
import maya.mel as mel

from PySide6 import QtWidgets, QtGui, QtCore
import shiboken6


# ----------------------------------------------------------------------
# 全局 UI 单例
# ----------------------------------------------------------------------
_overlay_widget = None


class BoneInfoOverlay(QtWidgets.QWidget):
    """
    屏幕悬浮标签：
    - 左侧小绿点代表骨骼屏幕位置
    - 右侧黑底文字显示骨骼名 + 笔刷模式
    """

    def __init__(self, parent=None):
        super(BoneInfoOverlay, self).__init__(parent)

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.ToolTip |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 10, 10)  # 左边给绿点

        self.label = QtWidgets.QLabel()
        self.label.setTextFormat(QtCore.Qt.RichText)
        self.label.setStyleSheet(u"""
            QLabel {
                background-color: rgba(0, 0, 0, 190);
                border-radius: 4px;
                padding: 6px 8px;
                font-family: Segoe UI, Arial;
                font-size: 12px;
                color: #EEEEEE;
            }
        """)
        layout.addWidget(self.label)

        self._opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)

        self._anim = QtCore.QPropertyAnimation(self._opacity_effect, b"opacity", self)
        self._anim.setDuration(1200)
        self._anim.setEasingCurve(QtCore.QEasingCurve.InQuad)
        self._anim.finished.connect(self.hide)

    def paintEvent(self, event):
        # 左侧画实心绿点
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 255, 0))
        painter.drawEllipse(QtCore.QPoint(10, 10), 10, 10)
        super(BoneInfoOverlay, self).paintEvent(event)

    def show_info(self, html_text, screen_x, screen_y):
        # 单例复用：只更新内容和位置
        try:
            self._anim.stop()
        except RuntimeError:
            return

        self.label.setText(html_text)
        self.adjustSize()

        # 绿点中心对齐到 screen_x/y
        self.move(int(screen_x - 10), int(screen_y - 10))

        self._opacity_effect.setOpacity(1.0)
        self.show()

        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()


# ----------------------------------------------------------------------
# 视图 / 鼠标坐标
# ----------------------------------------------------------------------
def _get_active_view():
    """
    使用 API2.0 获取当前 3D 视图和对应 QWidget
    """
    view = omui2.M3dView.active3dView()
    widget_ptr = view.widget()
    if widget_ptr is None:
        return view, None
    widget = shiboken6.wrapInstance(int(widget_ptr), QtWidgets.QWidget)
    return view, widget


def _get_scene_pos_from_mouse():
    """
    鼠标屏幕坐标 -> 当前视口坐标 (左下为原点，用于 view.viewToWorld)
    """
    view, widget = _get_active_view()
    if widget is None:
        return None

    view_height = view.portHeight()
    global_pos = QtGui.QCursor.pos()
    local_pos = widget.mapFromGlobal(global_pos)
    return local_pos.x(), view_height - local_pos.y()


# ----------------------------------------------------------------------
# 射线选面（API 1.0）
# ----------------------------------------------------------------------
def getFaceIDbyMouseCursor(mesh_name):
    """
    使用 OpenMaya (API1.0) 射线拾取，返回 "meshShape.f[index]" 字符串
    """
    if not cmds.objExists(mesh_name):
        cmds.warning(u"Mesh '{}' 不存在".format(mesh_name))
        return None

    scene_pos = _get_scene_pos_from_mouse()
    if scene_pos is None:
        return None

    view = omui.M3dView.active3dView()
    pos = om.MPoint()
    direction = om.MVector()
    view.viewToWorld(int(scene_pos[0]), int(scene_pos[1]), pos, direction)
    pos2 = om.MFloatPoint(pos.x, pos.y, pos.z)

    sel_list = om.MSelectionList()
    sel_list.add(mesh_name)
    dag_path = om.MDagPath()
    sel_list.getDagPath(0, dag_path)
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
        cmds.warning(u"射线没有击中模型")
        return None

    hit_face = hit_face_util.getInt(hit_face_ptr)
    return "{}.f[{}]".format(mesh_name, hit_face)


# ----------------------------------------------------------------------
# API2.0：高性能最大权重骨骼查询
# ----------------------------------------------------------------------
def get_max_influence_api2(face_id, skin_name):
    """
    使用 MFnSkinCluster.getWeights 查询 face 上最大权重的骨骼
    返回: (bone_name, bone_dagPath(API2.0))
    """
    if not face_id or not skin_name:
        return None, None

    try:
        obj_part, comp = face_id.split('.f[')
        face_index = int(comp.rstrip(']'))
    except Exception:
        cmds.warning(u"face_id 解析失败: {}".format(face_id))
        return None, None

    sel = om2.MSelectionList()
    try:
        sel.add(obj_part)
        dag_path = sel.getDagPath(0)
    except Exception as e:
        cmds.warning(u"获取 mesh DagPath 失败: {} -> {}".format(obj_part, e))
        return None, None

    if dag_path.apiType() == om2.MFn.kTransform:
        dag_path.extendToShape()

    try:
        fn_mesh = om2.MFnMesh(dag_path)
        vtx_ids = fn_mesh.getPolygonVertices(face_index)
    except Exception as e:
        cmds.warning(u"获取多边形顶点失败: face {} -> {}".format(face_index, e))
        return None, None

    if not vtx_ids:
        return None, None

    sel_skin = om2.MSelectionList()
    try:
        sel_skin.add(skin_name)
        skin_obj = sel_skin.getDependNode(0)
        fn_skin = oma2.MFnSkinCluster(skin_obj)
    except Exception as e:
        cmds.warning(u"创建 MFnSkinCluster 失败: {}".format(e))
        return None, None

    comp_fn = om2.MFnSingleIndexedComponent()
    comp = comp_fn.create(om2.MFn.kMeshVertComponent)
    comp_fn.addElements(vtx_ids)

    try:
        weights, inf_count = fn_skin.getWeights(dag_path, comp)
        inf_paths = fn_skin.influenceObjects()
    except Exception as e:
        cmds.warning(u"读取 skinCluster 权重失败: {}".format(e))
        return None, None

    if not weights or not inf_paths or inf_count <= 0:
        return None, None

    per_inf_max = [0.0] * len(inf_paths)
    for i, w in enumerate(weights):
        inf_idx = i % inf_count
        if w > per_inf_max[inf_idx]:
            per_inf_max[inf_idx] = w

    max_idx = max(range(len(inf_paths)), key=lambda idx: per_inf_max[idx])
    bone_path = inf_paths[max_idx]
    bone_name = bone_path.partialPathName()
    return bone_name, bone_path


# ----------------------------------------------------------------------
# 屏幕坐标（API 2.0 worldToView）
# ----------------------------------------------------------------------
def get_bone_screen_pos(bone_dag_path):
    """
    joint 世界坐标 -> 当前视口屏幕坐标 (global x,y)
    用于小绿点 + HUD 定位
    """
    try:
        view, widget = _get_active_view()
        if widget is None:
            return None

        fn_trans = om2.MFnTransform(bone_dag_path)
        world_vec = fn_trans.translation(om2.MSpace.kWorld)
        world_pt = om2.MPoint(world_vec)

        x, y, _ = view.worldToView(world_pt)
        view_h = view.portHeight()

        local_pos = QtCore.QPoint(int(x), int(view_h - y))
        global_pos = widget.mapToGlobal(local_pos)
        return global_pos.x(), global_pos.y()
    except Exception as e:
        sys.stderr.write("Quick_skin: get_bone_screen_pos failed: %s\n" % e)
        return None


# ----------------------------------------------------------------------
# 相机旋转枢轴：**关键修正点**（全部使用 API 1.0）
# ----------------------------------------------------------------------
def update_camera_tumble_pivot(bone_dag_path):
    """
    将当前视口相机的 Tumble Pivot 设置到指定骨骼世界坐标。
    这里完全使用 API1.0 (OpenMaya/OpenMayaUI)，避免签名问题。
    """
    try:
        # 1) 把 API2.0 的 DagPath 转成名字，再走 API1.0
        try:
            bone_name = bone_dag_path.fullPathName()
        except Exception:
            bone_name = str(bone_dag_path)

        sel = om.MSelectionList()
        sel.add(bone_name)
        bone_dag1 = om.MDagPath()
        sel.getDagPath(0, bone_dag1)

        fn_t = om.MFnTransform(bone_dag1)
        world_vec = fn_t.translation(om.MSpace.kWorld)
        world_pt = om.MPoint(world_vec)

        # 2) 获取当前视口相机 (API1.0 签名：getCamera(MDagPath&))
        view = omui.M3dView.active3dView()
        cam_dag1 = om.MDagPath()
        view.getCamera(cam_dag1)

        fn_cam1 = om.MFnCamera(cam_dag1)
        fn_cam1.setTumblePivot(world_pt)   # 真正设置 Tumble Pivot

        cam_shape_name = cam_dag1.fullPathName()

        # 3) 确保相机不启用“本地轴枢轴”（usePivotAsLocalSpace）
        if cmds.attributeQuery("usePivotAsLocalSpace", node=cam_shape_name, exists=True):
            try:
                cmds.setAttr(cam_shape_name + ".usePivotAsLocalSpace", 0)
            except Exception:
                pass

        # 4) 确保 tumbleContext 使用 Tumble Pivot 模式 (localTumble=0)
        if cmds.contextInfo("tumbleContext", exists=True):
            try:
                cmds.tumbleCtx("tumbleContext", e=True, localTumble=0)
            except Exception:
                pass

    except Exception as e:
        sys.stderr.write("Quick_skin: update_camera_tumble_pivot failed: %s\n" % e)


# ----------------------------------------------------------------------
# Skin Paint 工具：保持你原来的逻辑（自动切换加/替）
# ----------------------------------------------------------------------
def editSkinWeightTools():
    current_context = cmds.currentCtx()
    if current_context != 'artAttrSkinContext':
        mel.eval('ArtPaintSkinWeightsToolOptions')

    paint_operation = cmds.artAttrSkinPaintCtx('artAttrSkinContext', query=True, sao=True)
    if paint_operation == 'additive':
        cmds.artAttrSkinPaintCtx('artAttrSkinContext', edit=True, sao='absolute', value=1.0)
    elif paint_operation == 'absolute':
        cmds.artAttrSkinPaintCtx('artAttrSkinContext', edit=True, sao='additive', value=0.025)


def callPaintListWindowWithSetInfluence(max_inf):
    if not max_inf:
        return

    mel.eval('artSkinInflListChanging "{}" 1'.format(max_inf))
    mel.eval('artSkinInflListChanged artAttrSkinPaintCtx')
    cmds.headsUpMessage('{}'.format(max_inf), time=1)

    try:
        cmds.artAttrSkinPaintCtx('artAttrSkinContext', edit=True, inf=max_inf)
    except Exception:
        pass


def _build_brush_info_html():
    mode_str = u"未知"
    try:
        op = cmds.artAttrSkinPaintCtx('artAttrSkinContext', query=True, sao=True)
        val = cmds.artAttrSkinPaintCtx('artAttrSkinContext', query=True, value=True)
        if op == 'absolute':
            mode_str = u"REPLACE<span style='font-size:11px; color:#AAAAAA;'> ({:.3f})</span>".format(val)
        elif op == 'additive':
            mode_str = u"ADD<span style='font-size:11px; color:#AAAAAA;'> ({:.3f})</span>".format(val)
        else:
            mode_str = u"{}<span style='font-size:11px; color:#AAAAAA;'> ({:.3f})</span>".format(op, val)
    except Exception:
        pass
    return mode_str


# ----------------------------------------------------------------------
# 总流程：选中 -> 射线选面 -> 找最大权重骨骼 -> 刷权 -> HUD -> 相机枢轴
# ----------------------------------------------------------------------
def mainFunc():
    global _overlay_widget

    sel = cmds.ls(selection=True, long=True, fl=True)
    if not sel:
        cmds.warning(u'请先选择一个蒙皮模型或其组件')
        return

    first = sel[0]

    # transform / shape / component 统一处理
    if '.' in first:
        base = first.split('.')[0]
    else:
        base = first

    if not cmds.objExists(base):
        cmds.warning(u"选中的对象不存在: {}".format(base))
        return

    node_type = cmds.nodeType(base)
    if node_type == 'mesh':
        mesh_shape = cmds.ls(base, long=True)[0]
        parents = cmds.listRelatives(mesh_shape, parent=True, fullPath=True) or []
        mesh_transform = parents[0] if parents else None
    else:
        mesh_transform = cmds.ls(base, long=True)[0]
        shapes = cmds.listRelatives(mesh_transform, shapes=True, noIntermediate=True, fullPath=True) or []
        mesh_shape = None
        for s in shapes:
            if cmds.nodeType(s) == 'mesh':
                mesh_shape = s
                break

    if not mesh_transform or not mesh_shape:
        cmds.warning(u"选中的对象没有有效的 mesh 形节点")
        return

    # 1) 射线拾取面
    face_id = getFaceIDbyMouseCursor(mesh_shape)
    if not face_id:
        return

    # 2) 找 skinCluster
    skin = mel.eval('findRelatedSkinCluster("{}");'.format(mesh_transform))
    if not skin:
        cmds.warning(u"未找到与 '{}' 关联的 skinCluster".format(mesh_transform))
        return

    # 3) 高性能查询最大权重骨骼
    bone_name, bone_dag = get_max_influence_api2(face_id, skin)
    if not bone_name or bone_dag is None:
        cmds.warning(u"无法获取最大权重骨骼")
        return

    # 4) 打开 / 切换权重刷，并设置影响
    editSkinWeightTools()
    callPaintListWindowWithSetInfluence(bone_name)
    mel.eval('artSkinRevealSelected artAttrSkinPaintCtx')

    # 5) 计算骨骼屏幕位置
    screen_pos = get_bone_screen_pos(bone_dag)

    # 6) 相机旋转枢轴设置到该骨骼
    update_camera_tumble_pivot(bone_dag)

    # 7) HUD：绿色点 + 骨骼名 + 笔刷模式
    display_name = bone_name.split('|')[-1]
    brush_info = _build_brush_info_html()
    html = (
        u"<div style='font-weight:bold; font-size:15px; color:#FFDD00;'>{bone}</div>"
        u"<div style='font-weight:900; font-size:13px; color:#FF5555; margin-top:2px;'>{mode}</div>"
    ).format(bone=display_name, mode=brush_info)

    if screen_pos:
        if _overlay_widget is None or not shiboken6.isValid(_overlay_widget):
            _overlay_widget = BoneInfoOverlay()
        _overlay_widget.show_info(html, screen_pos[0], screen_pos[1])
    else:
        cmds.headsUpMessage(u"{} | {}".format(display_name, brush_info), time=1.0)



mainFunc()
