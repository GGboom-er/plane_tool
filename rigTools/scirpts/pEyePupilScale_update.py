# coding:utf-8
from __future__ import print_function, division

import maya.cmds as cmds
import maya.mel as mel
import maya.OpenMayaUI as omui
import math
import sys

# =========================
# PySide 兼容层 (Maya 2018-2025)
# =========================
try:
    # Maya 2018-2024：PySide2 / shiboken2
    from PySide2 import QtWidgets, QtGui, QtCore
    import shiboken2 as shiboken
except ImportError:
    # Maya 2025：PySide6 / shiboken6
    from PySide6 import QtWidgets, QtGui, QtCore
    import shiboken6 as shiboken

# Python2/3 兼容：long 在 Py3 中不存在
try:
    long
except NameError:
    long = int


# =========================
# 工具函数
# =========================
def is_shape(trans_node, typ="mesh"):
    if not cmds.objExists(trans_node):
        return False
    if cmds.objectType(trans_node) != "transform":
        return False
    shapes = cmds.listRelatives(trans_node, s=1, f=1)
    if not shapes:
        return False
    if cmds.objectType(shapes[0]) != typ:
        return False
    return True


def get_selected_vtx_center():
    points = [cmds.xform(sel, q=1, t=1, ws=1) for sel in cmds.ls(sl=1, fl=1)]
    center = [xyz / len(points) for xyz in map(sum, zip(*points))]
    return center


def order_select():
    if (cmds.selectPref(tso=True, q=True) == 0):
        cmds.selectPref(tso=True)
    ordered_selected = cmds.ls(orderedSelection=True, fl=1)
    return ordered_selected


def filter_vtx_from_selected():
    list_selected = order_select()
    returnValue = None
    if list_selected:
        first_element = list_selected[0]

        if '.vtx[' in first_element:
            returnValue = list_selected
        elif '.e[' in first_element:
            vertSel = []
            for item in list_selected:
                if cmds.filterExpand(item, sm=32) != "":
                    verts = cmds.polyListComponentConversion(item, fromEdge=True, toVertex=True)
                    vertSel.extend(verts)
            returnValue = cmds.ls(vertSel, fl=True)
        elif '.f[' in first_element:
            vertSel = []
            for item in list_selected:
                verts = cmds.polyListComponentConversion(item, fromFace=True, toVertex=True)
                vertSel.extend(verts)
            returnValue = cmds.ls(vertSel, fl=True)
        else:
            cmds.ConvertSelectionToVertices()
            returnValue = cmds.ls(sl=True, fl=True)
    if returnValue:
        cmds.select(returnValue, r=True)
    return returnValue


def get_skinCluster_node(Elements=None):
    Selected = cmds.ls(sl=True, fl=True)
    if Elements is None:
        Elements = Selected
    if not Elements:
        return
    History = cmds.listHistory(Elements)
    SkinNode = None
    for node in History:
        if cmds.nodeType(node) == 'skinCluster':
            SkinNode = node
            break
    return SkinNode


def get_sdk_value(percent=0.707):
    """把线性比例转换成 SDK 中使用的 sin 曲线比例"""
    # 防止浮点误差或模型比例导致超出 [-1,1] 触发 math domain error
    sin_theta = max(-1.0, min(1.0, float(percent)))
    theta_radians = math.asin(sin_theta)
    theta_degrees = math.degrees(theta_radians)
    result = (theta_degrees * 2.0) / 180.0
    return result


def get_largest_trans_axis(locator):
    # 使用 translate 值判断主轴向
    _x = cmds.getAttr("{}.translateX".format(locator))
    _y = cmds.getAttr("{}.translateY".format(locator))
    _z = cmds.getAttr("{}.translateZ".format(locator))

    abs_x = abs(_x)
    abs_y = abs(_y)
    abs_z = abs(_z)

    scales = {'x': abs_x, 'y': abs_y, 'z': abs_z}
    axis = max(scales, key=scales.get)

    if axis == 'x':
        direction = 1 if _x > 0 else -1
        other_axes = ['y', 'z']
    elif axis == 'y':
        direction = 1 if _y > 0 else -1
        other_axes = ['x', 'z']
    else:
        axis = 'z'
        direction = 1 if _z > 0 else -1
        other_axes = ['x', 'y']

    return axis, other_axes, direction


