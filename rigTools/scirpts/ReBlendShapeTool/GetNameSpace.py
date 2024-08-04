import maya.cmds as mc
import re


def GetNameSpace():
    sel = mc.ls(sl=1)
    selList = list()
    nameSpace = ''
    if sel:
        selList = [GetSplit(string=i)[-1] for i in sel]
        nameSpace = ''.join(GetSplit(string=sel[0])[:-1])
    return selList, nameSpace


def GetSplit(string='', pattern='(:)', maxsplit=0):
    return re.split(pattern, string, maxsplit)
