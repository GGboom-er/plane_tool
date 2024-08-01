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