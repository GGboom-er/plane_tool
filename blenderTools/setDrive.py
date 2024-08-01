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
    # ��ȡ��ǰѡ���Ķ���
    selected_objects = bpy.context.selected_objects

    # ȷ��ѡ��������һ������
    if not selected_objects:
        print("����ѡ��һ����������")
        return

    # ��ȡ���ƶ���
    control_object = bpy.data.objects.get(target_object_name)

    if not control_object:
        print(f"δ�ҵ���Ϊ {target_object_name} �Ŀ��ƶ���")
        return

    for i, obj in enumerate(selected_objects):
        # Ϊÿ��ѡ���Ķ������������
        driver = obj.driver_add("hide_viewport").driver
        var = driver.variables.new()
        var.name = 'var'
        var.type = 'SINGLE_PROP'
        target = var.targets[0]
        target.id = control_object
        target.data_path = f'["{control_property}"]'

        # �������������ʽ
        driver.expression = f'var < {a}'

        print(
            f"��Ϊ {obj.name} ������������� {control_object.name} ������ {control_property} ���ڻ���� {i + 1} ʱ��ʾ��")


# ʹ��ʾ��
target_object_name = "light_VIS_CTrl"  # ���ƶ��������
control_property = "Light_VIS_Value"  # �������Ե�����
a = 12
# ���к���
add_visibility_driver(target_object_name, control_property, a)
