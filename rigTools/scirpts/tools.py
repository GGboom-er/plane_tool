#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: tools.py
@date: 2023/12/18 15:21
@desc: 
"""
objects = makeList(cmds.ls(sl=True)) + makeList(cmds.ls(hl=True))
cmds.ngSkinRelax(objects, **{'numSteps' : 2,'stepSize' : 0.02})

import maya.cmds as cmds

def delete_custom_message_attributes():
    '''
    # 执行函数
    delete_custom_message_attributes()

    :return:
    '''
    # 获取所选节点列表
    selected_nodes = cmds.ls(selection=True)

    if not selected_nodes:
        cmds.error("请至少选择一个节点。")
        return

    # 遍历所选节点
    for node in selected_nodes:
        # 获取节点上的所有自定义属性
        custom_attrs = cmds.listAttr(node, userDefined=True)

        if custom_attrs:
            for attr in custom_attrs:
                # 检查属性是否为message类型
                if cmds.getAttr(node + "." + attr, type=True) == "message":
                    # 删除属性
                    cmds.deleteAttr(node, attribute=attr)
                    print("Deleted message attribute: {}.{}".format(node, attr))