# =========================
# 眼球瞳孔缩放核心类
# =========================
class EyePupil(object):
    def __init__(self, eyeBall_joint='Lf_EyeBall_Joint'):
        self.eyeBall_joint = eyeBall_joint
        self.eyeBall_pupilScale_null = eyeBall_joint + '_PupilScale' + '_Null'
        self.eyeBall_pupilScale_group = eyeBall_joint + '_PupilScale' + '_Group'

    def connect_eyeBall_control(self):
        sel = cmds.ls(sl=True)
        if not sel:
            cmds.warning(u'请先选择控制器')
            return

        _control = sel[0]
        _null = self.eyeBall_pupilScale_null
        if not cmds.objExists(_null):
            cmds.warning(u'未找到瞳孔缩放节点：{}，请先创建眼球定位器。'.format(_null))
            return

        attrs = ['pupil', 'iris']

        for _attr in attrs:
            obj_attr = '{}.{}'.format(_null, _attr)
            con_attr = '{}.{}'.format(_control, _attr)
            if cmds.objExists(obj_attr):
                if not cmds.objExists(con_attr):
                    cmds.addAttr(_control, ln=_attr, at='double', min=-1, max=1, dv=0)
                    cmds.setAttr(con_attr, e=True, keyable=True)
                if not cmds.isConnected(con_attr, obj_attr):
                    cmds.connectAttr(con_attr, obj_attr, f=True)

    def create_root_loc(self):
        eyeBall_joint = self.eyeBall_joint

        _Group = self.eyeBall_pupilScale_group
        if not cmds.objExists(_Group):
            cmds.createNode('transform', n=_Group)
            if cmds.objExists(eyeBall_joint):
                cmds.matchTransform(_Group, eyeBall_joint, pos=True, rot=True, scl=True)

        _Null = self.eyeBall_pupilScale_null
        if not cmds.objExists(_Null):
            cmds.createNode('transform', n=_Null)
            # pupil / iris 属性
            for attr in ("pupil", "iris"):
                if not cmds.objExists("{}.{}".format(_Null, attr)):
                    cmds.addAttr(_Null, ln=attr, at='double', min=-1, max=1, dv=0)
                    cmds.setAttr("{}.{}".format(_Null, attr), e=True, keyable=True)

            if cmds.objExists(eyeBall_joint):
                cmds.matchTransform(_Null, eyeBall_joint, pos=True, rot=True, scl=True)
            cmds.parent(_Null, _Group)

        eyeBall_root_loc = eyeBall_joint + '_Loc'
        if not cmds.objExists(eyeBall_root_loc):
            _guide = cmds.spaceLocator()[0]
            eyeBall_root_loc = cmds.rename(_guide, eyeBall_root_loc)
            if cmds.objExists(eyeBall_joint):
                cmds.matchTransform(eyeBall_root_loc, eyeBall_joint, pos=True, rot=True, scl=False)
            else:
                _joint = cmds.createNode('joint')
                eyeBall_joint = cmds.rename(_joint, eyeBall_joint)

        cmds.parent(eyeBall_root_loc, _Null)
        cmds.parentConstraint(eyeBall_joint, _Null, weight=1, mo=0)
        cmds.scaleConstraint(eyeBall_joint, _Null, weight=1, mo=0)
        cmds.select(eyeBall_root_loc, r=True)

    def auto_create_loc(self, auto_skinning_enabled=False):
        # 防呆：如果还没创建 root loc，自动创建一次
        eyeBall_joint = self.eyeBall_joint
        eyeBall_root_loc = eyeBall_joint + '_Loc'
        if not cmds.objExists(eyeBall_root_loc):
            self.create_root_loc()

        eyeBall_pupil_loc = eyeBall_joint + '_Pupil_Loc'
        if cmds.objExists(eyeBall_pupil_loc):
            self.create_loc(False, auto_skinning_enabled)
        else:
            result = cmds.confirmDialog(
                title=u'确认',
                message=u'请确认当前选择了虹膜边缘的顶点?',
                button=[u'是', '否'],
                defaultButton=u'是',
                cancelButton=u'否',
                dismissString=u'否'
            )

            if result == u'是':
                self.create_loc(True, auto_skinning_enabled)
            else:
                print(u"用户取消操作")

    def create_loc(self, if_Tip, auto_skinning_enabled=False):
        eyeBall_joint = self.eyeBall_joint

        eyeBall_root_loc = eyeBall_joint + '_Loc'
        eyeBall_pupil_loc = eyeBall_joint + '_Pupil_Loc'
        _Null = self.eyeBall_pupilScale_null

        if not cmds.objExists(eyeBall_root_loc):
            cmds.error(u'未找到眼球 Root 定位器：{}，请先创建。'.format(eyeBall_root_loc))
            return

        if not cmds.objExists(_Null):
            cmds.error(u'未找到瞳孔缩放节点：{}，请先创建。'.format(_Null))
            return

        cmds.setAttr(eyeBall_root_loc + '.v', 0)

        # 判断是不是选择了模型的点
        _vtxs = filter_vtx_from_selected()
        _shapes = cmds.ls(sl=1, o=True)

        if not _shapes:
            cmds.warning(u'请在模型上选择顶点。')
            return
        else:
            if cmds.nodeType(_shapes[0]) != 'mesh':
                cmds.warning(u'请选择多边形模型的顶点。')
                return
            eyeBall_mesh = cmds.listRelatives(_shapes[0], p=1)[0]

        # 检测 SkinCluster
        skinClusterName = get_skinCluster_node(Elements=None)

        point = get_selected_vtx_center()
        _loc = cmds.spaceLocator()[0]
        _loc = cmds.parent(_loc, eyeBall_root_loc)[0]

        cmds.setAttr(_loc + '.s', 1, 1, 1, type='float3')
        cmds.matchTransform(_loc, eyeBall_root_loc, pos=True, rot=True, scl=True)
        cmds.xform(_loc, t=point, ws=True)

        axis, other_axis, direction = get_largest_trans_axis(_loc)
        if cmds.objExists(eyeBall_pupil_loc):
            axis, other_axis, direction = get_largest_trans_axis(eyeBall_pupil_loc)

        _Percent = cmds.getAttr(_loc + '.t%s' % axis)
        Percent = get_sdk_value(_Percent)

        if if_Tip is True:
            _name = eyeBall_pupil_loc
            Max_Percent_SDK = direction
            other_axis = ['x', 'y', 'z']
        else:
            _id = "{:02d}".format(int(abs(Percent) * 100))
            _name = '{}_{}_Loc'.format(eyeBall_joint, _id)
            _Max_Percent = cmds.getAttr(eyeBall_pupil_loc + '.t%s' % axis)
            Max_Percent = get_sdk_value(_Max_Percent)
            # 防止除 0
            if Max_Percent == 0:
                Max_Percent_SDK = direction
            else:
                Max_Percent_SDK = Percent / Max_Percent * direction

            if _Percent > _Max_Percent:
                Max_Percent = 1

        if not cmds.objExists(_name):
            if abs(_Percent) < 0.01:
                cmds.warning(u'所选元素靠近中心,不需要被驱动.')
                cmds.delete(_loc)
                return
            elif abs(_Percent) > 0.99:
                cmds.warning(u'所选元素接近极限值,不需要被驱动.')
                cmds.delete(_loc)
                return
        else:
            cmds.delete(_loc)
            return

        _loc = cmds.rename(_loc, _name)

        # === 创建 SDK animCurveUU ===
        setKeyFrameNode = cmds.createNode('animCurveUU')
        cmds.setKeyframe(setKeyFrameNode, f=0, value=Percent, itt='linear', ott='linear')
        cmds.setKeyframe(setKeyFrameNode, f=1, value=Max_Percent_SDK, itt='linear', ott='linear')
        cmds.setKeyframe(setKeyFrameNode, f=-1, value=0, itt='linear', ott='linear')
        cmds.connectAttr(_Null + '.pupil', setKeyFrameNode + '.input')

        # floatMath
        mathNode = cmds.createNode('floatMath')
        cmds.setAttr(mathNode + '.operation', 2)  # multiply
        cmds.setAttr(mathNode + '.floatB', 180)
        cmds.connectAttr(setKeyFrameNode + '.output', mathNode + '.floatA')

        # eulerToQuat
        eulerToQuatNode = cmds.createNode('eulerToQuat')
        cmds.connectAttr(mathNode + '.outFloat', eulerToQuatNode + '.inputRotateX')

        # sin / cos 缓存
        if not cmds.objExists(_loc + ".sin"):
            cmds.addAttr(_loc, ln="sin", at='double', min=-1, max=1, dv=0, keyable=True)
        if not cmds.objExists(_loc + ".cos"):
            cmds.addAttr(_loc, ln="cos", at='double', min=-1, max=1, dv=0, keyable=True)

        cmds.connectAttr(eulerToQuatNode + '.outputQuatX', _loc + '.sin')
        cmds.connectAttr(eulerToQuatNode + '.outputQuatW', _loc + '.cos')
        cmds.connectAttr(_loc + '.sin', _loc + '.t%s' % axis)

        quatW = cmds.getAttr(eulerToQuatNode + '.outputQuatW')

        setKeyFrameNode = cmds.createNode('animCurveUU')
        cmds.setKeyframe(setKeyFrameNode, f=0, value=0, itt='linear', ott='linear')
        cmds.setKeyframe(setKeyFrameNode, f=quatW, value=1, itt='linear', ott='linear')
        cmds.setKeyframe(setKeyFrameNode, f=1, value=1.0 / quatW if quatW != 0 else 1.0, itt='linear', ott='linear')
        cmds.connectAttr(_loc + '.cos', setKeyFrameNode + '.input')

        thisTrans = cmds.createNode('transform')
        thisTrans = cmds.rename(thisTrans, _name.replace('_Loc', '_Trans'))
        cmds.parentConstraint(_loc, thisTrans, weight=1, mo=0)
        cmds.parent(thisTrans, _Null)

        for i in other_axis:
            if i == axis:
                power_node = cmds.createNode('floatMath')
                cmds.setAttr("{}.operation".format(power_node), 6)  # power
                cmds.setAttr("{}.floatB".format(power_node), 2)
                cmds.connectAttr(setKeyFrameNode + '.output', "{}.floatA".format(power_node))
                cmds.connectAttr("{}.outFloat".format(power_node), thisTrans + '.s%s' % i)
            else:
                cmds.connectAttr(setKeyFrameNode + '.output', thisTrans + '.s%s' % i)

        Loop_Joint = cmds.createNode('joint')
        Loop_Joint = cmds.rename(Loop_Joint, _name.replace('_Loc', '_Joint'))
        cmds.matchTransform(Loop_Joint, thisTrans, pos=True, rot=True)
        cmds.parent(Loop_Joint, eyeBall_joint)
        cmds.makeIdentity(Loop_Joint, apply=True, t=1, r=1, s=1, n=0)

        cmds.parentConstraint(thisTrans, Loop_Joint, weight=1, mo=0)
        cmds.scaleConstraint(thisTrans, Loop_Joint, weight=1, mo=0)

        eyeBall_iris_trans = eyeBall_joint + '_Iris_Trans'
        eyeBall_iris_joint = eyeBall_joint + '_Iris_Joint'

        Iris_Joint = None
        if len(other_axis) == 3:
            _Trans = cmds.createNode('transform')
            _Trans = cmds.rename(_Trans, eyeBall_iris_trans)
            cmds.parent(_Trans, thisTrans)
            cmds.matchTransform(_Trans, thisTrans)

            Iris_Joint = cmds.createNode('joint')
            Iris_Joint = cmds.rename(Iris_Joint, eyeBall_iris_joint)
            cmds.matchTransform(Iris_Joint, _Trans, pos=True, rot=True)
            cmds.parent(Iris_Joint, eyeBall_joint)
            cmds.makeIdentity(Iris_Joint, apply=True, t=1, r=1, s=1, n=0)

            cmds.parentConstraint(_Trans, Iris_Joint, weight=1, mo=0)
            cmds.scaleConstraint(_Trans, Iris_Joint, weight=1, mo=0)

            setKeyFrameNode = cmds.createNode('animCurveUU')
            cmds.setKeyframe(setKeyFrameNode, f=0, value=1, itt='linear', ott='linear')
            cmds.setKeyframe(setKeyFrameNode, f=-1, value=0, itt='linear', ott='linear')
            cmds.setKeyframe(setKeyFrameNode, f=1, value=2, itt='linear', ott='linear')
            cmds.connectAttr(_Null + ".iris", setKeyFrameNode + '.input')
            for i in other_axis:
                if i != axis:
                    cmds.connectAttr(setKeyFrameNode + '.output', _Trans + '.s%s' % i)

        cmds.select(_vtxs, r=True)

        # ========= 自动蒙皮 =========
        def lock_skin_influences(skin_cluster, if_lock=True):
            skin_inf_list = cmds.skinCluster(skin_cluster, query=True, wi=True)
            for inf in skin_inf_list:
                cmds.setAttr("%s.liw" % inf, if_lock)

        def add_joint_to_skin_cluster_locked(skin_cluster, joint_name):
            influences = cmds.skinCluster(skin_cluster, query=True, influence=True)
            if joint_name not in influences:
                lock_skin_influences(skin_cluster, True)
                cmds.skinCluster(skin_cluster, edit=True, addInfluence=joint_name, weight=1.0)
                lock_skin_influences(skin_cluster, False)
            else:
                print(u"骨骼 {} 已经是 skinCluster 的影响对象。".format(joint_name))

        vtx_list = _vtxs
        if auto_skinning_enabled is True:
            if not skinClusterName:
                cmds.error(u'没有发现蒙皮节点')
            else:
                add_joint_to_skin_cluster_locked(skinClusterName, Loop_Joint)
                for vtx in vtx_list:
                    cmds.skinPercent(skinClusterName, vtx, transformValue=[(Loop_Joint, 1.0)])
                if Iris_Joint:
                    add_joint_to_skin_cluster_locked(skinClusterName, Iris_Joint)

        cmds.select(_vtxs, r=True)


