# coding = utf-8
import re
import maya.cmds as mc


def getAllMesh(selObj = None, take = 'Orig'):
    selObj = mc.ls(sl =1,s =1)
    if selObj == None:
        selObj = mc.ls(g = 1)

    return list(tuple([mc.listRelatives(i, p = 1)[0] for i in selObj if not re.search(take, i)]))


def getMatchObj(prefix = ''):
    allObj = getAllMesh(take = 'Orig')
    getMatch = [[i] for i in allObj if re.search(prefix, i,re.IGNORECASE)]
    obj = [re.split(prefix,i[0])[-1] for i in getMatch ]
    matchObj = [[i] if mc.objExists(i) else None for i in obj]
    return getMatch,matchObj

def checkPrefix(prefix = [],obj = []):
    matchObjList = list()

    nomatchObjList = list()
    for i in obj:
        prefixobjList = list()
        for pre in prefix:
            prefixObj = re.split(pre,i)[-1]
            if prefixObj == i:
                prefixObj = pre+i
            else:
                prefixObj,i = i,prefixObj
            if mc.objExists(prefixObj):
                try:
                    mc.delete(mc.blendShape(prefixObj, i, n = 'testBS'))
                    prefixobjList.append(prefixObj)

                except:
                    nomatchObjList.append(i)
        prefixobjList.append(i)
        matchObjList.append(prefixobjList)
    return matchObjList,nomatchObjList
def matchInfo(prefix = [],obj = []):
    pass

