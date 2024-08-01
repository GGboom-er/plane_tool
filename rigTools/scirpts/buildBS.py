#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: buildBS.py
@date: 2024/4/15 17:25
@desc: 
"""
import maya.cmds as cmds


def create_blendshapes_from_groups( group_a, group_b ):
    models_a = cmds.listRelatives(group_a, allDescendents=True, type='mesh', fullPath=True)
    models_a = cmds.listRelatives(models_a, parent=True, fullPath=True)  # 获取变换节点
    models_b = cmds.listRelatives(group_b, allDescendents=True, type='mesh', fullPath=True)
    models_b = cmds.listRelatives(models_b, parent=True, fullPath=True)

    dict_a = {m.split(':')[-1]: m for m in models_a}
    dict_b = {m.split(':')[-1]: m for m in models_b}

    for name, model_a in dict_a.items():
        model_b = dict_b.get(name)
        if model_b:
            if cmds.polyEvaluate(model_a, vertex=True) == cmds.polyEvaluate(model_b, vertex=True):
                blendshape_name = "{}---CFXCheck---".format(name)
                blendshape_node = cmds.blendShape(model_a, model_b, name=blendshape_name)[0]
                cmds.setAttr("{}.weight[0]".format(blendshape_node), 1.0)
                print("Created and activated blendShape '{}' between '{}' and '{}'".format(blendshape_name, model_a,
                                                                                           model_b))
            else:
                print("Vertex count mismatch for '{}'".format(name))
        else:
            print("No matching model found for '{}' in group_b".format(name))


def on_create_blendshapes_pressed():
    selection = cmds.ls(selection=True, long=True)
    if len(selection) < 2:
        cmds.warning("Please select two groups.")
        return

    # Assuming the first selected is group_a and the second selected is group_b
    group_a = selection[0]
    group_b = selection[1]

    create_blendshapes_from_groups(group_a, group_b)


def create_blendshapes_ui():
    if cmds.window("blendShapeWindow", exists=True):
        cmds.deleteUI("blendShapeWindow", window=True)

    window = cmds.window("blendShapeWindow", title="Create BlendShapes", widthHeight=(200, 60))
    cmds.columnLayout(adjustableColumn=True)
    cmds.button(label="Create BlendShapes", command=lambda x: on_create_blendshapes_pressed())
    cmds.showWindow(window)


create_blendshapes_ui()
