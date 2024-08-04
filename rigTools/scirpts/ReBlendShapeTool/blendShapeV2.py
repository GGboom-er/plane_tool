# coding=utf-8
import maya.cmds as mc
import re
import maya.mel as mel
import pymel.core as pm
import mayaTools.compute as compute

class transferBs(object):
    def __init__( self ):
        self.returninfo = None

    @staticmethod
    def getDeformInfo( selMod=[] ):
        '''
            selMod => seleat obj
            ModInfo => ModName\ModPAthShapeName\ModShapeName\bsNodeList\skinClusterNodeList
        '''
        if selMod:
            pass
        else:
            selMod = mc.ls(sl=1)
        ModInfo = list()
        skinClusterNodeList = None
        if selMod:
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
    def getBelndShapeInfo( bsNodeList ):
        bsAttrInfoList = list()
        if bsNodeList:
            for i in range(len(bsNodeList)):
                bsNodeInfoDict = dict()
                bsNodeInfoDict['bsName'] = bsNodeList[i]
                aliasAttrinfo = mc.aliasAttr(bsNodeInfoDict['bsName'], q=1) or []
                aliasAttrweight = [c for idx, c in enumerate(aliasAttrinfo) if (idx % 2) != 0]
                aliasAttrList = [c for idx, c in enumerate(aliasAttrinfo) if
                                 (idx % 2) == 0]  # and not mc.getAttr(bsNodeInfoDict['bsName']+'.'+c,l =1)
                aliasConnectID = [str(re.sub(r'(\D)', '', i)) for i in aliasAttrweight]
                bsNodeInfoDict['bsAttr'] = {str(i): {} for i in aliasAttrList}
                bsNodeInfoDict['envelope'] = mc.getAttr(bsNodeInfoDict['bsName'] + '.envelope')
                bs_node = pm.PyNode(bsNodeInfoDict['bsName'])
                for idx, attr in enumerate(aliasAttrList):
                    bsNodeInfoDict['bsAttr'][attr]['lock'] = mc.getAttr(bsNodeInfoDict['bsName'] + '.' + attr, l=1)
                    bsNodeInfoDict['bsAttr'][attr]['value'] = mc.getAttr(bsNodeInfoDict['bsName'] + '.' + attr)
                    bsNodeInfoDict['bsAttr'][attr]['weight'] = 'weight[' + aliasConnectID[idx] + ']'
                    try:
                        bsNodeInfoDict['bsAttr'][attr]['InbetweenList'] = bs_node.targetItemIndexList(
                            aliasConnectID[idx], bs_node.getBaseObjects()[0])
                    except:
                        bsNodeInfoDict['bsAttr'][attr]['InbetweenList'] = None
                    try:
                        bsNodeInfoDict['bsAttr'][attr]['Input_Attrconnect'] = \
                            mc.listConnections(bsNodeInfoDict['bsName'] + '.' + attr, p=1, s=1, d=0)[0]
                    except:
                        bsNodeInfoDict['bsAttr'][attr]['Input_Attrconnect'] = None
                    try:
                        bsNodeInfoDict['bsAttr'][attr]['OutPut_Attrconnect'] = \
                            mc.listConnections(bsNodeInfoDict['bsName'] + '.' + attr, p=1, s=0, d=1)[0]
                    except:
                        bsNodeInfoDict['bsAttr'][attr]['OutPut_Attrconnect'] = None

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

    def connectAttrFn( self, type, start, end ):
        if type:
            mc.connectAttr(start, end)
        else:
            mc.disconnectAttr(start, end, f=1)

    def reBsShapeinfo( self, bsAttrInfoList, setType ):
        if bsAttrInfoList:
            for i in range(len(bsAttrInfoList)):
                for k, v in bsAttrInfoList[i]['bsAttr'].items():
                    if v['OutPut_Attrconnect'] and setType == 1:
                        OutPutCon = mc.listConnections(bsAttrInfoList[i]['bsName'] + '.' + k, p=1, s=0, d=1)
                        if OutPutCon and OutPutCon[0] == v['OutPut_Attrconnect']:
                            pass
                        else:
                            mc.connectAttr(bsAttrInfoList[i]['bsName'] + '.' + k, v['OutPut_Attrconnect'], f=1)
                    if v['Input_Attrconnect']:
                        connectType = mc.listConnections(bsAttrInfoList[i]['bsName'] + '.' + k, s=1, d=0, plugs=1)
                        if connectType and setType == 0:
                            mc.disconnectAttr(connectType[0], bsAttrInfoList[i]['bsName'] + '.' + k)
                            mc.setAttr(bsAttrInfoList[i]['bsName'] + '.' + k, 0)
                        else:
                            mc.connectAttr(v['Input_Attrconnect'], bsAttrInfoList[i]['bsName'] + '.' + k, f=1)
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

    def getSkinClusterinfo( self ):
        pass

    def unlockAttr( self, obj ):
        lockAttr = mc.listAttr(obj, l=1)
        for attr in lockAttr:
            mc.setAttr(obj + '.' + attr, l=0)

    def getOldBs( self, bsname ):
        pass

    def reBlendShapeNode( self, bsAttrInfoList, newObj, oldObj, deleteObjBs=1 ):
        global targetObjBsNode, targetObjShape, targetObjNode, newDeformobj
        for i in range(len(bsAttrInfoList)):
            old_BS_node = mc.rename(bsAttrInfoList[i]['bsName'], 'Pre_' + bsAttrInfoList[i]['bsName'])
            mc.setAttr(old_BS_node + '.envelope', 1)
            duplicateBsList = list()
            # print bsAttrInfoList[i]['bsName'] + '_new'
            newbsNode = bsAttrInfoList[i]['bsName']
            if not mc.objExists(newbsNode):
                mc.blendShape(newObj, n=newbsNode,
                              en=bsAttrInfoList[i]['envelope'], foc=1)
            newAttrobj = re.split('_New', oldObj, 0)[0] + '_New'
            if not mc.objExists(old_BS_node + '.' + newAttrobj):
                mc.duplicate(str(newObj), n=newAttrobj)
                mc.blendShape(old_BS_node, edit=True,
                              t=(
                                  oldObj, 999,
                                  newAttrobj, 1.0))
                mc.setAttr(old_BS_node + '.' + newAttrobj, 1)
            duplicateGrp = old_BS_node + '_Grp'
            if not mc.objExists(duplicateGrp):
                mc.group(n=duplicateGrp, empty=1)

            for k, v in bsAttrInfoList[i]['bsAttr'].items():
                if not mc.objExists(newbsNode + '.' + k):
                    mc.aliasAttr(k, newbsNode + '.' + v['weight'])
                    mc.setAttr(newbsNode + '.' + k, 0)
                if v['SourceConnectObj']:
                    targetObjShape = v['SourceConnectObj']
                    targetObjHistory = mc.listHistory(targetObjShape, pdo=1, gl=1, f=0, il=1)
                    targetObjNode = mc.ls(targetObjHistory, type=['skinCluster', 'cluster'])
                    targetObjBsNode = mc.ls(targetObjHistory, type='blendShape')
                if v['FinalConnect']:
                    newConnectAttr = re.sub(old_BS_node, newbsNode, v['FinalConnect'])
                    newDeformobj = str(oldObj) + '_newDeform'
                    if not mc.objExists(newDeformobj):
                        mc.duplicate(str(newObj), n=newDeformobj)
                        mc.parent(newDeformobj, duplicateGrp)
                    if targetObjBsNode:
                        targetObjBsNodeAttr = oldObj + '_New'
                        if mc.objExists(targetObjBsNode[0] + '.' + targetObjBsNodeAttr):

                            mel.eval("blendShapeDeleteTargetGroup %s %d" % (targetObjBsNode[0],
                                                                            int(re.findall(r'\[(.*?)\]', str(pm.PyNode(
                                                                                targetObjBsNode[
                                                                                    0] + '.' + targetObjBsNodeAttr)))[
                                                                                    0])))
                        mc.blendShape(targetObjBsNode[0], edit=True, t=(
                            targetObjShape, len(mc.aliasAttr(targetObjBsNode[0], q=1)) / 2 + 100, targetObjBsNodeAttr,
                            1.0), foc=1)
                        mc.setAttr(targetObjBsNode[0] + '.' + targetObjBsNodeAttr, 1)
                    else:
                        mc.blendShape(newDeformobj, v['SourceConnectObj'], n=k + '_newDform', en=1,
                                      foc=len(targetObjNode))
                        mc.setAttr(k + '_newDform' + '.' + newDeformobj, 1)
                    mc.connectAttr(v['SourceConnect'], newConnectAttr, f=1)
                else:
                    newDeformobj = None
                    duplicateName = old_BS_node + '_' + k
                    if not mc.objExists(duplicateName):
                        if not v['lock']:
                            oldAttr = mc.getAttr(old_BS_node + '.' + k)
                            mc.setAttr(old_BS_node + '.' + k, 1)
                            mc.duplicate(oldObj, n=duplicateName)
                            mc.parent(duplicateName, duplicateGrp)
                            mc.blendShape(newbsNode, edit=True,
                                          t=(newObj, int(re.sub(r'(\D)', '', v['weight'])), str(duplicateName), 1.0))
                            mc.aliasAttr(k, newbsNode + '.' + v['weight'])  # rename
                            if len(v['InbetweenList']) > 1:
                                for value in v['InbetweenList'][:-1]:
                                    inbetweenValue = (value - 5000) * 0.001
                                    # print inbetweenValue
                                    duplicate_InBetween_Name = old_BS_node + '_' + str(value) + '_' + k
                                    if not mc.objExists(duplicate_InBetween_Name):
                                        mc.setAttr(old_BS_node + '.' + k, inbetweenValue)
                                        mc.duplicate(oldObj, n=duplicate_InBetween_Name)
                                        mc.parent(duplicate_InBetween_Name, duplicateGrp)
                                        mc.blendShape(newbsNode, edit=True, ib=True,
                                                      t=(newObj, int(re.sub(r'(\D)', '', v['weight'])),
                                                         duplicate_InBetween_Name, inbetweenValue))

                            duplicateBsList.append(duplicateName)
                            mc.setAttr(old_BS_node + '.' + k, oldAttr)
            mc.setAttr(old_BS_node + '.envelope', 0)
            mel.eval("blendShapeDeleteTargetGroup %s %d" % (
                old_BS_node, 999))
            mc.delete(newAttrobj, newDeformobj)

            pre_bsAttrInfoList = dict(bsAttrInfoList[i])
            pre_bsAttrInfoList['bsName'] = old_BS_node
            self.reBsShapeinfo([pre_bsAttrInfoList], setType=1)
            mc.setAttr(old_BS_node + '.envelope', 1)
            if deleteObjBs:
                mc.delete(duplicateGrp)

    @staticmethod
    def getDeformInfo2( selMod=[] ):
        selModList, info = transferBs.getDeformInfo(selMod)
        return {selModList[x]: info[x] for x in range(len(selModList))}

    def transferBsFn( self, base_obj='', target_obj='' ):
        self.mathObjList = list()
        self.nomathObjList = list()
        self.base_obj = base_obj
        self.target_obj = target_obj
        try:
            mc.delete(mc.blendShape(self.base_obj, self.target_obj, n='test__BS__'))
            outerValue = compute.static_compare(self.base_obj, self.target_obj)
            if outerValue:

                self.returninfo = mc.confirmDialog(title='TransFormBlendShape', message=self.target_obj+u'\n绑定资产与新资产模型有\n%s\n差异，继续替换？'%outerValue,
                            button=['Yes', 'No'],
                            defaultButton='Yes', cancelButton='No', dismissString='No')
            if self.returninfo == 'No':
                self.nomathObjList.append(self.base_obj)
            else:
                self.mathObjList.append(self.base_obj)
        except:
            self.nomathObjList.append(self.base_obj)
        if self.mathObjList:
            self.selMod, self.objAttr = transferBs.getDeformInfo([self.base_obj])
            for i in range(len(self.objAttr)):
                if len(self.objAttr[i]['bsNodeList']) > 1:
                    mc.warning('BlendShapeNode has More!')
                    self.nomathObjList.append(self.base_obj)
                    break
                else:
                    self.bsAttrInfoList = transferBs.getBelndShapeInfo(self.objAttr[i]['bsNodeList'])
                    self.reBsShapeinfo(self.bsAttrInfoList, setType=0)
                    self.reBlendShapeNode(self.bsAttrInfoList, newObj=self.target_obj, oldObj=self.base_obj)
                    self.reBsShapeinfo(self.bsAttrInfoList, setType=1)

                    return self.objAttr[i]['bsNodeList'][0]
        elif self.nomathObjList:
            mc.warning('%s NO Match Obj!'%self.nomathObjList)
            return False

if __name__ == '__main__':
    a = transferBs()
    # b = a.getBelndShapeInfo(['blendShape1'])
    a.transferBsFn('baiyuecultistb_clothes5', 'baiyuecultistb_clothes3')
    # a.reBlendShapeNode(b,'pSphere10','pSphere1')
    # a.getDeformInfo2(['NewNamespace1:songtangcatsa_clothes5'])
    # a.reBsShapeinfo(b, setType=1)
    # transferBs.getDeformInfo2(['songtangcatsa_clothes2'])

































