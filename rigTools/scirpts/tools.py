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
    # ִ�к���
    delete_custom_message_attributes()

    :return:
    '''
    # ��ȡ��ѡ�ڵ��б�
    selected_nodes = cmds.ls(selection=True)

    if not selected_nodes:
        cmds.error("������ѡ��һ���ڵ㡣")
        return

    # ������ѡ�ڵ�
    for node in selected_nodes:
        # ��ȡ�ڵ��ϵ������Զ�������
        custom_attrs = cmds.listAttr(node, userDefined=True)

        if custom_attrs:
            for attr in custom_attrs:
                # ��������Ƿ�Ϊmessage����
                if cmds.getAttr(node + "." + attr, type=True) == "message":
                    # ɾ������
                    cmds.deleteAttr(node, attribute=attr)
                    print("Deleted message attribute: {}.{}".format(node, attr))

