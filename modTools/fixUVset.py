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
from __future__ import print_function  # 兼容 Python 2 和 Python 3
import maya.cmds as cmds

def ensure_single_uv_set(uv_set_name='map1'):
    # 获取当前选中的对象
    selected_objects = cmds.ls(selection=True, type='transform')

    if not selected_objects:
        cmds.warning("请先选择一个或多个网格对象。")
        return

    for obj in selected_objects:
        # 获取网格形状节点
        shapes = cmds.listRelatives(obj, shapes=True, type='mesh', fullPath=True)

        if not shapes:
            cmds.warning("{} 不是有效的网格对象。".format(obj))
            continue

        for shape in shapes:
            # 获取所有 UV 集
            uv_sets = cmds.polyUVSet(shape, query=True, allUVSets=True) or []
            current_uv = cmds.polyUVSet(shape, query=True, currentUVSet=True)[0]

            # 如果有多个 UV 集
            if len(uv_sets) > 1:
                print("检测到多个 UV 集：{} 在 {} 上。".format(uv_sets, obj))

                # 如果当前 UV 集不是 map1，则将其内容复制到 map1
                if current_uv != uv_set_name:
                    if uv_set_name not in uv_sets:
                        cmds.polyUVSet(shape, create=True, uvSetName=uv_set_name)
                    # 使用 select UV 并复制
                    cmds.polyUVSet(shape, currentUVSet=True, uvSet=current_uv)  # 切换到当前 UV 集
                    cmds.polyCopyUV(shape, uvSetName=uv_set_name, ch=False)  # 复制 UV 到 map1
                    print("已将 {} 复制为 {} 在 {} 上。".format(current_uv, uv_set_name, obj))

                # 删除其他多余的 UV 集，只保留 map1
                for uv_set in uv_sets:
                    if uv_set != uv_set_name:
                        cmds.polyUVSet(shape, delete=True, uvSet=uv_set)
                        print("已删除 {} 在 {} 上。".format(uv_set, obj))
            elif len(uv_sets) == 1 and uv_sets[0] != uv_set_name:
                # 如果只有一个 UV 集且不是 map1，则重命名为 map1
                cmds.polyUVSet(shape, rename=True, uvSet=uv_sets[0], newUVSet=uv_set_name)
                print("已将 {} 重命名为 {} 在 {} 上。".format(uv_sets[0], uv_set_name, obj))

    print("UV 集处理完成。")

# 运行脚本
ensure_single_uv_set()
