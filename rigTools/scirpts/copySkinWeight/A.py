#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: A.py
@date: 2025/1/11 13:31
@desc: 
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om
import numpy as np
from scipy.spatial import KDTree

# 获取顶点位置和法线
def get_mesh_vertices_and_normals(mesh_name):
    """
    获取网格的顶点位置和法线
    """
    mesh_fn = om.MFnMesh(om.MGlobal.getSelectionListByName(mesh_name).getDagPath(0))
    vertices = mesh_fn.getPoints(om.MSpace.kWorld)
    normals = mesh_fn.getVertexNormals(angleWeighted=True)
    return np.array([(v.x, v.y, v.z) for v in vertices]), np.array([(n.x, n.y, n.z) for n in normals])

# 获取最近顶点（基于位置和法线）
def get_closest_vertices(source_vertices, source_normals, target_position, target_normal, k=5):
    """
    找到源网格上距离目标位置和法线最近的 k 个顶点
    """
    # 计算位置距离
    pos_distances = np.linalg.norm(source_vertices - target_position, axis=1)
    # 计算法线相似度（点积）
    normal_similarities = np.dot(source_normals, target_normal)
    # 综合距离（位置距离越小越好，法线相似度越大越好）
    combined_distances = pos_distances - normal_similarities
    # 返回最近的 k 个顶点索引
    return np.argsort(combined_distances)[:k]

# 权重插值
def interpolate_weights(source_weights, distances, fit_factor):
    """
    根据距离和拟合程度对权重进行插值
    """
    # 计算权重插值系数（距离越小，权重越大）
    weights = 1.0 / (distances + 1e-6)  # 避免除零
    weights = np.power(weights, fit_factor)  # 根据拟合程度调整权重
    weights /= np.sum(weights)  # 归一化
    # 返回插值后的权重
    return np.sum(source_weights * weights[:, np.newaxis], axis=0)

# 权重修复（热扩散平滑）
def smooth_weights(weights, adjacency_list, smooth_factor, iterations=5):
    """
    对权重进行热扩散平滑
    """
    for _ in range(iterations):
        new_weights = weights.copy()
        for i in range(len(weights)):
            neighbors = adjacency_list[i]
            if neighbors:
                # 根据平滑程度调整权重
                new_weights[i] = (1 - smooth_factor) * weights[i] + smooth_factor * np.mean(weights[neighbors], axis=0)
        weights = new_weights
    return weights

# 获取顶点邻接表
def get_vertex_adjacency(mesh_name):
    """
    获取网格的顶点邻接表
    """
    adjacency = {}
    mesh_fn = om.MFnMesh(om.MGlobal.getSelectionListByName(mesh_name).getDagPath(0))
    num_vertices = mesh_fn.numVertices

    # 初始化邻接表
    for i in range(num_vertices):
        adjacency[i] = set()

    # 遍历所有面，获取顶点邻接关系
    num_faces = mesh_fn.numPolygons
    for face_id in range(num_faces):
        vertices = mesh_fn.getPolygonVertices(face_id)
        for i in range(len(vertices)):
            for j in range(i + 1, len(vertices)):
                adjacency[vertices[i]].add(vertices[j])
                adjacency[vertices[j]].add(vertices[i])

    # 将集合转换为列表
    for i in range(num_vertices):
        adjacency[i] = list(adjacency[i])

    return adjacency

