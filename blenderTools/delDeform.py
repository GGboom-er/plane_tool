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
    # ���������е����ж���
    for obj in bpy.data.objects:
        # �������Ƿ�ΪMesh����
        if obj.type == 'MESH':
            # ��ȡ��������б�����
            for modifier in obj.modifiers:
                # ���ñ�����
                modifier.show_viewport = False
                modifier.show_render = False
                # ɾ��������
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_remove(modifier=modifier.name)

# ���ú���
disable_and_remove_modifiers()
