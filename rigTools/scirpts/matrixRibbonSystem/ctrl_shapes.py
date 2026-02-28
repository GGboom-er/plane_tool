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
    ctrl = cmds.curve(name=name, d=1, p=[(0.037*size, 0.5*size, 0.0*size), (0.037*size, 0.483*size, -0.129*size), (0.037*size, 0.433*size, -0.25*size), (0.037*size, 0.354*size, -0.354*size), (0.037*size, 0.25*size, -0.433*size), (0.037*size, 0.129*size, -0.483*size), (0.037*size, 0.0*size, -0.5*size), (-0.037*size, 0.0*size, -0.5*size), (-0.037*size, 0.129*size, -0.483*size), (-0.037*size, 0.25*size, -0.433*size), (-0.037*size, 0.354*size, -0.354*size), (-0.037*size, 0.433*size, -0.25*size), (-0.037*size, 0.483*size, -0.129*size), (-0.037*size, 0.5*size, 0.0*size), (0.037*size, 0.5*size, 0.0*size), (0.037*size, 0.483*size, 0.129*size), (0.037*size, 0.433*size, 0.25*size), (0.037*size, 0.354*size, 0.354*size), (0.037*size, 0.25*size, 0.433*size), (0.037*size, 0.129*size, 0.483*size), (0.037*size, 0.0*size, 0.5*size), (0.037*size, -0.129*size, 0.483*size), (0.037*size, -0.25*size, 0.433*size), (0.037*size, -0.354*size, 0.354*size), (0.037*size, -0.433*size, 0.25*size), (0.037*size, -0.483*size, 0.129*size), (0.037*size, -0.5*size, 0.0*size), (-0.037*size, -0.5*size, 0.0*size), (-0.037*size, -0.483*size, -0.129*size), (-0.037*size, -0.433*size, -0.25*size), (-0.037*size, -0.354*size, -0.354*size), (-0.037*size, -0.25*size, -0.433*size), (-0.037*size, -0.129*size, -0.483*size), (-0.037*size, 0.0*size, -0.5*size), (0.037*size, 0.0*size, -0.5*size), (0.037*size, -0.129*size, -0.483*size), (0.037*size, -0.25*size, -0.433*size), (0.037*size, -0.354*size, -0.354*size), (0.037*size, -0.433*size, -0.25*size), (0.037*size, -0.483*size, -0.129*size), (0.037*size, -0.5*size, 0.0*size), (-0.037*size, -0.5*size, 0.0*size), (-0.037*size, -0.483*size, 0.129*size), (-0.037*size, -0.433*size, 0.25*size), (-0.037*size, -0.354*size, 0.354*size), (-0.037*size, -0.25*size, 0.433*size), (-0.037*size, -0.129*size, 0.483*size), (-0.037*size, 0.0*size, 0.5*size), (0.037*size, 0.0*size, 0.5*size), (-0.037*size, 0.0*size, 0.5*size), (-0.037*size, 0.129*size, 0.483*size), (-0.037*size, 0.25*size, 0.433*size), (-0.037*size, 0.354*size, 0.354*size), (-0.037*size, 0.433*size, 0.25*size), (-0.037*size, 0.483*size, 0.129*size), (-0.037*size, 0.5*size, 0.0*size)], k=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0, 38.0, 39.0, 40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0, 47.0, 48.0, 49.0, 50.0, 51.0, 52.0, 53.0, 54.0, 55.0])
    return ctrl, 17