# =========================
# UI 封装
# =========================
def maya_main_window():
    """获取 Maya 主窗口，兼容 PySide2 / PySide6 & Py2/3。"""
    ptr = omui.MQtUtil.mainWindow()
    if ptr is None:
        return None
    try:
        return shiboken.wrapInstance(long(ptr), QtWidgets.QWidget)
    except Exception:
        return None


class CopyButtonDialog(QtWidgets.QDialog):
    def __init__(self, parent=maya_main_window()):
        super(CopyButtonDialog, self).__init__(parent)

        self.setObjectName("pEyePupilScaleDialog")
        self.setWindowTitle(u'pEyePupilScale (瞳孔缩放添加工具) v1.0')

        # 关键：确保关闭按钮行为正常，并移除帮助按钮
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        try:
            # Qt5/Qt6 推荐写法
            self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        except AttributeError:
            # 旧版本备选写法
            self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)

        self.setMinimumWidth(300)
        self.createWidgets()
        self.createLayout()
        self.createConnections()

    def createWidgets(self):
        self.auto_skin_checkbox = QtWidgets.QCheckBox(u'自动蒙皮')
        self.auto_skin_checkbox.setChecked(True)

        self.select_eye_ball_button = QtWidgets.QPushButton(u'创建眼球定位器并手动适配眼球大小')
        self.select_eye_white_circle_button = QtWidgets.QPushButton(u'依次选择眼白圈线(先选瞳孔边界线)')
        self.load_bones_button = QtWidgets.QPushButton(u'加载眼球骨骼')
        self.connect_controller_button = QtWidgets.QPushButton(u'选择控制器并连接')

        self.bone_name_field = QtWidgets.QLineEdit(self)
        self.bone_name_field.setPlaceholderText(u"请输入骨骼名称...")
        self.bone_name_field.setReadOnly(True)

    def createLayout(self):
        layout = QtWidgets.QVBoxLayout(self)

        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addWidget(self.auto_skin_checkbox)
        top_layout.addWidget(self.load_bones_button)
        top_layout.addWidget(self.bone_name_field)

        layout.addLayout(top_layout)
        layout.addWidget(self.select_eye_ball_button)
        layout.addWidget(self.select_eye_white_circle_button)
        layout.addWidget(self.connect_controller_button)

    def createConnections(self):
        self.select_eye_ball_button.clicked.connect(self.select_eye_ball)
        self.select_eye_white_circle_button.clicked.connect(self.select_eye_white_circle)
        self.load_bones_button.clicked.connect(self.load_bones)
        self.connect_controller_button.clicked.connect(self.connect_controller)

    def _first_bone_name(self):
        """内部小工具：从文本里取第一个骨骼名。"""
        txt = self.bone_name_field.text()
        if not txt:
            return ""
        return txt.split(',')[0].strip()

    def select_eye_ball(self):
        bone_name = self._first_bone_name()
        if bone_name:
            EYE = EyePupil(bone_name)
            EYE.create_root_loc()
        else:
            cmds.warning(u"骨骼名称为空，请先加载骨骼。")

    def select_eye_white_circle(self):
        bone_name = self._first_bone_name()
        auto_skinning_enabled = self.auto_skin_checkbox.isChecked()
        if bone_name:
            EYE = EyePupil(bone_name)
            EYE.auto_create_loc(auto_skinning_enabled)
        else:
            cmds.warning(u"骨骼名称为空，请先加载骨骼。")

    def load_bones(self):
        # 保持原逻辑：允许多选，全部写进文本框
        selection = cmds.ls(selection=True, type="transform")
        if selection:
            self.bone_name_field.setText(", ".join(selection))
        else:
            cmds.warning(u"请先选择眼球骨骼(Transform / Joint)")

    def connect_controller(self):
        bone_name = self._first_bone_name()
        if bone_name:
            EYE = EyePupil(bone_name)
            EYE.connect_eyeBall_control()
        else:
            cmds.warning(u"骨骼名称为空，请先加载骨骼。")


# =========================
# 入口函数
# =========================
def main():
    global copy_dialog
    try:
        copy_dialog.close()
        copy_dialog.deleteLater()
    except:
        pass

    copy_dialog = CopyButtonDialog()
    copy_dialog.show()


main()
