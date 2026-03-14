#!/usr/bin/env python
# _*_ coding:utf-8 _*_

"""
@author: GGboom
@desc:
    Quick Skin Picker + 关节屏幕标记 + 相机旋转枢轴对齐
    [纯 API 2.0 终极生产环境级稳健版 - V2.0 Final]

    核心升级:
    1. 彻底剔除 API 1.0 (OpenMaya)，全线使用 API 2.0 (maya.api.OpenMaya)。
    2. 严格校准 viewToWorld 与 closestIntersection 的 C++ 内存指针传参。
    3. 引入全局生命周期接管 (Global Lifecycle Management)，彻底杜绝热键多开导致的 Qt 线程崩溃 (Fatal Error)。
    4. 移除双重 UI 冲突，确保 HUD 清爽。
"""

import sys

# --- API 2.0：高性能底层框架 -----------------------------------------------
import maya.api.OpenMaya as om2
import maya.api.OpenMayaUI as omui2
import maya.api.OpenMayaAnim as oma2

import maya.cmds as cmds
import maya.mel as mel

from PySide6 import QtWidgets, QtGui, QtCore
import shiboken6


# ----------------------------------------------------------------------
# 悬浮 UI 模块 (PySide6)
# ----------------------------------------------------------------------
class BoneInfoOverlay(QtWidgets.QWidget):
    """
    屏幕悬浮标签 (纯净版)
    """

    def __init__( self, parent=None ):
        # 强制使用 Python 3 无参 super()，免疫 __main__ 命名空间类重载导致的 TypeError
        super().__init__(parent)

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.ToolTip |
            QtCore.Qt.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(18, 10, 10, 10)

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

    def paintEvent( self, event ):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QColor(0, 255, 0))
        painter.drawEllipse(QtCore.QPoint(10, 10), 10, 10)

        super().paintEvent(event)

    def show_info( self, html_text, screen_x, screen_y ):
        try:
            self._anim.stop()
        except RuntimeError:
            pass

        self.label.setText(html_text)
        self.adjustSize()
        self.move(int(screen_x - 10), int(screen_y - 10))

        self._opacity_effect.setOpacity(1.0)
        self.show()

        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()


# ----------------------------------------------------------------------
# 视口 (Viewport) 与射线工具 (Raycast) (纯 API 2.0)
# ----------------------------------------------------------------------
def _get_active_view():
    view = omui2.M3dView.active3dView()
    widget_ptr = view.widget()
    if widget_ptr is None:
        return view, None
    widget = shiboken6.wrapInstance(int(widget_ptr), QtWidgets.QWidget)
    return view, widget


def _get_scene_pos_from_mouse():
    view, widget = _get_active_view()
    if widget is None:
        return None

    view_height = view.portHeight()
    global_pos = QtGui.QCursor.pos()
    local_pos = widget.mapFromGlobal(global_pos)
    return local_pos.x(), view_height - local_pos.y()


def getFaceIDbyMouseCursor( mesh_name ):
    if not cmds.objExists(mesh_name):
        return None

    scene_pos = _get_scene_pos_from_mouse()
    if scene_pos is None:
        return None

    view, _ = _get_active_view()

    # API 2.0 严格传参：强制分配接收指针的内存空间
    ray_source = om2.MPoint()
    ray_direction = om2.MVector()
    view.viewToWorld(int(scene_pos[0]), int(scene_pos[1]), ray_source, ray_direction)

    # 强制类型转换：closestIntersection 仅接受 MFloat 变体
    ray_source_float = om2.MFloatPoint(ray_source)
    ray_direction_float = om2.MFloatVector(ray_direction)

    sel_list = om2.MSelectionList()
    sel_list.add(mesh_name)
    dag_path = sel_list.getDagPath(0)

    if dag_path.apiType() == om2.MFn.kTransform:
        dag_path.extendToShape()

    fn_mesh = om2.MFnMesh(dag_path)

    try:
        hit_info = fn_mesh.closestIntersection(
            ray_source_float,
            ray_direction_float,
            om2.MSpace.kWorld,
            99999.0,
            False
        )

        if hit_info:
            hit_face_idx = hit_info[2]
            return "{}.f[{}]".format(mesh_name, hit_face_idx)
    except RuntimeError:
        return None

    return None


