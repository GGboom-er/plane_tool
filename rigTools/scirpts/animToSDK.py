#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: animToSDK.py
@date: 2024/3/25 14:45
@desc: 
"""
import maya.cmds as cmds

# 动画曲线节点的名称
animCurveNode = cmds.ls(sl=1)[0]

# 获取关键帧时间和值
keyTimes = [i - 100 for i in cmds.keyframe(animCurveNode, query=True, timeChange=True)]
keyValues = cmds.keyframe(animCurveNode, query=True, valueChange=True)

# 驱动者和被驱动者的属性
driverAttr = 'walk_Main_Ctr.walk'
drivenAttr = 'PoleExtraArm1_R' + '.' + animCurveNode.split('_')[-1]

# 清除已有的SDK（根据需要决定是否执行这步）
# cmds.delete(drivenAttr, inputConnections=True)

# 为每个关键帧设置SDK
for time, value in zip(keyTimes, keyValues):
    # 设置驱动者的值
    cmds.setAttr(driverAttr, time)

    # 创建或更新SDK
    cmds.setDrivenKeyframe(drivenAttr, currentDriver=driverAttr, driverValue=time, value=value)

cmds.delete(animCurveNode)