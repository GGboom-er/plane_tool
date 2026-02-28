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
    ctrl = cmds.curve(name=name, d=1, p=[(0.025*size, 1.001*size, 0.000*size), (0.025*size, 0.966*size, -0.259*size), (0.025*size, 0.866*size, -0.500*size), (0.025*size, 0.708*size, -0.708*size), (0.025*size, 0.500*size, -0.866*size), (0.025*size, 0.259*size, -0.966*size), (0.025*size, 0.000*size, -1.001*size), (-0.025*size, 0.000*size, -1.001*size), (-0.025*size, 0.259*size, -0.966*size), (-0.025*size, 0.500*size, -0.866*size), (-0.025*size, 0.708*size, -0.708*size), (-0.025*size, 0.866*size, -0.500*size), (-0.025*size, 0.966*size, -0.259*size), (-0.025*size, 1.001*size, 0.000*size), (0.025*size, 1.001*size, 0.000*size), (0.025*size, 0.966*size, 0.259*size), (0.025*size, 0.866*size, 0.500*size), (0.025*size, 0.708*size, 0.708*size), (0.025*size, 0.500*size, 0.866*size), (0.025*size, 0.259*size, 0.966*size), (0.025*size, 0.000*size, 1.001*size), (0.025*size, -0.259*size, 0.966*size), (0.025*size, -0.500*size, 0.866*size), (0.025*size, -0.708*size, 0.708*size), (0.025*size, -0.866*size, 0.500*size), (0.025*size, -0.966*size, 0.259*size), (0.025*size, -1.001*size, 0.000*size), (-0.025*size, -1.001*size, 0.000*size), (-0.025*size, -0.966*size, -0.259*size), (-0.025*size, -0.866*size, -0.500*size), (-0.025*size, -0.708*size, -0.708*size), (-0.025*size, -0.500*size, -0.866*size), (-0.025*size, -0.259*size, -0.966*size), (-0.025*size, 0.000*size, -1.001*size), (0.025*size, 0.000*size, -1.001*size), (0.025*size, -0.259*size, -0.966*size), (0.025*size, -0.500*size, -0.866*size), (0.025*size, -0.708*size, -0.708*size), (0.025*size, -0.866*size, -0.500*size), (0.025*size, -0.966*size, -0.259*size), (0.025*size, -1.001*size, 0.000*size), (-0.025*size, -1.001*size, 0.000*size), (-0.025*size, -0.966*size, 0.259*size), (-0.025*size, -0.866*size, 0.500*size), (-0.025*size, -0.708*size, 0.708*size), (-0.025*size, -0.500*size, 0.866*size), (-0.025*size, -0.259*size, 0.966*size), (-0.025*size, 0.000*size, 1.001*size), (0.025*size, 0.000*size, 1.001*size), (-0.025*size, 0.000*size, 1.001*size), (-0.025*size, 0.259*size, 0.966*size), (-0.025*size, 0.500*size, 0.866*size), (-0.025*size, 0.708*size, 0.708*size), (-0.025*size, 0.866*size, 0.500*size), (-0.025*size, 0.966*size, 0.259*size), (-0.025*size, 1.001*size, 0.000*size)], k=[0.0, 1.565366, 3.130758, 4.696126, 6.261487, 7.826885, 9.392244, 15.392244, 16.957602, 18.523, 20.088361, 21.653729, 23.219121, 24.784487, 30.784487, 32.349852, 33.915246, 35.480611, 37.045976, 38.61137, 40.176735, 41.7421, 43.307494, 44.872859, 46.438224, 48.003618, 49.568983, 55.568983, 57.134349, 58.699741, 60.265109, 61.83047, 63.395868, 64.961226, 70.961226, 72.526584, 74.091982, 75.657343, 77.222712, 78.788104, 80.35347, 86.35347, 87.918834, 89.484229, 91.049594, 92.614959, 94.180353, 95.745718, 101.745718, 107.745718, 109.311083, 110.876477, 112.441842, 114.007207, 115.572601, 117.137966])
    return ctrl, 17


