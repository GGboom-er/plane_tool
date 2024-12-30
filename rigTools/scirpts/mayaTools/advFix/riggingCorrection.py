# _*_ coding:cp936 _*_
"""
Scripts :    python.tools.rigging.riggingCorrection
Author  :    JesseChou
Date    :    2021/4/27
QQ      :    375714316
E-Mail  :    JesseChou0612@gmail.com or 375714316@qq.com
"""
from python.tools.ywmTools.attrToolsPK import attrTools
from python.core import config, setting
from python.meta import parent, selection
from python.tools.rigging import controllerManager
import python.tools.rigging.utils as utils

from maya import cmds


def check_node(name, node):
    """
    # 检查指定类型指定名称的节点是否存在
    :param name: 节点名称
    :param node: 节点类型
    :return: 节点名称
    """
    judge = False
    if cmds.objExists(name):
        if cmds.nodeType(name) == node:
            judge = True
    if not judge:
        name = cmds.createNode(node, n=name)
    return name


def get_controller_size(controller):
    """
    # 获取控制器真实大小
    :param controller: 控制器名称
    :return: 控制器的尺寸
             [x,y,z]
    """
    try:
        bbx = cmds.xform('%s.cv[*]' % controller, q=1, bb=1)
    except Exception as e:
        print(e)
        bbx = cmds.xform(controller, q=1, bb=1)
    x = abs(bbx[3] - bbx[0])
    y = abs(bbx[4] - bbx[1])
    z = abs(bbx[5] - bbx[2])
    return [x, y, z]


def match_controller_size(controller, size):
    """
    # 匹配控制器大小
    :param controller: 控制器名称
    :param size: 指定大小
    :return:
    """
    radius = max(*get_controller_size(controller))
    num = size * 1.0 / radius
    cmds.select('%s.cv[*]' % controller, r=1)
    cmds.scale(num, num, num, r=True, ocp=True)


def match_transform(base, target):
    """
    # 匹配物体位置
    :param base: 要匹配位置的基础物体
    :param target: 要匹配位置的的目标物体
    :return:
    """
    position = cmds.xform(target, q=True, ws=True, t=True)
    rotation = cmds.xform(target, q=True, ws=True, ro=True)
    scale = cmds.xform(target, q=True, ws=True, s=True)
    cmds.xform(base, ws=True, t=position, ro=rotation, s=scale)


def check_sub_group(name, parentObj):
    """
    # 检查附加组别
    :param name:组别名称
    :param parentObj: 父物体
    :return:组别名称
    """
    if not cmds.objExists(name):
        cmds.createNode('transform', n=name)
    cmds.setAttr('%s.inheritsTransform' % name, 0)
    parent.fitParent(name, parentObj)
    for attr in setting.CHANNEL_BASE_ATTRS:
        if attr != 'v':
            cmds.setAttr('%s.%s' % (name, attr), e=1, l=1, k=0)
        else:
            cmds.setAttr('%s.%s' % (name, attr), e=1, l=0, k=0)
    return name


def lock_channel_attrs(transform, attrs):
    for attr in attrs:
        cmds.setAttr('%s.%s' % (transform, attr), e=True, l=True, k=False)


def get_target_child(start, end):
    """
    通过指定的起始/结束骨骼，获取两个骨骼间的中间骨骼列表
    :param start: 起始骨点名称
    :param end: 结束骨点名称
    :return: 中间的骨骼列表
    """
    infos = []
    children = cmds.listRelatives(start, c=True) or []
    if end in children:
        infos.append(start)
    else:
        for child in children:
            infos = get_target_child(child, end)
            if infos:
                infos.insert(0, start)
    return infos


def check_parent(child, parent):
    """
    检查并设置父物体
    :param child:
    :param parent:
    :return:
    """
    judge = False
    par = cmds.listRelatives(child, p=True)
    if par:
        if par[0] == parent:
            judge = True
    if not judge:
        cmds.parent(child, parent)
    try:
        cmds.setAttr('%s.t' % child, 0, 0, 0, typ='double3')
    except Exception as e:
        print(e)
    try:
        cmds.setAttr('%s.r' % child, 0, 0, 0, typ='double3')
    except Exception as e:
        print(e)
    try:
        cmds.setAttr('%s.s' % child, 1, 1, 1, typ='double3')
    except Exception as e:
        print(e)


class Controller(object):
    def __init__(self, name, index, color, parentObj=None):
        self.name = name
        self.color = color
        self.index = index
        self.parent = parentObj

    @property
    def controller(self):
        if not cmds.objExists(self.name):
            control = controllerManager.Controller(self.name, post='', color=self.color)
            control.create(self.index)
        return self.name

    @property
    def extra(self):
        ext = '%sExt' % self.controller
        if not cmds.objExists(ext):
            cmds.createNode('transform', n=ext)
            match_transform(ext, self.controller)
        parent.fitParent(self.controller, ext)
        return ext

    @property
    def offset(self):
        oft = '%sOft' % self.controller
        if not cmds.objExists(oft):
            cmds.createNode('transform', n=oft)
            match_transform(oft, self.extra)
        parent.fitParent(self.extra, oft)
        # print ('<>' * 50, oft, '\r\n', self.parent, '<>' * 50)
        parent.fitParent(oft, self.parent)
        return oft

    def __repr__(self):
        return self.controller

    def create(self):
        return self.offset


class Rigging(object):
    def __init__(self, **kwargs):
        """
        :param kwargs:  main_group_name/mgn         主组别的名称(字符串)
                        geometry_group_name/ggn     模型组别名称(字符串)
                        rigging_group_name/rgn      绑定组别名称(字符串)
                        deform_group_name/dgn       影响物组别名称(字符串)
                        other_group_name/ogn        其他杂项组别名称(字符串)

                        main_controller_name/mcn    主控制器名称(字符串)
                        main_controller_index/mci   主控制器创建编号(整数)
                        main_controller_color/mcc   主控制器颜色(3位0-1小数列表)

                        second_controller_name/scn  次级控制器名称(字符串)
                        second_controller_index/sci 次级控制器创建编号(整数)
                        second_controller_color/scc 次级控制器颜色(3位0-1小数列表)
        """
        self.__main_group = None
        self.__main_group_name = kwargs.get('main_group_name', kwargs.get('mgn', 'Group'))
        self.__geometry_group = None
        self.__geometry_group_name = kwargs.get('geometry_group_name', kwargs.get('ggn', 'Geometry'))
        self.__rigging_group = None
        self.__rigging_group_name = kwargs.get('rigging_group_name', kwargs.get('rgn', 'Rigging'))
        self.__deform_group = None
        self.__deform_group_name = kwargs.get('deform_group_name', kwargs.get('dgn', 'Deformation'))
        self.__other_group = None
        self.__other_group_name = kwargs.get('other_group_name', kwargs.get('ogn', 'Reference'))

        self.__skinMod_group = None
        self.__skinMod_group_name = kwargs.get('skinMod_group', kwargs.get('sgn', 'SkinModGrp'))

        self.__followMod_group = None
        self.__followMod_group_name = kwargs.get('followMod_group', kwargs.get('fgn', 'FollowModGrp'))

        self.__main_controller = None
        self.__main_controller_name = kwargs.get('main_controller_name', kwargs.get('mcn', 'Rig'))
        self.__main_controller_index = kwargs.get('main_controller_index', kwargs.get('mci', 41))
        self.__main_controller_color = kwargs.get('main_controller_color', kwargs.get('mcc', [0, 1, 0]))

        self.__second_controller = None
        self.__second_controller_name = kwargs.get('second_controller_name', kwargs.get('scn', 'Ctr'))
        self.__second_controller_index = kwargs.get('second_controller_index', kwargs.get('sci', 28))
        self.__second_controller_color = kwargs.get('second_controller_color', kwargs.get('scc', [1, 1, 0]))

        self.__group_infos = config.RIG_GROUP_CONFIG

    @property
    def main_group_name(self):
        return self.__main_group_name

    @property
    def main_group(self):
        return self.__main_group

    @property
    def geometry_group_name(self):
        return self.__geometry_group_name

    @property
    def geometry_group(self):
        return self.__geometry_group

    @property
    def other_group_name(self):
        return self.__other_group_name

    @property
    def other_group(self):
        return self.__other_group

    @property
    def skinMod_group_name(self):
        return self.__skinMod_group_name

    @property
    def skinMod_group(self):
        return self.__skinMod_group

    @property
    def followMod_group_name(self):
        return self.__followMod_group_name

    @property
    def followMod_group(self):
        return self.__followMod_group

    @property
    def rigging_group_name(self):
        return self.__rigging_group_name

    @property
    def rigging_group(self):
        return self.__rigging_group

    @property
    def deform_group_name(self):
        return self.__deform_group_name

    @property
    def deform_group(self):
        return self.__deform_group

    @property
    def main_controller_name(self):
        return self.__main_controller_name

    @property
    def main_controller_index(self):
        return self.__main_controller_index

    @property
    def main_controller_color(self):
        return self.__main_controller_color

    @property
    def main_controller(self):
        return self.__main_controller

    @property
    def second_controller_name(self):
        return self.__second_controller_name

    @property
    def second_controller_index(self):
        return self.__second_controller_index

    @property
    def second_controller_color(self):
        return self.__second_controller_color

    @property
    def second_controller(self):
        return self.__second_controller

    def check_groups(self):
        if not self.main_group:
            self.__main_group = check_node(self.main_group_name, 'transform')
            lock_channel_attrs(self.main_group, setting.CHANNEL_BASE_ATTRS)
        if not self.geometry_group:
            self.__geometry_group = check_node(self.geometry_group_name, 'transform')
            lock_channel_attrs(self.geometry_group, setting.CHANNEL_BASE_ATTRS)
            parent.fitParent(self.geometry_group, self.main_group)
            cmds.setAttr('%s.overrideDisplayType' % self.geometry_group, 2)
            for node in ['cache', 'data']:
                if cmds.objExists(node):
                    parent.fitParent(node, self.geometry_group)
        if not self.rigging_group:
            self.__rigging_group = check_node(self.rigging_group_name, 'transform')
            lock_channel_attrs(self.rigging_group, setting.CHANNEL_BASE_ATTRS)
            parent.fitParent(self.rigging_group, self.main_group)
        if not self.deform_group:
            self.__deform_group = check_node(self.deform_group_name, 'transform')
            lock_channel_attrs(self.deform_group, setting.CHANNEL_BASE_ATTRS)
            parent.fitParent(self.deform_group, self.main_group)
        if not self.other_group:
            self.__other_group = check_node(self.other_group_name, 'transform')
            lock_channel_attrs(self.other_group_name, setting.CHANNEL_BASE_ATTRS)
            parent.fitParent(self.other_group_name, self.main_group)
            cmds.setAttr('%s.overrideDisplayType' % self.other_group_name, 2)

        if not self.skinMod_group:
            self.__skinMod_group = check_node(self.skinMod_group_name, 'transform')
            try:
                cmds.setAttr(self.skinMod_group_name + '.v', 0)
            except:
                cmds.setAttr(self.skinMod_group_name + '.v', l=0)
                cmds.setAttr(self.skinMod_group_name + '.v', 0)
            lock_channel_attrs(self.skinMod_group_name, setting.CHANNEL_BASE_ATTRS)
            parent.fitParent(self.skinMod_group_name, self.other_group)
            cmds.setAttr('%s.overrideDisplayType' % self.skinMod_group_name, 2)

        if not self.followMod_group:
            self.__followMod_group = check_node(self.followMod_group_name, 'transform')
            try:
                cmds.setAttr(self.followMod_group_name + '.v', 0)
            except:
                cmds.setAttr(self.followMod_group_name + '.v', l=0)
                cmds.setAttr(self.followMod_group_name + '.v', 0)
            lock_channel_attrs(self.followMod_group_name, setting.CHANNEL_BASE_ATTRS)
            parent.fitParent(self.followMod_group_name, self.other_group)
            cmds.setAttr('%s.overrideDisplayType' % self.followMod_group_name, 2)

    def fit_controller_size(self, size=1.0):
        """
        适配控制器大小
        :param size: 物体大小
        :return:
        """
        select = selection.Selection()
        match_controller_size(self.main_controller, size * 2.2)
        match_controller_size(self.second_controller, size * 1.1)
        select.reselect()

    def check_controllers(self):
        # 创建控制器
        if self.rigging_group:
            if not self.main_controller:
                self.__main_controller = Controller(self.main_controller_name, self.main_controller_index,
                                                    self.main_controller_color, self.rigging_group)
                self.main_controller.create()
            if not self.second_controller:
                self.__second_controller = Controller(self.second_controller_name, self.second_controller_index,
                                                      self.second_controller_color, self.main_controller.controller)
                self.second_controller.create()
        else:
            print (u'请先创建基础组别，再来执行创建控制器命令！')


