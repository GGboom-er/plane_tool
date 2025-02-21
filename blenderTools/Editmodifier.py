#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: editModi.py
@date: 2025/2/18 19:45
@desc: 
"""
import bpy

def set_geometry_nodes_socket(target_modifier_name, node_param_name, name_suffix=".001"):
    """
    遍历所有选中的物体，找到指定的 Geometry Nodes 变形器，并设置其 Socket 参数。

    :param target_modifier_name: 目标 Geometry Nodes 变形器名称（如 "Geometry Nodes_curve_cache"）
    :param node_param_name: 变形器节点的参数名称（如 "Socket_1"）
    :param name_suffix: 物体名称后缀（默认为 ".001"）
    """
    selected_objects = bpy.context.selected_objects  # 获取所有选中的物体

    if not selected_objects:
        print("错误：未选中任何对象！")
        return

    for obj in selected_objects:
        print(f"\n处理对象: {obj.name}")

        # 获取新对象的名称（当前物体名称 + 后缀，如 'a' → 'a.001'）
        new_object_name = f"{obj.name}{name_suffix}"

        # 确保新对象存在
        new_obj = bpy.data.objects.get(new_object_name)
        if new_obj is None:
            print(f"错误：新对象 '{new_object_name}' 不存在！")
            continue

        # 遍历物体的所有修改器，查找目标 Geometry Nodes 变形器
        for modifier in obj.modifiers:
            print (modifier.name,modifier.type)
            if modifier.type == "NODES" and modifier.name == target_modifier_name:
                print(f"找到变形器: {modifier.name}")

                # 直接设置变形器的 Socket 参数
                try:
                    modifier[node_param_name] = new_obj
                    print(f"成功设置 '{node_param_name}' 为 '{new_object_name}'")
                except KeyError:
                    print(f"错误：'{node_param_name}' 不是变形器 '{modifier.name}' 的有效参数")
                break
        else:
            print(f"错误：未找到名为 '{target_modifier_name}' 的变形器")

# 使用示例
target_modifier = "Geometry Nodes_curve_cache"  # 目标变形器
node_param = "Socket_1"  # 变形器参数
set_geometry_nodes_socket(target_modifier, node_param)




\\批量修改指定变形器下节点组
import bpy
def apply_existing_geometry_nodes_group( target_modifier_name, node_group_name ):
    """批量修改选中对象的第一个几何体节点变形器的节点组"""

    # 获取目标几何体节点组
    node_group = bpy.data.node_groups.get(node_group_name)
    if not node_group:
        print(f"错误：场景中未找到节点组 '{node_group_name}'")
        return

    # 遍历所有选中的对象
    for obj in bpy.context.selected_objects:
        if not obj.modifiers:
            continue  # 跳过没有修改器的物体

        # 获取第一个修改器
        first_modifier = obj.modifiers[0]

        # 检查是否是几何体节点（Geometry Nodes）且名称匹配
        if first_modifier.type == 'NODES' and first_modifier.name == target_modifier_name:
            first_modifier.node_group = node_group
            print(f"已为 {obj.name} 设置节点组 '{node_group_name}'")


# 调用示例
apply_existing_geometry_nodes_group("MyGeoModifier", "a")




