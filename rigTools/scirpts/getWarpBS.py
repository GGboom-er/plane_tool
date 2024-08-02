#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: getWarpBS.py
@date: 2024/8/2 13:11
@desc: 
"""
import maya.cmds as mc
bsA = 'blendShape1'
mod = mc.ls(sl =1)
bsAattr  = [c for idx, c in enumerate(mc.aliasAttr(bsA,q =1)) if (idx % 2) == 0]
grp = mc.group(n = bsA+'_grp',em =1)
for i in bsAattr:
    con = mc.listConnections(bsA+'.'+i,p =1,s =1,d =0)
    if con:
        mc.disconnectAttr(con[0],bsA+'.'+i)
    mc.setAttr(bsA+'.'+i,1)
    mc.parent(mc.duplicate(mod,n = i),grp)
    if con :
        mc.connectAttr(con[0],bsA+'.'+i)
    else:
        mc.setAttr(bsA+'.'+i,0)
mc.delete([i for i in mc.listHistory(mod,lv= 4) if mc.nodeType(i) == 'wrap'])
mc.blendShape(mc.listRelatives(grp,c =1)+mod,foc =1)
mc.delete(grp)
