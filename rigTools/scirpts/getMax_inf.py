#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: getMax_inf.py
@date: 2024/11/28 13:17
@desc: 
"""
import maya.api.OpenMaya as om
import maya.api.OpenMayaAnim as oma
import numpy as np
from maya import cmds


def get_skin_cluster( mesh ):
    """
    获取给定模型的 skinCluster
    """
    history = cmds.listHistory(mesh)
    skin_clusters = cmds.ls(history, type="skinCluster")
    if skin_clusters:
        return skin_clusters[0]
    return None


def get_influencing_points( mesh, max_influences, weight_threshold=0.00001 ):
    """
    获取模型中受骨骼影响超过 max_influences 的顶点
    """
    skin_cluster = get_skin_cluster(mesh)
    if not skin_cluster:
        cmds.error(f"模型 {mesh} 没有绑定的 skinCluster.")
        return []

    # 获取 skinCluster 对象
    sel_list = om.MSelectionList()
    sel_list.add(skin_cluster)
    skin_obj = sel_list.getDependNode(0)
    skin_fn = oma.MFnSkinCluster(skin_obj)

    # 获取模型的 DagPath
    mesh_sel = om.MSelectionList()
    mesh_sel.add(mesh)
    dag_path = mesh_sel.getDagPath(0)

    # 获取所有影响的骨骼数量
    influence_paths = skin_fn.influenceObjects()
    num_influences = len(influence_paths)

    # 获取所有顶点的权重
    vertex_count = cmds.polyEvaluate(mesh, vertex=True)
    weights, _ = skin_fn.getWeights(dag_path, om.MObject())  # 解包返回值，仅取权重数组

    # 检查权重长度并填充
    weights = list(weights)  # 转为可变列表
    expected_length = vertex_count * num_influences
    if len(weights) < expected_length:
        weights.extend([0.0] * (expected_length - len(weights)))
    elif len(weights) > expected_length:
        weights = weights[:expected_length]

    # 将权重转换为 NumPy 数组
    weights_array = np.array(weights).reshape((vertex_count, num_influences))

    # 计算每个顶点受影响的骨骼数量
    influence_counts = np.sum(weights_array > weight_threshold, axis=1)

    # 找出超过 max_influences 的顶点索引
    exceeded_indices = np.where(influence_counts > max_influences)[0]

    # 构建超过的顶点列表
    exceeded_points = [f"{mesh}.vtx[{i}]" for i in exceeded_indices]

    return exceeded_points


def main( max_influences, weight_threshold=0.00001 ):
    """
    主功能入口
    """
    # 获取选中的对象
    selection = cmds.ls(selection=True, dag=True, type="mesh")
    if not selection:
        cmds.error("请先选择一个模型.")
        return

    mesh = selection[0]
    exceeded_points = get_influencing_points(mesh, max_influences, weight_threshold)

    if not exceeded_points:
        cmds.confirmDialog(title="结果", message=f"没有顶点的骨骼影响数量超过 {max_influences}.")
    else:
        # 选择超出的点
        cmds.select(exceeded_points)
        cmds.confirmDialog(title="结果",
                           message=f"共找到 {len(exceeded_points)} 个顶点的骨骼影响数量超过 {max_influences}.\n已选择这些点.")


# 示例调用
main(max_influences=12)  # 设置骨骼最大影响数量为 12
