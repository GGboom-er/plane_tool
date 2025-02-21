#!/usr/bin/env python
# _*_ coding:cp936 _*_
"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: buildBS.py
@date: 2024/4/15 17:25
@desc: 
"""
from __future__ import print_function  # 兼容 Python 2 和 Python 3
import maya.cmds as cmds


def create_blendshapes_from_groups( group_a, group_b ):
    models_a = cmds.listRelatives(group_a, allDescendents=True, type='mesh', fullPath=True)
    models_a = cmds.listRelatives(models_a, parent=True, fullPath=True)  # 获取变换节点
    models_b = cmds.listRelatives(group_b, allDescendents=True, type='mesh', fullPath=True)
    models_b = cmds.listRelatives(models_b, parent=True, fullPath=True)

    dict_a = {m.split(':')[-1]: m for m in models_a}
    dict_b = {m.split(':')[-1]: m for m in models_b}

    for name, model_a in dict_a.items():
        model_b = dict_b.get(name)
        if model_b:
            if cmds.polyEvaluate(model_a, vertex=True) == cmds.polyEvaluate(model_b, vertex=True):
                blendshape_name = "{}---CFXCheck---".format(name)
                blendshape_node = cmds.blendShape(model_a, model_b, name=blendshape_name)[0]
                cmds.setAttr("{}.weight[0]".format(blendshape_node), 1.0)
                print("Created and activated blendShape '{}' between '{}' and '{}'".format(blendshape_name, model_a,
                                                                                           model_b))
            else:
                print("Vertex count mismatch for '{}'".format(name))
        else:
            print("No matching model found for '{}' in group_b".format(name))
def on_create_blendshapes_pressed():
    selection = cmds.ls(selection=True, long=True)
    if len(selection) < 2:
        cmds.warning("Please select two groups.")
        return
    # Assuming the first selected is group_a and the second selected is group_b
    group_a = selection[0]
    group_b = selection[1]
    create_blendshapes_from_groups(group_a, group_b)
def create_blendshapes_ui():
    if cmds.window("blendShapeWindow", exists=True):
        cmds.deleteUI("blendShapeWindow", window=True)

    window = cmds.window("blendShapeWindow", title="Create BlendShapes", widthHeight=(200, 60))
    cmds.columnLayout(adjustableColumn=True)
    cmds.button(label="Create BlendShapes", command=lambda x: on_create_blendshapes_pressed())
    cmds.showWindow(window)
'''
create_blendshapes_ui()#名称查找批量创建bs
'''

def add_blend_shapes():
    # 获取当前选中的物体
    selection = cmds.ls(selection=True, long=True)

    if len(selection) < 2:
        cmds.error("请至少选择两个物体，其中最后一个物体为目标物体。")
        return

    # 目标物体是最后一个选择的物体
    target = selection[-1]
    # 源物体是除了最后一个以外的其他物体
    sources = selection[:-1]

    # 无效模型列表
    invalid_models = []

    # 检查目标物体的历史节点，找到正确的blendShape节点
    history = cmds.listHistory(target)
    blend_shape_node = None

    for node in history:
        if cmds.nodeType(node) == 'blendShape':
            blend_shape_node = node
            break

    if not blend_shape_node:
        # 如果没有找到blendShape节点，则创建一个，并放在其他变形器历史后面
        deformers = [node for node in history if cmds.nodeType(node) in ['skinCluster', 'cluster', 'ffd', 'wrap']]
        if deformers:
            blend_shape_node = cmds.blendShape(target, frontOfChain=False, origin='local', topologyCheck=True)[0]
        else:
            blend_shape_node = cmds.blendShape(target, origin='local', topologyCheck=True)[0]
        max_index = -1
    else:
        # 获取当前已存在的最大索引
        indices = cmds.getAttr(blend_shape_node + ".weight", multiIndices=True)
        if indices:
            max_index = max(indices)
        else:
            max_index = -1

    # 添加新的blendShape目标
    for i, source in enumerate(sources):
        try:
            new_index = max_index + 1
            cmds.blendShape(blend_shape_node, edit=True, target=(target, new_index, source, 1.0), topologyCheck=True)
            # 启用新的blendShape目标
            cmds.setAttr("{0}.weight[{1}]".format(blend_shape_node, new_index), 1.0)
            print("已将 {0} 添加到 {1} 的索引 {2}".format(source, blend_shape_node, new_index))
            # 更新max_index
            max_index += 1
        except Exception as e:
            # 如果有任何错误（例如拓扑不匹配），记录到无效模型列表中
            invalid_models.append(source)
            print("无法将 {0} 添加为BlendShape目标：{1}".format(source, str(e)))

    # 返回无效模型列表
    return invalid_models

'''
# 执行函数并获取无效模型列表
invalid_models = add_blend_shapes()#————选择对应模型创建bs节点
if invalid_models:
    print("以下模型未能通过拓扑检查，无法添加为BlendShape目标：", invalid_models)
else:
    print("所有模型都已成功添加到BlendShape节点。")
'''



def get_blendshape_nodes_for_selection():
    """获取当前选中模型的 BlendShape 节点。"""
    selected_objects = cmds.ls(selection=True, type='transform')
    blendshape_nodes = {}

    if not selected_objects:
        cmds.warning("请先选择一个或多个模型。")
        return blendshape_nodes

    for obj in selected_objects:
        # 获取模型的形状节点
        shapes = cmds.listRelatives(obj, shapes=True, type='mesh', fullPath=True) or []

        for shape in shapes:
            # 查找与该形状节点相关的 BlendShape 节点
            history = cmds.listHistory(shape, future=True, pruneDagObjects=True) or []
            bs_nodes = cmds.ls(history, type='blendShape')

            if bs_nodes:
                blendshape_nodes[obj] = bs_nodes[0]  # 每个模型对应的第一个 BlendShape 节点

    return blendshape_nodes
def connect_attribute_to_blendshape( attr_name, bs_name, bs_index ):
    """
    将给定的属性与 BlendShape 的特定 index 进行连接。

    参数：
    attr_name: 要连接的属性名（格式为 "节点.属性"）。
    bs_name: BlendShape 节点的名称。
    bs_index: BlendShape 的目标索引。
    """
    bs_attr = "{}.weight[{}]".format(bs_name, bs_index)

    # 检查属性和 BlendShape 权重是否存在
    if not cmds.objExists(attr_name):
        cmds.warning("属性 {} 不存在。".format(attr_name))
        return

    if not cmds.objExists(bs_attr):
        cmds.warning("BlendShape 权重 {} 不存在。".format(bs_attr))
        return

    # 创建连接
    try:
        cmds.connectAttr(attr_name, bs_attr, force=True)
        print("已将 {} 连接到 {}。".format(attr_name, bs_attr))
    except Exception as e:
        cmds.warning("连接失败: {}".format(str(e)))
# 主程序
def main( attr_name, bs_index ):
    """
    主程序，获取选中模型的 BlendShape 节点并将其与属性连接。

    参数：
    attr_name: 要连接的属性名（格式为 "节点.属性"）。
    bs_index: BlendShape 的目标索引。
    """
    blendshape_nodes = get_blendshape_nodes_for_selection()

    if not blendshape_nodes:
        print("未找到任何 BlendShape 节点。")
        return

    for obj, bs_node in blendshape_nodes.items():
        print("在 {} 上找到 BlendShape 节点: {}".format(obj, bs_node))
        connect_attribute_to_blendshape(attr_name, bs_node, bs_index)
'''
# 使用示例：传入属性名称和 BlendShape 的索引
# 示例：将 "controller1.attr" 连接到 BlendShape 的索引 0
main("condition12.outColor.outColorR", 1)#批量将属性连接至选中模型的指定bs索引
'''

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
