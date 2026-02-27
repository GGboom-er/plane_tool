"""
Matrix Ribbon System (MRS) - 控制器形状定义
用户可修改此文件中的函数来自定义 FK/IK 控制器外观。
每个函数返回 (transform_name, override_color_index) 元组。
"""
import maya.cmds as cmds


def create_fk_shape(name, size=1.0):
    """FK 控制器形状（默认：圆环，法线朝 X）。

    Args:
        name: 控制器名称
        size: 控制器尺寸（基于 rig width × FK_CTRL_SCALE）

    Returns:
        (transform, color): transform 节点名, Maya overrideColor 索引
    """
    ctrl = cmds.circle(name=name, nr=(1, 0, 0), r=size, ch=False)[0]
    return ctrl, 17


def create_ik_shape(name, size=1.0):
    """IK 控制器形状（默认：方块，朝 X）。

    Args:
        name: 控制器名称
        size: 控制器尺寸（基于 rig width × IK_CTRL_SCALE）

    Returns:
        (transform, color): transform 节点名, Maya overrideColor 索引
    """
    ctrl = cmds.curve(name=name, d=1,
                      p=[(-size, -size, 0), (size, -size, 0),
                         (size, size, 0), (-size, size, 0),
                         (-size, -size, 0)])
    cmds.setAttr(f"{ctrl}.rotateY", 90)
    cmds.makeIdentity(ctrl, apply=True, r=True)
    return ctrl, 13