# 权重转移函数
def transfer_skin_weights(source_mesh, target_mesh, fit_factor, smooth_factor):
    """
    将皮肤权重从源网格转移到目标网格
    """
    # 检查源网格和目标网格是否存在
    if not cmds.objExists(source_mesh) or not cmds.objExists(target_mesh):
        cmds.warning("源网格或目标网格不存在！")
        return

    # 获取源网格的皮肤簇
    skin_cluster = cmds.ls(cmds.listHistory(source_mesh), type="skinCluster")
    if not skin_cluster:
        cmds.warning("源网格没有皮肤簇！")
        return
    skin_cluster = skin_cluster[0]

    # 获取源网格的骨骼
    joints = cmds.skinCluster(skin_cluster, query=True, influence=True)
    if not joints:
        cmds.warning("源网格没有绑定骨骼！")
        return

    # 创建目标网格的皮肤簇
    target_skin_cluster = cmds.skinCluster(joints, target_mesh, toSelectedBones=True, normalizeWeights=1)[0]

    # 获取源网格和目标网格的顶点位置和法线
    source_vertices, source_normals = get_mesh_vertices_and_normals(source_mesh)
    target_vertices, target_normals = get_mesh_vertices_and_normals(target_mesh)

    # 构建源网格的 KD-Tree
    source_kdtree = KDTree(source_vertices)

    # 获取目标网格的顶点邻接表
    adjacency = get_vertex_adjacency(target_mesh)

    # 遍历目标网格的顶点
    target_weights = []
    for i, (pos, normal) in enumerate(zip(target_vertices, target_normals)):
        # 找到源网格上最近的 k 个顶点
        closest_indices = get_closest_vertices(source_vertices, source_normals, pos, normal, k=5)
        closest_vtx = [f"{source_mesh}.vtx[{idx}]" for idx in closest_indices]
        # 获取源网格顶点的权重
        weights = [cmds.skinPercent(skin_cluster, vtx, query=True, value=True) for vtx in closest_vtx]
        # 计算插值权重
        distances = np.linalg.norm(source_vertices[closest_indices] - pos, axis=1)
        interpolated_weights = interpolate_weights(np.array(weights), distances, fit_factor)
        target_weights.append(interpolated_weights)

    # 对权重进行热扩散平滑
    target_weights = smooth_weights(np.array(target_weights), adjacency, smooth_factor)

    # 设置目标网格顶点的权重
    for i, weights in enumerate(target_weights):
        vtx = f"{target_mesh}.vtx[{i}]"
        cmds.skinPercent(target_skin_cluster, vtx, transformValue=zip(joints, weights))

    # 提示完成
    cmds.inViewMessage(amg="皮肤权重转移完成！", pos="midCenter", fade=True)

# UI 界面
def create_ui():
    """
    创建 UI 界面
    """
    window_name = "SkinWeightTransferUI"
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    # 创建窗口
    cmds.window(window_name, title="皮肤权重转移工具", widthHeight=(400, 200))
    cmds.columnLayout(adjustableColumn=True)

    # 源模型选择
    cmds.text(label="选择源模型：")
    cmds.textField("source_mesh_field", editable=False)
    cmds.button(label="选择源模型", command=lambda *args: update_source_mesh_field())

    # 目标模型选择
    cmds.text(label="选择目标模型：")
    cmds.textScrollList("target_mesh_list", allowMultiSelection=True)
    cmds.button(label="选择目标模型", command=lambda *args: update_target_mesh_list())

    # 拟合程度滑条
    cmds.text(label="拟合程度（越高越接近源模型）：")
    cmds.floatSliderGrp("fit_factor_slider", min=0.1, max=10.0, value=1.0, step=0.1)

    # 平滑程度滑条
    cmds.text(label="平滑程度（越高越均匀）：")
    cmds.floatSliderGrp("smooth_factor_slider", min=0.0, max=1.0, value=0.5, step=0.1)

    # 执行按钮
    cmds.button(label="转移权重", command=lambda *args: run_transfer())

    cmds.showWindow()

# 更新源模型字段
def update_source_mesh_field():
    """
    更新源模型字段
    """
    selection = cmds.ls(selection=True, type="transform")
    if selection:
        cmds.textField("source_mesh_field", edit=True, text=selection[0])

# 更新目标模型列表
def update_target_mesh_list():
    """
    更新目标模型列表
    """
    selection = cmds.ls(selection=True, type="transform")
    if selection:
        for item in selection:
            cmds.textScrollList("target_mesh_list", edit=True, append=item)

# 执行权重转移
def run_transfer():
    """
    执行权重转移
    """
    source_mesh = cmds.textField("source_mesh_field", query=True, text=True)
    target_meshes = cmds.textScrollList("target_mesh_list", query=True, allItems=True)
    fit_factor = cmds.floatSliderGrp("fit_factor_slider", query=True, value=True)
    smooth_factor = cmds.floatSliderGrp("smooth_factor_slider", query=True, value=True)

    if not source_mesh:
        cmds.warning("请选择源模型！")
        return
    if not target_meshes:
        cmds.warning("请选择目标模型！")
        return

    for target_mesh in target_meshes:
        transfer_skin_weights(source_mesh, target_mesh, fit_factor, smooth_factor)

    # 提示完成
    cmds.inViewMessage(amg="权重转移完成！", pos="midCenter", fade=True)

# 运行 UI
create_ui()