def create_ik_shape(name, size=1.0):
    """IK 控制器形状（默认：方块，朝 X）。

    Args:
        name: 控制器名称
        size: 控制器尺寸（基于 rig width × IK_CTRL_SCALE）

    Returns:
        (transform, color): transform 节点名, Maya overrideColor 索引
    """
    ctrl = cmds.curve(name=name, d=1, p=[(0.000*size, 0.0*size, 0.25*size), (0.000*size, 0.0*size, 0.125*size), (-0.048*size, 0.0*size, 0.116*size), (-0.088*size, 0.0*size, 0.088*size), (-0.116*size, 0.0*size, 0.048*size), (-0.125*size, 0.0*size, 0.0*size), (-0.25*size, 0.0*size, 0.0*size), (-0.125*size, 0.0*size, 0.0*size), (-0.116*size, 0.0*size, -0.048*size), (-0.088*size, 0.0*size, -0.088*size), (-0.048*size, 0.0*size, -0.116*size), (0.000*size, 0.0*size, -0.125*size), (0.000*size, 0.0*size, -0.25*size), (0.000*size, 0.0*size, -0.125*size), (0.048*size, 0.0*size, -0.116*size), (0.088*size, 0.0*size, -0.088*size), (0.116*size, 0.0*size, -0.048*size), (0.125*size, 0.0*size, 0.0*size), (0.25*size, 0.0*size, 0.0*size), (0.125*size, 0.0*size, 0.0*size), (0.116*size, 0.0*size, 0.048*size), (0.088*size, 0.0*size, 0.088*size), (0.048*size, 0.0*size, 0.116*size), (0.000*size, 0.0*size, 0.125*size), (0.000*size, -0.048*size, 0.116*size), (0.000*size, -0.088*size, 0.088*size), (0.000*size, -0.116*size, 0.048*size), (0.000*size, -0.125*size, 0.0*size), (0.000*size, -0.25*size, 0.0*size), (0.000*size, -0.125*size, 0.0*size), (0.000*size, -0.116*size, -0.048*size), (0.000*size, -0.088*size, -0.088*size), (0.000*size, -0.048*size, -0.116*size), (0.000*size, 0.0*size, -0.125*size), (0.000*size, 0.048*size, -0.116*size), (0.000*size, 0.088*size, -0.088*size), (0.000*size, 0.116*size, -0.048*size), (0.000*size, 0.125*size, 0.0*size), (0.000*size, 0.25*size, 0.0*size), (0.000*size, 0.125*size, 0.0*size), (-0.048*size, 0.116*size, 0.0*size), (-0.088*size, 0.088*size, 0.0*size), (-0.116*size, 0.048*size, 0.0*size), (-0.125*size, 0.0*size, 0.0*size), (-0.116*size, -0.048*size, 0.0*size), (-0.088*size, -0.088*size, 0.0*size), (-0.048*size, -0.116*size, 0.0*size), (0.000*size, -0.125*size, 0.0*size), (0.048*size, -0.116*size, 0.0*size), (0.088*size, -0.088*size, 0.0*size), (0.116*size, -0.048*size, 0.0*size), (0.125*size, 0.0*size, 0.0*size), (0.116*size, 0.048*size, 0.0*size), (0.088*size, 0.088*size, 0.0*size), (0.048*size, 0.116*size, 0.0*size), (0.000*size, 0.125*size, 0.0*size), (0.000*size, 0.116*size, 0.048*size), (0.000*size, 0.088*size, 0.088*size), (0.000*size, 0.048*size, 0.116*size), (0.000*size, 0.0*size, 0.125*size), (0.000*size, 0.0*size, 0.0*size), (0.000*size, 0.0*size, -0.125*size), (0.000*size, 0.0*size, 0.0*size), (0.000*size, 0.125*size, 0.0*size), (0.000*size, 0.0*size, 0.0*size), (0.000*size, -0.125*size, 0.0*size), (0.000*size, 0.0*size, 0.0*size), (0.125*size, 0.0*size, 0.0*size), (0.000*size, 0.0*size, 0.0*size), (-0.125*size, 0.0*size, 0.0*size)], k=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0, 38.0, 39.0, 40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0, 47.0, 48.0, 49.0, 50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0, 58.0, 59.0, 60.0, 61.0, 62.0, 63.0, 64.0, 65.0, 66.0, 67.0, 68.0, 69.0])
    return ctrl, 13
