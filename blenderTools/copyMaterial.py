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
    # ��ȡ��ǰѡ�еĶ����б�
    selected_objects = bpy.context.selected_objects

    # ����Ƿ����㹻�Ķ���ѡ��
    if len(selected_objects) < 2:
        print("������ѡ��������������һ���Ǽ�ѡ��Դ����")
        return

    # ��ȡ��ѡ��Դ����
    source_obj = bpy.context.active_object

    # Ŀ�����������ѡ�ж����У����˼�ѡ��Դ����֮��Ķ���
    target_objects = [obj for obj in selected_objects if obj != source_obj]

    # ���Դ�����Ƿ�Ϊ�������
    if source_obj is None or source_obj.type != 'MESH':
        print("��ѡ��Դ���󲻴��ڻ����������")
        return

    # ��ȡԴ����Ĳ����б�
    source_materials = source_obj.data.materials
    if not source_materials:
        print(f"Դ���� {source_obj.name} û�в��ʡ�")
        return

    # ��ȡԴ���������ʷ�����Ϣ
    source_material_assignments = [poly.material_index for poly in source_obj.data.polygons]

    # ����Ŀ������б�
    for target_obj in target_objects:
        if target_obj.type != 'MESH':
            print(f"Ŀ����� {target_obj.name} �����������������")
            continue

        # ���Ŀ�����Ĳ��ʲ�
        target_obj.data.materials.clear()

        # ���Ʋ��ʵ�Ŀ�����
        for material in source_materials:
            target_obj.data.materials.append(material)

        # ��������Ƿ�һ��
        if len(target_obj.data.polygons) != len(source_material_assignments):
            print(f"Ŀ����� {target_obj.name} ������Դ����ƥ�䣬�޷����Ʋ��ʷ��䡣")
            continue

        # ��������ʷ��䣺��һ��Ӧÿ����
        for i, poly in enumerate(target_obj.data.polygons):
            poly.material_index = source_material_assignments[i]

        print(f"�ѽ����ʺͷ���� {source_obj.name} ���Ƶ� {target_obj.name}")


# ���к���
copy_materials_and_assignments_to_selected()
