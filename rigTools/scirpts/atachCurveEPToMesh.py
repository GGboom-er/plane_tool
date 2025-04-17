#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: atachCurveEPToMesh.py
@date: 2025/4/10 14:00
@desc: 
"""
import maya.cmds as cmds
import maya.OpenMaya as om

# -------------------------
# 1. 获取选中对象列表
# -------------------------
sel = cmds.ls(sl=True, long=True)
if not sel or len(sel) < 2:
    cmds.warning("请先选择至少一条曲线（EP状态）和一个多边形网格！")
    raise Exception("选择对象不足")

mesh = None
curves = []

# -------------------------
# 2. 根据子节点类型区分网格与曲线
# -------------------------
for obj in sel:
    shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
    for shape in shapes:
        nodeType = cmds.nodeType(shape)
        if nodeType == "mesh":
            mesh = obj  # 记录网格所在的变换节点
        elif nodeType == "nurbsCurve":
            if obj not in curves:
                curves.append(obj)

if not mesh:
    cmds.error("未检测到多边形网格！")

# -------------------------
# 3. 获取网格形状节点并构造 MFnMesh 对象
# -------------------------
meshShapes = cmds.listRelatives(mesh, shapes=True, fullPath=True) or []
if not meshShapes:
    cmds.error("无法获取网格 {} 的形状节点！".format(mesh))
meshShape = meshShapes[0]  # 使用第一个形状节点

selList = om.MSelectionList()
try:
    selList.add(meshShape)
except Exception as e:
    cmds.error("添加网格形状到 API 选择列表时出错：{}".format(e))

try:
    meshDag = om.MDagPath()
    selList.getDagPath(0, meshDag)
except Exception as e:
    cmds.error("获取网格形状的 DAG 路径时出错：{}".format(e))

try:
    meshFn = om.MFnMesh(meshDag)
except Exception as e:
    cmds.error("构造 MFnMesh 时出错：{}".format(e))

# 获取网格的转换矩阵与逆矩阵：
# worldToObjMat：将世界坐标转换到网格对象空间；
# worldMatrix：将网格对象空间坐标转换回世界坐标。
worldToObjMat = meshDag.inclusiveMatrixInverse()
worldMatrix = meshDag.inclusiveMatrix()

# -------------------------
# 4. 构造 MMeshIntersector 对象
# -------------------------
intersector = om.MMeshIntersector()
try:
    intersector.create(meshDag.node(), worldToObjMat)
except Exception as e:
    cmds.error("创建 MMeshIntersector 失败：{}".format(e))

# -------------------------
# 5. 遍历所有曲线的编辑点，移动到网格上最近的点位置
# -------------------------
for curve in curves:
    # 查询曲线的编辑点（ep组件）
    epList = cmds.ls("{}.ep[*]".format(curve), fl=True)
    if not epList:
        cmds.warning("曲线 {} 没有检测到编辑点(ep)。".format(curve))
        continue

    for ep in epList:
        # 获取当前编辑点的世界坐标 [x, y, z]
        ep_world = cmds.pointPosition(ep, world=True)
        # 这里使用参数解包构造MPoint（注意，传入3个数值即可，默认为w=1.0）
        point_world = om.MPoint(*ep_world)
        # 转换至网格对象空间
        point_obj = point_world * worldToObjMat

        # 通过 MMeshIntersector 查询最近点，结果存于 MPointOnMesh 对象中
        pointOnMesh = om.MPointOnMesh()
        intersector.getClosestPoint(point_obj, pointOnMesh)

        # 从 MPointOnMesh 中提取最近点（得到的是 MFloatPoint 类型）
        closestPoint_float = pointOnMesh.getPoint()
        # 将 MFloatPoint 转换为 MPoint（确保支持矩阵乘法）
        closestPoint = om.MPoint(closestPoint_float.x, closestPoint_float.y, closestPoint_float.z, closestPoint_float.w)
        # 将最近点从网格对象空间转换为世界空间
        closestPoint_world = closestPoint * worldMatrix

        # 将曲线编辑点移动到计算得到的最近网格点位置（使用绝对世界坐标）
        cmds.move(closestPoint_world.x, closestPoint_world.y, closestPoint_world.z, ep, a=True, ws=True)
        print("编辑点 {} 被移动到新位置：{}".format(ep, closestPoint_world))
