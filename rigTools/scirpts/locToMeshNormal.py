#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: locToMeshNormal.py
@date: 2025/4/9 17:59
@desc: 
"""
import maya.cmds as cmds
import math
from maya.api import OpenMaya


def alignLocatorsToMeshNormal():
    """
    该函数将选中的目标物体（例如 locators）的局部 Z 轴对齐到目标 mesh 的表面法线方向。

    使用步骤：
      1. 选择一组需要旋转对齐的物体（一般为 locator）并同时选择一个目标 mesh（注意：只应有一个 mesh）。
      2. 运行该函数，函数会自动：
         - 遍历选中物体，区分出 mesh 与需要对齐的物体；
         - 利用 closestPointOnMesh 节点计算每个物体在 mesh 上的最近点和法线；
         - 计算并设置每个物体的旋转，使其局部 Z 轴与 mesh 对应点的法线方向一致。

    注意事项：
      - 该函数假设待对齐物体的旋转中心（pivot）为其对齐参考点；
      - 如果选中多个 mesh，则只使用第一个检测到的 mesh，并会发出警告；
      - 运算中使用 Maya Python API2.0 进行旋转计算，确保数值稳定性。
    """
    # 获取当前选中物体列表
    selList = cmds.ls(selection=True, long=True)
    if not selList or len(selList) < 2:
        cmds.error("请选中至少两个物体：一个目标 mesh 和多个需要对齐的对象。")
        return

    targetMesh = None
    objsToAlign = []

    # 遍历选中物体，区分出 mesh 和其他对象
    for obj in selList:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
        isMesh = False
        for shp in shapes:
            if cmds.nodeType(shp) == "mesh":
                isMesh = True
                break
        if isMesh:
            if not targetMesh:
                targetMesh = obj
            else:
                cmds.warning("检测到多个 mesh，已使用第一个找到的 mesh: {0}".format(targetMesh))
        else:
            objsToAlign.append(obj)

    if not targetMesh:
        cmds.error("在选中的物体中未检测到有效的 mesh。")
        return

    if not objsToAlign:
        cmds.error("未检测到需要旋转对齐的对象。")
        return

    # 获取目标 mesh 的 shape 节点
    meshShapes = cmds.listRelatives(targetMesh, shapes=True, fullPath=True) or []
    meshShape = None
    for shp in meshShapes:
        if cmds.nodeType(shp) == "mesh":
            meshShape = shp
            break
    if not meshShape:
        cmds.error("目标 mesh 节点无效。")
        return

    # 创建一个临时的 closestPointOnMesh 节点并连接目标 mesh 的 outMesh 属性
    cpmNode = cmds.createNode("closestPointOnMesh")
    cmds.connectAttr(meshShape + ".outMesh", cpmNode + ".inMesh", force=True)

    def getRotationFromNormal( normalVec ):
        """
        将法线向量转换为从默认 Z 轴 (0, 0, 1) 旋转到该法线所需的欧拉角（单位：度）。
        """
        currZ = OpenMaya.MVector(0, 0, 1)  # 默认本地 Z 轴
        target = OpenMaya.MVector(normalVec[0], normalVec[1], normalVec[2])
        try:
            target.normalize()
        except:
            # 若向量无法归一化，则返回零旋转
            return (0, 0, 0)

        # 计算点积
        dotVal = currZ * target
        dotVal = max(min(dotVal, 1.0), -1.0)  # 限制在[-1,1]内

        # 当两向量平行或方向相同时，不需要旋转
        if math.isclose(dotVal, 1.0, abs_tol=1e-6):
            return (0, 0, 0)
        # 当两向量反向时，选择绕 X 轴旋转180度
        if math.isclose(dotVal, -1.0, abs_tol=1e-6):
            return (180, 0, 0)

        # 利用 acos 计算旋转角度
        angle = math.acos(dotVal)
        # 计算旋转轴（叉乘）
        axis = currZ ^ target  # 使用 ^ 运算符得到叉乘向量
        try:
            axis.normalize()
        except:
            axis = OpenMaya.MVector(1, 0, 0)

        # 构造四元数并转换为欧拉角
        quat = OpenMaya.MQuaternion(angle, axis)
        euler = quat.asEulerRotation()
        return (math.degrees(euler.x), math.degrees(euler.y), math.degrees(euler.z))

    # 针对每个待对齐对象
    for obj in objsToAlign:
        # 获取对象的世界坐标（这里以旋转中心为参考点）
        pos = cmds.xform(obj, q=True, ws=True, rp=True)
        # 将位置传入 closestPointOnMesh 节点
        cmds.setAttr(cpmNode + ".inPositionX", pos[0])
        cmds.setAttr(cpmNode + ".inPositionY", pos[1])
        cmds.setAttr(cpmNode + ".inPositionZ", pos[2])

        # 从节点获取计算出的法线（返回为三元组）
        normal = cmds.getAttr(cpmNode + ".normal")[0]
        # 计算对齐所需的欧拉旋转值
        rot = getRotationFromNormal(normal)
        # 将计算的旋转应用到对象（使用世界空间旋转）
        cmds.xform(obj, ws=True, rotation=rot)

    # 清理临时创建的节点
    cmds.delete(cpmNode)
    cmds.inViewMessage(amg='对齐完成！', pos='topCenter', fade=True)


# 运行函数，对选中的 locators 进行法线对齐
alignLocatorsToMeshNormal()
