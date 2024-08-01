#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: batchReference.py
@date: 2024/7/25 13:40
@desc: 
"""
from __future__ import print_function
import maya.cmds as cmds


def import_file_for_each_vertex( file_path, target_object_name ):
    # 获取当前选择的物体
    selection = cmds.ls(selection=True)
    if not selection:
        cmds.warning("请先选择一个网格物体！")
        return

    # 获取选择物体的形节点
    shape_node = cmds.listRelatives(selection[0], shapes=True)[0]

    # 确保选择的是一个网格
    if cmds.nodeType(shape_node) != 'mesh':
        cmds.warning("请选择一个网格物体！")
        return

    # 获取顶点位置
    vertex_positions = cmds.xform(selection[0] + ".vtx[*]", query=True, translation=True, worldSpace=True)
    vertex_count = len(vertex_positions) // 3
    print("顶点数量: {}".format(vertex_count))

    # 遍历每个顶点并导入文件，记录命名空间
    namespaces = []
    for i in range(vertex_count):
        namespace = "import_{}".format(i)
        cmds.file(file_path, r=True, namespace=namespace)  # 以引用方式导入文件
        namespaces.append(namespace)

        # 获取导入物体的名称
        imported_object = "{}:{}".format(namespace, target_object_name)

        if not cmds.objExists(imported_object):
            cmds.warning("在命名空间 {} 下未找到物体 {}".format(namespace, target_object_name))
            continue

        # 设置导入物体的位置为当前顶点位置
        pos = vertex_positions[i * 3:i * 3 + 3]
        cmds.xform(imported_object, translation=pos, worldSpace=True)
        print("顶点 {}: 导入文件 {}，命名空间 {}，位置 {}".format(i, file_path, namespace, pos))

    return namespaces


# 调用函数，替换为你的文件路径和目标物体名称
imported_namespaces = import_file_for_each_vertex(r"U:\ywm\tbx\slrobot\rig_slrobtlowb_low.ma", "Main_Ctr")
print("导入的命名空间: ", imported_namespaces)

# 示例如何使用导入的命名空间
for ns in imported_namespaces:
    imported_objects = cmds.ls("{}:*".format(ns))
    print("命名空间 {} 导入的物体: {}".format(ns, imported_objects))
