#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: setSDK.py
@date: 2024/11/4 18:47
@desc: 
"""
import maya.cmds as cmds

def set_animCurve_keyframe_values(animCurveNodes, indices, values):
    """
    设置指定 animCurve 节点中多个索引的关键帧值。

    Parameters:
        animCurveNodes (list): animCurve 节点名称列表
        indices (list): 要设置的关键帧索引列表
        values (list): 对应每个索引的新值列表
    """
    if len(indices) != len(values):
        print("Error: 索引列表和值列表的长度不匹配。")
        return

    for animCurveNode in animCurveNodes:
        if not cmds.objExists(animCurveNode):
            print(f"节点 {animCurveNode} 不存在，跳过该节点")
            continue

        # 对每个索引和对应的值进行设置
        for i, index in enumerate(indices):
            try:
                cmds.keyframe(animCurveNode, index=(index, index), absolute=True, valueChange=values[i])
                print(f"设置 {animCurveNode} 节点索引 {index} 的关键帧值为 {values[i]}")
            except Exception as e:
                print(f"无法设置 {animCurveNode} 节点索引 {index} 的关键帧值。错误信息: {e}")

# 示例使用
animCurveNodes = cmds.ls(sl=1)  # 批量选择的 animCurve 节点列表
indices = [0, 2]  # 指定的索引列表
values = [-18, 90]  # 对应的值列表

set_animCurve_keyframe_values(animCurveNodes, indices, values)
