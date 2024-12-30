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

def parent_objects_by_selection_order():
    """
    将选中的物体按照选中顺序进行父子层级关联
    """
    selected_objects = cmds.ls(selection=True)
    if not selected_objects or len(selected_objects) < 2:
        cmds.error("请至少选择两个对象进行父子层级关联")

    # 按照选中顺序进行父子关系设置
    for i in range(1, len(selected_objects)):
        try:
            cmds.parent(selected_objects[i], selected_objects[i - 1])
        except RuntimeError as e:
            cmds.warning("无法将 {} 设置为 {} 的子物体: {}".format(selected_objects[i], selected_objects[i - 1], e))

    # 显示消息，设置时间短一点（例如1秒）
    cmds.inViewMessage(amg="父子层级关联完成", pos="midCenter", fade=True, fadeStayTime=500)


if __name__ == "__main__":
    parent_objects_by_selection_order()#选择顺序搭建父子关系
    delete_custom_message_attributes()#删除自定义属性
