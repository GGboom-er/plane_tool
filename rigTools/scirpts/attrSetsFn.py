#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: attrSetsFn.py
@date: 2024/8/20 14:36
@desc: 
"""
import maya.cmds as cmds


def set_soft_limits_on_selected_attrs( min_value, max_value ):
    # 获取当前选择的物体
    selected_objects = cmds.ls(selection=True)

    # 获取当前选择的属性
    selected_channels = cmds.channelBox('mainChannelBox', query=True, selectedMainAttributes=True)

    if not selected_objects:
        cmds.warning("请选择至少一个对象")
        return

    if not selected_channels:
        cmds.warning("请选择至少一个属性")
        return

    for obj in selected_objects:
        for attr_name in selected_channels:
            # 构建属性路径
            attr_full_name = obj + '.' + attr_name

            # 检查属性是否存在
            if cmds.attributeQuery(attr_name, node=obj, exists=True):
                # 设置软边界
                cmds.addAttr(attr_full_name, edit=True, hasMinValue=True, minValue=min_value)
                cmds.addAttr(attr_full_name, edit=True, hasMaxValue=True, maxValue=max_value)


# 示例使用：
# 选择物体和你想要设置的属性，然后调用函数设置最小值和最大值
set_soft_limits_on_selected_attrs(-10, 10)