class ChrRigging(Rigging):
    def __init__(self, **kwargs):
        """
        :param kwargs:  main_group_name/mgn             主组别的名称(字符串)
                        geometry_group_name/ggn         模型组别名称(字符串)
                        rigging_group_name/rgn          绑定组别名称(字符串)
                        deform_group_name/dgn           影响物组别名称(字符串)
                        other_group_name/ogn            其他杂项组别名称(字符串)

                        main_controller_name/mcn        主控制器名称(字符串)
                        main_controller_index/mci       主控制器创建编号(整数)
                        main_controller_color/mcc       主控制器颜色(3位0-1小数列表)

                        second_controller_name/scn      次级控制器名称(字符串)
                        second_controller_index/sci     次级控制器创建编号(整数)
                        second_controller_color/scc     次级控制器颜色(3位0-1小数列表)

                        third_controller_name/tcn       三级控制器名称(字符串)
                        third_controller_index/tci      三级控制器创建编号(整数)
                        third_controller_color/tcc      三级控制器颜色(3位0-1小数列表)

                        visibility_controller_name/vcn  显隐控制器名称(字符串)
                        visibility_controller_index/vci 显隐控制器创建编号(整数)
                        visibility_controller_color/vcc 显隐控制器颜色(3位0-1小数列表)

                        extra_group_name/egn            附加绑定组别名称(字符串)
                        facial_group_name/fgn           表情绑定组别名称(字符串)
        """
        super(ChrRigging, self).__init__(**kwargs)
        self.__second_controller_name = kwargs.get('second_controller_name', kwargs.get('scn', 'Chr'))
        self.__second_controller_index = kwargs.get('second_controller_index', kwargs.get('sci', 112))
        self.__second_controller_color = kwargs.get('second_controller_color', kwargs.get('scc', [.45, .25, 0.05]))

        self.__third_controller = None
        self.__third_controller_name = kwargs.get('third_controller_name', kwargs.get('tcn', 'Main'))
        self.__third_controller_index = kwargs.get('third_controller_index', kwargs.get('tci', 56))
        self.__third_controller_color = kwargs.get('third_controller_color', kwargs.get('tcc', [0.22, 0.02, 0.54]))
        self.__visibility_controller = None
        self.__visibility_controller_name = kwargs.get('visibility_controller_name', kwargs.get('vcn', 'VisibilityCtr'))
        self.__visibility_controller_index = kwargs.get('visibility_controller_index', kwargs.get('vci', 117))
        self.__visibility_controller_color = kwargs.get('visibility_controller_color', kwargs.get('vcc', [1, 0, 0]))

        self.__extra_group = None
        self.__extra_group_name = kwargs.get('extra_group_name', kwargs.get('egn', 'ExtraSystem'))
        self.__facial_group = None
        self.__facial_group_name = kwargs.get('facial_group_name', kwargs.get('fgn', 'FacialSystem'))

    @property
    def visibility_Attributes(self):
        attrs = [{'name': 'deform_sys_vis', 'type': 'bool', 'value': True, 'keyable': False},
                 {'name': 'extra_sys_vis', 'type': 'bool', 'value': False, 'keyable': False},
                 {'name': 'facial_sys_vis', 'type': 'bool', 'value': False, 'keyable': False},
                 {'name': 'sub_facial_sys_vis', 'type': 'bool', 'value': False, 'keyable': False},
                 {'name': 'geometry_select_able', 'type': 'bool', 'value': False, 'keyable': False},
                 # {'name': 'RigSpeed', 'type': 'enum', 'value': 'normal(SLOW):proxy(FAST)', 'keyable': False},
                 {'name': 'cache_vis', 'type': 'bool', 'value': True, 'keyable': True}]
        return attrs

    @property
    def extra_group_name(self):
        return self.__extra_group_name

    @property
    def extra_group(self):
        return self.__extra_group

    @property
    def facial_group_name(self):
        return self.__facial_group_name

    @property
    def facial_group(self):
        return self.__facial_group

    @property
    def second_controller_name(self):
        return self.__second_controller_name

    @property
    def second_controller_index(self):
        return self.__second_controller_index

    @property
    def second_controller_color(self):
        return self.__second_controller_color

    @property
    def third_controller_name(self):
        return self.__third_controller_name

    @property
    def third_controller_index(self):
        return self.__third_controller_index

    @property
    def third_controller_color(self):
        return self.__third_controller_color

    @property
    def third_controller(self):
        return self.__third_controller

    @property
    def visibility_controller_name(self):
        return self.__visibility_controller_name

    @property
    def visibility_controller_index(self):
        return self.__visibility_controller_index

    @property
    def visibility_controller_color(self):
        return self.__visibility_controller_color

    @property
    def visibility_controller(self):
        return self.__visibility_controller

    def check_visibility_attrs(self, controller):
        """
        检查显示控制器控制属性
        :return:
        """
        for attr in self.visibility_Attributes:
            name = attr.get('name')
            if name:
                if not cmds.objExists('%s.%s' % (controller, name)):
                    if attr.get('type' != 'enum'):
                        cmds.addAttr(controller, ln=name, at=attr.get('type'), dv=attr.get('value'))
                    else:
                        cmds.addAttr(controller, ln=name, at=attr.get('type'), en=attr.get('value'))
                # cmds.setAttr('%s.%s' % (controller, name), attr.get('value'))
                keyable = attr.get('keyable')
                if keyable:
                    cmds.setAttr('%s.%s' % (controller, name), e=1, l=0, k=1)
                else:
                    cmds.setAttr('%s.%s' % (controller, name), e=1, l=0, cb=1)

        for attr in setting.CHANNEL_BASE_ATTRS:
            cmds.setAttr('%s.%s' % (controller, attr), e=1, l=1, k=0)

    def check_chr_controllers(self):
        # 检查角色绑定控制器
        # 检测基础控制器
        self.check_controllers()
        if self.rigging_group:
            # 检测第三级控制器
            if not self.third_controller:
                self.__third_controller = Controller(self.third_controller_name, self.third_controller_index,
                                                     self.third_controller_color, self.second_controller.controller)
                self.third_controller.create()

            # 检测显隐控制器
            if not self.visibility_controller:
                self.__visibility_controller = Controller(self.visibility_controller_name,
                                                          self.visibility_controller_index,
                                                          self.visibility_controller_color,
                                                          self.third_controller.controller)
                self.visibility_controller.create()
            # 检测显隐控制器控制属性
            self.check_visibility_attrs(self.visibility_controller)

    def fit_visibility_controller(self, position, size):
        """
        适配显示控制器位置和大小
        :param position: 控制器位置
        :param size: 控制器大小
        :return:
        """
        visOft = self.visibility_controller.offset
        cmds.xform(visOft, ws=1, t=position)
        cmds.setAttr('%s.rx' % visOft, 90)
        match_controller_size(self.visibility_controller.controller, size)

    def fit_chr_controller_size(self, size=1.0):
        """
        匹配角色绑定特有控制器尺寸
        :param size: 控制器尺寸
        :return:
        """
        self.fit_controller_size(size)
        match_controller_size(self.third_controller.controller, size)

    def check_chr_sub_groups(self):
        # 检测所需附加组别
        if not self.extra_group:
            self.__extra_group = check_sub_group(self.extra_group_name, self.third_controller.controller)
        if not self.facial_group:
            self.__facial_group = check_sub_group(self.facial_group_name, self.third_controller.controller)

    def connect_sub_groups_attrs(self):
        # 连接组别间的属性控制连接
        controller = self.visibility_controller.controller
        # 检测可选性反转节点
        geoRev = check_node('GeometrySelectAbleRV', 'reverse')
        # 连接控制器的模型可选性到反转节点
        cmds.connectAttr('%s.%s' % (controller, self.visibility_Attributes[4].get('name')),
                         '%s.ix' % geoRev, f=1)
        # 将反转后的属性，连接到 geometry 和 other 组别的控制属性上
        for group in [self.geometry_group, self.other_group]:
            cmds.connectAttr('%s.ox' % geoRev, '%s.overrideEnabled' % group, f=1)
        # 连接deform组别的显隐
        cmds.connectAttr('%s.%s' % (controller, self.visibility_Attributes[0].get('name')),
                         '%s.lodVisibility' % self.deform_group, f=True)
        # 连接extra组别的显隐属性
        cmds.connectAttr('%s.%s' % (controller, self.visibility_Attributes[1].get('name')),
                         '%s.lodVisibility' % self.extra_group, f=True)
        # 连接facial组别的显隐属性
        cmds.connectAttr('%s.%s' % (controller, self.visibility_Attributes[2].get('name')),
                         '%s.lodVisibility' % self.facial_group, f=True)
        # 锁定extra和facial组别的显隐属性
        '''for grp in [self.extra_group, self.facial_group]:
            cmds.setAttr('%s.v' % grp, e=True, l=True, k=False)'''
        # 连接 cache 组的显隐
        if cmds.objExists('cache'):
            cmds.connectAttr('%s.%s' % (controller, self.visibility_Attributes[5].get('name')),
                             'cache.visibility', f=True)

    def chr_correct(self):
        # 检测并创建基础组别
        self.check_groups()
        # 检测并创建角色绑定特有控制器
        self.check_chr_controllers()
        # 检测并创建角色绑定特有附加组别
        self.check_chr_sub_groups()
        # 连接组别间的属性控制连接
        self.connect_sub_groups_attrs()


class AdvRigging59(ChrRigging):
    def __init__(self, **kwargs):
        super(AdvRigging59, self).__init__(**kwargs)
        self._mainSize_ = 1
        self.__deform_group_name = kwargs.get('deform_group_name', kwargs.get('dgn', 'DeformationSystem'))

    @property
    def deform_group_name(self):
        return self.__deform_group_name

    @property
    def main_system_name(self):
        return 'MainSystem'

    @property
    def main_system(self):
        if cmds.objExists(self.main_system_name):
            return self.main_system_name

    @property
    def main_extra_name(self):
        return 'MainExt'

    @property
    def main_extra(self):
        if cmds.objExists(self.main_extra_name):
            return self.main_extra_name

    def rename_adv_group(self):
        # 重命名 adv 主控制器的组别
        if self.main_system and not self.main_extra:
            cmds.rename(self.main_system, self.main_extra_name)
            if cmds.objExists('MainOft'):
                parent.fitParent(self.main_extra, 'MainOft')

    def get_adv_rig_size(self):
        # 获取绑定控制器基础大小
        if cmds.objExists(self.third_controller):
            self._mainSize_ = max(*get_controller_size(self.third_controller))

    def match_other_adv_groups(self):
        # 匹配adv其他组别
        if cmds.objExists('MotionSystem'):
            parent.fitParent('MotionSystem', self.third_controller)

        if cmds.objExists('FitSkeleton'):
            parent.fitParent('FitSkeleton', self.other_group)

    def fit_adv_visibility_controller(self):
        if cmds.objExists('HeadEnd_M'):
            point = cmds.xform('HeadEnd_M', q=True, ws=True, t=True)
            new_point = [point[0], point[1] * 1.15, point[2]]
            self.fit_visibility_controller(new_point, self._mainSize_ * 0.25)

    def adv_chr_correct(self):
        self.rename_adv_group()
        self.chr_correct()
        self.match_other_adv_groups()
        self.get_adv_rig_size()
        self.fit_chr_controller_size(self._mainSize_)
        self.fit_adv_visibility_controller()

        print (self, u'Advance Skeleton 绑定修正')

    def adv_system_reset(self):
        if cmds.objExists('FitSkeleton') and cmds.objExists(self.main_group_name):
            parent.fitParent('FitSkeleton', self.main_group_name)
        if cmds.objExists('MotionSystem') and cmds.objExists(self.main_group_name):
            parent.fitParent('MotionSystem', self.main_group_name)
            if cmds.objExists(self.third_controller_name):
                if self.main_extra:
                    cmds.rename(self.main_extra, self.main_system_name)
                parent.fitParent(self.main_system, 'MotionSystem')
        if cmds.objExists(self.deform_group_name):
            cmds.setAttr('%s.v' % self.deform_group_name, e=True, l=False)


