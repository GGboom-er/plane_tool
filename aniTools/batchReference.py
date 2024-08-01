#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: batchReference.py
@date: 2024/7/25 13:40
@desc: 
"""
from __future__ import print_function
import maya.cmds as cmds


def import_file_for_each_vertex( file_path, target_object_name ):
    # ��ȡ��ǰѡ�������
    selection = cmds.ls(selection=True)
    if not selection:
        cmds.warning("����ѡ��һ���������壡")
        return

    # ��ȡѡ��������νڵ�
    shape_node = cmds.listRelatives(selection[0], shapes=True)[0]

    # ȷ��ѡ�����һ������
    if cmds.nodeType(shape_node) != 'mesh':
        cmds.warning("��ѡ��һ���������壡")
        return

    # ��ȡ����λ��
    vertex_positions = cmds.xform(selection[0] + ".vtx[*]", query=True, translation=True, worldSpace=True)
    vertex_count = len(vertex_positions) // 3
    print("��������: {}".format(vertex_count))

    # ����ÿ�����㲢�����ļ�����¼�����ռ�
    namespaces = []
    for i in range(vertex_count):
        namespace = "import_{}".format(i)
        cmds.file(file_path, r=True, namespace=namespace)  # �����÷�ʽ�����ļ�
        namespaces.append(namespace)

        # ��ȡ�������������
        imported_object = "{}:{}".format(namespace, target_object_name)

        if not cmds.objExists(imported_object):
            cmds.warning("�������ռ� {} ��δ�ҵ����� {}".format(namespace, target_object_name))
            continue

        # ���õ��������λ��Ϊ��ǰ����λ��
        pos = vertex_positions[i * 3:i * 3 + 3]
        cmds.xform(imported_object, translation=pos, worldSpace=True)
        print("���� {}: �����ļ� {}�������ռ� {}��λ�� {}".format(i, file_path, namespace, pos))

    return namespaces


# ���ú������滻Ϊ����ļ�·����Ŀ����������
imported_namespaces = import_file_for_each_vertex(r"U:\ywm\tbx\slrobot\rig_slrobtlowb_low.ma", "Main_Ctr")
print("����������ռ�: ", imported_namespaces)

# ʾ�����ʹ�õ���������ռ�
for ns in imported_namespaces:
    imported_objects = cmds.ls("{}:*".format(ns))
    print("�����ռ� {} ���������: {}".format(ns, imported_objects))
