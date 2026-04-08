# -*- coding: utf-8 -*-
"""
maya_helpers.py — Maya 通用辅助函数

提供与 Maya 交互的底层工具函数，供所有模块复用。
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import maya.api.OpenMayaAnim as oma2
import logging

logger = logging.getLogger("CutMod")


def get_skin_cluster(mesh):
    """
    获取指定网格的 skinCluster 节点名。

    Args:
        mesh: 网格 transform 节点名

    Returns:
        skinCluster 节点名，找不到则返回 None
    """
    shapes = cmds.listRelatives(mesh, shapes=True, noIntermediate=True, fullPath=True) or []
    for shape in shapes:
        history = cmds.listHistory(shape, pruneDagObjects=True, interestLevel=2) or []
        for node in history:
            if cmds.nodeType(node) == "skinCluster":
                return node
    return None


def get_mesh_fn(mesh):
    """
    获取 MFnMesh 函数集。

    Args:
        mesh: 网格 transform 或 shape 节点名

    Returns:
        om2.MFnMesh 实例
    """
    sel = om2.MSelectionList()
    sel.add(mesh)
    dag_path = sel.getDagPath(0)
    # 如果是 transform，获取其 shape
    if dag_path.apiType() == om2.MFn.kTransform:
        dag_path.extendToShape()
    return om2.MFnMesh(dag_path)


def get_skin_cluster_fn(skin_cluster_name):
    """
    获取 MFnSkinCluster 函数集。

    Args:
        skin_cluster_name: skinCluster 节点名

    Returns:
        (om2.MFnSkinCluster, om2.MDagPath) 元组
    """
    sel = om2.MSelectionList()
    sel.add(skin_cluster_name)
    skin_obj = sel.getDependNode(0)
    skin_fn = oma2.MFnSkinCluster(skin_obj)
    return skin_fn


def get_influence_joints(skin_cluster_name):
    """
    获取 skinCluster 的所有影响骨骼。

    Args:
        skin_cluster_name: skinCluster 节点名

    Returns:
        list[str]: 影响骨骼名称列表（按 influence index 排序）
    """
    return cmds.skinCluster(skin_cluster_name, q=True, inf=True) or []


def get_dag_path(node_name):
    """
    获取节点的 MDagPath。

    Args:
        node_name: 节点名

    Returns:
        om2.MDagPath
    """
    sel = om2.MSelectionList()
    sel.add(node_name)
    return sel.getDagPath(0)


def get_world_matrix(node_name):
    """
    获取节点的世界矩阵（4x4）。

    Args:
        node_name: 节点名

    Returns:
        list[float]: 16 个浮点数的矩阵
    """
    return cmds.getAttr("{}.worldMatrix[0]".format(node_name))


def get_world_inverse_matrix(node_name):
    """
    获取节点的世界逆矩阵。

    Args:
        node_name: 节点名

    Returns:
        list[float]: 16 个浮点数的逆矩阵
    """
    return cmds.getAttr("{}.worldInverseMatrix[0]".format(node_name))


def ensure_group(group_name, parent=None):
    """
    确保指定名称的 transform 组存在于正确的父级下。

    如果同名节点已存在但不在目标父级下（命名冲突），
    会自动添加后缀避免与绑定系统已有节点冲突。

    Args:
        group_name: 组名
        parent: 父节点名，None 则在世界级

    Returns:
        str: 组节点名
    """
    if cmds.objExists(group_name):
        # 检查现有节点是否在正确的父级下
        if parent:
            existing_parents = cmds.listRelatives(
                group_name, parent=True, fullPath=False) or []
            if existing_parents and existing_parents[0] == parent:
                # 已在正确父级下，直接返回
                return group_name
            else:
                # 同名节点在其他位置（可能是绑定系统的节点）
                # 不要动它！创建新的带前缀的组
                safe_name = "CutMod_{}".format(group_name)
                if cmds.objExists(safe_name):
                    safe_parents = cmds.listRelatives(
                        safe_name, parent=True, fullPath=False) or []
                    if safe_parents and safe_parents[0] == parent:
                        return safe_name
                grp = cmds.createNode(
                    "transform", name=safe_name, parent=parent)
                logger.debug(
                    "CutMod: '{}' 已存在于其他层级，"
                    "使用 '{}' 避免冲突".format(group_name, safe_name))
                return grp
        else:
            return group_name

    if parent and cmds.objExists(parent):
        grp = cmds.createNode("transform", name=group_name, parent=parent)
    else:
        grp = cmds.createNode("transform", name=group_name)
    return grp


def ensure_display_layer(layer_name, color=29, display_type=2):
    """
    确保指定的 displayLayer 存在。

    Args:
        layer_name: 图层名
        color: 图层颜色索引（默认 29 = 浅蓝色）
        display_type: 0=Normal, 1=Template, 2=Reference
    """
    if not cmds.objExists(layer_name):
        cmds.createDisplayLayer(name=layer_name, empty=True)
    cmds.setAttr("{}.color".format(layer_name), color)
    cmds.setAttr("{}.displayType".format(layer_name), display_type)
    return layer_name


def short_joint_name(joint_full_name):
    """
    获取骨骼的短名称（去除命名空间和路径）。

    Args:
        joint_full_name: 骨骼全路径名

    Returns:
        str: 短名称
    """
    name = joint_full_name.split("|")[-1]
    name = name.split(":")[-1]
    return name


def safe_delete(nodes):
    """
    安全删除节点，忽略不存在的节点。

    Args:
        nodes: 节点名或列表
    """
    if isinstance(nodes, str):
        nodes = [nodes]
    existing = [n for n in nodes if cmds.objExists(n)]
    if existing:
        cmds.delete(existing)


def get_hierarchy_joints(root_joint):
    """
    获取指定骨骼及其所有子层级骨骼的短名称集合。

    Args:
        root_joint: 根骨骼名（如 "Head_M"）

    Returns:
        set[str]: 包含根骨骼自身及所有后代 joint 的短名称集合
    """
    if not cmds.objExists(root_joint):
        return set()

    descendants = cmds.listRelatives(
        root_joint, allDescendents=True, type="joint",
        fullPath=False) or []
    result = {short_joint_name(root_joint)}
    for jnt in descendants:
        result.add(short_joint_name(jnt))
    return result


def build_face_adjacency(mesh):
    """
    构建面拓扑邻接图 — 共享边的面互为邻面。

    使用 OpenMaya 2.0 的 MItMeshPolygon 迭代器获取邻接信息，
    比 cmds 逐面查询快数十倍。

    Args:
        mesh: 网格 transform 名

    Returns:
        dict[int, list[int]]: {面ID: [邻面ID列表]}
    """
    sel = om2.MSelectionList()
    sel.add(mesh)
    dag_path = sel.getDagPath(0)
    if dag_path.apiType() == om2.MFn.kTransform:
        dag_path.extendToShape()

    mesh_fn = om2.MFnMesh(dag_path)
    num_faces = mesh_fn.numPolygons

    # 使用 MItMeshPolygon 迭代器获取每个面的边
    face_iter = om2.MItMeshPolygon(dag_path)
    edge_to_faces = {}

    while not face_iter.isDone():
        face_id = face_iter.index()
        face_edges = face_iter.getEdges()
        for edge_id in face_edges:
            if edge_id not in edge_to_faces:
                edge_to_faces[edge_id] = []
            edge_to_faces[edge_id].append(face_id)
        face_iter.next()

    # 从 edge→faces 推导 face→neighbors
    adjacency = {fid: [] for fid in range(num_faces)}
    for edge_id, faces in edge_to_faces.items():
        if len(faces) == 2:
            f_a, f_b = faces
            adjacency[f_a].append(f_b)
            adjacency[f_b].append(f_a)

    return adjacency


def get_joint_parent_map(joint_names):
    """
    构建骨骼名 → 父骨骼名的映射字典。

    Args:
        joint_names: 骨骼名列表

    Returns:
        dict[str, str|None]: {骨骼短名: 父骨骼短名 或 None}
    """
    name_set = set(short_joint_name(j) for j in joint_names)
    parent_map = {}
    for jnt in joint_names:
        short = short_joint_name(jnt)
        parents = cmds.listRelatives(jnt, parent=True, type="joint") or []
        if parents:
            p_short = short_joint_name(parents[0])
            parent_map[short] = p_short if p_short in name_set else None
        else:
            parent_map[short] = None
    return parent_map
