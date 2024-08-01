#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: compareInMaya.py
@date: 2023/12/11 13:29
@desc: 
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om


def get_name_without_namespace( name ):
    """从带有命名空间的名字中获取实际名字。"""
    return name.split(':')[-1]


def get_shape_node( node ):
    """获取给定节点的形状节点。"""
    shapes = cmds.listRelatives(node, children=True, shapes=True)
    return shapes[0] if shapes else None


def compare_vertex_positions( shape1, shape2 ):
    """比较两个形状的顶点位置，返回差异率。"""
    selList = om.MSelectionList()
    selList.add(shape1)
    selList.add(shape2)
    dagPath1 = selList.getDagPath(0)
    dagPath2 = selList.getDagPath(1)
    mfnMesh1 = om.MFnMesh(dagPath1)
    mfnMesh2 = om.MFnMesh(dagPath2)

    points1 = mfnMesh1.getPoints(om.MSpace.kWorld)
    points2 = mfnMesh2.getPoints(om.MSpace.kWorld)

    if len(points1) != len(points2):
        return None, len(points1), len(points2)  # 不同数量的顶点，无法比较

    diff_count = [p1.distanceTo(p2) for p1, p2 in zip(points1, points2) if p1.distanceTo(p2) > 0.00001]
    diff_rate = len(diff_count) / float(len(points1)) if len(points1) > 0 else 0
    if len(diff_count) > 0:
        maxValue = max(diff_count)
        minValue = min(diff_count)
    else:
        maxValue = 0.0
        minValue = 0.0
    return diff_rate, maxValue, minValue


def match_hierarchy_recursive( reference_node, target_node, target_lookup, unmatched_nodes ):
    """递归函数，用于调整目标节点的层级结构，使其匹配参考节点，并在有型节点时比对顶点信息。"""
    ref_children = cmds.listRelatives(reference_node, children=True, type='transform') or []
    target_children = cmds.listRelatives(target_node, children=True, type='transform') or []

    matched_target_children = set()

    for ref_child in ref_children:
        ref_child_name = get_name_without_namespace(ref_child)
        if ref_child_name in target_lookup:
            target_child = target_lookup[ref_child_name]
            matched_target_children.add(target_child)

            cmds.reorder(target_child, b=1)  # 保持层级调整逻辑

            target_child_shape_node = get_shape_node(target_child)
            ref_child_shape_node = get_shape_node(ref_child)
            if target_child_shape_node and ref_child_shape_node:
                target_child_Orig_node = target_child_shape_node + "Orig"  # 假设原始形状节点命名规则

                if cmds.objExists(target_child_Orig_node):
                    diff_rate = compare_vertex_positions(ref_child_shape_node, target_child_Orig_node)
                    if diff_rate[0] != None:

                        unmatched_nodes['Difference'].append((ref_child_shape_node, target_child_Orig_node, diff_rate))

                    else:
                        print('===No match point===:\n%s===%s\n%s===%s\n' % (
                            ref_child_shape_node, diff_rate[1], target_child_Orig_node, diff_rate[2]))
            match_hierarchy_recursive(ref_child, target_child, target_lookup, unmatched_nodes)
        else:
            unmatched_nodes['reference'].append(ref_child)

    for target_child in target_children:
        if target_child not in matched_target_children:
            target_child_name = get_name_without_namespace(target_child)
            unmatched_nodes['target'].append(target_child_name)


def match_hierarchy( reference_group, target_group ):
    """调整目标组的层级结构，使其与参考组匹配，并在有型节点时比对顶点信息，返回不匹配的物体列表。"""
    target_lookup = {}
    unmatched_nodes = {'reference': [], 'target': [], 'Difference': []}

    for child in cmds.listRelatives(target_group, allDescendents=True, type='transform') or []:
        target_lookup[get_name_without_namespace(child)] = child

    match_hierarchy_recursive(reference_group, target_group, target_lookup, unmatched_nodes)

    print("Adjusted hierarchy of '{}' to match '{}'.".format(target_group, reference_group))
    return unmatched_nodes


# 使用示例1
unmatched = match_hierarchy("tbx_chr_xiaqing_tex_refinement_v003:cache", "cache")
print("Unmatched in reference group:", unmatched['reference'])
print("Unmatched in target group:", unmatched['target'])
for i in unmatched['Difference']:
    print("Difference rate between {} and {}: {:2%}".format(i[0], i[1], i[2][0]))
    print('maxValue:%s======minValue:%s\n' % (i[2][1], i[2][2]))



