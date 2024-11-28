#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: reConnectBSDIrve.py
@date: 2024/11/26 17:32
@desc: 
"""
from __future__ import print_function
import pymel.core as pm
import maya.cmds as cmds
import sys

# 检查 Python 版本
PY2 = sys.version_info[0] == 2


def get_blendshape_aliases_dict( blendshape_node ):
    """
    获取 BlendShape 节点的权重别名与属性名称的对应字典。

    :param blendshape_node: BlendShape 节点名称
    :return: {别名: 完整属性路径} 的字典
    """
    if not cmds.objExists(blendshape_node):
        raise ValueError("BlendShape 节点 {} 不存在！".format(blendshape_node))

    aliases = cmds.aliasAttr(blendshape_node, q=True)
    if not aliases:
        return {}

    # aliasAttr 返回 [别名, 属性, 别名, 属性...] 的列表
    alias_dict = {}
    for i in range(0, len(aliases), 2):
        alias_name = aliases[i]
        attribute_name = "{}.{}".format(blendshape_node, aliases[i + 1])  # 添加完整路径
        alias_dict[alias_name] = attribute_name
    return alias_dict


def migrate_blendshape_connections_by_name( source_bs, target_bs ):
    """
    将源 BlendShape 节点的 weight 属性连接迁移到目标 BlendShape 节点，
    根据权重别名（属性名称）匹配连接，而非仅依赖索引。

    :param source_bs: 源 BlendShape 节点名称
    :param target_bs: 目标 BlendShape 节点名称
    """
    # 获取源和目标 BlendShape 的权重别名字典
    source_aliases_dict = get_blendshape_aliases_dict(source_bs)
    target_aliases_dict = get_blendshape_aliases_dict(target_bs)

    if not source_aliases_dict:
        print("源 BlendShape 节点 {} 没有权重别名！".format(source_bs))
        return

    if not target_aliases_dict:
        print("目标 BlendShape 节点 {} 没有权重别名！".format(target_bs))
        return

    # 遍历源 BlendShape 的别名
    for alias_name, source_attr in source_aliases_dict.items():
        if alias_name not in target_aliases_dict:
            print(u"跳过迁移：权重名称 {} 在目标 BlendShape 节点中不存在".format(alias_name))
            continue

        # 获取目标属性路径
        target_attr = target_aliases_dict[alias_name]

        # 检查源属性是否有连接
        source_attr_node = pm.PyNode(source_attr)
        target_attr_node = pm.PyNode(target_attr)

        if source_attr_node.isConnected():
            # 获取连接信息
            connections = source_attr_node.listConnections(s=True, d=False, p=True)
            for conn in connections:
                # 断开旧连接并重新连接到目标
                pm.disconnectAttr(conn, source_attr_node)
                pm.connectAttr(conn, target_attr_node)

                # 输出迁移信息
                print(u"迁移连接：{} -> {}".format(source_attr, target_attr))

    print(u"完成从 {} 到 {} 的连接迁移！".format(source_bs, target_bs))


# 使用示例
migrate_blendshape_connections_by_name("clothes1_bs", "blendShape19")
