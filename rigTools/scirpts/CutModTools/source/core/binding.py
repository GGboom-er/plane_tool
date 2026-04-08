# -*- coding: utf-8 -*-
"""
binding.py — 绑定器 v1.2

将切分后的子网格绑定到对应骨骼。

关键设计 v1.2：
- 同一骨骼的多个子网格（来自多个源网格）共享同一个 transform 组
- 矩阵节点只控制 transform 组，不控制每个子网格
- 大幅减少节点数量，提升求值效率

层级结构：
    CutModGeometry/
    ├── Spine1_M_grp                ← multMatrix → OPM 控制这个组
    │    ├── bodyA_Spine1_M_CutMod  ← 直接放在组内，无需额外矩阵
    │    └── armorB_Spine1_M_CutMod
    ├── Head_M_grp                  ← skinCluster 子网格直接绑自身
    │    └── bodyA_Head_M_CutMod
    ...
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2
import logging
from collections import defaultdict

from CutModTools.source.utils.maya_helpers import (
    get_world_matrix,
    get_world_inverse_matrix,
    get_skin_cluster,
    get_influence_joints,
    ensure_group,
)

logger = logging.getLogger("CutMod")

CUTMOD_GROUP = "CutModGeometry"


class Binder(object):
    """
    绑定器 v1.2 — 按骨骼分组绑定，每个骨骼只创建一个矩阵节点。

    Args:
        cut_results: MeshCutter 产出的 CutMeshResult 列表（可以来自多个网格）
        mode: 绑定模式 "matrix" 或 "constraint"
        maintain_offset: 是否保持偏移（默认 True）
        source_meshes: 原始网格名列表（用于 skinCluster 模式复制权重）
    """

    def __init__(self, cut_results, mode="matrix", maintain_offset=True,
                 source_meshes=None):
        self.cut_results = cut_results
        self.mode = mode.lower()
        self.maintain_offset = maintain_offset
        self.source_meshes = source_meshes or []

        if self.mode not in ("matrix", "constraint"):
            raise ValueError(
                "未知的绑定模式 '{}'，支持 'matrix' 或 'constraint'".format(
                    self.mode))

    def execute(self):
        """
        执行绑定操作。

        流程：
            1. 按骨骼名分组所有 cut_results
            2. 每个骨骼创建一个 transform 组
            3. 将子网格放入对应组
            4. 对组做矩阵/约束绑定（一个骨骼只一个矩阵节点）
            5. skinCluster 子网格单独处理

        Returns:
            list[dict]: 绑定结果列表
        """
        logger.info("CutMod: 开始绑定 ({} 模式)...".format(self.mode))

        # 按骨骼分组
        joint_groups = defaultdict(list)
        for cut_result in self.cut_results:
            joint_groups[cut_result.joint_name].append(cut_result)

        results = []

        for joint_name, group_results in sorted(joint_groups.items()):
            if not cmds.objExists(joint_name):
                logger.warning(
                    "CutMod: 骨骼 '{}' 不存在，跳过".format(joint_name))
                continue

            # 分离 skinCluster 和普通绑定的子网格
            sc_results = [r for r in group_results if r.is_skincluster]
            normal_results = [r for r in group_results
                              if not r.is_skincluster]

            # --- 处理普通绑定的子网格（矩阵/约束）---
            if normal_results:
                valid_meshes = [
                    r for r in normal_results
                    if cmds.objExists(r.mesh_name)]

                if valid_meshes:
                    if self.mode == "matrix":
                        bind_result = self._bind_group_matrix(
                            valid_meshes, joint_name)
                    else:
                        bind_result = self._bind_group_constraint(
                            valid_meshes, joint_name)
                    results.append(bind_result)

            # --- 处理 skinCluster 子网格（面部区域）---
            for sc_result in sc_results:
                mesh = sc_result.mesh_name
                if not cmds.objExists(mesh):
                    continue

                # 创建组（如果还没创建）
                grp_name = "{}_grp".format(joint_name)
                ensure_group(grp_name, parent=CUTMOD_GROUP)
                # 移入组
                current_parent = cmds.listRelatives(
                    mesh, parent=True, fullPath=False) or []
                if current_parent and current_parent[0] != grp_name:
                    cmds.parent(mesh, grp_name)

                # 对每个 skinCluster 子网格单独绑定
                bind_result = self._bind_skincluster(
                    mesh, joint_name, sc_result.source_mesh)
                results.append(bind_result)

        logger.info("CutMod: 绑定完成 — {} 个骨骼组".format(
            len(results)))
        return results

    def _bind_group_matrix(self, cut_results, joint):
        """
        矩阵分组绑定 — 多个子网格共享一个 transform 组和一个矩阵节点。

        结构：
            joint.worldMatrix × parent.worldInverseMatrix
                → multMatrix.matrixSum → group.offsetParentMatrix
            子网格直接成为 group 的子节点

        Args:
            cut_results: 同一骨骼的 CutMeshResult 列表
            joint: 骨骼名

        Returns:
            dict: 绑定结果
        """
        nodes_created = []

        # 1. 创建或获取骨骼组
        grp_name = "{}_grp".format(joint)
        grp = ensure_group(grp_name, parent=CUTMOD_GROUP)

        # 2. 将所有子网格移入组（保持世界位置）
        for cr in cut_results:
            mesh = cr.mesh_name
            current_parent = cmds.listRelatives(
                mesh, parent=True, fullPath=False) or []
            if current_parent and current_parent[0] != grp_name:
                cmds.parent(mesh, grp_name)

        # 3. 计算组的偏移矩阵
        grp_world = cmds.getAttr("{}.worldMatrix[0]".format(grp))
        joint_world_inv = cmds.getAttr(
            "{}.worldInverseMatrix[0]".format(joint))
        offset_matrix = self._multiply_matrices(grp_world, joint_world_inv)

        # 4. 创建 multMatrix 节点（每个骨骼只一个）
        mm_name = "{}_MM".format(joint)
        if cmds.objExists(mm_name):
            cmds.delete(mm_name)
        mm_node = cmds.createNode("multMatrix", name=mm_name)
        nodes_created.append(mm_node)

        # 5. 连接矩阵链
        plug_idx = 0

        if self.maintain_offset:
            cmds.setAttr("{}.matrixIn[{}]".format(mm_node, plug_idx),
                         offset_matrix, type="matrix")
            plug_idx += 1

        # joint.worldMatrix → multMatrix
        cmds.connectAttr(
            "{}.worldMatrix[0]".format(joint),
            "{}.matrixIn[{}]".format(mm_node, plug_idx),
            force=True)
        plug_idx += 1

        # group 的父级 worldInverseMatrix → multMatrix
        grp_parents = cmds.listRelatives(grp, parent=True)
        if grp_parents:
            cmds.connectAttr(
                "{}.worldInverseMatrix[0]".format(grp_parents[0]),
                "{}.matrixIn[{}]".format(mm_node, plug_idx),
                force=True)
            plug_idx += 1

        # 6. multMatrix.matrixSum → group.offsetParentMatrix
        cmds.connectAttr(
            "{}.matrixSum".format(mm_node),
            "{}.offsetParentMatrix".format(grp),
            force=True)

        # 7. 清零 group 的本地 TRS 通道
        cmds.xform(grp, objectSpace=True,
                   translation=(0, 0, 0),
                   rotation=(0, 0, 0),
                   scale=(1, 1, 1))

        mesh_names = [cr.mesh_name for cr in cut_results]
        logger.debug(
            "CutMod: [Matrix Group] '{}' -> '{}' ({} 子网格)".format(
                grp, joint, len(cut_results)))

        return {
            "group": grp,
            "meshes": mesh_names,
            "joint": joint,
            "mode": "matrix",
            "nodes_created": nodes_created
        }

    def _bind_group_constraint(self, cut_results, joint):
        """
        约束分组绑定 — 用 parentConstraint + scaleConstraint 驱动组。

        Args:
            cut_results: 同一骨骼的 CutMeshResult 列表
            joint: 骨骼名

        Returns:
            dict: 绑定结果
        """
        nodes_created = []

        # 1. 创建或获取骨骼组
        grp_name = "{}_grp".format(joint)
        grp = ensure_group(grp_name, parent=CUTMOD_GROUP)

        # 2. 移入子网格
        for cr in cut_results:
            mesh = cr.mesh_name
            current_parent = cmds.listRelatives(
                mesh, parent=True, fullPath=False) or []
            if current_parent and current_parent[0] != grp_name:
                cmds.parent(mesh, grp_name)

        # 3. 约束组
        pc = cmds.parentConstraint(joint, grp, maintainOffset=True)
        if pc:
            nodes_created.extend(pc)
        sc = cmds.scaleConstraint(joint, grp)
        if sc:
            nodes_created.extend(sc)

        mesh_names = [cr.mesh_name for cr in cut_results]
        logger.debug(
            "CutMod: [Constraint Group] '{}' -> '{}' ({} 子网格)".format(
                grp, joint, len(cut_results)))

        return {
            "group": grp,
            "meshes": mesh_names,
            "joint": joint,
            "mode": "constraint",
            "nodes_created": nodes_created
        }

    def _bind_skincluster(self, mesh, joint, source_mesh):
        """
        skinCluster 绑定模式 — 用于面部区域。

        从原始网格复制蒙皮权重到切分后的子网格，保留完整的
        多骨骼混合变形能力（表情不丢失）。

        Args:
            mesh: 子网格名
            joint: 归属骨骼名
            source_mesh: 原始网格名

        Returns:
            dict: 绑定结果
        """
        nodes_created = []

        if not source_mesh or not cmds.objExists(source_mesh):
            logger.warning(
                "CutMod: 原始网格 '{}' 不可用，"
                "回退到矩阵绑定".format(source_mesh))
            # 回退：把这个 mesh 单独矩阵绑定
            return self._bind_single_matrix(mesh, joint)

        source_sc = get_skin_cluster(source_mesh)
        if not source_sc:
            logger.warning(
                "CutMod: 原始网格 '{}' 无 skinCluster，"
                "回退到矩阵绑定".format(source_mesh))
            return self._bind_single_matrix(mesh, joint)

        inf_joints = get_influence_joints(source_sc)
        if not inf_joints:
            return self._bind_single_matrix(mesh, joint)

        try:
            new_sc = cmds.skinCluster(
                inf_joints, mesh,
                toSelectedBones=True,
                bindMethod=0,
                skinMethod=0,
                normalizeWeights=1,
                maximumInfluences=4,
                name="{}_skinCluster".format(mesh))[0]
            nodes_created.append(new_sc)

            cmds.copySkinWeights(
                sourceSkin=source_sc,
                destinationSkin=new_sc,
                noMirror=True,
                surfaceAssociation="closestPoint",
                influenceAssociation=["oneToOne", "closestJoint"])

            logger.debug(
                "CutMod: [SkinCluster] '{}' -> '{}' "
                "({} 影响骨骼)".format(mesh, joint, len(inf_joints)))

        except Exception as e:
            logger.warning(
                "CutMod: skinCluster 绑定失败 '{}': {}，"
                "回退到矩阵绑定".format(mesh, e))
            return self._bind_single_matrix(mesh, joint)

        return {
            "mesh": mesh,
            "joint": joint,
            "mode": "skincluster",
            "nodes_created": nodes_created
        }

    def _bind_single_matrix(self, mesh, joint):
        """
        单个网格的矩阵绑定（回退用）。

        Args:
            mesh: 网格名
            joint: 骨骼名

        Returns:
            dict: 绑定结果
        """
        nodes_created = []

        mesh_world = cmds.getAttr("{}.worldMatrix[0]".format(mesh))
        joint_world_inv = cmds.getAttr(
            "{}.worldInverseMatrix[0]".format(joint))
        offset_matrix = self._multiply_matrices(mesh_world, joint_world_inv)

        mm_name = "{}_MM".format(mesh.replace("_CutMod", ""))
        if cmds.objExists(mm_name):
            cmds.delete(mm_name)
        mm_node = cmds.createNode("multMatrix", name=mm_name)
        nodes_created.append(mm_node)

        plug_idx = 0
        if self.maintain_offset:
            cmds.setAttr("{}.matrixIn[{}]".format(mm_node, plug_idx),
                         offset_matrix, type="matrix")
            plug_idx += 1

        cmds.connectAttr(
            "{}.worldMatrix[0]".format(joint),
            "{}.matrixIn[{}]".format(mm_node, plug_idx),
            force=True)
        plug_idx += 1

        parents = cmds.listRelatives(mesh, parent=True)
        if parents:
            cmds.connectAttr(
                "{}.worldInverseMatrix[0]".format(parents[0]),
                "{}.matrixIn[{}]".format(mm_node, plug_idx),
                force=True)

        cmds.connectAttr(
            "{}.matrixSum".format(mm_node),
            "{}.offsetParentMatrix".format(mesh),
            force=True)

        cmds.xform(mesh, objectSpace=True,
                   translation=(0, 0, 0),
                   rotation=(0, 0, 0),
                   scale=(1, 1, 1))

        return {
            "mesh": mesh,
            "joint": joint,
            "mode": "matrix",
            "nodes_created": nodes_created
        }

    @staticmethod
    def _multiply_matrices(mat_a, mat_b):
        """矩阵乘法（4x4），使用 OpenMaya 2.0"""
        if isinstance(mat_a[0], (list, tuple)):
            flat_a = [v for row in mat_a for v in row]
        else:
            flat_a = list(mat_a)

        if isinstance(mat_b[0], (list, tuple)):
            flat_b = [v for row in mat_b for v in row]
        else:
            flat_b = list(mat_b)

        m_a = om2.MMatrix(flat_a)
        m_b = om2.MMatrix(flat_b)
        result = m_a * m_b
        return list(result)
