import maya.cmds as mc
import re
import maya.mel as mel
import GetNameSpace


class ReModTool(object):
    def __init__(self, OldobjNameList, objPrefix):

        mathObjList = list()
        self.nomathObjList = list()
        # exitOldObj = [i for i in OldobjNameList if mc.objExists(i)]
        # print exitOldObj
        print objPrefix
        for i in OldobjNameList:
            try:
                try:
                    mc.delete(mc.blendShape(i, objPrefix + i, n='testBS'))
                    if len(objPrefix + i) == len(i):
                        mathObjList.append(objPrefix)
                    else:
                        mathObjList.append(i)
                except:
                    mc.delete(mc.blendShape(i, re.split(objPrefix, i)[-1], n='testBS'))
                    mathObjList.append(re.split(objPrefix, i)[-1])
            except:
                self.nomathObjList.append([i])
        #print mathObjList
        if mathObjList:
            mc.select(mathObjList)
            self.selMod, self.objAttr = ReModTool.getDeformInfo()

            for i in range(len(self.objAttr)):
                self.bsAttrInfoList = ReModTool.getBelndShapeInfo(self.objAttr[i]['bsNodeList'])
                self.reBsShapeinfo(self.bsAttrInfoList, setType=0)
                try:
                    self.reBlendShapeNode(self.bsAttrInfoList, newObj=objPrefix + self.selMod[i], oldObj=self.selMod[i])
                except:
                    self.reBlendShapeNode(self.bsAttrInfoList, newObj=re.split(objPrefix, self.selMod[i])[-1],
                                          oldObj=self.selMod[i])

                self.reBsShapeinfo(self.bsAttrInfoList, setType=1)
        else:
            mc.warning('NO Match Obj!')
        # print self.nomathObjList

    @staticmethod
    def getDeformInfo():
        selMod = mc.ls(sl=1)
        ModInfo = list()
        skinClusterNodeList = None
        if selMod:
            pass
        else:
            selMod = mc.ls(typ='mesh', g=1)
        for i in range(len(selMod)):
            ModDict = dict()
            bsNodeList = list()
            selType = mc.objectType(selMod[i])
            if selType == 'mesh':
                shapeName = selMod[i]
                ModDict['ModShapeName'] = selMod[i]
                ModDict['ModName'] = mc.listRelatives(selMod[i], p=1)[0]
                ModDict['ModPAthShapeName'] = mc.ls(selMod[i], l=1)
            elif selType == 'transform':
                try:
                    shapeName = mc.listRelatives(selMod[i], s=1)[0]
                except:
                    shapeName = list()
                ModDict['ModShapeName'] = shapeName
                ModDict['ModName'] = selMod[i]
                ModDict['ModPAthShapeName'] = mc.ls(shapeName, l=1)
            else:
                break
            shapeConType = None
            shapecon = mc.listConnections(ModDict['ModPAthShapeName'], d=1) or None
            if shapecon:
                shapeConType = [i for i in shapecon if mc.nodeType(i) == 'objectSet']
            if shapeConType:
                setList = mc.listConnections(
                    ModDict['ModShapeName'] + '.instObjGroups.objectGroups[*].objectGrpColor', d=0)
                DeformNodeList = [mc.listConnections(setNode + '.usedBy[0]', d=0)[0] for setNode in setList if
                                  mc.listConnections(setNode + '.usedBy[0]', d=0)]
                for node in DeformNodeList:
                    nodeType = mc.objectType(node)
                    if nodeType == 'skinCluster':
                        skinClusterNodeList = node
                    elif nodeType == 'blendShape':
                        bsNodeList.append(node)
                    else:
                        continue
            ModDict['skinClusterNodeList'] = skinClusterNodeList
            ModDict['bsNodeList'] = bsNodeList
            ModInfo.append(ModDict)
        return selMod, ModInfo

    @staticmethod
    def getBelndShapeInfo(bsNodeList):
        bsAttrInfoList = list()
        if bsNodeList:
            for i in range(len(bsNodeList)):
                bsNodeInfoDict = dict()
                bsNodeInfoDict['bsName'] = bsNodeList[i]
                aliasAttrinfo = mc.aliasAttr(bsNodeInfoDict['bsName'], q=1) or []

                aliasAttrweight = [c for idx, c in enumerate(aliasAttrinfo) if (idx % 2) != 0]
                # print aliasAttrweight
                aliasAttrList = [c for idx, c in enumerate(aliasAttrinfo) if
                                 (idx % 2) == 0]  # and not mc.getAttr(bsNodeInfoDict['bsName']+'.'+c,l =1)
                aliasConnectID = [str(re.sub(r'(\D)', '', i)) for i in aliasAttrweight]
                # print aliasConnectID
                bsNodeInfoDict['bsAttr'] = {str(i): {} for i in aliasAttrList}
                bsNodeInfoDict['envelope'] = mc.getAttr(bsNodeInfoDict['bsName'] + '.envelope')
                for idx, attr in enumerate(aliasAttrList):
                    bsNodeInfoDict['bsAttr'][attr]['lock'] = mc.getAttr(bsNodeInfoDict['bsName'] + '.' + attr, l=1)
                    bsNodeInfoDict['bsAttr'][attr]['value'] = mc.getAttr(bsNodeInfoDict['bsName'] + '.' + attr)
                    bsNodeInfoDict['bsAttr'][attr]['weight'] = 'weight[' + aliasConnectID[idx] + ']'
                    try:
                        bsNodeInfoDict['bsAttr'][attr]['Attrconnect'] = \
                            mc.listConnections(bsNodeInfoDict['bsName'] + '.' + attr, p=1, s=1)[0]
                    except:
                        bsNodeInfoDict['bsAttr'][attr]['Attrconnect'] = None
                    try:
                        bsNodeInfoDict['bsAttr'][attr]['FinalConnect'] = mc.listConnections(
                            bsNodeInfoDict['bsName'] + '.inputTarget[0].inputTargetGroup[' + aliasConnectID[
                                idx] + '].inputTargetItem[*].inputGeomTarget', s=1, d=0, plugs=1, c=1)[0]
                    except:
                        bsNodeInfoDict['bsAttr'][attr]['FinalConnect'] = None

                    if bsNodeInfoDict['bsAttr'][attr]['FinalConnect'] != None:
                        bsNodeInfoDict['bsAttr'][attr]['SourceConnect'] = \
                            mc.listConnections(bsNodeInfoDict['bsAttr'][attr]['FinalConnect'], s=1, d=1, plugs=1,
                                               c=0)[0]
                        bsNodeInfoDict['bsAttr'][attr]['SourceConnectObj'] = \
                            mc.listConnections(bsNodeInfoDict['bsAttr'][attr]['FinalConnect'], s=1)[0]
                    else:
                        bsNodeInfoDict['bsAttr'][attr]['SourceConnect'] = None
                        bsNodeInfoDict['bsAttr'][attr]['SourceConnectObj'] = None

                bsAttrInfoList.append(bsNodeInfoDict)
        return bsAttrInfoList

    def connectAttr(self, type, start, end):
        if type:
            mc.connectAttr(start, end)
        else:
            mc.disconnectAttr(start, end, f=1)

    def reBsShapeinfo(self, bsAttrInfoList, setType):
        if bsAttrInfoList:
            for i in range(len(bsAttrInfoList)):
                for k, v in bsAttrInfoList[i]['bsAttr'].items():
                    if v['Attrconnect']:
                        connectType = mc.listConnections(bsAttrInfoList[i]['bsName'] + '.' + k, s=1, d=0, plugs=1)
                        if connectType and setType == 0:
                            mc.disconnectAttr(connectType[0], bsAttrInfoList[i]['bsName'] + '.' + k)
                            mc.setAttr(bsAttrInfoList[i]['bsName'] + '.' + k, 0)
                        else:
                            mc.connectAttr(v['Attrconnect'], bsAttrInfoList[i]['bsName'] + '.' + k, f=1)
                    else:
                        if not setType:
                            if v['lock']:
                                mc.setAttr(bsAttrInfoList[i]['bsName'] + '.' + k, l=0)
                            mc.setAttr(bsAttrInfoList[i]['bsName'] + '.' + k, v['value'] * setType)
                        else:
                            try:
                                mc.setAttr(bsAttrInfoList[i]['bsName'] + '.' + k, v['value'] * setType)
                                mc.setAttr(bsAttrInfoList[i]['bsName'] + '.' + k, l=v['lock'])
                            except:
                                pass

    def getSkinClusterinfo(self):
        pass

    def unlockAttr(self, obj):
        lockAttr = mc.listAttr(obj, l=1)
        for attr in lockAttr:
            mc.setAttr(obj + '.' + attr, l=0)

    def getOldBs(self, bsname):
        pass

    def reBlendShapeNode(self, bsAttrInfoList, newObj, oldObj, deleteObjBs=1):
        for i in range(len(bsAttrInfoList)):
            mc.setAttr(bsAttrInfoList[i]['bsName'] + '.envelope', 1)
            duplicateBsList = list()
            # print bsAttrInfoList[i]['bsName'] + '_new'
            newbsNode = bsAttrInfoList[i]['bsName'] + '_new'
            if not mc.objExists(newbsNode):
                mc.blendShape(newObj, n=newbsNode,
                              en=bsAttrInfoList[i]['envelope'], foc=1)[0]
            newAttrobj = re.split('_New', oldObj, 0)[0] + '_New'
            if not mc.objExists(bsAttrInfoList[i]['bsName'] + '.' + newAttrobj):
                mc.duplicate(str(newObj), n=newAttrobj)
                mc.blendShape(bsAttrInfoList[i]['bsName'], edit=True,
                              t=(
                                  oldObj, len(mc.aliasAttr(bsAttrInfoList[i]['bsName'], q=1)) / 2 + 100,
                                  oldObj + '_New', 1.0))
                mc.setAttr(bsAttrInfoList[i]['bsName'] + '.' + oldObj + '_New', 1)
            duplicateGrp = bsAttrInfoList[i]['bsName'] + '_Grp'
            if not mc.objExists(duplicateGrp):
                mc.group(n=duplicateGrp, empty=1)

            for k, v in bsAttrInfoList[i]['bsAttr'].items():
                if not mc.objExists(newbsNode + '.' + k):
                    mc.aliasAttr(k, newbsNode + '.' + v['weight'])

                    mc.setAttr(newbsNode + '.' + k, 0)
                if v['SourceConnectObj']:
                    targetObjShape = v['SourceConnectObj']
                    targetObjHistory = mc.listHistory(targetObjShape, ha=1)
                    targetObjNode = mc.ls(targetObjHistory, type=['skinCluster', 'cluster'])
                    targetObjBsNode = mc.ls(targetObjHistory, type='blendShape')
                if v['FinalConnect'] and (targetObjNode or targetObjBsNode):
                    newConnectAttr = re.sub(bsAttrInfoList[i]['bsName'], newbsNode, v['FinalConnect'])
                    newDeformobj = str(oldObj) + '_newDeform'
                    if not mc.objExists(newDeformobj):
                        mc.duplicate(str(newObj), n=newDeformobj)
                        mc.parent(newDeformobj, duplicateGrp)
                    if targetObjBsNode:
                        mc.blendShape(targetObjBsNode[0], edit=True, t=(
                            targetObjShape, len(mc.aliasAttr(targetObjBsNode[0], q=1)) / 2 + 100, oldObj + '_New',
                            1.0), foc=1)
                        mc.setAttr(targetObjBsNode[0] + '.' + oldObj + '_New', 1)
                    else:
                        mc.blendShape(newDeformobj, v['SourceConnectObj'], n=k + '_newDform', en=1, foc=1)
                        mc.setAttr(k + '_newDform' + '.' + newDeformobj, 1)
                    mc.connectAttr(v['SourceConnect'], newConnectAttr, f=1)
                else:
                    newDeformobj = None
                    duplicateName = bsAttrInfoList[i]['bsName'] + '_' + k
                    if not mc.objExists(duplicateName):
                        if not v['lock']:
                            oldAttr = mc.getAttr(bsAttrInfoList[i]['bsName'] + '.' + k)
                            mc.setAttr(bsAttrInfoList[i]['bsName'] + '.' + k, 1)
                            mc.duplicate(oldObj, n=duplicateName)
                            mc.parent(duplicateName, duplicateGrp)
                            mc.blendShape(newbsNode, edit=True,
                                          t=(newObj, int(re.sub(r'(\D)', '', v['weight'])), str(duplicateName), 1.0))
                            mc.aliasAttr(k, newbsNode + '.' + v['weight'])
                            duplicateBsList.append(duplicateName)
                            mc.setAttr(bsAttrInfoList[i]['bsName'] + '.' + k, oldAttr)
            mc.setAttr(bsAttrInfoList[i]['bsName'] + '.envelope', 0)
            mel.eval("blendShapeDeleteTargetGroup %s %d" % (
                bsAttrInfoList[i]['bsName'], len(mc.aliasAttr(bsAttrInfoList[i]['bsName'], q=1)) / 2 + 99))
            mc.delete(newAttrobj, newDeformobj)
            self.reBsShapeinfo(self.bsAttrInfoList, setType=1)
            mc.setAttr(bsAttrInfoList[i]['bsName'] + '.envelope', 1)
            if deleteObjBs:
                mc.delete(duplicateGrp)
            bsAttrInfoList[i].update({'bsName': newbsNode})


if __name__ == '__main__':
    mathObjList = list()
    nomathObjList = list()
    a = ReModTool()
    OldobjNameList = GetNameSpace.GetNameSpace()[0]
    objPrefix = GetNameSpace.GetNameSpace()[1]
    exitOldObj = [i for i in OldobjNameList if mc.objExists(i)]
    for i in OldobjNameList:
        try:
            mc.delete(mc.blendShape(i, objPrefix + i, n='testBS'))
            mathObjList.append(i)
        except:
            nomathObjList.append([i, objPrefix + i])

    mc.select(mathObjList)
    b = a.getDeformInfo()

    for i in range(len(b)):
        bsAttrInfoList = a.getBelndShapeInfo(b[i]['bsNodeList'])
        a.reBsShapeinfo(bsAttrInfoList, setType=0)
        a.reBlendShapeNode(bsAttrInfoList, newObj=objPrefix + a.selMod[i], oldObj=a.selMod[i])
        a.reBsShapeinfo(bsAttrInfoList, setType=1)
