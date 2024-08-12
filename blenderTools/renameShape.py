#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: renameShape.py
@date: 2024/8/5 17:40
@desc: 
"""
import bpy


def rename_mesh_data_to_object_name():
    # 遍历所有对象
    for obj in bpy.data.objects:
        # 只处理网格对象
        if obj.type == 'MESH':
            # 获取当前对象的网格数据名称
            mesh_data_name = obj.data.name
            # 构建目标名称
            target_name = f"{obj.name}Shape"

            # 检查并修改网格数据名称
            if mesh_data_name != target_name:
                print(f"修改 '{mesh_data_name}' 为 '{target_name}'")
                obj.data.name = target_name
            else:
                print(f"'{mesh_data_name}' 已经是正确的名称")


# 运行函数
rename_mesh_data_to_object_name()