def create_ik_shape(name, size=1.0):
    """IK 控制器形状（默认：方块，朝 X）。

    Args:
        name: 控制器名称
        size: 控制器尺寸（基于 rig width × IK_CTRL_SCALE）

    Returns:
        (transform, color): transform 节点名, Maya overrideColor 索引
    """
    ctrl = cmds.curve(name=name, d=1, p=[(0.000*size, 0.000*size, 0.550*size), (0.000*size, 0.000*size, 0.275*size), (-0.105*size, 0.000*size, 0.254*size), (-0.195*size, 0.000*size, 0.195*size), (-0.254*size, 0.000*size, 0.105*size), (-0.275*size, 0.000*size, 0.000*size), (-0.550*size, 0.000*size, 0.000*size), (-0.275*size, 0.000*size, 0.000*size), (-0.254*size, 0.000*size, -0.105*size), (-0.195*size, 0.000*size, -0.195*size), (-0.105*size, 0.000*size, -0.254*size), (0.000*size, 0.000*size, -0.275*size), (0.000*size, 0.000*size, -0.550*size), (0.000*size, 0.000*size, -0.275*size), (0.105*size, 0.000*size, -0.254*size), (0.195*size, 0.000*size, -0.195*size), (0.254*size, 0.000*size, -0.105*size), (0.275*size, 0.000*size, 0.000*size), (0.550*size, 0.000*size, 0.000*size), (0.275*size, 0.000*size, 0.000*size), (0.254*size, 0.000*size, 0.105*size), (0.195*size, 0.000*size, 0.195*size), (0.105*size, 0.000*size, 0.254*size), (0.000*size, 0.000*size, 0.275*size), (0.000*size, -0.105*size, 0.254*size), (0.000*size, -0.195*size, 0.195*size), (0.000*size, -0.254*size, 0.105*size), (0.000*size, -0.275*size, 0.000*size), (0.000*size, -0.550*size, 0.000*size), (0.000*size, -0.275*size, 0.000*size), (0.000*size, -0.254*size, -0.105*size), (0.000*size, -0.195*size, -0.195*size), (0.000*size, -0.105*size, -0.254*size), (0.000*size, 0.000*size, -0.275*size), (0.000*size, 0.105*size, -0.254*size), (0.000*size, 0.195*size, -0.195*size), (0.000*size, 0.254*size, -0.105*size), (0.000*size, 0.275*size, 0.000*size), (0.000*size, 0.550*size, 0.000*size), (0.000*size, 0.275*size, 0.000*size), (-0.105*size, 0.254*size, 0.000*size), (-0.195*size, 0.195*size, 0.000*size), (-0.254*size, 0.105*size, 0.000*size), (-0.275*size, 0.000*size, 0.000*size), (-0.254*size, -0.105*size, 0.000*size), (-0.195*size, -0.195*size, 0.000*size), (-0.105*size, -0.254*size, 0.000*size), (0.000*size, -0.275*size, 0.000*size), (0.105*size, -0.254*size, 0.000*size), (0.195*size, -0.195*size, 0.000*size), (0.254*size, -0.105*size, 0.000*size), (0.275*size, 0.000*size, 0.000*size), (0.254*size, 0.105*size, 0.000*size), (0.195*size, 0.195*size, 0.000*size), (0.105*size, 0.254*size, 0.000*size), (0.000*size, 0.275*size, 0.000*size), (0.000*size, 0.254*size, 0.105*size), (0.000*size, 0.195*size, 0.195*size), (0.000*size, 0.105*size, 0.254*size), (0.000*size, 0.000*size, 0.275*size), (0.000*size, 0.000*size, 0.000*size), (0.000*size, 0.000*size, -0.275*size), (0.000*size, 0.000*size, 0.000*size), (0.000*size, 0.275*size, 0.000*size), (0.000*size, 0.000*size, 0.000*size), (0.000*size, -0.275*size, 0.000*size), (0.000*size, 0.000*size, 0.000*size), (0.275*size, 0.000*size, 0.000*size), (0.000*size, 0.000*size, 0.000*size), (-0.275*size, 0.000*size, 0.000*size)], k=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0, 38.0, 39.0, 40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0, 47.0, 48.0, 49.0, 50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0, 58.0, 59.0, 60.0, 61.0, 62.0, 63.0, 64.0, 65.0, 66.0, 67.0, 68.0, 69.0])
    return ctrl, 13