# ----------------------------------------------------------------------
# 高性能权重提取 (Skin Weight Data) (纯 API 2.0)
# ----------------------------------------------------------------------
def get_max_influence_api2( face_id, skin_name ):
    if not face_id or not skin_name:
        return None, None

    try:
        obj_part, comp = face_id.split('.f[')
        face_index = int(comp.rstrip(']'))
    except Exception:
        return None, None

    sel = om2.MSelectionList()
    sel.add(obj_part)
    dag_path = sel.getDagPath(0)

    if dag_path.apiType() == om2.MFn.kTransform:
        dag_path.extendToShape()

    fn_mesh = om2.MFnMesh(dag_path)
    vtx_ids = fn_mesh.getPolygonVertices(face_index)

    if not vtx_ids:
        return None, None

    sel_skin = om2.MSelectionList()
    sel_skin.add(skin_name)
    skin_obj = sel_skin.getDependNode(0)
    fn_skin = oma2.MFnSkinCluster(skin_obj)

    comp_fn = om2.MFnSingleIndexedComponent()
    comp = comp_fn.create(om2.MFn.kMeshVertComponent)
    comp_fn.addElements(vtx_ids)

    weights, inf_count = fn_skin.getWeights(dag_path, comp)
    inf_paths = fn_skin.influenceObjects()

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
# 相机枢轴对齐 (Camera Pivot Alignment)
# ----------------------------------------------------------------------
def get_bone_screen_pos( bone_dag_path ):
    try:
        view, widget = _get_active_view()
        if widget is None:
            return None

        fn_trans = om2.MFnTransform(bone_dag_path)
        world_pt = om2.MPoint(fn_trans.translation(om2.MSpace.kWorld))

        x, y, _ = view.worldToView(world_pt)
        view_h = view.portHeight()

        local_pos = QtCore.QPoint(int(x), int(view_h - y))
        global_pos = widget.mapToGlobal(local_pos)
        return global_pos.x(), global_pos.y()
    except Exception:
        return None


def update_camera_tumble_pivot( bone_dag_path ):
    try:
        fn_t = om2.MFnTransform(bone_dag_path)
        world_vec = fn_t.translation(om2.MSpace.kWorld)

        view, _ = _get_active_view()
        cam_dag = view.getCamera()
        cam_shape_name = cam_dag.partialPathName()

        cmds.setAttr("{}.tumblePivot".format(cam_shape_name), world_vec.x, world_vec.y, world_vec.z)

        if cmds.attributeQuery("usePivotAsLocalSpace", node=cam_shape_name, exists=True):
            cmds.setAttr("{}.usePivotAsLocalSpace".format(cam_shape_name), 0)

        if cmds.contextInfo("tumbleContext", exists=True):
            cmds.tumbleCtx("tumbleContext", e=True, localTumble=0)

    except Exception as e:
        sys.stderr.write("Quick_skin Pivot Update Failed: %s\n" % e)


# ----------------------------------------------------------------------
# 笔刷操作调度 (Paint Context Logic)
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


def callPaintListWindowWithSetInfluence( max_inf ):
    if not max_inf:
        return

    mel.eval('artSkinInflListChanging "{}" 1'.format(max_inf))
    mel.eval('artSkinInflListChanged artAttrSkinPaintCtx')

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
# 主程序入口 (Main Execution)
# ----------------------------------------------------------------------
def mainFunc():
    # [核心修复] 热键执行防爆破：强行接管垃圾回收，销毁旧实例
    if "_quick_skin_overlay" in globals():
        old_widget = globals()["_quick_skin_overlay"]
        if old_widget is not None and shiboken6.isValid(old_widget):
            old_widget.close()
            old_widget.deleteLater()

    globals()["_quick_skin_overlay"] = None

    sel = cmds.ls(selection=True, long=True, fl=True)
    if not sel:
        cmds.warning(u'请先选择一个蒙皮模型 (Skinned Mesh) 或其组件')
        return

    first = sel[0]
    base = first.split('.')[0] if '.' in first else first

    if not cmds.objExists(base):
        return

    node_type = cmds.nodeType(base)
    if node_type == 'mesh':
        mesh_shape = cmds.ls(base, long=True)[0]
        parents = cmds.listRelatives(mesh_shape, parent=True, fullPath=True) or []
        mesh_transform = parents[0] if parents else None
    else:
        mesh_transform = cmds.ls(base, long=True)[0]
        shapes = cmds.listRelatives(mesh_transform, shapes=True, noIntermediate=True, fullPath=True) or []
        mesh_shape = next((s for s in shapes if cmds.nodeType(s) == 'mesh'), None)

    if not mesh_transform or not mesh_shape:
        return

    face_id = getFaceIDbyMouseCursor(mesh_shape)
    if not face_id:
        return

    skin = mel.eval('findRelatedSkinCluster("{}");'.format(mesh_transform))
    if not skin:
        return

    bone_name, bone_dag = get_max_influence_api2(face_id, skin)
    if not bone_name or bone_dag is None:
        return

    editSkinWeightTools()
    callPaintListWindowWithSetInfluence(bone_name)
    mel.eval('artSkinRevealSelected artAttrSkinPaintCtx')

    screen_pos = get_bone_screen_pos(bone_dag)
    update_camera_tumble_pivot(bone_dag)

    display_name = bone_name.split('|')[-1]
    brush_info = _build_brush_info_html()
    html = (
        u"<div style='font-weight:bold; font-size:15px; color:#FFDD00;'>{bone}</div>"
        u"<div style='font-weight:900; font-size:13px; color:#FF5555; margin-top:2px;'>{mode}</div>"
    ).format(bone=display_name, mode=brush_info)

    if screen_pos:
        _, viewport_widget = _get_active_view()
        # 实例化并注入全局字典以供追踪销毁
        new_overlay = BoneInfoOverlay(parent=viewport_widget)
        globals()["_quick_skin_overlay"] = new_overlay
        new_overlay.show_info(html, screen_pos[0], screen_pos[1])
    else:
        # 容错：当屏幕坐标转换失败时，回退到普通打印控制台输出
        print(u"Quick_skin: {} | {}".format(display_name, brush_info))


if __name__ == "__main__":
    mainFunc()