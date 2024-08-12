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
    # �������ж���
    for obj in bpy.data.objects:
        # ֻ�����������
        if obj.type == 'MESH':
            # ��ȡ��ǰ�����������������
            mesh_data_name = obj.data.name
            # ����Ŀ������
            target_name = f"{obj.name}Shape"

            # ��鲢�޸�������������
            if mesh_data_name != target_name:
                print(f"�޸� '{mesh_data_name}' Ϊ '{target_name}'")
                obj.data.name = target_name
            else:
                print(f"'{mesh_data_name}' �Ѿ�����ȷ������")


# ���к���
rename_mesh_data_to_object_name()