class AdvRigging(ChrRigging):
    def __init__(self, **kwargs):
        super(AdvRigging, self).__init__(**kwargs)
        self._mainSize_ = 1
        self.__deform_group_name = kwargs.get('deform_group_name', kwargs.get('dgn', 'DeformationSystem'))
        self.__adv_version = kwargs.get('adv_version', kwargs.get('av', '5.74'))
        self.__adv_face_group = 'FaceGroup'
        self.__adv_facial_rig = None

    @property
    def adv_version(self):
        return self.__adv_version

    @property
    def deform_group_name(self):
        return self.__deform_group_name

    @property
    def adv_face_group(self):
        return self.__adv_face_group

    @property
    def adv_facial_rig(self):
        if cmds.objExists(self.adv_face_group):
            if not self.__adv_facial_rig:
                self.__adv_facial_rig = AdvFacialRigging(av=self.adv_version, afg=self.adv_face_group,
                                                         ms=self._mainSize_)
        return self.__adv_facial_rig

    @property
    def adv_sides(self):
        return ['_L', '_R']

    def get_adv_rig_size(self):
        # 获取绑定控制器基础大小
        if cmds.objExists(self.third_controller):
            self._mainSize_ = max(*get_controller_size(self.third_controller))

    def match_other_adv_groups(self):
        # 匹配adv其他组别
        if cmds.objExists('MotionSystem'):
            parent.fitParent('MotionSystem', self.third_controller.controller)

        if cmds.objExists('FitSkeleton'):
            parent.fitParent('FitSkeleton', self.other_group)

        if cmds.objExists(self.adv_face_group):
            parent.fitParent(self.adv_face_group, self.facial_group)

    def fit_adv_visibility_controller(self):
        if cmds.objExists('HeadEnd_M'):
            point = cmds.xform('HeadEnd_M', q=True, ws=True, t=True)
            new_point = [point[0], point[1] * 1.10, point[2]]
            self.fit_visibility_controller(new_point, self._mainSize_ * 0.25)

    def match_adv_vis_attrs(self):
        # # 匹配adv控制器的显隐控制属性到vis控制器上
        # if self.third_controller and self.visibility_controller:
        #     attr_infos = {}
        #     # 将原始大环上的显隐控制属性，转移到头顶的vis控制器上，由于是新想到的需求，之前任务中并未安排，暂时停止，后续安排时间处理
        #
        pass
    def main_scale_correct(self):
        judge = True
        for ctrl in [self.main_controller_name, self.second_controller_name, self.third_controller_name]:
            if not cmds.objExists(ctrl):
                judge = False
                break
        if judge:
            rig_offset_scale_md = check_node('riggingOffsetScaleMD', 'multiplyDivide')
            rig_extra_scale_md = check_node('riggingExtraScaleMD', 'multiplyDivide')
            rig_ctrl_scale_md = check_node('riggingControllerScaleMD', 'multiplyDivide')
            chr_offset_scale_md = check_node('characterOffsetScaleMD', 'multiplyDivide')
            chr_extra_scale_md = check_node('characterExtraScaleMD', 'multiplyDivide')
            chr_ctrl_scale_md = check_node('characterControllerScaleMD', 'multiplyDivide')
            main_offset_scale_md = check_node('mainOffsetScaleMD', 'multiplyDivide')
            main_extra_scale_md = check_node('mainExtraScaleMD', 'multiplyDivide')
            main_ctrl_scale_md = check_node('mainControllerScaleMD', 'multiplyDivide')

            cmds.setAttr('%s.i1' % rig_offset_scale_md, 1, 1, 1, type='double3')
            cmds.connectAttr('%sOft.s' % self.main_controller_name, '%s.i2' % rig_offset_scale_md, f=True)
            cmds.connectAttr('%s.o' % rig_offset_scale_md, '%s.i1' % rig_extra_scale_md, f=True)
            cmds.connectAttr('%sExt.s' % self.main_controller_name, '%s.i2' % rig_extra_scale_md, f=True)
            cmds.connectAttr('%s.o' % rig_extra_scale_md, '%s.i1' % rig_ctrl_scale_md, f=True)
            cmds.connectAttr('%s.s' % self.main_controller_name, '%s.i2' % rig_ctrl_scale_md, f=True)

            cmds.connectAttr('%s.o' % rig_ctrl_scale_md, '%s.i1' % chr_offset_scale_md, f=True)
            cmds.connectAttr('%sOft.s' % self.second_controller_name, '%s.i2' % chr_offset_scale_md, f=True)
            cmds.connectAttr('%s.o' % chr_offset_scale_md, '%s.i1' % chr_extra_scale_md, f=True)
            cmds.connectAttr('%sExt.s' % self.second_controller_name, '%s.i2' % chr_extra_scale_md, f=True)
            cmds.connectAttr('%s.o' % chr_extra_scale_md, '%s.i1' % chr_ctrl_scale_md, f=True)
            cmds.connectAttr('%s.s' % self.second_controller_name, '%s.i2' % chr_ctrl_scale_md, f=True)

            cmds.connectAttr('%s.o' % rig_ctrl_scale_md, '%s.i1' % main_offset_scale_md, f=True)
            cmds.connectAttr('%sOft.s' % self.third_controller_name, '%s.i2' % main_offset_scale_md, f=True)
            cmds.connectAttr('%s.o' % main_offset_scale_md, '%s.i1' % main_extra_scale_md, f=True)
            cmds.connectAttr('%sExt.s' % self.third_controller_name, '%s.i2' % main_extra_scale_md, f=True)
            cmds.connectAttr('%s.o' % main_extra_scale_md, '%s.i1' % main_ctrl_scale_md, f=True)
            cmds.connectAttr('%s.s' % self.third_controller_name, '%s.i2' % main_ctrl_scale_md, f=True)

            cmds.connectAttr('%s.o' % main_ctrl_scale_md, 'MainScaleMultiplyDivide.i1', f=True)
        if cmds.objExists(self.deform_group_name):
            judge = True
            for attr in ['s', 'sx', 'sy', 'sz']:
                cmds.setAttr('%s.%s' % (self.deform_group_name, attr), e=True, l=False)
                cons = cmds.listConnections('%s.%s' % (self.deform_group_name, attr), s=True, d=False)
                if cons:
                    if cmds.nodeType(cons[0]) == 'scaleConstraint':
                        judge = False
            if judge:
                cmds.scaleConstraint(self.main_controller_name, self.deform_group_name, mo=True)
            cmds.setAttr('%s.s' % self.deform_group_name, e=True, l=True)

    def main_scale_correctFn(self):
        judge = True
        for ctrl in [self.main_controller_name, self.second_controller_name, self.third_controller_name]:
            if not cmds.objExists(ctrl):
                judge = False
                break
        if judge:
            main_ctrl_scale_DeMatrix = check_node('mainControllerScaleDeMAtrix', 'decomposeMatrix')
            cmds.connectAttr(self.third_controller_name + '.worldMatrix[0]', main_ctrl_scale_DeMatrix + '.inputMatrix',
                             f=1)
            con = cmds.listConnections('MainScaleMultiplyDivide.i1', p=1, d=0, s=1)
            if con == ['Main.scale']:
                cmds.disconnectAttr(con[0], 'MainScaleMultiplyDivide.i1')
            cmds.connectAttr(main_ctrl_scale_DeMatrix + '.outputScale', 'MainScaleMultiplyDivide.i1', f=True)
            self.add_to_set(obj=main_ctrl_scale_DeMatrix, set='AllSet')
            if cmds.objExists(self.deform_group_name):
                self.deform_scale_DeMatrix = check_node('deform_scale_DeMatrix', 'decomposeMatrix')
                cmds.setAttr('%s.s' % self.deform_group_name, e=True, l=False)
                cmds.connectAttr(self.third_controller_name + '.worldMatrix[0]',
                                 self.deform_scale_DeMatrix + '.inputMatrix',
                                 f=1)
                cmds.connectAttr(self.deform_scale_DeMatrix + '.outputScale', self.deform_group_name + '.s', f=True)
                cmds.setAttr('%s.s' % self.deform_group_name, e=True, l=True)
                cmds.setAttr('%s.v' % self.deform_group_name, e=True, l=False)
                self.add_to_set(obj=self.deform_scale_DeMatrix, set='AllSet')

    def lock_fk_translate(self):
        # 锁定并隐藏fk控制器的translate 和 visibility 属性
        body_parts = [u'Shoulder', u'Elbow', u'Wrist', u'Hip', u'Knee', u'Ankle', u'Toes']
        for side in self.adv_sides:
            for part in body_parts:
                fk_ctr = 'FK%s%s' % (part, side)
                if cmds.objExists(fk_ctr):
                    attrs = ['v'] + ['t%s' % x for x in 'xyz']
                    for attr in attrs:
                        cmds.setAttr('%s.%s' % (fk_ctr, attr), e=True, l=True, k=False, cb=False)

    def lock_ikSec_scale(self):
        body_parts = [u'Neck', u'Shoulder', u'Elbow', u'Hip', u'Knee']
        for side in self.adv_sides:
            for part in body_parts:
                for i in range(1, 3):
                    iksec_ctr = 'Bend%s%s%s' % (part, i, side)
                    if cmds.objExists(iksec_ctr):
                        attrs = ['v'] + ['s%s' % x for x in 'yz']
                        for attr in attrs:
                            cmds.setAttr('%s.%s' % (iksec_ctr, attr), e=True, l=True, k=False, cb=False)

    def correct_hand_cup(self):
        # 修正手掌无名指和小拇指缩放问题
        for side in ['_L', '_R']:
            # 额外修复IK状态下Cup_L不受控制器控制
            FKXCup_Jnt = 'FKXCup%s' % side
            IKXCup_Jnt = 'IKXCup%s' % side
            if cmds.objExists(FKXCup_Jnt) and cmds.objExists(IKXCup_Jnt):
                FKXGrp = cmds.listRelatives(FKXCup_Jnt, p=1)
                FKXGrpChild = cmds.listRelatives(FKXGrp, c=1)
                if IKXCup_Jnt not in FKXGrpChild:
                    cmds.parent(IKXCup_Jnt, FKXGrp)
            ctrl_grp = 'FKParentConstraintToCup%s' % side
            if cmds.objExists(ctrl_grp):
                ctrl_grpParent = cmds.listRelatives(ctrl_grp, p=1)
                if 'FKParentConstraintToWrist' + side not in ctrl_grpParent:
                    cons = cmds.listConnections('%s.s' % ctrl_grp, s=True, d=False, p=True) or []
                    if cons:
                        if cmds.nodeType(cons[0]) == 'joint':
                            cmds.disconnectAttr(cons[0], '%s.s' % ctrl_grp)
                    constraintList = cmds.listConnections('FKParentConstraintToCup' + side, s=True, d=False) or []
                    if constraintList:
                        cmds.delete(constraintList)

                    cmds.parent(cmds.listRelatives(ctrl_grp, c=1), 'FKCup' + side)
                    cmds.parent('FKOffsetCup' + side, ctrl_grp)
                    cmds.parent(ctrl_grp, 'FKParentConstraintToWrist' + side)

                    FKIKBlendCupConditionNode = 'FKIKBlendCupCondition' + side
                    if cmds.objExists(FKIKBlendCupConditionNode):
                        cmds.delete(FKIKBlendCupConditionNode)
                    cmds.createNode('floatMath', n=FKIKBlendCupConditionNode)
                    self.add_to_set(FKIKBlendCupConditionNode, 'AllSet')
                    cmds.connectAttr('FKIKBlendArmDCondition%s.outColorG' % side, FKIKBlendCupConditionNode + '.floatA',
                                     f=1)
                    cmds.connectAttr('FKIKBlendArmECondition%s.outColorG' % side, FKIKBlendCupConditionNode + '.floatB',
                                     f=1)
                    cmds.setAttr(FKIKBlendCupConditionNode + '.operation', 2)
                    cmds.connectAttr(FKIKBlendCupConditionNode + '.outFloat', 'FKParentConstraintToCup%s.v' % side)

    def correct_global_scale(self):
        nodeList = ['ScaleBlendHip', 'ScaleBlendKnee', 'ScaleBlendAnkle', 'ScaleBlendShoulder',
                    'ScaleBlendElbow',
                    'ScaleBlendWrist']
        for side in ['_R', '_L', '_M']:
            for i in nodeList:
                if cmds.objExists('%s%s' % (i, side)):
                    hasCon = cmds.listConnections('%s%s.color2R' % (i, side), s=1) or []

                    if hasCon:
                        try:
                            cmds.disconnectAttr("%s.sx" % (hasCon[0]), '%s%s.color2R' % (i, side))
                            cmds.disconnectAttr("%s.sy" % (hasCon[0]), '%s%s.color2G' % (i, side))
                            cmds.disconnectAttr("%s.sz" % (hasCon[0]), '%s%s.color2B' % (i, side))
                        except:
                            pass
                        matrixNode = check_node("%s_MatrixNode" % (hasCon[0]), 'decomposeMatrix')
                        cmds.connectAttr("%s.worldMatrix[0]" % (hasCon[0]), matrixNode + '.inputMatrix', f=1)
                        globalMUNode = check_node("%s_globalMUNode" % (hasCon[0]), 'multiplyDivide')
                        cmds.setAttr(globalMUNode + '.operation', 2)
                        cmds.connectAttr(matrixNode + '.outputScale', '%s.input1' % globalMUNode, f=1)
                        cmds.connectAttr(self.deform_scale_DeMatrix + '.outputScale', '%s.input2' % globalMUNode, f=1)
                        cmds.connectAttr(globalMUNode + '.output', '%s%s.color2' % (i, side), f=True)

    def edit_foot_ik_ctrl_shape_backups(self):
        for side in self.adv_sides:
            if side == '_L':
                scaleValue = -1
            elif side == '_R':
                scaleValue = 1
            try:
                frontCtrl = cmds.xform('RollToesEnd' + side, q=1, ws=1, t=1)
                backCtrl = cmds.xform('RollHeel' + side, q=1, ws=1, t=1)
                insidePnt = cmds.xform('IKLegFootRockInnerPivot' + side, q=1, ws=1, t=1)
                outsidePnt = cmds.xform('IKLegFootRockOuterPivot' + side, q=1, ws=1, t=1)
                ctrlShape = cmds.listRelatives('IKLeg' + side, s=1, type='nurbsCurve')
            except Exception as e:
                frontCtrl = None
                backCtrl = None
                insidePnt = None
                outsidePnt = None
                ctrlShape = None
                print (e)
            if frontCtrl and backCtrl and insidePnt and outsidePnt and ctrlShape:
                ctrlShape = ctrlShape[0]

                # ctrlWIMatrix = pm.dt.Matrix(cmds.xform('IKLeg' + side, q=1, ws=1, m=1)).inverse()
                # Apnt = pm.dt.Point(frontCtrl) * ctrlWIMatrix
                # Bpnt = pm.dt.Point(backCtrl)
                # Bpnt = pm.dt.Point(backCtrl) * ctrlWIMatrix
                # Cpnt = pm.dt.Point([insidePnt[0],insidePnt[1],insidePnt[2]+1*scaleValue*0.02*self._mainSize_]) * ctrlWIMatrix
                # Dpnt = pm.dt.Point([outsidePnt[0],outsidePnt[1],outsidePnt[2]-1*scaleValue*0.02*self._mainSize_]) * ctrlWIMatrix
                #
                # setApnt = [cmds.setAttr(ctrlShape + '.cv[%s]' % (pnt), Bpnt[0], Apnt[1], Cpnt[2]) for pnt in
                #            ['3', '6', '10', '11']]
                # setBpnt = [cmds.setAttr(ctrlShape + '.cv[%s]' % (pnt), Bpnt[0], Bpnt[1], Cpnt[2]) for pnt in
                #            ['2', '7', '14', '15']]
                # setCpnt = [cmds.setAttr(ctrlShape + '.cv[%s]' % (pnt), Bpnt[0], Apnt[1], Dpnt[2]) for pnt in
                #            ['4', '5', '9', '12']]
                # setDpnt = [cmds.setAttr(ctrlShape + '.cv[%s]' % (pnt), Bpnt[0], Bpnt[1], Dpnt[2]) for pnt in
                #            ['0', '1', '8', '13']]

                setApnt = [cmds.xform(ctrlShape + '.cv[%s]' % pnt,
                                      t=[insidePnt[0] + 1 * scaleValue * 0.02 * self._mainSize_, backCtrl[1],
                                         frontCtrl[2]], ws=1) for pnt in ['3', '6', '10', '11']]
                setBpnt = [cmds.xform(ctrlShape + '.cv[%s]' % pnt,
                                      t=[outsidePnt[0] - 1 * scaleValue * 0.02 * self._mainSize_, backCtrl[1],
                                         frontCtrl[2]], ws=1) for pnt in
                           ['2', '7', '14', '15']]
                setCpnt = [cmds.xform(ctrlShape + '.cv[%s]' % pnt,
                                      t=[insidePnt[0] + 1 * scaleValue * 0.02 * self._mainSize_, backCtrl[1],
                                         backCtrl[2]], ws=1) for pnt in
                           ['4', '5', '9', '12']]
                setDpnt = [cmds.xform(ctrlShape + '.cv[%s]' % pnt,
                                      t=[outsidePnt[0] - 1 * scaleValue * 0.02 * self._mainSize_, backCtrl[1],
                                         backCtrl[2]], ws=1) for pnt in
                           ['0', '1', '8', '13']]
    def fix_foot_ik_ctrl_aix( self ):
        for side in self.adv_sides:
            foot_ik_ctrl = 'IKLeg%s' % side
            foot_ik_ctrl_Oft = 'IKOffsetLeg%s' % side
            IKLeg_LOft_Null = 'IKLeg%s_Oft' % side
            RollToesEnd_L_ctlr = 'RollToesEnd%s' % side

            if foot_ik_ctrl not in cmds.listRelatives('IKFKAlignedOffsetLeg%s' % side,p =1):
                pass
            else:
                v = cmds.getAttr(foot_ik_ctrl_Oft + '.r')[0]
                if v[1] != 0.0 and v[-1] != 90.0:
                    Oft = cmds.group(['IKFKAlignedOffsetLeg%s' % side, 'IKLegFootRockInnerPivot%s' % side],
                                     n=IKLeg_LOft_Null)
                    print Oft
                    cmds.parent(Oft, w=1)
                    self.add_to_set(Oft,set = 'AllSet')
                    if side == '_L':
                        cmds.xform(foot_ik_ctrl_Oft, ro=(v[0], 0.0, 90.0))
                        cmds.delete(
                            cmds.aimConstraint(RollToesEnd_L_ctlr, foot_ik_ctrl_Oft, w=1, aim=(0, -1, 0), u=(1, 0, 0),
                                               wut="scene", skip=("y", "z")))
                    elif side == '_R':
                        cmds.xform(foot_ik_ctrl_Oft, ro=(v[0], 0.0, -90.0))
                        cmds.delete(
                            cmds.aimConstraint(RollToesEnd_L_ctlr, foot_ik_ctrl_Oft, w=1, aim=(0, 1, 0), u=(-1, 0, 0),
                                               wut="scene", skip=("y", "z")))
                    cmds.parent(IKLeg_LOft_Null, foot_ik_ctrl)
        if cmds.objExists('RootCenterBtwLegsOffset_M'):
            cmds.delete(cmds.parentConstraint('RootCenter_M','RootCenterBtwLegsOffset_M'))
        if cmds.objExists('RootCenterBtwLegs_M'):
            con = cmds.listConnections('RootCenterBtwLegs_M', type="constraint",d =0,s =1) or []
            if con:
                cmds.delete(con)

    def edit_foot_ik_ctrl_shape(self):
        for side in self.adv_sides:
            toe_end = 'RollToesEnd%s' % side
            hell = 'RollHeel%s' % side
            inside = 'IKLegFootRockInnerPivot%s' % side
            outside = 'IKLegFootRockOuterPivot%s' % side
            ctrl_shapes = cmds.listRelatives('IKLeg%s' % side, s=1, type='nurbsCurve')
            if cmds.objExists(toe_end) and cmds.objExists(hell) and cmds.objExists(inside) and cmds.objExists(
                    outside) and ctrl_shapes:
                front_position = cmds.xform(toe_end, q=1, ws=1, t=1)
                back_position = cmds.xform(hell, q=1, ws=1, t=1)
                inside_position = cmds.xform(inside, q=1, ws=1, t=1)
                outside_position = cmds.xform(outside, q=1, ws=1, t=1)
                length = pow(
                    pow(front_position[0] - back_position[0], 2) + 0 + pow(front_position[2] - back_position[2], 2),
                    0.5) * 1.1
                width = pow(
                    pow(inside_position[0] - outside_position[0], 2) + 0 + pow(inside_position[2] - outside_position[2],
                                                                               2), 0.5) * 1.2
                plane, plane_shape = cmds.polyPlane(sx=1, sy=1, h=length, w=width)
                cmds.setAttr('%s.tz' % plane, length * 0.5)
                plane_grp = cmds.group(plane)
                cmds.xform(plane_grp, ws=True, piv=[0, 0, 0])
                cmds.delete(cmds.parentConstraint(hell, plane_grp, w=True, mo=False))
                if side == '_L':
                    cmds.delete(cmds.aimConstraint(toe_end, plane_grp, w=1, aim=(0, 0, -1), u=(0, -1, 0),
                                                   wut="scene", skip=("x", "z")))
                elif side == '_R':
                    cmds.delete(cmds.aimConstraint(toe_end, plane_grp, w=1, aim=(0, 0, 1), u=(0, 1, 0),
                                                   wut="scene", skip=("x", "z")))

                point1 = cmds.xform('%s.vtx[0]' % plane, q=True, ws=True, t=True)
                point2 = cmds.xform('%s.vtx[1]' % plane, q=True, ws=True, t=True)
                point3 = cmds.xform('%s.vtx[2]' % plane, q=True, ws=True, t=True)
                point4 = cmds.xform('%s.vtx[3]' % plane, q=True, ws=True, t=True)
                for index in [3, 6, 10, 11]:
                    cmds.xform('%s.cv[%d]' % (ctrl_shapes[0], index), ws=True, t=point1)
                for index in [4, 5, 9, 12]:
                    cmds.xform('%s.cv[%d]' % (ctrl_shapes[0], index), ws=True, t=point2)
                for index in [2, 7, 14, 15]:
                    cmds.xform('%s.cv[%d]' % (ctrl_shapes[0], index), ws=True, t=point3)
                for index in [0, 1, 8, 13]:
                    cmds.xform('%s.cv[%d]' % (ctrl_shapes[0], index), ws=True, t=point4)
                cmds.delete(plane_grp)

    def adv_rig_preset(self):
        # 针对于adv绑定的参数预设
        if cmds.objExists('%s.jointVis' % self.third_controller.controller):
            cmds.setAttr('%s.jointVis' % self.third_controller.controller, True)
            cmds.setAttr('%s.jointVis' % self.third_controller.controller, e=True, cb=False)

    def adv_hiden_dirveJnt(self):
        if cmds.objExists('MotionSystem'):
            [cmds.setAttr(i + '.drawStyle', 2) for i in cmds.ls('MotionSystem', dag=1, type='joint')]

    def create_finger_ctrl(self):
        for side in self.adv_sides:
            ctrlName = 'FKIKFingersMain' + side
            FingersCtrl = 'Fingers' + side
            if cmds.objExists('Fingers' + side) and not cmds.objExists(ctrlName):
                cmds.setAttr(FingersCtrl + '.lodVisibility', 0)
                self.del_to_set(FingersCtrl, 'ControlSet')
                sideValue = 1
                ctr = controllerManager.Controller(ctrlName, size=self._mainSize_ * 0.1, postfix='')
                ctr.create(9)
                cmds.setAttr(ctrlName + '.lineWidth', 1.5)
                cmds.setAttr(ctrlName + '.overrideEnabled', 1)
                cmds.setAttr(ctrlName + '.overrideColor', 17)
                self.add_to_set(obj=ctrlName, set='AllSet')
                self.add_to_set(obj=ctrlName, set='ControlSet')
                newNameShape = cmds.listRelatives(ctrlName, type='nurbsCurve', ni=1) or []
                if newNameShape:
                    self.add_to_set(obj=newNameShape[0], set='AllSet')
                ctrlGrpName = ctrlName + '_Grp'
                if not cmds.objExists(ctrlGrpName):
                    cmds.group(n=ctrlGrpName, empty=1)
                    self.add_to_set(obj=ctrlGrpName, set='AllSet')
                ctrlGrpChilden = cmds.listRelatives(ctrlGrpName, c=1) or []
                if ctrlName not in ctrlGrpChilden:
                    cmds.parent(ctrlName, ctrlGrpName)
                    cmds.parentConstraint('Wrist' + side, ctrlGrpName, mo=0)
                    if side == '_L':
                        sideValue = -1
                    elif side == '_R':
                        sideValue = 1
                    cmds.setAttr(ctrlName + '.r', 90 * sideValue, 0, -90 * sideValue)
                    cmds.setAttr(ctrlName + '.t', 0, 0, self._mainSize_ * 0.15 * sideValue)
                    cmds.makeIdentity(ctrlName, apply=1, r=1)
                if cmds.objExists('Wrist' + side):
                    m = cmds.xform('Wrist' + side, q=1, ws=1, m=1)
                    cmds.xform(ctrlGrpName, ws=1, m=m)
                    cmds.connectAttr('Wrist%s.s' % side, ctrlGrpName + '.s', f=1)
                DrivingSystem = 'DrivingSystem'
                DrivingSystemChilden = cmds.listRelatives(DrivingSystem, c=1) or []
                if cmds.objExists(DrivingSystem) and ctrlGrpName not in DrivingSystemChilden:
                    cmds.parent(ctrlGrpName, DrivingSystem)
                lock_channel_attrs(ctrlName, ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz', 'v'])
                FKIKSystemGrp = 'FKIKSystem'
                if cmds.objExists(FKIKSystemGrp):
                    FKIKSystemGrp = cmds.ls('FKIKSystem', dag=1, type='parentConstraint')
                    fingerIKFKswitchCtrlList = list()
                    for part in ['Wrist', 'Cup']:
                        wristConstraint = [ctrl for ctrl in FKIKSystemGrp if
                                           part + side in cmds.listConnections(ctrl, d=0, s=1, type='transform')]
                        fingerIKFKswitchCtrlList += [cmds.listRelatives(
                            cmds.ls(
                                cmds.listConnections(constraint + '.constraintRotateY', d=1, s=0, type='transform',
                                                     et=1)[
                                    0], s=1,
                                dag=1)[0], p=1)[0] for constraint in wristConstraint]
                    fingerIKFKswitchCtrlList.sort()
                    attrInfo = attrTools.AttrToolsClass.getAttrInfo(FingersCtrl,
                                                                    cmds.listAttr(FingersCtrl, ud=1, k=1, l=0))
                    attrInfo.values()[0].insert(0, {
                        '___FK___': {'lock': True, 'cb': True, 'type': 'enum', 'enum': '__________',
                                     'longName': '___FK___',
                                     'key': False, 'niceName': '___FK___'}})
                    attrInfo.values()[0].append({'___FK_IK_FKIKBlend___': {'lock': True, 'cb': True, 'type': 'enum',
                                                                           'enum': '__________',
                                                                           'longName': '___FK_IK_FKIKBlend___',
                                                                           'key': False,
                                                                           'niceName': '___FK_IK_FKIKBlend___'}})
                    [attrInfo.values()[0].append({ctrl: {'max': 10, 'min': 0, 'lock': False, 'defaultValue': 0.0,
                                                         'longName': ctrl, 'niceName': ctrl, 'key': True, 'cb': False,
                                                         'type': u'float'}})
                     for ctrl in fingerIKFKswitchCtrlList]

                    attrList = attrTools.AttrToolsClass.createAttrFn(ctrlName, attrInfo.values())
                    for attr in attrList:
                        ctrlAttr = ctrlName + '.' + attr
                        if cmds.objExists(ctrlAttr):
                            cmds.addAttr(ctrlAttr, e=1, max=10)
                            if cmds.objExists(FingersCtrl + '.' + attr):
                                self.update_build_pose(ctrlAttr, value=0)
                                if attr == 'spread':
                                    cmds.addAttr(ctrlAttr, e=1, min=-5)
                                    cmds.setDrivenKeyframe(FingersCtrl + '.' + attr, cd=ctrlAttr, dv=-5,
                                                           v=-5)
                                    cmds.setDrivenKeyframe(FingersCtrl + '.' + attr, cd=ctrlAttr,
                                                           dv=10, v=10)
                                elif attr == 'cup':
                                    cmds.addAttr(ctrlAttr, e=1, min=0)
                                    cmds.setDrivenKeyframe(FingersCtrl + '.' + attr, cd=ctrlAttr, dv=0,
                                                           v=0)
                                    cmds.setDrivenKeyframe(FingersCtrl + '.' + attr, cd=ctrlAttr,
                                                           dv=10, v=10)
                                elif attr in ['indexCurl', 'middleCurl', 'ringCurl', 'pinkyCurl', 'thumbCurl']:
                                    cmds.addAttr(ctrlAttr, e=1, min=-2)
                                    cmds.setDrivenKeyframe(FingersCtrl + '.' + attr, cd=ctrlAttr, dv=-2,
                                                           v=-2)
                                    cmds.setDrivenKeyframe(FingersCtrl + '.' + attr, cd=ctrlAttr,
                                                           dv=10, v=10)
                                cmds.setDrivenKeyframe(FingersCtrl + '.' + attr, cd=ctrlAttr, dv=0,
                                                       v=0)
                                if cmds.objExists(FingersCtrl + '_' + attr):
                                    self.add_to_set(FingersCtrl + '_' + attr, 'AllSet')
                            if cmds.objExists(attr + '.FKIKBlend'):
                                self.update_build_pose(ctrlAttr, value=0)
                                self.del_to_set(attr, 'ControlSet')
                                cmds.setDrivenKeyframe(attr + '.FKIKBlend', cd=ctrlAttr, dv=0,
                                                       v=0)
                                cmds.setDrivenKeyframe(attr + '.FKIKBlend', cd=ctrlAttr,
                                                       dv=10, v=10)
                                cmds.setAttr(attr + '.lodVisibility', 0)
                                if cmds.objExists(FingersCtrl + '_' + attr):
                                    self.add_to_set(FingersCtrl + '_' + attr, 'AllSet')

    def add_to_set(self, obj='', set=''):
        if not cmds.sets(obj, im=set):
            cmds.sets(obj, addElement=set)

    def del_to_set(self, obj='', set=''):
        if cmds.sets(obj, im=set):
            cmds.sets(obj, rm=set)

    def update_build_pose(self, attr='', type='value', value=0, buildPose='buildPose'):
        if cmds.objExists(buildPose + '.udAttr'):
            oldAttrStr = str(cmds.getAttr(buildPose + '.udAttr'))
            if attr not in oldAttrStr:
                if type == 'value':
                    cmds.setAttr(buildPose + '.udAttr', oldAttrStr + ';setAttr %s %s;' % (attr, value), type='string')
                elif type == 'ctrl':
                    cmds.setAttr(buildPose + '.udAttr',
                                 oldAttrStr + ';xform -os -t 0 0 0 -ro 0 0 0 -s 1 1 1 %s;' % attr, type='string')

    def update_build_pose_and_set_fn(self, name):
        newname = cmds.listRelatives(name[0], p=1) or []
        if newname == [] or newname == ['Group']:
            return 0
        else:
            newNameShape = cmds.listRelatives(newname, type='nurbsCurve', ni=1) or []
            if newNameShape:
                self.add_to_set(obj=newNameShape[0], set='AllSet')
            self.add_to_set(obj=newname, set='AllSet')
            self.add_to_set(obj=newname, set='ControlSet')
            self.update_build_pose(newname[0], type='ctrl')
            return self.update_build_pose_and_set_fn(newname)

    def fix_update_build_pose_and_set_fn(self):
        self.add_to_set(obj=self.extra_group_name, set='AllSet')
        self.add_to_set(obj=self.extra_group_name, set='ControlSet')
        self.add_to_set(obj=self.facial_group_name, set='AllSet')
        self.add_to_set(obj=self.facial_group_name, set='ControlSet')
        self.add_to_set(obj=self.other_group_name, set='AllSet')
        # self.add_to_set(obj=self.other_group_name, set='ControlSet')
        self.add_to_set(obj=self.geometry_group_name, set='AllSet')
        # self.add_to_set(obj=self.geometry_group_name, set='ControlSet')
        self.add_to_set(obj=self.visibility_controller_name, set='AllSet')
        self.add_to_set(obj=self.visibility_controller_name, set='ControlSet')

        self.add_to_set(obj='VisibilityCtrOft', set='AllSet')
        self.add_to_set(obj='VisibilityCtrOft', set='ControlSet')
        self.add_to_set(obj='VisibilityCtrExt', set='AllSet')
        self.add_to_set(obj='VisibilityCtrShape', set='AllSet')
        self.add_to_set(obj='VisibilityCtr', set='AllSet')
        self.add_to_set(obj='VisibilityCtr', set='ControlSet')

    def edit_RootX_M_color(self):
        if cmds.objExists('RootX_M'):
            cmds.setAttr('RootX_MShape1.overrideColor', 17)
            cmds.setAttr('RootX_MShape.overrideColor', 6)
            cmds.setAttr('RootX_MShape2.overrideColor', 6)
            cmds.setAttr('RootX_MShape3.overrideColor', 6)
            shapeList = cmds.listRelatives('RootX_M', s=1)
            if shapeList:
                for shape in shapeList:
                    cmds.setAttr('%s.lineWidth' % shape, 1.5)

    def adv_chr_correct(self):
        self.chr_correct()
        self.match_other_adv_groups()
        self.get_adv_rig_size()
        self.fit_chr_controller_size(self._mainSize_)
        self.edit_RootX_M_color()
        self.fit_adv_visibility_controller()
        self.match_adv_vis_attrs()
        if self.adv_facial_rig:
            self.adv_facial_rig.do_facial_correct()
        self.main_scale_correctFn()
        self.lock_fk_translate()
        self.lock_ikSec_scale()
        self.adv_hiden_dirveJnt()
        self.correct_hand_cup()
        self.fix_foot_ik_ctrl_aix()
        self.edit_foot_ik_ctrl_shape()
        self.create_finger_ctrl()
        self.correct_global_scale()
        self.adv_rig_preset()
        self.update_build_pose_and_set_fn(['Main'])
        self.fix_update_build_pose_and_set_fn()
        # 添加手脚缩放衰减控制
        # self.add_scale_decay()

    def adv_system_reset(self):
        if cmds.objExists('FitSkeleton') and cmds.objExists(self.third_controller_name):
            parent.fitParent('FitSkeleton', self.third_controller_name)
        if cmds.objExists(self.deform_group_name):
            parent.fitParent(self.deform_group_name, self.third_controller_name)
            cmds.setAttr('%s.v' % self.deform_group_name, e=True, l=False)
        if cmds.objExists(self.adv_face_group) and cmds.objExists(self.main_group_name):
            parent.fitParent(self.adv_face_group, self.main_group_name)

    def add_scale_decay(self):
        def check_decay_attr(part, side):
            attr = '%s%s_decay' % (part, side)
            if not cmds.objExists('%s.%s' % (self.third_controller, attr)):
                cmds.addAttr(self.third_controller, ln=attr, at='double', min=0, max=1)
            cmds.setAttr('%s.%s' % (self.third_controller, attr), e=True, k=True, l=False)
            cmds.setAttr('%s.%s' % (self.third_controller, attr), 0.15)
            return '%s.%s' % (self.third_controller, attr)

        def get_front_scale_attr(joint):
            attr = None
            cons = cmds.listConnections('%s.s' % joint, s=True, d=False, p=True) or []
            if cons:
                if cmds.nodeType(cons[0]) == 'joint':
                    attr = get_front_scale_attr(cons[0].split('.')[0])
                else:
                    attr = cons[0]
            else:
                for axis in 'xyz':
                    cons = cmds.listConnections('%s.s%s' % (joint, axis), s=True, d=False, p=True) or []
                    if cmds.nodeType(cons[0]) == 'joint':
                        attr = get_front_scale_attr(cons[0].split('.')[0])
                        if attr:
                            break
                    else:
                        attr = cons[0]
            return attr

        part_infos = {'leg': {'start': 'Hip', 'end': 'Ankle'},
                      'arm': {'start': 'Shoulder', 'end': 'Wrist'}}
        for part in ['arm', 'leg']:
            infos = part_infos.get(part, {})
            for side in self.adv_sides:
                start = '%s%s' % (infos.get('start'), side)
                end = '%s%s' % (infos.get('end'), side)

                # 检查并生成控制属性
                control_attr = check_decay_attr(part, side)

                # 检查并生成缩放值差计算节点
                scale_pma = '%s%s_scale_pma' % (part, side)
                if not cmds.objExists(scale_pma):
                    cmds.createNode('plusMinusAverage', n=scale_pma)
                cmds.setAttr('%s.operation' % scale_pma, 2)

                end_blend = 'ScaleBlend%s' % end
                start_blend = 'ScaleBlend%s' % start
                if cmds.objExists(start_blend) and cmds.objExists(end_blend):
                    cmds.connectAttr('%s.output' % end_blend, '%s.input3D[0]' % scale_pma, f=True)
                    cmds.connectAttr('%s.output' % start_blend, '%s.input3D[1]' % scale_pma, f=True)

                joints = get_target_child(start, end)
                joints.reverse()
                for i in range(len(joints)):
                    joint = joints[i]
                    # 检查并创建骨骼缩放数值MDL节点
                    joint_scale_mdl = '%s_scale_mdl' % joint
                    if not cmds.objExists(joint_scale_mdl):
                        cmds.createNode('multDoubleLinear', n=joint_scale_mdl)
                    cmds.setAttr('%s.i1' % joint_scale_mdl, len(joints) - i)
                    cmds.connectAttr(control_attr, '%s.i2' % joint_scale_mdl, f=True)
                    # 检查并创建缩放区间节点
                    joint_scale_cmp = '%s_scale_cmp' % joint
                    if not cmds.objExists(joint_scale_cmp):
                        cmds.createNode('clamp', n=joint_scale_cmp)
                    cmds.setAttr('%s.maxR' % joint_scale_cmp, 0)
                    cmds.setAttr('%s.maxG' % joint_scale_cmp, 1)
                    cmds.setAttr('%s.maxB' % joint_scale_cmp, 1)

                    cmds.connectAttr('%s.o' % joint_scale_mdl, '%s.inputG' % joint_scale_cmp, f=True)
                    cmds.connectAttr('%s.o' % joint_scale_mdl, '%s.inputB' % joint_scale_cmp, f=True)

                    # 检查并创建骨骼缩放乘除节点
                    joint_scale_md = '%s_scale_md' % joint
                    if not cmds.objExists(joint_scale_md):
                        cmds.createNode('multiplyDivide', n=joint_scale_md)
                    cmds.connectAttr('%s.output3D' % scale_pma, '%s.i1' % joint_scale_md, f=True)
                    cmds.connectAttr('%s.output' % joint_scale_cmp, '%s.i2' % joint_scale_md, f=True)
                    # cmds.setAttr('%s.i2x' % joint_scale_md, 0)

                    # 检查并创建缩放叠加节点
                    joint_scale_pma = '%s_total_scale_pma' % joint
                    if not cmds.objExists(joint_scale_pma):
                        cmds.createNode('plusMinusAverage', n=joint_scale_pma)
                    cmds.connectAttr('%s.o' % joint_scale_md, '%s.input3D[0]' % joint_scale_pma, f=True)

                    # 获取前置节点信息
                    attr = get_front_scale_attr(joint)
                    if attr:
                        cmds.connectAttr(attr[:-1], '%s.input3D[1]' % joint_scale_pma, f=True)
                        cmds.connectAttr('%s.output3D' % joint_scale_pma, '%s.s' % joint, f=True)
                        for axis in 'xyz':
                            s_cons = cmds.listConnections('%s.s%s' % (joint, axis), s=True, d=False, p=True)
                            if s_cons:
                                cmds.disconnectAttr(s_cons[0], '%s.s%s' % (joint, axis))

    def correct(self):
        self.adv_chr_correct()


class AdvFacialRigging(object):
    def __init__(self, **kwargs):
        self.__adv_version = kwargs.get('adv_version', kwargs.get('av', '5.74'))
        self.__adv_face_group = kwargs.get('adv_face_group', kwargs.get('afg', 'FaceGroup'))
        self._mainSize_ = kwargs.get('main_size', kwargs.get('ms', 1))

    @property
    def adv_versio(self):
        return self.__adv_version

    @property
    def adv_face_group(self):
        return self.__adv_face_group

    @property
    def adv_sides(self):
        return ['_L', '_R']

    @property
    def mouth_parts(self):
        return ['upper', 'lower']

    def add_to_set(self, obj='', set=''):
        if not cmds.sets(obj, im=set):
            cmds.sets(obj, addElement=set)

    def del_to_set(self, obj='', set=''):
        if cmds.sets(obj, im=set):
            cmds.sets(obj, rm=set)

    def eye_brow_inner_correct(self):
        # 修正眉毛内测控制
        # 第一步，锁定无用控制器属性
        lock_attr_list = ['v', 'influence', 'EyeBrowMid1Joint', 'EyeBrowMiddleJoint']
        for side in self.adv_sides:
            for attr in lock_attr_list:
                obj_attr = 'EyeBrowInner%s.%s' % (side, attr)
                if cmds.objExists(obj_attr):
                    cmds.setAttr(obj_attr, e=True, l=False, k=False, cb=False)
        # 第二步，转移控制面板属性到面部控制器上
        for side in self.adv_sides:
            ctrl_box = 'ctrlBrow%s' % side
            brow_ctrl = 'EyeBrowInner%s' % side
            transfer_attr_list = ['squeeze', 'outerUpDown']
            utils.transfer_connect_attrs(ctrl_box, brow_ctrl, transfer_attr_list, defaultMode=1)
            if cmds.objExists('faceBuildPose'):
                faceBuildPoseinfo = cmds.getAttr('faceBuildPose.udAttr')
                for attr in transfer_attr_list:
                    faceBuildPoseinfo = faceBuildPoseinfo.replace('%s.%s'%(ctrl_box,attr),'%s.%s'%(brow_ctrl,attr))
                    cmds.setAttr('faceBuildPose' + '.udAttr', faceBuildPoseinfo, type='string')
    def eye_region_correct(self):
        # 眼睛控制器修正
        # transfer_attr_list = ['pupil', 'iris', 'blink', 'blinkCenter', 'upperLid', 'lowerLid', 'squint']
        transfer_attr_list = ['upperLid', 'lowerLid', 'blink', 'blinkCenter', 'squint', 'iris', 'pupil']
        for side in self.adv_sides:
            ctrl_box = 'ctrlEye%s' % side
            eye_ctrl = 'EyeRegion%s' % side
            utils.transfer_connect_attrs(ctrl_box, eye_ctrl, transfer_attr_list)
            for attr in transfer_attr_list:
                if attr in ['blink', 'blinkCenter', 'squint']:
                    cmds.addAttr('%s.%s' % (eye_ctrl, attr), e=True, maxValue=10, minValue=0)
                else:
                    cmds.addAttr('%s.%s' % (eye_ctrl, attr), e=True, maxValue=10, minValue=-10)
            if cmds.objExists('faceBuildPose'):
                faceBuildPoseinfo = cmds.getAttr('faceBuildPose.udAttr')
                for attr in transfer_attr_list:
                    if attr != 'blinkCenter':
                        faceBuildPoseinfo = faceBuildPoseinfo.replace('setAttr %s.%s %s' % (ctrl_box, attr,0 ),
                                                                      'setAttr %s.%s %s' % (eye_ctrl, attr,0))
                    elif attr == 'blinkCenter':
                        faceBuildPoseinfo = faceBuildPoseinfo.replace('setAttr %s.%s ' % (ctrl_box, attr),
                                                                      'setAttr %s.%s ' % (eye_ctrl, attr))

                    cmds.setAttr('faceBuildPose' + '.udAttr', faceBuildPoseinfo, type='string')
    def lip_region_correct(self):
        # 嘴唇控制器修正
        # 骨骼位移修正，增加转嘴功能
        lip_region_joint = 'LipRegionJoint_M'
        lip_region_oft = 'LipRegionJointOffset_M'
        lip_region_ext = '%sExt' % lip_region_joint
        lip_region_tra = '%sTra' % lip_region_joint

        lip_region_ext = check_node(lip_region_ext, 'transform')
        lip_region_tra = check_node(lip_region_tra, 'transform')
        parent.fitParent(lip_region_ext, lip_region_tra)
        parent.fitParent(lip_region_tra, lip_region_oft)

        # 求出牙齿到嘴唇的距离，来确定转嘴的中心点位置
        lip_joint_position = cmds.xform(lip_region_joint, q=True, ws=True, t=True)
        teeth_joint_position = cmds.xform('upperTeethJoint_M', q=True, ws=True, t=True)
        lip_length = abs(lip_joint_position[2] - teeth_joint_position[2])
        cmds.setAttr('%s.t' % lip_region_tra, 0, 0, -lip_length, typ='double3')
        cmds.setAttr('%s.r' % lip_region_tra, 0, 0, 0, typ='double3')
        cmds.setAttr('%s.s' % lip_region_tra, 1, 1, 1, typ='double3')
        connections = cmds.listConnections(lip_region_joint, s=True, d=False, p=True) or []
        for connection in connections:
            sub_connections = cmds.listConnections(connection, s=False, d=True, p=True) or []
            for sub_connection in sub_connections:
                replace_attr = sub_connection.replace(lip_region_joint, lip_region_ext)
                if cmds.objExists(replace_attr):
                    cmds.connectAttr(connection, replace_attr, f=True)
                    cmds.disconnectAttr(connection, sub_connection)
        parent.fitParent(lip_region_joint, lip_region_ext)
        cmds.setAttr('%s.t' % lip_region_joint, 0, 0, lip_length, type='double3')
        cmds.setAttr('%s.r' % lip_region_joint, 0, 0, 0, typ='double3')
        cmds.setAttr('%s.s' % lip_region_joint, 1, 1, 1, typ='double3')

        # 隐藏 SmileBulge 控制器
        for side in self.adv_sides:
            ctrl = 'SmileBulge%s' % side
            if cmds.objExists(ctrl):
                cmds.setAttr('%s.lodVisibility' % ctrl, 0)
        # lower,upper lip 属性修正
        for part in ['lower', 'upper']:
            lip_ctrl = '%sLip_M' % part
            # press 属性连接修正
            press_rv = '%s_press_RV' % lip_ctrl
            check_node(press_rv, 'remapValue')
            cmds.setAttr('%s.inputMin' % press_rv, 2)
            cmds.setAttr('%s.inputMax' % press_rv, 0)
            cmds.setAttr('%s.outputMin' % press_rv, -10)
            cmds.setAttr('%s.outputMax' % press_rv, 10)
            cmds.connectAttr('%s.sz' % lip_ctrl, '%s.inputValue' % press_rv, f=True)
            cmds.connectAttr('%s.outColorR' % press_rv, 'ctrlMouth_M.%sPress' % part, f=True)

            # squeeze 属性连接修正
            squeeze_rv = '%s_squeeze_RV' % lip_ctrl
            check_node(squeeze_rv, 'remapValue')
            cmds.setAttr('%s.inputMin' % squeeze_rv, 1)
            cmds.setAttr('%s.inputMax' % squeeze_rv, 0)
            cmds.setAttr('%s.outputMin' % squeeze_rv, 0)
            cmds.setAttr('%s.outputMax' % squeeze_rv, 10)
            cmds.connectAttr('%s.sy' % lip_ctrl, '%s.inputValue' % squeeze_rv, f=True)
            cmds.connectAttr('%s.outColorR' % squeeze_rv, 'ctrlMouth_M.%sSqueeze' % part, f=True)

            # lower roll 属性修正
            roll_rv = '%s_roll_RV' % lip_ctrl
            check_node(roll_rv, 'remapValue')
            multi = -1 if part == 'upper' else 1
            cmds.setAttr('%s.inputMin' % roll_rv, 40 * multi)
            cmds.setAttr('%s.inputMax' % roll_rv, -40 * multi)
            cmds.setAttr('%s.outputMin' % roll_rv, 10)
            cmds.setAttr('%s.outputMax' % roll_rv, -10)
            cmds.connectAttr('%s.rx' % lip_ctrl, '%s.inputValue' % roll_rv, f=True)
            cmds.connectAttr('%s.outColorR' % roll_rv, 'ctrlMouth_M.%sRoll' % part, f=True)

            cmds.setAttr('%s.ry' % lip_ctrl, e=True, l=True, k=False)
            cmds.setAttr('%s.rz' % lip_ctrl, e=True, l=True, k=False)
            cmds.setAttr('%s.sx' % lip_ctrl, e=True, l=True, k=False)

        if cmds.objExists('faceBuildPose'):
            faceBuildPoseinfo = cmds.getAttr('faceBuildPose.udAttr')
            for part in ['lower', 'upper']:
                lip_ctrl = '%sLip_M' % part
                for attr in ['Press','Squeeze','Roll']:
                    faceBuildPoseinfo = faceBuildPoseinfo.replace('setAttr %s.%s%s 0' % ('ctrlMouth_M', part,attr),'')
                for attr in ['ry', 'rz']:
                    faceBuildPoseinfo = faceBuildPoseinfo.replace('setAttr %s.%s 0;' % (lip_ctrl, attr),'')
                for attr in ['sx']:
                    faceBuildPoseinfo = faceBuildPoseinfo.replace('setAttr %s.%s 1;' % (lip_ctrl, attr),'')
                cmds.setAttr('faceBuildPose' + '.udAttr', faceBuildPoseinfo, type='string')
    def smile_pull_correct(self):
        # 限制位移幅度并传递 zip 属性
        for side in self.adv_sides:
            smile_ctr = 'SmilePull%s' % side
            cmds.transformLimits(smile_ctr, tx=[-0.5, 1], etx=[1, 1], ty=[-0.5, 1], ety=[1, 1])
            if cmds.objExists('ctrlMouth_M.zipLips%s' % side):
                if not cmds.objExists(smile_ctr + '.' + 'zipLips'):
                    info = utils.transfer_connect_attrs('ctrlMouth_M', smile_ctr, ['zipLips%s' % side],
                                                        defaultMode=False)
                    if 'zipLips%s' % side in info['success']:
                        cmds.renameAttr(smile_ctr + '.' + 'zipLips%s' % side, 'zipLips')

            if cmds.objExists('faceBuildPose'):
                faceBuildPoseinfo = cmds.getAttr('faceBuildPose.udAttr')
                faceBuildPoseinfo = faceBuildPoseinfo.replace('%s.%s' % ('ctrlMouth_M', 'zipLips%s' % side), '%s.%s' % (smile_ctr, 'zipLips'))

                cmds.setAttr('faceBuildPose' + '.udAttr', faceBuildPoseinfo, type='string')
    def eidtCtrlPosition(self):
        for side in self.adv_sides:
            # 修正眉头控制器的位置不对（advBug）
            for cv in ['EyeBrowInner', 'EyeBrowOuter', 'EyeBrowMid1', 'EyeBrowMid2', 'EyeBrowMid3']:
                pociNode = cmds.listConnections('%sAttachCurve%sShape.worldSpace[0]' % (cv, side), d=1,
                                                type='pointOnCurveInfo') or []
                if len(pociNode) == 1:

                    if side == '_L':
                        cvMinParameter = cmds.getAttr('%sAttachCurve%s.minValue' % (cv, side))
                        cvMaxParameter = cmds.getAttr('%sAttachCurve%s.maxValue' % (cv, side))
                        cvMinPnt = cmds.pointOnCurve(cv + 'AttachCurve' + side, pr=cvMinParameter)
                        cvMaxPnt = cmds.pointOnCurve(cv + 'AttachCurve' + side, pr=cvMaxParameter)
                        ctrlPntA = cmds.xform(cv + '_R', ws=1, q=1, t=1)
                        ctrlPntB = [-1 * ctrlPntA[0], ctrlPntA[1], ctrlPntA[2]]
                        Parameter = 1
                        if ((cvMinPnt[0] - ctrlPntB[0]) ** 2 + (cvMinPnt[1] - ctrlPntB[1]) ** 2 + (
                                cvMinPnt[2] - ctrlPntB[2]) ** 2) ** 0.5 < (
                                (cvMaxPnt[0] - ctrlPntB[0]) ** 2 + (cvMaxPnt[1] - ctrlPntB[1]) ** 2 + (
                                cvMaxPnt[2] - ctrlPntB[2]) ** 2) ** 0.5:
                            Parameter = 0

                        cmds.setAttr(pociNode[0] + '.parameter', Parameter)
                    EyeBrowAttachGrp = cv + 'Attach' + side
                    EyeBrowAttachPc = cmds.listConnections(EyeBrowAttachGrp + '.tx', s=1, d=0,
                                                           type='pointConstraint')
                    if len(EyeBrowAttachPc) == 1:
                        cmds.setAttr(EyeBrowAttachPc[0] + '.offset', 0.0, 0.0, 0.0)
                        EyeBrowAttachOffset = cmds.listConnections(
                            EyeBrowAttachPc[0] + '.target[0].targetTranslate', s=1, d=0, type='transform')
                        if len(EyeBrowAttachOffset) == 1:
                            # cmds.setAttr(EyeBrowInnerAttachOffset[0]+'.t',0.0,0.0,0.0)
                            cmds.xform(EyeBrowAttachOffset[0], ws=1,
                                       t=cmds.xform('%sJoint%s' % (cv, side), q=1, ws=1, t=1))
            # 修正SmilePull控制器TZ有数值bug
            for cv in ['SmilePull']:
                cvPnt = cmds.xform('%s%s' % (cv, side), q=1, t=1)
                if cvPnt[-1] != 0.0:
                    cmds.setAttr('%s%s.tz' % (cv, side), l=0)
                    cmds.setAttr('%s%s.tz' % (cv, side), 0.0)
                    cmds.setAttr('%s%s.tz' % (cv, side), l=1)

    def mouth_controller_offset(self):
        # 上下牙控制器调整
        main_offset_list = []
        for part in ['upper', 'lower']:
            teeth_ctr = '%sTeeth_M' % part
            teeth_ctr_oft = '%sTeethOffset_M' % part
            if cmds.objExists(teeth_ctr_oft) and cmds.objExists(teeth_ctr) and not cmds.objExists(
                    'con_%s' % teeth_ctr) and not cmds.objExists('con_%s' % teeth_ctr_oft):

                par = cmds.listRelatives(teeth_ctr_oft, p=True)
                cmds.rename(teeth_ctr_oft, 'con_%s' % teeth_ctr_oft)
                cmds.rename(teeth_ctr, 'con_%s' % teeth_ctr)

                cmds.createNode('transform', n=teeth_ctr_oft)
                if par:
                    parent.fitParent(teeth_ctr_oft, par[0])
                for attr in 'trs':
                    values = cmds.getAttr('con_%s.%s' % (teeth_ctr_oft, attr))[0]
                    cmds.setAttr('%s.%s' % (teeth_ctr_oft, attr), *values, typ='double3')
                print teeth_ctr
                if not cmds.objExists(teeth_ctr):
                    cmds.duplicate('con_%s' % teeth_ctr, n=teeth_ctr)
                parent.fitParent(teeth_ctr, teeth_ctr_oft)
                for attr in 'trs':
                    cmds.connectAttr('%s.%s' % (teeth_ctr, attr), 'con_%s.%s' % (teeth_ctr, attr), f=True)
                main_offset_list.append(teeth_ctr_oft)

        # 舌头控制器调整
        tongue_par = None
        i = 0
        while True:
            tongue_ctr = 'Tongue%d_M' % i

            if not cmds.objExists(tongue_ctr) or cmds.objExists('con_%s' % tongue_ctr):
                print 'con_%s' % tongue_ctr
                break
            tongue_sdk = 'SDKTongue%d_M' % i
            tongue_rever = 'Tongue%dSideReverse_M' % i
            tongue_offset = 'Tongue%dOffset_M' % i
            for item in [tongue_offset, tongue_rever, tongue_sdk, tongue_ctr]:

                if cmds.objExists(item):
                    judge = True
                    if not tongue_par:
                        tongue_par = cmds.listRelatives(item, p=True)[0]
                        judge = False
                        main_offset_list.append(item)
                    cmds.rename(item, 'con_%s' % item)
                    self.del_to_set('con_%s' % item, 'FaceControlSet')
                    if item == tongue_ctr:
                        cmds.circle(n=item, ch=False, nr=[1, 0, 0])
                        shape = cmds.listRelatives(item, s=True)
                        cmds.setAttr('%s.ove' % shape[0], True)
                        cmds.setAttr('%s.ovc' % shape[0], 23)
                        self.add_to_set(item, 'FaceControlSet')
                    else:
                        cmds.createNode('transform', n=item)
                    cmds.parent(item, tongue_par)
                    for attr in 'trs':
                        values = cmds.getAttr('con_%s.%s' % (item, attr))[0]
                        cmds.setAttr('%s.%s' % (item, attr), *values, typ='double3')
                    # 属性关联
                    s_cons = cmds.listConnections('con_%s' % item, s=True, d=False, p=True) or []
                    for con in s_cons:
                        d_cons = cmds.listConnections(con, s=False, d=True, p=True) or []
                        for d_con in d_cons:
                            cmds.connectAttr(con, d_con.replace('con_', ''), f=True)
                            cmds.disconnectAttr(con, d_con)
                    if judge:
                        for attr in 'trs':
                            cmds.connectAttr('%s.%s' % (item, attr), 'con_%s.%s' % (item, attr), f=True)
                    tongue_par = item
            i += 1

        for item in main_offset_list:
            cmds.setAttr('con_%s.lodVisibility' % item, 0)
            # cmds.setAttr('%s.tx' % item, 15)
        return main_offset_list

    def add_teeth_ctrls(self):
        # 增加牙齿控制器
        global pntCtrl
        def add_single_ctr(part, joint_name, controller_name,position):
            # 创建骨骼和所需组别
            global colorList

            check_node(joint_name, 'joint')
            check_node(joint_oft, 'transform')

            cmds.xform(joint_name, ws=1, t=position)
            cmds.xform(joint_oft, ws=1, t=position)
            parent.fitParent(joint_name, joint_oft)
            # 创建控制器
            if not cmds.objExists(controller_name):
                if part == 'upper':
                    colorList = [0.7, 0.2, 0.2]
                if part == 'lower':
                    colorList = [0.2, 0.7, 0.7]
                control = controllerManager.Controller(controller_name, post='', color=colorList, ge=True,
                                                       g=['Ext', 'Tra', 'Oft'], d='z')
                control.create(99)
                cmds.xform(control.groups[-1], ws=True, t=position)
                # cmds.parentConstraint(control.curve, joint_name, w=True, mo=True)
                # cmds.scaleConstraint(control.curve, joint_name, w=True)
                cmds.connectAttr('%s.t' % control.curve, '%s.t' % joint_name, f=1)
                cmds.connectAttr('%s.r' % control.curve, '%s.r' % joint_name, f=1)
                cmds.connectAttr('%s.s' % control.curve, '%s.s' % joint_name, f=1)
                return [joint_oft, control.groups[-1]]
            return [joint_oft, controller_name + 'Oft']

        left_position = cmds.xform('SmilePull_L', q=True, ws=True, t=True)
        right_position = cmds.xform('SmilePull_R', q=True, ws=True, t=True)
        for part in ['upper', 'lower']:

            positions = {}
            center_position = cmds.xform('%sTeethJoint_M' % part, q=True, ws=True, t=True)
            positions['left_side1'] = [left_position[0], center_position[1], center_position[2]]
            positions['left_side2'] = [center_position[0] + (left_position[0] - center_position[0]) * 0.5,
                                       center_position[1],
                                       center_position[2] + (left_position[2] - center_position[2]) * 0.4]
            positions['center'] = [center_position[0], center_position[1],
                                   center_position[2] + (left_position[2] - center_position[2]) * 0.5]
            positions['right_side1'] = [right_position[0], center_position[1], center_position[2]]
            positions['right_side2'] = [center_position[0] + (right_position[0] - center_position[0]) * 0.5,
                                        center_position[1],
                                        center_position[2] + (right_position[2] - center_position[2]) * 0.4]

            for key, position in positions.items():
                name = '%sTeeth_%s' % (part, key)
                joint_name = '%sJoint' % name
                joint_oft = '%sJoint_oft' % name
                controller_name = '%sCtr' % name

                if not cmds.objExists(controller_name) :

                    joint_grp, ctrl_grp = add_single_ctr(part, joint_name, controller_name,position)
                    if part == 'upper':
                        pntCtrl = 'ctrlMouth_M'
                    if part == 'lower':
                        pntCtrl = 'ctrlPhonemes_M'

                    parent.fitParent(joint_grp, '%sTeethJoint_M' % part)
                    parent.fitParent(ctrl_grp, '%sTeeth_M' % part)

            parentConstraints = cmds.listRelatives('%sTeethJoint_M' % part, type='parentConstraint')
            if parentConstraints:
                for constraint in parentConstraints:
                    parentList = cmds.parentConstraint(constraint, query=True, targetList=True)
                    for parentNode in parentList:
                        if parentNode == '%sTeeth_M' % part:
                            jntGrp = '%sTeethJoint_M_TraGrp' % part
                            if not cmds.objExists(jntGrp):
                                cmds.createNode('transform', n=jntGrp)
                                cmds.delete(cmds.parentConstraint('%sTeethJoint_M' % part, jntGrp))
                                cmds.parent(jntGrp, cmds.listRelatives('%sTeethJoint_M' % part, p=1)[0])
                                cmds.parent('%sTeethJoint_M' % part, jntGrp)

                                cmds.delete(constraint)
                                ctrlMouth_MPnt = cmds.xform(pntCtrl, q=1, ws=1, t=1)
                                cmds.xform('%sTeethOffset_M' % part, ws=1,
                                           t=[ctrlMouth_MPnt[0], ctrlMouth_MPnt[1], ctrlMouth_MPnt[2]])

                                cmds.parentConstraint('%sTeeth_M' % part, jntGrp, mo=1)
        if not cmds.objExists('Tongue0_M.follow'):
            cmds.addAttr('Tongue0_M', ln='follow', at='double', min=0, max=10)
            cmds.setAttr('%s.%s' % ('Tongue0_M', 'follow'), e=True, k=True, l=False)
    def eye_iris_correct(self):
        # 当前版本暂时未发现问题
        pass
    def addJaw_tra( self ):
        jaw_M_ctrl = 'Jaw_M'
        SDKJaw_M_Null = 'SDK%s' % jaw_M_ctrl
        if cmds.objExists(SDKJaw_M_Null) and cmds.objExists(SDKJaw_M_Null):
            SDKJaw_M_Null_TY = cmds.listConnections(SDKJaw_M_Null + '.ty', s=1, d=0, p=1)
            SDKJaw_M_Null_TZ = cmds.listConnections(SDKJaw_M_Null + '.tz', s=1, d=0, p=1)
            preTyNodeType = cmds.nodeType(cmds.listConnections(SDKJaw_M_Null + '.ty', s=1, d=0))
            preTzNodeType = cmds.nodeType(cmds.listConnections(SDKJaw_M_Null + '.tz', s=1, d=0))
            if preTyNodeType == 'blendWeighted' or preTzNodeType == 'blendWeighted':
                multiplyNode = '%s__MD_JAW__' % SDKJaw_M_Null
                plusMANode = '%s__PMA_JAW__' % SDKJaw_M_Null
                if not (cmds.objExists(multiplyNode) and cmds.objExists(plusMANode)):
                    cmds.createNode('multiplyDivide', n=multiplyNode)
                    cmds.createNode('plusMinusAverage', n=plusMANode)
                cmds.setAttr('%s.input2Y' % multiplyNode, -0.02)
                cmds.setAttr('%s.input2Z' % multiplyNode, 0.02)
                cmds.connectAttr('%s.outputY' % multiplyNode, '%s.input3D[0].input3Dy' % plusMANode, f=1)
                cmds.connectAttr('%s.outputZ' % multiplyNode, '%s.input3D[0].input3Dz' % plusMANode, f=1)
                cmds.connectAttr('%s.rotateX' % jaw_M_ctrl, '%s.input1Y' % multiplyNode, f=1)
                cmds.connectAttr('%s.rotateX' % jaw_M_ctrl, '%s.input1Z' % multiplyNode, f=1)
                if SDKJaw_M_Null_TY:
                    cmds.connectAttr(SDKJaw_M_Null_TY[0], '%s.input3D[1].input3Dy' % plusMANode, f=1)
                if SDKJaw_M_Null_TZ:
                    cmds.connectAttr(SDKJaw_M_Null_TZ[0], '%s.input3D[1].input3Dz' % plusMANode, f=1)
                cmds.connectAttr('%s.output3Dy' % plusMANode, '%s.translateY' % SDKJaw_M_Null, f=1)
                cmds.connectAttr('%s.output3Dz' % plusMANode, '%s.translateZ' % SDKJaw_M_Null, f=1)
    def correct_sub_facial(self):
        items = [u'EyeBrowMid2Offset_R',
                 u'EyeBrowMid3Offset_R',
                 u'EyeBrowMid1Offset_R',
                 u'EyeBrowOuterOffset_R',
                 u'EyeBrowMid2Offset_L',
                 u'EyeBrowMid1Offset_L',
                 u'EyeBrowMid3Offset_L',
                 u'EyeBrowOuterOffset_L',
                 u'NoseOffset_M',
                 u'NostrilOffset_R',
                 u'NostrilOffset_L',
                 u'upperOuterLidOffset_R',
                 u'lowerOuterLidOffset_R',
                 u'lowerInnerLidOffset_R',
                 u'upperInnerLidOffset_L',
                 u'upperOuterLidOffset_L',
                 u'lowerInnerLidOffset_L',
                 u'lowerOuterLidOffset_L',
                 u'upperInnerLidOffset_R',
                 u'innerLidDroopyOffset_R',
                 u'outerLidDroopyOffset_R',
                 u'upperInnerLidDroopyOffset_R',
                 u'upperOuterLidDroopyOffset_R',
                 u'lowerLidDroopyOffset_R',
                 u'lowerInnerLidDroopyOffset_R',
                 u'lowerOuterLidDroopyOffset_R',
                 u'lowerOuterLidDroopyOffset_L',
                 u'innerLidOffset_R',
                 u'outerLidOffset_R',
                 u'innerLidOffset_L',
                 u'outerLidOffset_L',
                 u'innerLidDroopyOffset_L',
                 u'outerLidDroopyOffset_L',
                 u'upperInnerLidDroopyOffset_L',
                 u'upperOuterLidDroopyOffset_L',
                 u'lowerLidDroopyOffset_L',
                 u'lowerInnerLidDroopyOffset_L',
                 u'NoseUnderOffset_M',
                 u'upperFace_MShape',
                 u'middleFace_MShape',
                 u'lowerFace_MShape']
        if cmds.objExists('VisibilityCtr.sub_facial_sys_vis'):
            for item in items:
                if cmds.objExists(item):
                    if item in ['upperFace_MShape', 'middleFace_MShape', 'lowerFace_MShape']:
                        cmds.connectAttr('VisibilityCtr.sub_facial_sys_vis', '%s.lodVisibility' % item, f=True)
                    else:
                        cmds.connectAttr('VisibilityCtr.sub_facial_sys_vis', '%s.v' % item, f=True)

    def lip_sub_correct(self):
        # 新增嘴唇单独控制器
        for part in self.mouth_parts:
            bbs = cmds.xform('%sLip_M' % part, q=True, bb=True)
            radius = max(bbs[3] - bbs[0], bbs[4] - bbs[1], bbs[5] - bbs[2])
            sub_ctr = '%sLip_M_sec_Ctr' % part
            if not cmds.objExists(sub_ctr):
                cmds.circle(n=sub_ctr, r=radius * 0.35, ch=False)
                cmds.setAttr(sub_ctr+'.v',l =1 ,k =0 , channelBox = 0)
                shapes = cmds.listRelatives(sub_ctr, s=True)
                for shape in shapes:
                    cmds.setAttr('%s.ove' % shape, True)
                    cmds.setAttr('%s.ovc' % shape, 18)

                ctr_tra = check_node('%sTra' % sub_ctr, 'transform')
                check_parent(sub_ctr, ctr_tra)
                ctr_oft = check_node('%sOft' % sub_ctr, 'transform')
                check_parent(ctr_tra, ctr_oft)
                check_parent(ctr_oft, '%sLip_M' % part)

                sub_con = check_node('%sLip_M_con' % part, 'transform')
                check_parent(sub_con, '%sLipJoint_M' % part)
                cmds.connectAttr('%s.t' % sub_ctr, '%s.t' % sub_con, f=True)
                cmds.connectAttr('%s.r' % sub_ctr, '%s.r' % sub_con, f=True)

                reverse_md = check_node('%s_reverse_md' % sub_ctr, 'multiplyDivide')
                cmds.setAttr('%s.i2' % reverse_md, -1, -1, -1, type='double3')
                cmds.connectAttr('%s.t' % sub_ctr, '%s.i1' % reverse_md, f=True)
                cmds.connectAttr('%s.o' % reverse_md, '%s.t' % ctr_tra, f=True)

                constraints = cmds.listConnections('%s%sLipClusterHandle_M.tx' % (part, part), s=True, d=False)
                if constraints:
                    cmds.delete(constraints)
                cmds.parentConstraint(sub_con, '%s%sLipClusterHandle_M' % (part, part), w=1, mo=True)
            if not cmds.objExists('%s.lip_middle_fix'%sub_ctr):
                cmds.addAttr(sub_ctr, ln='lip_middle_fix', at='double', min=0, max=1)
                cmds.setAttr('%s.%s' % (sub_ctr, 'lip_middle_fix'), e=True, k=True, l=False)

            if cmds.objExists('faceBuildPose'):
                faceBuildPoseinfo = cmds.getAttr('faceBuildPose.udAttr')
                if ';setAttr %s.%s 0 0 0;'%(sub_ctr, 't') not in faceBuildPoseinfo:
                    faceBuildPoseinfo += ';setAttr %s.%s 0 0 0;'%(sub_ctr, 't')
                if ';setAttr %s.%s 0 0 0;' % (sub_ctr, 'r') not in faceBuildPoseinfo:
                    faceBuildPoseinfo += ';setAttr %s.%s 0 0 0;' % (sub_ctr, 'r')
                if ';setAttr %s.%s 1 1 1;' % (sub_ctr, 's') not in faceBuildPoseinfo:
                    faceBuildPoseinfo += ';setAttr %s.%s 1 1 1;' % (sub_ctr, 's')
                if ';setAttr %s.%s 0;' % (sub_ctr, 'lip_middle_fix') not in faceBuildPoseinfo:
                    faceBuildPoseinfo += ';setAttr %s.%s 0;' % (sub_ctr, 'lip_middle_fix')
                cmds.setAttr('faceBuildPose' + '.udAttr', faceBuildPoseinfo, type='string')
    def do_facial_correct(self):
        self.eye_brow_inner_correct()
        self.eye_region_correct()
        self.lip_region_correct()
        self.smile_pull_correct()
        main_offset_list = self.mouth_controller_offset()
        self.add_teeth_ctrls()
        if cmds.objExists('ctrlBoxOffset'):
            cmds.setAttr('ctrlBoxOffset.v', False)
        self.eye_iris_correct()
        self.eidtCtrlPosition()
        self.correct_sub_facial()
        self.lip_sub_correct()
        self.addJaw_tra()
        for item in main_offset_list:
            cmds.setAttr('%s.tx' % item, 0.15 * self._mainSize_)


def chr_correct(**kwargs):
    rig = None
    '''if cmds.objExists('TSM3_root'):
        rig = TSM3Rigging(**kwargs)'''
    if cmds.objExists('FitSkeleton') and cmds.objExists('Main'):
        rig = AdvRigging(**kwargs)
    if rig:
        rig.correct()
    return rig


def correct(**kwargs):
    """
    根据场景信息，判断资产类型和修正方案，并执行修正
    :param kwargs: 修正参数
    :return:
    """
    chr_correct(**kwargs)
