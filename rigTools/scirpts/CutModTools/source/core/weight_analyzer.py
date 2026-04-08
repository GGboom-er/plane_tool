# -*- coding: utf-8 -*-
"""
weight_analyzer.py — 权重分析器 v1.1

从 skinCluster 读取权重数据，确定每个面（face）应归属哪个骨骼。
v1.1 新增：
    - 形态学边界平滑（消除锯齿状切分线）
    - 连通性修复（消除孤立面碎片）
    - 父骨骼优先策略（权重接近时归属父骨骼）
    - 面部区域排除（Head_M 子层级合并为一个整体）
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import logging
from collections import defaultdict, deque

from CutModTools.source.utils.maya_helpers import (
    get_skin_cluster,
    get_mesh_fn,
    get_skin_cluster_fn,
    get_influence_joints,
    get_dag_path,
    short_joint_name,
    get_hierarchy_joints,
    build_face_adjacency,
    get_joint_parent_map,
)

logger = logging.getLogger("CutMod")


class WeightAnalyzer(object):
    """
    权重分析器 v1.1 — 分析 skinCluster 权重并将面分组到对应骨骼。

    Args:
        mesh: 网格 transform 名称
        threshold: 权重忽略阈值（低于此值的影响忽略），默认 0.001
        exclude_hierarchy: 需要合并为一个整体的骨骼根节点名
                          （如 "Head_M"，其所有子层级骨骼的面会合并到该根骨骼）
        smooth_iterations: 边界平滑迭代次数，默认 3
        smooth_tolerance: 平滑容差 — 权重差低于此值时允许翻转归属，默认 0.15
        parent_priority: 是否启用父骨骼优先策略，默认 True
        parent_priority_tolerance: 父骨骼优先的容差，默认 0.08
    """

    def __init__(self, mesh, threshold=0.001, exclude_hierarchy=None,
                 smooth_iterations=3, smooth_tolerance=0.15,
                 parent_priority=True, parent_priority_tolerance=0.08):
        self.mesh = mesh
        self.threshold = threshold
        self.exclude_hierarchy = exclude_hierarchy
        self.smooth_iterations = smooth_iterations
        self.smooth_tolerance = smooth_tolerance
        self.parent_priority = parent_priority
        self.parent_priority_tolerance = parent_priority_tolerance

        # 验证输入
        if not cmds.objExists(mesh):
            raise ValueError("网格 '{}' 不存在".format(mesh))

        self.skin_cluster = get_skin_cluster(mesh)
        if not self.skin_cluster:
            raise ValueError("网格 '{}' 上未找到 skinCluster".format(mesh))

        self.influence_joints = get_influence_joints(self.skin_cluster)
        if not self.influence_joints:
            raise ValueError("skinCluster '{}' 无影响骨骼".format(
                self.skin_cluster))

        # 排除层级的骨骼集合
        self._excluded_joints = set()
        self._exclude_root_short = None
        if exclude_hierarchy and cmds.objExists(exclude_hierarchy):
            self._excluded_joints = get_hierarchy_joints(exclude_hierarchy)
            self._exclude_root_short = short_joint_name(exclude_hierarchy)

        # 缓存
        self._weights = None            # 全量权重数据
        self._face_map = None           # 面→骨骼映射结果
        self._face_weight_data = None   # 每个面的详细权重信息（用于平滑判断）
        self._adjacency = None          # 面邻接图
        self._parent_map = None         # 骨骼父级映射

    def analyze(self):
        """
        执行权重分析，返回骨骼→面ID映射。

        处理流程：
            1. 批量读取全部权重（OpenMaya 2.0）
            2. 初始面归属计算（权重求和取最大）
            3. 排除层级合并（Head_M 子骨骼面合并）
            4. 父骨骼优先（权重接近时偏向父骨骼）
            5. 形态学边界平滑（消除锯齿）
            6. 连通性修复（消除孤立碎片）

        Returns:
            dict: {骨骼名: [面ID列表]}
        """
        logger.info("CutMod: 开始分析 '{}' 的权重...".format(self.mesh))

        # 1. 读取全部权重
        self._read_all_weights()

        # 2. 初始面归属
        face_ownership, face_weight_data = self._compute_face_ownership()
        self._face_weight_data = face_weight_data

        # 3. 排除层级合并
        if self._excluded_joints and self._exclude_root_short:
            face_ownership = self._merge_excluded_hierarchy(face_ownership)

        # 4. 父骨骼优先
        if self.parent_priority:
            face_ownership = self._apply_parent_priority(
                face_ownership, face_weight_data)

        # 5. 形态学边界平滑
        if self.smooth_iterations > 0:
            self._adjacency = build_face_adjacency(self.mesh)
            face_ownership = self._smooth_boundaries(
                face_ownership, face_weight_data)

        # 6. 连通性修复
        if self._adjacency:
            face_ownership = self._fix_connectivity(face_ownership)

        # 转换为 face_map 格式
        self._face_map = defaultdict(list)
        for face_id, joint_name in face_ownership.items():
            self._face_map[joint_name].append(face_id)
        self._face_map = dict(self._face_map)

        total_faces = sum(len(v) for v in self._face_map.values())
        logger.info("CutMod: 权重分析完成 — {} 个面分配到 {} 个骨骼".format(
            total_faces, len(self._face_map)))

        return self._face_map

    def get_summary(self):
        """
        获取分析结果摘要（用于 UI 预览显示）。

        Returns:
            list[dict]: [{joint, face_count, percentage, is_skincluster}, ...]
        """
        if self._face_map is None:
            self.analyze()

        total = sum(len(v) for v in self._face_map.values())
        summary = []
        for joint, faces in sorted(self._face_map.items(),
                                    key=lambda x: -len(x[1])):
            is_sc = (self._exclude_root_short and
                     joint == self._exclude_root_short)
            summary.append({
                "joint": joint,
                "face_count": len(faces),
                "percentage": (len(faces) / float(total) * 100) if total else 0,
                "is_skincluster": is_sc
            })
        return summary

    def get_excluded_joints(self):
        """获取被排除（合并）的骨骼集合"""
        return self._excluded_joints

    def get_exclude_root(self):
        """获取排除层级的根骨骼短名"""
        return self._exclude_root_short

    # ================================================================
    # 内部方法
    # ================================================================

    def _read_all_weights(self):
        """
        使用 OpenMaya 2.0 批量读取 skinCluster 的全部权重。
        """
        skin_fn = get_skin_cluster_fn(self.skin_cluster)
        mesh_dag = get_dag_path(self.mesh)
        if mesh_dag.apiType() == om2.MFn.kTransform:
            mesh_dag.extendToShape()

        mesh_fn = om2.MFnMesh(mesh_dag)
        num_verts = mesh_fn.numVertices

        comp_fn = om2.MFnSingleIndexedComponent()
        vert_comp = comp_fn.create(om2.MFn.kMeshVertComponent)
        comp_fn.setCompleteData(num_verts)

        weights, num_influences = skin_fn.getWeights(mesh_dag, vert_comp)

        self._weights = {}
        for vtx_idx in range(num_verts):
            vtx_weights = []
            for inf_idx in range(num_influences):
                w = weights[vtx_idx * num_influences + inf_idx]
                if w > self.threshold:
                    vtx_weights.append((inf_idx, w))
            self._weights[vtx_idx] = vtx_weights

    def _compute_face_ownership(self):
        """
        初始面归属计算：面内顶点权重按骨骼求和，取最大者。

        Returns:
            (dict[int, str], dict[int, dict[str, float]]):
                face_ownership: {面ID: 骨骼短名}
                face_weight_data: {面ID: {骨骼短名: 归一化权重}}
        """
        mesh_fn = get_mesh_fn(self.mesh)
        num_faces = mesh_fn.numPolygons
        joint_names = self.influence_joints

        face_ownership = {}
        face_weight_data = {}

        for face_id in range(num_faces):
            face_verts = mesh_fn.getPolygonVertices(face_id)
            joint_weight_sum = defaultdict(float)

            for vtx_idx in face_verts:
                for inf_idx, w in self._weights.get(vtx_idx, []):
                    jname = short_joint_name(joint_names[inf_idx])
                    joint_weight_sum[jname] += w

            if not joint_weight_sum:
                best = short_joint_name(joint_names[0]) if joint_names else "unknown"
            else:
                best = max(joint_weight_sum, key=joint_weight_sum.get)

            face_ownership[face_id] = best

            # 归一化权重（用于后续平滑判断）
            total_w = sum(joint_weight_sum.values()) or 1.0
            face_weight_data[face_id] = {
                k: v / total_w for k, v in joint_weight_sum.items()
            }

        return face_ownership, face_weight_data

    def _merge_excluded_hierarchy(self, face_ownership):
        """
        将排除层级骨骼的面全部合并到根骨骼名下。

        例：Head_M 子层级所有骨骼(Jaw_M, Eye_L 等)的面 → 全部归为 "Head_M"

        Args:
            face_ownership: {面ID: 骨骼短名}

        Returns:
            dict: 合并后的 face_ownership
        """
        merged_count = 0
        for face_id, joint in face_ownership.items():
            if joint in self._excluded_joints:
                face_ownership[face_id] = self._exclude_root_short
                merged_count += 1

        if merged_count > 0:
            logger.info(
                "CutMod: 面部排除 — {} 个面合并到 '{}'".format(
                    merged_count, self._exclude_root_short))
        return face_ownership

    def _apply_parent_priority(self, face_ownership, face_weight_data):
        """
        父骨骼优先策略：当面上最大骨骼与其父骨骼权重差 < 容差时，
        将该面归属到父骨骼。

        效果：切分线向子骨骼侧偏移，父骨骼区域更完整平滑。

        Args:
            face_ownership: {面ID: 骨骼短名}
            face_weight_data: {面ID: {骨骼短名: 权重}}

        Returns:
            dict: 调整后的 face_ownership
        """
        if self._parent_map is None:
            self._parent_map = get_joint_parent_map(self.influence_joints)

        flipped = 0
        for face_id, current_joint in list(face_ownership.items()):
            parent_j = self._parent_map.get(current_joint)
            if not parent_j:
                continue

            weights = face_weight_data.get(face_id, {})
            w_current = weights.get(current_joint, 0)
            w_parent = weights.get(parent_j, 0)

            # 如果权重差小于容差，翻转到父骨骼
            if (w_current - w_parent) < self.parent_priority_tolerance:
                if w_parent > 0:
                    face_ownership[face_id] = parent_j
                    flipped += 1

        if flipped:
            logger.info(
                "CutMod: 父骨骼优先 — {} 个面翻转到父骨骼".format(flipped))
        return face_ownership

    def _smooth_boundaries(self, face_ownership, face_weight_data):
        """
        形态学边界平滑 — 消除锯齿状切分线。

        算法：
            循环 N 轮：
                对每个边界面（有邻面属于不同骨骼）：
                    统计邻面中各骨骼的数量
                    如果该面是邻面中的少数派（被包围）
                    且该面对两个骨骼的权重差 < 容差
                    → 翻转归属到多数派骨骼

        Args:
            face_ownership: {面ID: 骨骼短名}
            face_weight_data: {面ID: {骨骼短名: 权重}}

        Returns:
            dict: 平滑后的 face_ownership
        """
        adjacency = self._adjacency
        total_flipped = 0

        for iteration in range(self.smooth_iterations):
            changes = 0
            new_ownership = dict(face_ownership)

            for face_id, current_joint in face_ownership.items():
                neighbors = adjacency.get(face_id, [])
                if not neighbors:
                    continue

                # 统计邻面的骨骼归属
                neighbor_votes = defaultdict(int)
                for n_fid in neighbors:
                    n_joint = face_ownership.get(n_fid)
                    if n_joint:
                        neighbor_votes[n_joint] += 1

                if not neighbor_votes:
                    continue

                # 找出邻面中的多数派骨骼
                majority_joint = max(neighbor_votes, key=neighbor_votes.get)
                majority_count = neighbor_votes[majority_joint]
                current_count = neighbor_votes.get(current_joint, 0)

                # 如果当前骨骼不是多数派（被包围）
                if majority_joint != current_joint and majority_count > current_count:
                    # 检查权重差是否在容差范围内
                    weights = face_weight_data.get(face_id, {})
                    w_current = weights.get(current_joint, 0)
                    w_majority = weights.get(majority_joint, 0)

                    # 权重差小于容差 → 允许翻转
                    if (w_current - w_majority) < self.smooth_tolerance:
                        new_ownership[face_id] = majority_joint
                        changes += 1

            face_ownership = new_ownership
            total_flipped += changes

            if changes == 0:
                break

        if total_flipped:
            logger.info(
                "CutMod: 边界平滑 — {} 轮共翻转 {} 个面".format(
                    iteration + 1, total_flipped))
        return face_ownership

    def _fix_connectivity(self, face_ownership):
        """
        连通性修复 — 消除孤立面碎片。

        对每个骨骼区域做 BFS flood fill：
            1. 找出最大连通块
            2. 把小的孤立块重新归属到相邻的骨骼

        Args:
            face_ownership: {面ID: 骨骼短名}

        Returns:
            dict: 修复后的 face_ownership
        """
        adjacency = self._adjacency

        # 按骨骼分组
        joint_faces = defaultdict(set)
        for fid, jname in face_ownership.items():
            joint_faces[jname].add(fid)

        total_reassigned = 0

        for joint, faces in joint_faces.items():
            if len(faces) <= 1:
                continue

            # BFS 找所有连通分量
            visited = set()
            components = []

            for seed in faces:
                if seed in visited:
                    continue
                # BFS
                component = set()
                queue = deque([seed])
                while queue:
                    fid = queue.popleft()
                    if fid in visited:
                        continue
                    if fid not in faces:
                        continue
                    visited.add(fid)
                    component.add(fid)
                    for n_fid in adjacency.get(fid, []):
                        if n_fid not in visited and n_fid in faces:
                            queue.append(n_fid)
                if component:
                    components.append(component)

            if len(components) <= 1:
                continue

            # 保留最大连通块，重新分配较小块
            components.sort(key=len, reverse=True)
            for small_comp in components[1:]:
                for fid in small_comp:
                    # 找相邻的非本骨骼面中最常见的骨骼
                    neighbor_votes = defaultdict(int)
                    for n_fid in adjacency.get(fid, []):
                        n_joint = face_ownership.get(n_fid)
                        if n_joint and n_joint != joint:
                            neighbor_votes[n_joint] += 1

                    if neighbor_votes:
                        best_neighbor = max(neighbor_votes,
                                            key=neighbor_votes.get)
                        face_ownership[fid] = best_neighbor
                        total_reassigned += 1

        if total_reassigned:
            logger.info(
                "CutMod: 连通性修复 — {} 个孤立面已重新分配".format(
                    total_reassigned))
        return face_ownership
