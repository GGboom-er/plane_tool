#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: trasnSGInfo.py
@date: 2024/5/24 15:16
@desc: 
"""
import maya.cmds as cmds
def get_shape_node( transform ):
    """
    获取给定transform节点的第一个shape节点。
    """
    shapes = cmds.listRelatives(transform, shapes=True, ni=1)
    if len(shapes) == 1:
        return shapes[0]
    else:
        cmds.warning("No shape nodes found for {}.".format(transform))
        return None


def get_components_from_sg( shading_group ):
    """
    获取指定Shading Group节点包含的模型组件信息。

    :param shading_group: Shading Group节点名称
    :return: 包含的组件列表
    """
    components = cmds.sets(shading_group, query=True)
    return components


def copy_sg_components( source_transform, target_transform ):
    """
    将源模型的组件信息添加到目标模型，并将目标模型的组件添加到现有的Shading Group节点。
    :param source_transform: 源模型的transform节点名称
    :param target_transform: 目标模型的transform节点名称
    # 示例使用
    source_transform = "xiaoyueqinwild_head1"
    target_transform = "xiaoyueqinwild_head2"
    copy_sg_components(source_transform, target_transform)
    """
    source_shape = get_shape_node(source_transform)
    target_shape = get_shape_node(target_transform)

    if not source_shape or not target_shape:
        cmds.warning("Source or target shape node not found.")
        return

    # 获取源模型的SG节点
    shading_groups = cmds.listConnections(source_shape, type='shadingEngine')
    if not shading_groups:
        cmds.warning("No shading groups found for {}.".format(source_shape))
        return

    for shading_group in shading_groups:
        # 获取连接到SG节点的组件信息
        components = get_components_from_sg(shading_group)
        if not components:
            cmds.warning("No components found for shading group {}.".format(shading_group))
            continue
        # 将目标模型的相应组件添加到现有的SG节点
        new_components = []
        for comp in components:
            if comp.startswith(source_transform):
                comp_index = comp[len(source_transform):]
                new_components.append(target_transform + comp_index)

        if new_components:
            cmds.sets(new_components, edit=True, forceElement=shading_group)
            print("Added components to {}: {}".format(shading_group, new_components))
