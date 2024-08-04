#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: texTureFN.py
@date: 2024/8/2 13:45
@desc: 
"""
import maya.cmds as cmds

def changeTextureFilePath( fileNodeList, oldName='', newName='' ):
    for i in fileNodeList:
        cmds.setAttr(i + '.fileTextureName', cmds.getAttr(i + '.fileTextureName').replace(oldName, newName),
                     type='string')
