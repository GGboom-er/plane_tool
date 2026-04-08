# -*- coding: utf-8 -*-
"""
snapshot.py — 属性快照保护系统

在切分操作前后保存/恢复关键节点属性，防止切分过程中意外修改
既有绑定网络的状态（如 inheritsTransform、通道值、OPM 连接等）。

这是解决 AdvancedSkeleton CutUp 在矩阵绑定模式下破坏绑定的核心方案。
"""

import maya.cmds as cmds
import logging
from collections import OrderedDict

logger = logging.getLogger("CutMod")

# 需要保护的关键属性列表
PROTECTED_ATTRS = [
    "inheritsTransform",
    "translateX", "translateY", "translateZ",
    "rotateX", "rotateY", "rotateZ",
    "scaleX", "scaleY", "scaleZ",
    "visibility",
]

# joint 特有属性
JOINT_PROTECTED_ATTRS = [
    "jointOrientX", "jointOrientY", "jointOrientZ",
]

# 需要保护连接的属性
PROTECTED_CONNECTIONS = [
    "offsetParentMatrix",
    "inheritsTransform",
    "translateX", "translateY", "translateZ",
    "rotateX", "rotateY", "rotateZ",
    "scaleX", "scaleY", "scaleZ",
]


class NodeSnapshot(object):
    """单个节点的属性快照"""

    def __init__(self, node_name):
        self.node = node_name
        self.attr_values = {}       # {attr_name: value}
        self.connections = {}       # {attr_name: (source_plug, is_connected)}
        self.is_joint = False

    def __repr__(self):
        return "NodeSnapshot('{}', attrs={})".format(self.node, len(self.attr_values))


