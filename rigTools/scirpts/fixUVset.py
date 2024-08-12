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
    # 获取当前选择的物体
    selected_objects = cmds.ls(selection=True, dag=True, shapes=True)

    for obj in selected_objects:
        # 获取物体的UV集
        uv_sets = cmds.polyUVSet(obj, query=True, allUVSets=True)

        # 确保存在map1，如果不存在则创建
        if 'map1' not in uv_sets:
            cmds.polyUVSet(obj, create=True, uvSet='map1')
            print(f"UV set 'map1' created for {obj}.")

        # 获取当前的UV集
        current_uv_set = cmds.polyUVSet(obj, query=True, currentUVSet=True)[0]

        # 如果当前UV集不为map1，拷贝内容并删除当前集
        if current_uv_set != 'map1':
            cmds.polyCopyUV(obj, uvSetNameInput=current_uv_set, uvSetName='map1')
            print(f"Copied UV set '{current_uv_set}' to 'map1' for {obj}.")
            cmds.polyUVSet(obj, delete=True, uvSet=current_uv_set)
            print(f"Deleted UV set '{current_uv_set}' for {obj}.")

        # 再次检查所有的UV集，确保没有其他UV集
        uv_sets = cmds.polyUVSet(obj, query=True, allUVSets=True)
        for uv_set in uv_sets:
            if uv_set != 'map1':
                cmds.polyUVSet(obj, delete=True, uvSet=uv_set)
                print(f"Deleted UV set '{uv_set}' for {obj}.")

        print(f"Final UV sets for {obj}: {cmds.polyUVSet(obj, query=True, allUVSets=True)}")

# 运行函数
check_and_create_map1()
