# -*- coding: utf-8 -*-
"""
mesh_cutter.py — 几何切分器

根据权重分析器产出的骨骼→面映射，将原始网格切分为多个子网格。
每个子网格包含归属于同一骨骼的所有面。
操作在副本上执行，不修改原始网格。
"""

import maya.cmds as cmds
import logging

from CutModTools.source.utils.maya_helpers import (
    ensure_group,
    ensure_display_layer,
    safe_delete,
)

logger = logging.getLogger("CutMod")

# 切分组名称
CUTMOD_GROUP = "CutModGeometry"
# 显示图层名称
CUTMOD_LAYER = "CutMod"


class CutMeshResult(object):
    """单个切分结果"""

    def __init__(self, mesh_name, joint_name, face_ids, face_count,
                 is_skincluster=False, source_mesh=None):
        self.mesh_name = mesh_name          # 切分后的网格名
        self.joint_name = joint_name        # 归属骨骼名
        self.face_ids = face_ids            # 原始面 ID 列表
        self.face_count = face_count        # 面数量
        self.is_skincluster = is_skincluster  # 是否使用 skinCluster 绑定
        self.source_mesh = source_mesh      # 来源原始网格名

    def __repr__(self):
        mode_tag = " [skinCluster]" if self.is_skincluster else ""
        return "CutMeshResult('{}' -> '{}', {} faces{})".format(
            self.mesh_name, self.joint_name, self.face_count, mode_tag)


