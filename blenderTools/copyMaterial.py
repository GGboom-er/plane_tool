#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: copyMaterial.py
@date: 2024/8/5 15:55
@desc: 
"""
import bpy


def copy_materials_and_assignments_to_selected():
    # 获取当前选中的对象列表
    selected_objects = bpy.context.selected_objects

    # 检查是否有足够的对象被选中
    if len(selected_objects) < 2:
        print("请至少选择两个对象，其中一个是加选的源对象。")
        return

    # 获取加选的源对象
    source_obj = bpy.context.active_object

    # 目标对象是所有选中对象中，除了加选的源对象之外的对象
    target_objects = [obj for obj in selected_objects if obj != source_obj]

    # 检查源对象是否为网格对象
    if source_obj is None or source_obj.type != 'MESH':
        print("加选的源对象不存在或不是网格对象。")
        return

    # 获取源对象的材质列表
    source_materials = source_obj.data.materials
    if not source_materials:
        print(f"源对象 {source_obj.name} 没有材质。")
        return

    # 获取源对象的面材质分配信息
    source_material_assignments = [poly.material_index for poly in source_obj.data.polygons]

    # 遍历目标对象列表
    for target_obj in target_objects:
        if target_obj.type != 'MESH':
            print(f"目标对象 {target_obj.name} 不是网格对象，跳过。")
            continue

        # 清空目标对象的材质槽
        target_obj.data.materials.clear()

        # 复制材质到目标对象
        for material in source_materials:
            target_obj.data.materials.append(material)

        # 检查面数是否一致
        if len(target_obj.data.polygons) != len(source_material_assignments):
            print(f"目标对象 {target_obj.name} 面数与源对象不匹配，无法复制材质分配。")
            continue

        # 复制面材质分配：逐一对应每个面
        for i, poly in enumerate(target_obj.data.polygons):
            poly.material_index = source_material_assignments[i]

        print(f"已将材质和分配从 {source_obj.name} 复制到 {target_obj.name}")


# 运行函数
copy_materials_and_assignments_to_selected()
