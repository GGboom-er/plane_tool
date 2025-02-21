#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: replaceAttr.py
@date: 2025/2/21 17:23
@desc: 
"""
import maya.cmds as cmds

def replace_custom_attr_values(old_str, new_str):
    """
    替换选中物体的自定义属性中包含的字符串。

    :param old_str: 要替换的字符串
    :param new_str: 替换后的字符串
    """
    # 获取当前选中的物体
    selected_objects = cmds.ls(selection=True)

    if not selected_objects:
        cmds.error("请先选择一个或多个对象！")
        return

    for obj in selected_objects:
        # 获取对象的自定义属性
        custom_attrs = cmds.listAttr(obj, userDefined=True)

        if not custom_attrs:
            print("对象 {} 没有自定义属性。".format(obj))
            continue

        for attr in custom_attrs:
            try:
                # 获取属性值
                attr_full_path = "{}.{}".format(obj, attr)
                value = cmds.getAttr(attr_full_path)
                # 检查属性值是否为字符串并进行替换
                if isinstance(value,basestring) and old_str in value:
                    new_value = value.replace(old_str, new_str)
                    cmds.setAttr(attr_full_path, new_value, type="string")
                    print("已更新 {}.{}: '{}' -> '{}'".format(obj, attr, value, new_value))

            except Exception as e:
                print("无法处理属性 {}：{}".format(attr, e))
# 示例用法：将选中物体的自定义属性中 'ccab' 替换为 'ccchangeab'
replace_custom_attr_values('ctpupilboya', 'ctboychange')
