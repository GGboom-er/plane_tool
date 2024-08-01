#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: setDrive.py
@date: 2024/5/22 21:12
@desc: 
"""
import bpy


def add_visibility_driver( target_object_name, control_property, a ):
    # 获取当前选定的对象
    selected_objects = bpy.context.selected_objects

    # 确保选中了至少一个对象
    if not selected_objects:
        print("请先选择一个或多个对象。")
        return

    # 获取控制对象
    control_object = bpy.data.objects.get(target_object_name)

    if not control_object:
        print(f"未找到名为 {target_object_name} 的控制对象。")
        return

    for i, obj in enumerate(selected_objects):
        # 为每个选定的对象添加驱动器
        driver = obj.driver_add("hide_viewport").driver
        var = driver.variables.new()
        var.name = 'var'
        var.type = 'SINGLE_PROP'
        target = var.targets[0]
        target.id = control_object
        target.data_path = f'["{control_property}"]'

        # 设置驱动器表达式
        driver.expression = f'var < {a}'

        print(
            f"已为 {obj.name} 添加驱动器，当 {control_object.name} 的属性 {control_property} 大于或等于 {i + 1} 时显示。")


# 使用示例
target_object_name = "light_VIS_CTrl"  # 控制对象的名称
control_property = "Light_VIS_Value"  # 控制属性的名称
a = 12
# 运行函数
add_visibility_driver(target_object_name, control_property, a)
