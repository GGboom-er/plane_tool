#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: attrSetsFn.py
@date: 2024/8/20 14:36
@desc: 
"""
import maya.cmds as cmds


def set_soft_limits_on_selected_attrs( min_value, max_value ):
    # ��ȡ��ǰѡ�������
    selected_objects = cmds.ls(selection=True)

    # ��ȡ��ǰѡ�������
    selected_channels = cmds.channelBox('mainChannelBox', query=True, selectedMainAttributes=True)

    if not selected_objects:
        cmds.warning("��ѡ������һ������")
        return

    if not selected_channels:
        cmds.warning("��ѡ������һ������")
        return

    for obj in selected_objects:
        for attr_name in selected_channels:
            # ��������·��
            attr_full_name = obj + '.' + attr_name

            # ��������Ƿ����
            if cmds.attributeQuery(attr_name, node=obj, exists=True):
                # ������߽�
                cmds.addAttr(attr_full_name, edit=True, hasMinValue=True, minValue=min_value)
                cmds.addAttr(attr_full_name, edit=True, hasMaxValue=True, maxValue=max_value)


# ʾ��ʹ�ã�
# ѡ�����������Ҫ���õ����ԣ�Ȼ����ú���������Сֵ�����ֵ
set_soft_limits_on_selected_attrs(-10, 10)
