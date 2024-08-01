#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: fixReferenceName.py
@date: 2024/7/8 17:02
@desc: 
"""
import re
import maya.cmds as cmds
for i in cmds.ls(sl =1,type = 'reference'):
    newName = re.search(r'/([^/]+)\.ma', cmds.referenceQuery(i, filename=True)).group(1)
    cmds.lockNode(i,l =0)
    cmds.rename(i,newName+'RN')
    cmds.lockNode(newName+'RN',l =1)