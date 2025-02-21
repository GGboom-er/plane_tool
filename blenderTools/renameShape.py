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


def rename_shape_node():
    # 获取当前选中的对象
    obj = bpy.context.active_object
    if obj is None:
        print("错误：当前未选中任何对象。")
        return

    # 确保对象有 data（即 shape 节点）
    if not hasattr(obj, "data") or obj.data is None:
        print("错误：选中对象没有 shape 节点。")
        return

    # 构造新名称，例如 A → AShape
    new_name = obj.name + "Shape"
    obj.data.name = new_name
    print(f"成功：构造节点已重命名为 '{new_name}'")


# 运行函数
rename_shape_node()