class SnapshotManager(object):
    """
    属性快照管理器。

    工作流:
        1. capture_scene_state() — 操作前拍快照
        2. 执行切分/绑定操作
        3. restore_protected_attrs() — 操作后恢复被意外修改的属性
    """

    def __init__(self):
        self._snapshots = OrderedDict()     # {node_name: NodeSnapshot}
        self._change_log = []               # 变更日志

    def capture_scene_state(self, nodes=None):
        """
        捕获场景中指定节点的属性快照。

        如果 nodes 为 None，自动扫描场景中所有可能受影响的节点：
        - 所有 transform / joint 类型节点（DeformationSystem 下的）
        - 所有带 offsetParentMatrix 连接的节点

        Args:
            nodes: 要快照的节点列表，None 则自动扫描
        """
        if nodes is None:
            nodes = self._auto_detect_nodes()

        self._snapshots.clear()
        for node in nodes:
            if not cmds.objExists(node):
                continue
            snap = self._capture_node(node)
            self._snapshots[node] = snap

        logger.info("CutMod Snapshot: 已捕获 {} 个节点的属性快照".format(
            len(self._snapshots)))

    def restore_protected_attrs(self):
        """
        对比当前状态与快照，恢复被意外修改的属性。

        Returns:
            list[str]: 变更日志
        """
        self._change_log = []

        for node_name, snap in self._snapshots.items():
            if not cmds.objExists(node_name):
                continue
            self._restore_node(node_name, snap)

        if self._change_log:
            logger.warning(
                "CutMod Snapshot: 已恢复 {} 处被意外修改的属性：".format(
                    len(self._change_log)))
            for entry in self._change_log:
                logger.warning("  - {}".format(entry))
        else:
            logger.info("CutMod Snapshot: 所有受保护属性未发生变化，无需恢复")

        return self._change_log

    def get_change_log(self):
        """获取变更日志"""
        return list(self._change_log)

    # ---- 内部方法 ----

    def _auto_detect_nodes(self):
        """
        自动检测需要保护的节点。

        策略：
        1. DeformationSystem 下的所有骨骼
        2. 所有 FKOffset* / FK* 控制器节点
        3. 所有带 offsetParentMatrix 输入连接的 transform 节点
        """
        nodes = set()

        # 1. DeformationSystem 下所有 joint
        if cmds.objExists("DeformationSystem"):
            joints = cmds.listRelatives(
                "DeformationSystem", allDescendents=True, type="joint",
                fullPath=False) or []
            nodes.update(joints)

        # 2. FKOffset / FK 控制器
        fk_nodes = cmds.ls("FKOffset*", "FK*", type="transform") or []
        nodes.update(fk_nodes)

        # 3. 带 OPM 输入连接的 transform
        all_transforms = cmds.ls(type="transform") or []
        for t in all_transforms:
            conns = cmds.listConnections(
                "{}.offsetParentMatrix".format(t),
                source=True, destination=False) or []
            if conns:
                nodes.add(t)

        return list(nodes)

    def _capture_node(self, node_name):
        """
        拍摄单个节点的快照。

        Args:
            node_name: 节点名

        Returns:
            NodeSnapshot 实例
        """
        snap = NodeSnapshot(node_name)
        snap.is_joint = cmds.objectType(node_name) == "joint"

        # 捕获属性值
        attrs_to_capture = list(PROTECTED_ATTRS)
        if snap.is_joint:
            attrs_to_capture.extend(JOINT_PROTECTED_ATTRS)

        for attr in attrs_to_capture:
            attr_full = "{}.{}".format(node_name, attr)
            if cmds.objExists(attr_full):
                try:
                    snap.attr_values[attr] = cmds.getAttr(attr_full)
                except Exception:
                    pass

        # 捕获连接状态
        for attr in PROTECTED_CONNECTIONS:
            attr_full = "{}.{}".format(node_name, attr)
            if not cmds.objExists(attr_full):
                continue
            conns = cmds.listConnections(
                attr_full, source=True, destination=False,
                plugs=True) or []
            if conns:
                snap.connections[attr] = (conns[0], True)
            else:
                snap.connections[attr] = (None, False)

        return snap

    def _restore_node(self, node_name, snap):
        """
        恢复单个节点被修改的属性。

        Args:
            node_name: 节点名
            snap: 该节点的 NodeSnapshot
        """
        # 恢复属性值
        attrs_to_check = list(PROTECTED_ATTRS)
        if snap.is_joint:
            attrs_to_check.extend(JOINT_PROTECTED_ATTRS)

        for attr in attrs_to_check:
            if attr not in snap.attr_values:
                continue
            attr_full = "{}.{}".format(node_name, attr)
            if not cmds.objExists(attr_full):
                continue

            # 跳过被连接驱动的属性（不能直接 setAttr）
            conns = cmds.listConnections(
                attr_full, source=True, destination=False) or []
            if conns:
                continue

            try:
                current_val = cmds.getAttr(attr_full)
            except Exception:
                continue

            original_val = snap.attr_values[attr]

            # 对比值是否变化（浮点数使用容差比较）
            if not self._values_match(current_val, original_val):
                try:
                    # 解锁属性以便设置
                    was_locked = cmds.getAttr(attr_full, lock=True)
                    if was_locked:
                        cmds.setAttr(attr_full, lock=False)

                    cmds.setAttr(attr_full, original_val)

                    if was_locked:
                        cmds.setAttr(attr_full, lock=True)

                    self._change_log.append(
                        "{}: {} 从 {} 恢复为 {}".format(
                            node_name, attr, current_val, original_val))
                except Exception as e:
                    logger.debug(
                        "无法恢复 {}.{}: {}".format(node_name, attr, e))

        # 恢复连接
        for attr, (source_plug, was_connected) in snap.connections.items():
            attr_full = "{}.{}".format(node_name, attr)
            if not cmds.objExists(attr_full):
                continue

            current_conns = cmds.listConnections(
                attr_full, source=True, destination=False,
                plugs=True) or []
            is_connected_now = bool(current_conns)

            if was_connected and not is_connected_now:
                # 连接被断开了，尝试恢复
                if source_plug and cmds.objExists(source_plug.split(".")[0]):
                    try:
                        cmds.connectAttr(source_plug, attr_full, force=True)
                        self._change_log.append(
                            "{}: {} 的连接已恢复 ({})".format(
                                node_name, attr, source_plug))
                    except Exception as e:
                        logger.debug(
                            "无法恢复连接 {} -> {}: {}".format(
                                source_plug, attr_full, e))

            elif not was_connected and is_connected_now:
                # 意外新增了连接，断开它
                try:
                    cmds.disconnectAttr(current_conns[0], attr_full)
                    self._change_log.append(
                        "{}: {} 被意外连接 ({}), 已断开".format(
                            node_name, attr, current_conns[0]))
                except Exception as e:
                    logger.debug(
                        "无法断开意外连接 {}: {}".format(attr_full, e))

    @staticmethod
    def _values_match(val_a, val_b, tolerance=1e-6):
        """
        比较两个值是否匹配（支持浮点容差）。

        Args:
            val_a: 值 A
            val_b: 值 B
            tolerance: 浮点容差

        Returns:
            bool: 是否匹配
        """
        if isinstance(val_a, (int, bool)) and isinstance(val_b, (int, bool)):
            return val_a == val_b
        if isinstance(val_a, float) and isinstance(val_b, float):
            return abs(val_a - val_b) < tolerance
        return val_a == val_b
