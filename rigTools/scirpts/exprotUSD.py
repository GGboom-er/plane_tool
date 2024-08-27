#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: exprotUSD.py
@date: 2024/6/21 22:59
@desc: 
"""
import maya.cmds as cmds


def expotUSD( start=101, end=110, outPath=r'' ):
    options = (';exportUVs=1;exportSkels=none;exportSkin=none'
               ';exportBlendShapes=0;exportDisplayColor=0;exportColorSets=0'
               ';defaultMeshScheme=catmullClark;defaultUSDFormat=usdc;animation={is_ani}'
               ';eulerFilter=0;staticSingleSample=0;'
               ';startTime={start};endTime={end};frameStride=1;frameSample=0.0'
               ';parentScope=;shadingMode=useRegistry;exportInstances=1;convertMaterialsTo=[]'
               ';exportVisibility=1;mergeTransformAndShape=1;stripNamespaces={strip_namespace}'.format(is_ani=1,
                                                                                                       start=start,
                                                                                                       end=end,
                                                                                                       strip_namespace=1
                                                                                                       ))
    for i in cmds.ls(sl=1):
        cmds.select(cl=1)
        cmds.select(i)
        cmds.file(outPath + i.replace(':', '_'), force=1, options=options, typ='USD Export', preserveReferences=1,
                  exportSelected=1)


expotUSD(start=101, end=110, outPath=r'X:\Project\tbx\cache\\')