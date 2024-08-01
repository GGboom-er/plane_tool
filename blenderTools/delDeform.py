#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: delDeform.py
@date: 2024/6/11 11:35
@desc: 
"""
import bpy

def disable_and_remove_modifiers():
    # 遍历场景中的所有对象
    for obj in bpy.data.objects:
        # 检查对象是否为Mesh类型
        if obj.type == 'MESH':
            # 获取对象的所有变形器
            for modifier in obj.modifiers:
                # 禁用变形器
                modifier.show_viewport = False
                modifier.show_render = False
                # 删除变形器
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_remove(modifier=modifier.name)

# 调用函数
disable_and_remove_modifiers()
