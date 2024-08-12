#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: fixUVset.py
@date: 2024/8/5 17:13
@desc: 
"""
import maya.cmds as cmds

def check_and_create_map1():
    # ��ȡ��ǰѡ�������
    selected_objects = cmds.ls(selection=True, dag=True, shapes=True)

    for obj in selected_objects:
        # ��ȡ�����UV��
        uv_sets = cmds.polyUVSet(obj, query=True, allUVSets=True)

        # ȷ������map1������������򴴽�
        if 'map1' not in uv_sets:
            cmds.polyUVSet(obj, create=True, uvSet='map1')
            print(f"UV set 'map1' created for {obj}.")

        # ��ȡ��ǰ��UV��
        current_uv_set = cmds.polyUVSet(obj, query=True, currentUVSet=True)[0]

        # �����ǰUV����Ϊmap1���������ݲ�ɾ����ǰ��
        if current_uv_set != 'map1':
            cmds.polyCopyUV(obj, uvSetNameInput=current_uv_set, uvSetName='map1')
            print(f"Copied UV set '{current_uv_set}' to 'map1' for {obj}.")
            cmds.polyUVSet(obj, delete=True, uvSet=current_uv_set)
            print(f"Deleted UV set '{current_uv_set}' for {obj}.")

        # �ٴμ�����е�UV����ȷ��û������UV��
        uv_sets = cmds.polyUVSet(obj, query=True, allUVSets=True)
        for uv_set in uv_sets:
            if uv_set != 'map1':
                cmds.polyUVSet(obj, delete=True, uvSet=uv_set)
                print(f"Deleted UV set '{uv_set}' for {obj}.")

        print(f"Final UV sets for {obj}: {cmds.polyUVSet(obj, query=True, allUVSets=True)}")

# ���к���
check_and_create_map1()
