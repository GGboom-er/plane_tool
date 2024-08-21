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
create_blendshapes_ui()
'''
import maya.cmds as cmds

import maya.cmds as cmds


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


# # 执行函数并获取无效模型列表
# invalid_models = add_blend_shapes()
# if invalid_models:
#     print("以下模型未能通过拓扑检查，无法添加为BlendShape目标：", invalid_models)
# else:
#     print("所有模型都已成功添加到BlendShape节点。")