class MeshCutter(object):
    """
    几何切分器 — 根据骨骼-面映射关系切分几何体。

    工作流:
        1. 复制原始网格
        2. 对每个骨骼的面集合，从副本中提取为独立子网格
        3. 将子网格组织到 CutModGeometry 组下
        4. 清理中间数据

    Args:
        mesh: 原始网格 transform 名称
        face_map: 权重分析器产出的 {骨骼名: [面ID列表]} 映射
        parent_group: 子网格的父组名，默认 "CutModGeometry"
        keep_original: 是否保留原始网格（隐藏），默认 True
        enable_cap: 是否对切分后的子网格封口，默认 True
        skincluster_joint: 需要保留 skinCluster 绑定的骨骼名（如 Head_M），
                          该骨骼的子网格不做矩阵/约束绑定
    """

    def __init__(self, mesh, face_map, parent_group=None,
                 keep_original=True, enable_cap=True,
                 skincluster_joint=None):
        self.mesh = mesh
        self.face_map = face_map
        self.parent_group = parent_group or CUTMOD_GROUP
        self.keep_original = keep_original
        self.enable_cap = enable_cap
        self.skincluster_joint = skincluster_joint

        if not cmds.objExists(mesh):
            raise ValueError("网格 '{}' 不存在".format(mesh))

    def execute(self):
        """
        执行切分操作。

        Returns:
            list[CutMeshResult]: 切分结果列表
        """
        logger.info("CutMod: 开始切分 '{}'...".format(self.mesh))

        # 1. 确保输出组和显示图层存在
        self._setup_output()

        # 2. 采集原始网格的 border 顶点位置（用于智能封口）
        original_border_positions = self._collect_border_positions(self.mesh)
        if original_border_positions:
            logger.debug(
                "CutMod: 原始网格有 {} 个 border 顶点"
                "（片状/开放模型）".format(len(original_border_positions)))

        # 3. 复制原始网格
        work_copy = self._duplicate_mesh()

        # 4. 执行切分
        results = self._split_mesh(work_copy, original_border_positions)

        # 5. 处理原始网格
        self._handle_original()

        # 6. 清理工作副本
        safe_delete(work_copy)

        logger.info("CutMod: 切分完成 — 产生 {} 个子网格".format(len(results)))
        return results

    # ---- 内部方法 ----

    def _setup_output(self):
        """设置输出组和显示图层"""
        # 查找 Geometry 组作为父级
        geometry_parent = None
        if cmds.objExists("Geometry"):
            geometry_parent = "Geometry"

        ensure_group(self.parent_group, parent=geometry_parent)
        ensure_display_layer(CUTMOD_LAYER, color=18, display_type=2)

    def _duplicate_mesh(self):
        """
        复制原始网格用于切分（不修改原始）。

        Returns:
            str: 副本名称
        """
        copy_name = "{}_CutModWork".format(self.mesh)

        # 复制几何体
        dup = cmds.duplicate(self.mesh, name=copy_name,
                             returnRootsOnly=True)[0]

        # 删除中间 shape（intermediate objects）
        shapes = cmds.listRelatives(dup, shapes=True, fullPath=True) or []
        for shape in shapes:
            if cmds.getAttr("{}.intermediateObject".format(shape)):
                cmds.delete(shape)

        return dup

    def _split_mesh(self, work_copy, original_border_positions=None):
        """
        从工作副本中按骨骼提取子网格。

        Args:
            work_copy: 工作副本网格名
            original_border_positions: 原始网格的 border 顶点位置集合

        Returns:
            list[CutMeshResult]: 切分结果列表
        """
        results = []
        total_joints = len(self.face_map)

        for idx, (joint_name, face_ids) in enumerate(
                sorted(self.face_map.items())):
            if not face_ids:
                continue

            # 命名规范：原始网格名_骨骼短名_CutMod
            cut_name = "{}_{}_CutMod".format(self.mesh, joint_name)
            # 清理可能已存在的同名节点
            safe_delete(cut_name)

            logger.debug(
                "CutMod: [{}/{}] 提取 '{}' ({} 面)".format(
                    idx + 1, total_joints, joint_name, len(face_ids)))

            # 复制工作副本
            sub_mesh = cmds.duplicate(
                work_copy, name=cut_name, returnRootsOnly=True)[0]

            # 删除中间 shape
            shapes = cmds.listRelatives(
                sub_mesh, shapes=True, fullPath=True) or []
            for shape in shapes:
                if cmds.getAttr("{}.intermediateObject".format(shape)):
                    cmds.delete(shape)

            # 获取总面数
            total_faces = cmds.polyEvaluate(sub_mesh, face=True)

            # 计算需要删除的面（此骨骼不拥有的面）
            all_face_ids = set(range(total_faces))
            keep_faces = set(face_ids)
            delete_faces = all_face_ids - keep_faces

            if delete_faces:
                # 构建面选择列表（使用连续范围优化）
                face_ranges = self._compress_face_ids(
                    sorted(delete_faces), sub_mesh)
                cmds.select(face_ranges, replace=True)
                cmds.delete()

            # 清理历史 + 居中 pivot
            cmds.select(sub_mesh)
            cmds.delete(constructionHistory=True)
            cmds.xform(sub_mesh, centerPivots=True)

            # 封口（智能模式：只封切割产生的新边界，不封原始开放边）
            if self.enable_cap:
                self._cap_open_borders(
                    sub_mesh, original_border_positions)

            # 移到输出组下
            cmds.parent(sub_mesh, self.parent_group)

            # 加入 Display Layer
            cmds.editDisplayLayerMembers(CUTMOD_LAYER, sub_mesh,
                                         noRecurse=True)

            # 判断是否为面部 skinCluster 子网格
            is_sc = (self.skincluster_joint and
                     joint_name == self.skincluster_joint)

            result = CutMeshResult(
                mesh_name=sub_mesh,
                joint_name=joint_name,
                face_ids=face_ids,
                face_count=len(face_ids),
                is_skincluster=is_sc,
                source_mesh=self.mesh
            )
            results.append(result)

        return results

    def _handle_original(self):
        """处理原始网格——隐藏或删除"""
        if self.keep_original:
            cmds.setAttr("{}.visibility".format(self.mesh), 0)
            logger.info(
                "CutMod: 原始网格 '{}' 已隐藏（保留用于恢复）".format(
                    self.mesh))
        else:
            logger.info("CutMod: 原始网格 '{}' 已保留".format(self.mesh))

    @staticmethod
    def _compress_face_ids(face_ids, mesh_name):
        """
        将面 ID 列表压缩为 Maya 面选择字符串（连续范围合并）。

        例: [0,1,2,5,6,10] → ["mesh.f[0:2]", "mesh.f[5:6]", "mesh.f[10]"]

        Args:
            face_ids: 排序过的面 ID 列表
            mesh_name: 网格名

        Returns:
            list[str]: Maya 面选择字符串列表
        """
        if not face_ids:
            return []

        ranges = []
        start = face_ids[0]
        end = face_ids[0]

        for fid in face_ids[1:]:
            if fid == end + 1:
                end = fid
            else:
                ranges.append((start, end))
                start = fid
                end = fid
        ranges.append((start, end))

        result = []
        for s, e in ranges:
            if s == e:
                result.append("{}.f[{}]".format(mesh_name, s))
            else:
                result.append("{}.f[{}:{}]".format(mesh_name, s, e))
        return result

    @staticmethod
    def _collect_border_positions(mesh, tolerance=0.0001):
        """
        采集网格的所有 border 顶点世界位置。

        Border 顶点 = 位于开放边界上的顶点（片状/非封闭模型的边缘）。
        封口时用来区分“原始就有的开放边”和“切割产生的新边”。

        Args:
            mesh: 网格 transform 名
            tolerance: 坐标量化精度（用于哈希）

        Returns:
            set[tuple]: 量化后的 (x,y,z) 元组集合，空集合表示模型完全封闭
        """
        # 获取 border 边的顶点
        border_verts = set()
        num_edges = cmds.polyEvaluate(mesh, edge=True)
        if not num_edges:
            return border_verts

        # 选择所有 border edges
        cmds.select("{}.e[0:{}]".format(mesh, num_edges - 1), replace=True)
        cmds.polySelectConstraint(
            mode=2, type=0x8000, where=1)  # where=1 = border
        border_edges = cmds.ls(sl=True, flatten=True) or []
        cmds.polySelectConstraint(disable=True)
        cmds.select(clear=True)

        if not border_edges:
            return border_verts

        # 获取 border 边的顶点位置
        cmds.select(border_edges, replace=True)
        cmds.ConvertSelectionToVertices()
        border_vert_list = cmds.ls(sl=True, flatten=True) or []
        cmds.select(clear=True)

        inv_tol = 1.0 / tolerance
        for vtx in border_vert_list:
            pos = cmds.pointPosition(vtx, world=True)
            # 量化坐标以便哈希查找
            key = (
                round(pos[0] * inv_tol),
                round(pos[1] * inv_tol),
                round(pos[2] * inv_tol)
            )
            border_verts.add(key)

        return border_verts

    def _cap_open_borders(self, mesh, original_border_positions=None):
        """
        智能封口 — 只封切割产生的新边界，不封原始已有的开放边。

        判断逻辑：
            对每个 border loop，检查其顶点是否在原始网格的 border 中。
            - 如果大部分顶点都是原始 border → 这是片状模型的原始边缘，不封
            - 如果大部分顶点不是原始 border → 这是切割产生的新缺口，封

        Args:
            mesh: 子网格名
            original_border_positions: 原始网格的 border 顶点位置集合
        """
        # 获取当前子网格的所有 border edges
        num_edges = cmds.polyEvaluate(mesh, edge=True)
        if not num_edges:
            return

        cmds.select("{}.e[0:{}]".format(mesh, num_edges - 1), replace=True)
        cmds.polySelectConstraint(mode=2, type=0x8000, where=1)
        border_edges = cmds.ls(sl=True, flatten=True) or []
        cmds.polySelectConstraint(disable=True)
        cmds.select(clear=True)

        if not border_edges:
            return

        # 如果原始网格没有 border（完全封闭），所有 border 都是新的 → 全部封
        if not original_border_positions:
            self._do_cap(mesh, border_edges)
            return

        # 分离新边界和原始边界
        tolerance = 0.0001
        inv_tol = 1.0 / tolerance
        new_border_edges = []
        old_border_edges = []

        for edge in border_edges:
            # 获取边的顶点位置
            cmds.select(edge, replace=True)
            cmds.ConvertSelectionToVertices()
            verts = cmds.ls(sl=True, flatten=True) or []
            cmds.select(clear=True)

            is_original = True
            for vtx in verts:
                pos = cmds.pointPosition(vtx, world=True)
                key = (
                    round(pos[0] * inv_tol),
                    round(pos[1] * inv_tol),
                    round(pos[2] * inv_tol)
                )
                if key not in original_border_positions:
                    is_original = False
                    break

            if is_original:
                old_border_edges.append(edge)
            else:
                new_border_edges.append(edge)

        if old_border_edges:
            logger.debug(
                "CutMod: '{}' 跳过 {} 条原始开放边"
                "（片状模型）".format(mesh, len(old_border_edges)))

        if not new_border_edges:
            logger.debug(
                "CutMod: '{}' 无新产生的 border，跳过封口".format(mesh))
            return

        # 只封新产生的边界
        self._do_cap(mesh, new_border_edges)

    def _do_cap(self, mesh, border_edges):
        """
        执行实际封口操作。

        策略：选中指定的 border edges，用 Fill Hole 封口，
        封口面分配 lambert1 材质。

        Args:
            mesh: 子网格名
            border_edges: 要封口的 border edge 列表
        """
        face_count_before = cmds.polyEvaluate(mesh, face=True)

        try:
            # 选中需要封口的 border edges
            cmds.select(border_edges, replace=True)
            # 用 polyCloseBorder 封口（它会封闭所有包含所选 border 边的开放环）
            cmds.polyCloseBorder(constructionHistory=False)
            cmds.select(clear=True)

            # 获取新增的封口面
            face_count_after = cmds.polyEvaluate(mesh, face=True)
            new_face_count = face_count_after - face_count_before

            if new_face_count > 0:
                cap_faces = [
                    "{}.f[{}]".format(mesh, i)
                    for i in range(face_count_before, face_count_after)
                ]

                # 分配 lambert1 材质
                if cmds.objExists("lambert1"):
                    sg = cmds.listConnections(
                        "lambert1.outColor", type="shadingEngine") or []
                    if sg:
                        cmds.sets(cap_faces, edit=True,
                                  forceElement=sg[0])

                logger.debug(
                    "CutMod: '{}' 封口完成 ({} 个封口面)".format(
                        mesh, new_face_count))

        except Exception as e:
            logger.debug(
                "CutMod: '{}' 封口时出现异常: {} (非致命)".format(mesh, e))
            cmds.select(clear=True)


def delete_cutmod():
    """
    删除所有 CutMod 产生的节点，恢复原始状态。
    """
    # 删除显示图层成员
    if cmds.objExists(CUTMOD_LAYER):
        members = cmds.editDisplayLayerMembers(
            CUTMOD_LAYER, query=True) or []
        safe_delete(members)
        cmds.delete(CUTMOD_LAYER)

    # 删除几何体组
    safe_delete(CUTMOD_GROUP)

    # 恢复原始网格可见性
    # 查找所有 visibility=0 的可能原始网格
    all_transforms = cmds.ls(type="transform") or []
    for t in all_transforms:
        if cmds.objExists("{}.cutModOriginal".format(t)):
            cmds.setAttr("{}.visibility".format(t), 1)

    logger.info("CutMod: 所有切分数据已清除")
