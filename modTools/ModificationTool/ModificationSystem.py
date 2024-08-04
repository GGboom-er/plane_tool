#!/usr/bin/env python
# _*_ coding:cp936 _*_
import CtrlSystem as cs, maya.api.OpenMaya as om, maya.mel as mel, re
import trasnSGInfo as tSG
reload(cs)
import maya.cmds as mc
import os
def load_plugin_if_not_loaded(plugin_name, plugin_path):
    """
    查询某个插件是否被加载，如果没有加载则从指定路径加载该插件。
    :param plugin_name: 插件名称（不带文件扩展名）
    :param plugin_path: 插件文件路径
    """
    if not mc.pluginInfo(plugin_name, query=True, loaded=True):
        try:
            mc.loadPlugin(plugin_path)
            print("插件 '{}' 已成功从路径 '{}' 加载。".format(plugin_name, plugin_path))
        except Exception as e:
            print("加载插件 '{}' 时出错: {}".format(plugin_name, str(e)))
    else:
        print("插件 '{}' 已经加载。".format(plugin_name))

plugin_path = os.path.dirname(__file__)+r"\extractDeltas.py"
load_plugin_if_not_loaded("extractDeltas", plugin_path)


class BSModifiTool(object):
    def __init__( self, deformerOrder=1, BSpart='L_eblow_90' ,createDrive = True,dirvenName = '',dirveValue = 1.0,dirAttr = '',oldDirveValue = 45.0):
        self.BSModifiSystem = '__BS_ModifiSystem_Grp'
        self.__obj, self.__objInfo = BSModifiTool.checkModDeformNode()
        if self.__obj:
            self.limitCtrlTX, self.limitCtrlTY = self.getModBoundingBox()
        self.__deformerOrder = deformerOrder
        self.BSModifiMainCtrlGrp = '__BS_ModifiMainCtrl_Grp'
        self.BSModifiModGrp = '__BS_ModifiBSMod_Grp'
        self.__BSpart = BSpart or 'newBS'
        self.BSModifiLimitCtrlName = self.__BSpart + '_BS_Ctrl'
        self.BSModifiPart = self.__BSpart + '_BS_Modifi_Offect'
        self.createDrive = createDrive
        self.dirvenName = dirvenName
        self.dirveValue = dirveValue
        self.dirAttr = dirAttr
        self.oldDirveValue = oldDirveValue
        self.panel = 'modelPanel5'
    def createBS( self ):
        if not mc.objExists(self.BSModifiSystem):
            mc.group(n=self.BSModifiSystem, em=1)
        mc.setAttr(self.BSModifiSystem + '.useOutlinerColor', 1)
        mc.setAttr(self.BSModifiSystem + '.outlinerColor', 1, 0, 0)
        if not mc.objExists(self.BSModifiModGrp):
            mc.group(n=self.BSModifiModGrp, em=1)
        mc.setAttr(self.BSModifiModGrp + '.useOutlinerColor', 1)
        mc.setAttr(self.BSModifiModGrp + '.outlinerColor', 1, 0, 0)

        self.BSModifiSystemChild = mc.listRelatives(self.BSModifiSystem, c=1) or []
        if self.BSModifiModGrp not in self.BSModifiSystemChild:
            mc.parent(self.BSModifiModGrp, self.BSModifiSystem)
        self.BSattrList = list()
        if self.panel:
            mc.isolateSelect(self.panel, state=True)
        for i in self.__objInfo:
            mc.setAttr(i['ModName'] + '.useOutlinerColor', 1)
            mc.setAttr(i['ModName'] + '.outlinerColor', 1, 0, 0)

            self.BSObjModGrp = i['ModName'] + '__BSMod__Grp'
            if not mc.objExists(self.BSObjModGrp):
                mc.group(n=self.BSObjModGrp, em=1)
            if mc.objExists(i['ModName']):
                BSModifiMod = '__'+self.__BSpart + '_' + i['ModName']
                BSObjModGrpChild = mc.listRelatives(self.BSObjModGrp, c=1) or []
                if BSModifiMod not in BSObjModGrpChild:
                    BSModifiTool.getShapeMod(i['ModName'], name=BSModifiMod)
                    mc.parent(BSModifiMod, self.BSObjModGrp)
                if len(i['bsNodeList']) < 1:
                    BSModifiNode = i['ModName'] + '_BSModifi_BSN_'
                    i['bsNodeList'].append(BSModifiNode)
                else:
                    BSModifiNode = i['bsNodeList'][(-1)]
                if not mc.objExists(BSModifiNode):
                    mc.blendShape(i['ModPAthShapeName'], foc=self.__deformerOrder, n=BSModifiNode)
                origShapeName = mc.listRelatives(i['ModName'], s=1)[(-1)]
                if origShapeName and mc.getAttr(origShapeName + '.intermediateObject'):
                    origShapePathName = mc.ls(origShapeName, l=1)[0]
                else:
                    origShapePathName = None
                mc.setAttr(i['ModName'] + '.v', 0)
                mc.setAttr(BSModifiMod + '.v', 1)

                mc.connectAttr(i['ModPAthShapeName'] + '.worldMesh[0]', BSModifiMod + '.inMesh', f=1)
                '''
                closedeform
                '''
                closeDeform = [mc.setAttr(j+'.envelope',0) for j in mc.listHistory(i['ModPAthShapeName'], lv=4) if mc.nodeType(j) in ['deltaMush']]
                tSG.copy_sg_components(i['ModName'], BSModifiMod)
                mc.isolateSelect(self.panel, addDagObject=BSModifiMod)
                self.BSattrList.append([BSModifiNode,
                                        BSModifiMod, i['ModName'],
                                        i['ModPAthShapeName'], origShapePathName,
                                        i['scNodeList']])
                BSModifiModGrpChild = mc.listRelatives(self.BSModifiModGrp, c=1) or []
                if self.BSObjModGrp not in BSModifiModGrpChild:
                    mc.parent(self.BSObjModGrp, self.BSModifiModGrp)
        mc.displayPref(displayGradient=1)
        mc.displayRGBColor("backgroundTop", 0.15, 0.15, 0.15)
        mc.displayRGBColor("backgroundBottom", 0.55, 0.55, 0.55)

        mc.select([i[1] for i in self.BSattrList])

    def buildConnectCtrl( self ):
        connectList = list()
        deltaShapeList = list()
        mc.displayPref(displayGradient=0)
        if self.__obj:
            for bsObjInfo in self.BSattrList:
                mc.setAttr(bsObjInfo[2] + '.useOutlinerColor', 1)
                mc.setAttr(bsObjInfo[2] + '.outlinerColor', 0, 1, 0)
                self.clearMeshInput(bsObjInfo[2], bsObjInfo[1])
                bsAliasAttr = mc.aliasAttr(bsObjInfo[0], q=1) or []
                if bsObjInfo[5]:
                    mc.setAttr(bsObjInfo[5] + '.envelope', 0)
                shapelist = [bsObjInfo[3], bsObjInfo[4]]
                selList = om.MSelectionList()
                for i in shapelist:
                    selList.add(i)
                Obj = selList.getDependNode(0)
                ObjFn = om.MFnMesh()
                ObjFn.setObject(Obj)
                ObjPoints = ObjFn.getPoints()
                intermediateObj = selList.getDependNode(1)
                intermediateFn = om.MFnMesh()
                intermediateFn.setObject(intermediateObj)
                intermediatePoints = intermediateFn.getPoints()
                mc.setAttr(bsObjInfo[0] + '.envelope', 0)
                ObjFn.setPoints(ObjPoints)
                if bsObjInfo[5]:
                    mc.setAttr(bsObjInfo[5] + '.envelope', 1)
                deltaShape = mc.extractDeltas(s=bsObjInfo[2], c=bsObjInfo[1])
                if bsObjInfo[5]:
                    mc.setAttr(bsObjInfo[5] + '.envelope', 0)
                ObjFn.setPoints(intermediatePoints)
                mc.setAttr(bsObjInfo[0] + '.envelope', 1)
                if deltaShape:
                    deltaShapeList.append(deltaShape)
                    if self.__BSpart in bsAliasAttr:
                        bsnodeNum = bsAliasAttr[bsAliasAttr.index(self.__BSpart) + 1]
                        bsWeightIndex = int(bsnodeNum.split('[')[1].split(']')[0])
                        bsInterValue = mc.getAttr(bsObjInfo[0] + '.it[0].itg[' + str(bsWeightIndex) + '].iti', mi=1) or None
                        if bsInterValue:
                            bsAttrValue = mc.getAttr(bsObjInfo[0] + '.' + self.__BSpart)
                            bsNodeinfo = BSModifiTool.getBelndShapeInfo(bsObjInfo[0])
                            BSModifiTool.reBsShapeinfo(bsNodeinfo, setType=0)
                            BSModifiTool.soloBs(bsNode=bsObjInfo[0], bsAttr=self.__BSpart, value=bsAttrValue)
                            if bsObjInfo[5]:
                                mc.setAttr(bsObjInfo[5] + '.envelope', 0)
                            bsAttrMod = BSModifiTool.getShapeMod(bsObjInfo[2], name=bsObjInfo[2] + '_' + self.__BSpart)[
                                0]
                            BSModifiTool.reBsShapeinfo(bsNodeinfo, setType=1)
                            if bsObjInfo[5]:
                                mc.setAttr(bsObjInfo[5] + '.envelope', 1)
                            origMod = BSModifiTool.getOrigShapeMod(bsObjInfo[4], name=self.__BSpart)[0]
                            BSModifiTool.removeBS(bsNode=bsObjInfo[0], bsAttr=self.__BSpart)
                            BSModifiTool.mergeBs(outputObj=origMod, inputObj=[bsAttrMod, deltaShape])
                            mc.blendShape(bsObjInfo[0], e=1, t=(bsObjInfo[2], int(bsWeightIndex), origMod, 1.0))
                            connectList.append(bsObjInfo[0] + '.w[' + str(bsWeightIndex) + ']')
                            mc.delete(origMod, bsObjInfo[1])
                    else:
                        bsNodeCList = mc.getAttr(bsObjInfo[0] + '.weight', mi=1)
                        if bsNodeCList:
                            bsWeightIndex = bsNodeCList[(-1)] + 1
                        else:
                            bsWeightIndex = 0
                        mc.blendShape(bsObjInfo[0], e=1, t=(bsObjInfo[2], int(bsWeightIndex), deltaShape, 1.0))
                        mc.delete(deltaShape, bsObjInfo[1])
                        num = 0
                        while self.__BSpart in bsAliasAttr:
                            num += 1
                            self.__BSpart = self.__BSpart + '_' + str(num)
                        mc.aliasAttr(self.__BSpart, bsObjInfo[0]  + '.w[' + str(bsWeightIndex) + ']')
                        connectList.append(bsObjInfo[0] + '.w[' + str(bsWeightIndex) + ']')
                if bsObjInfo[5]:
                    mc.setAttr(bsObjInfo[5] + '.envelope', 1)
                mc.setAttr(bsObjInfo[2] + '.v', 1)
                try:
                    mc.setAttr(self.BSModifiSystem + '.useOutlinerColor', 1)
                    mc.setAttr(self.BSModifiSystem + '.outlinerColor', 0, 1, 0)
                    mc.setAttr(self.BSModifiModGrp + '.useOutlinerColor', 1)
                    mc.setAttr(self.BSModifiModGrp + '.outlinerColor', 0, 1, 0)
                    '''
                    recover  deform
                    '''
                    recoverDeform = [mc.setAttr(i + '.envelope', 1) for i in mc.listHistory(bsObjInfo[2], lv=4) if
                                   mc.nodeType(i) in ['deltaMush']]
                    if self.panel:
                        mc.isolateSelect(self.panel, state=False)
                except:
                    pass
                try:
                    mc.delete(bsObjInfo[1])
                except:
                    pass
            if deltaShapeList :
                if  self.createDrive:
                    self.createCtrl()
                    for i in connectList:
                        mc.connectAttr(self.BSModifiLimitCtrlName + '.ty', i, f=1)
                    if self.BSModifiMainCtrlGrp not in self.BSModifiSystemChild:
                        mc.parent(self.BSModifiMainCtrlGrp, self.BSModifiSystem)
                    mc.select(cl=1)
                    mc.select(self.BSModifiLimitCtrlName)
                else:
                    if mc.objExists(self.dirvenName+'.'+self.dirAttr):
                        dirveFMNode = mc.createNode('setRange',n = self.__BSpart+'_SR_')
                        mc.setAttr(dirveFMNode+'.maxX',self.dirveValue)
                        mc.setAttr(dirveFMNode + '.oldMaxX', self.oldDirveValue)
                        mc.connectAttr(self.dirvenName + '.' + self.dirAttr, dirveFMNode + '.valueX')
                        for i in connectList:
                            mc.connectAttr(dirveFMNode + '.outValue.outValueX', i, f=1)
            else:
                mc.delete(self.BSObjModGrp, self.BSModifiModGrp)

            return 1
        return 0

    def clearMeshInput( self, obj, Bobj ):
        historyList = mc.listHistory(Bobj)
        objShape = mc.listRelatives(obj, s=1)[0]
        BobjShape = mc.listRelatives(Bobj, s=1)[0]
        if objShape in historyList:
            for i in historyList:
                nodetype = mc.nodeType(i)
                if nodetype == 'createColorSet' or nodetype == 'polyColorPerVertex':
                    mc.delete(i)

            if mc.isConnected(objShape + '.worldMesh[0]', BobjShape + '.inMesh'):
                mc.disconnectAttr(objShape + '.worldMesh[0]', BobjShape + '.inMesh')

    def setModDeformNode( self ):
        pass

    def getModBoundingBox( self ):
        objMaxX = max([mc.xform(i, bb=1, q=1)[3] for i in self.__obj])
        objMaxY = max([mc.xform(i, bb=1, q=1)[4] for i in self.__obj])
        return [abs(objMaxX), abs(objMaxY)]

    def createCtrl( self ):
        if mc.objExists(self.BSModifiLimitCtrlName):
            deftValue = mc.getAttr(self.BSModifiLimitCtrlName + '.ty')
        else:
            deftValue = 1
        if not mc.objExists(self.BSModifiMainCtrlGrp):
            mc.group(n=self.BSModifiMainCtrlGrp, em=1)
        mc.setAttr(self.BSModifiMainCtrlGrp + '.useOutlinerColor', 1)
        mc.setAttr(self.BSModifiMainCtrlGrp + '.outlinerColor', 1, 1, 0)
        AllBsCtrl = mc.listRelatives(self.BSModifiMainCtrlGrp, c=1) or []
        AllBsCtrlChild = len(AllBsCtrl)
        if AllBsCtrlChild > 0:
            moveSpan = AllBsCtrlChild * self.limitCtrlTX
        else:
            moveSpan = 0.0
        if not mc.objExists(self.BSModifiPart):
            mc.group(n=self.BSModifiPart, em=1)
        BSModifiLimitCtrl = cs.Ctrl()
        BSModifiLimitGrpName, self.BSModifiLimitCtrlName = BSModifiLimitCtrl.LimitCtrl(name=self.__BSpart,
                                                                                       ctrlPnt=BSModifiLimitCtrl.SpindleCurvePnt,
                                                                                       limitPnt=BSModifiLimitCtrl.RectangleCurvePnt,
                                                                                       deftValue=deftValue)
        BSModifiPartChild = mc.listRelatives(self.BSModifiPart, c=1) or []
        if BSModifiLimitGrpName not in BSModifiPartChild:
            mc.parent(BSModifiLimitGrpName, self.BSModifiPart)
        BSModifiMainCtrlChild = mc.listRelatives(self.BSModifiMainCtrlGrp, c=1) or []
        if self.BSModifiPart not in BSModifiMainCtrlChild:
            mc.parent(self.BSModifiPart, self.BSModifiMainCtrlGrp)
        mc.setAttr(self.BSModifiPart + '.tx', self.limitCtrlTX * 1.2 + moveSpan)
        mc.setAttr(self.BSModifiPart + '.ty', self.limitCtrlTY)
        mc.setAttr(self.BSModifiPart + '.s', self.limitCtrlTX / 2, self.limitCtrlTX / 2, self.limitCtrlTX / 2)
        return 0

    @staticmethod
    def checkModDeformNode():
        selMod = [i for i in mc.ls(sl=1, dag=1, tr=1) if mc.listRelatives(i, s=1, type='mesh')]
        ModInfo = list()
        for i in range(len(selMod)):
            ModDict = dict()
            bsNodeList = list()
            scNode = None
            selType = mc.objectType(selMod[i])
            if selType == 'transform':
                try:
                    shapeName = mc.listRelatives(selMod[i], s=1)[0]
                except:
                    shapeName = list()

            else:
                break
            ModDict['ModShapeName'] = str(shapeName)
            ModDict['ModName'] = str(selMod[i])
            ModDict['ModPAthShapeName'] = str(mc.ls(shapeName, l=1)[0])
            shapeConType = None
            shapecon = mc.listConnections(ModDict['ModPAthShapeName'], d=1) or None
            if shapecon:
                shapeConType = [i for i in shapecon if mc.nodeType(i) == 'objectSet']
            if shapeConType:
                setList = mc.listConnections(ModDict['ModShapeName'] + '.instObjGroups.objectGroups[*].objectGrpColor',
                                             d=0)
                DeformNodeList = [mc.listConnections(setNode + '.usedBy[0]', d=0)[0] for setNode in setList if
                                  mc.listConnections(setNode + '.usedBy[0]', d=0)
                                  ]
                for node in DeformNodeList:
                    nodeType = mc.objectType(node)
                    if nodeType == 'skinCluster':
                        scNode = node
                    elif nodeType == 'blendShape':
                        bsNodeList.append(node)
                    else:
                        continue

            ModDict['scNodeList'] = scNode
            ModDict['bsNodeList'] = bsNodeList
            ModInfo.append(ModDict)

        return (selMod, ModInfo)

    @staticmethod
    def getBelndShapeInfo( bsNode ):
        if mc.objExists(bsNode):
            bsNodeInfoDict = dict()
            bsNodeInfoDict['bsName'] = bsNode
            aliasAttrinfo = mc.aliasAttr(bsNodeInfoDict['bsName'], q=1) or []
            aliasAttrweight = [c for idx, c in enumerate(aliasAttrinfo) if idx % 2 != 0]
            aliasAttrList = [c for idx, c in enumerate(aliasAttrinfo) if idx % 2 == 0
                             ]
            aliasConnectID = [str(re.sub('(\\D)', '', i)) for i in aliasAttrweight]
            bsNodeInfoDict['bsAttr'] = {str(i): {} for i in aliasAttrList}
            bsNodeInfoDict['envelope'] = mc.getAttr(bsNodeInfoDict['bsName'] + '.envelope')
            for idx, attr in enumerate(aliasAttrList):
                bsNodeInfoDict['bsAttr'][attr]['lock'] = mc.getAttr(bsNodeInfoDict['bsName'] + '.' + attr, l=1)
                bsNodeInfoDict['bsAttr'][attr]['value'] = mc.getAttr(bsNodeInfoDict['bsName'] + '.' + attr)
                bsNodeInfoDict['bsAttr'][attr]['weight'] = 'weight[' + aliasConnectID[idx] + ']'
                try:
                    bsNodeInfoDict['bsAttr'][attr]['Attrconnect'] = \
                        mc.listConnections(bsNodeInfoDict['bsName'] + '.' + attr, p=1, s=1,d =0)[0]
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
                        mc.listConnections(bsNodeInfoDict['bsAttr'][attr]['FinalConnect'], s=1, d=1, plugs=1, c=0)[0]
                    bsNodeInfoDict['bsAttr'][attr]['SourceConnectObj'] = \
                        mc.listConnections(bsNodeInfoDict['bsAttr'][attr]['FinalConnect'], s=1)[0]
                else:
                    bsNodeInfoDict['bsAttr'][attr]['SourceConnect'] = None
                    bsNodeInfoDict['bsAttr'][attr]['SourceConnectObj'] = None

            return bsNodeInfoDict

    @staticmethod
    def reBsShapeinfo( bsNodeInfoDict, setType ):
        for k, v in bsNodeInfoDict['bsAttr'].items():
            if v['Attrconnect']:
                connectType = mc.listConnections(bsNodeInfoDict['bsName'] + '.' + k, s=1, d=0, plugs=1)
                if connectType and setType == 0:
                    mc.disconnectAttr(connectType[0], bsNodeInfoDict['bsName'] + '.' + k)
                    mc.setAttr(bsNodeInfoDict['bsName'] + '.' + k, 0)
                else:
                    mc.connectAttr(v['Attrconnect'], bsNodeInfoDict['bsName'] + '.' + k, f=1)
            elif not setType:
                if v['lock']:
                    mc.setAttr(bsNodeInfoDict['bsName'] + '.' + k, l=0)
                mc.setAttr(bsNodeInfoDict['bsName'] + '.' + k, v['value'] * setType)
            else:
                try:
                    mc.setAttr(bsNodeInfoDict['bsName'] + '.' + k, v['value'] * setType)
                    mc.setAttr(bsNodeInfoDict['bsName'] + '.' + k, l=v['lock'])
                except:
                    pass

    @staticmethod
    def getShapeMod( sourceMod, name=None ):
        transformName = mc.duplicate(sourceMod, n=name)[0]
        AllshapeName = mc.listRelatives(transformName, s=1)
        if len(AllshapeName) > 1:
            mc.delete(AllshapeName[1:])
        mc.setAttr(transformName + '.tx', l=0)
        mc.setAttr(transformName + '.ty', l=0)
        mc.setAttr(transformName + '.tz', l=0)
        mc.setAttr(transformName + '.rx', l=0)
        mc.setAttr(transformName + '.rz', l=0)
        mc.setAttr(transformName + '.ry', l=0)
        mc.setAttr(transformName + '.sx', l=0)
        mc.setAttr(transformName + '.sy', l=0)
        mc.setAttr(transformName + '.sz', l=0)
        mc.setAttr(transformName + '.v', l=0)
        mc.sets(transformName, e=1, fe='initialShadingGroup')
        return [transformName, AllshapeName[0]]

    @staticmethod
    def getOrigShapeMod( origname, name=None ):
        transformName = mc.createNode('transform', n=name)
        OrigShape = mc.createNode('mesh', n=name + 'Shape', p=transformName)
        mc.connectAttr(origname + '.worldMesh[0]', OrigShape + '.inMesh', f=1)
        mc.setAttr(transformName + '.v', 0)
        mc.refresh()
        mc.disconnectAttr(origname + '.worldMesh[0]', OrigShape + '.inMesh')
        return [transformName, OrigShape]

    @staticmethod
    def soloBs( bsNode='', bsAttr='', value=1 ):
        bsAllAttr = mc.aliasAttr(bsNode, q=1)
        if bsAttr in bsAllAttr:
            bsWeightIndex = mc.getAttr(bsNode + '.weight', mi=1)
            for w in bsWeightIndex:
                try:
                    mc.setAttr(bsNode + '.weight[%s]' % w, 0)
                except:
                    mc.setAttr(bsNode + '.weight[%s]' % w, l=0)

            mc.setAttr(bsNode + '.' + bsAttr, value)

    @staticmethod
    def removeBS( bsNode='', bsAttr='' ):
        bsAllAttr = mc.aliasAttr(bsNode, q=1)
        if bsAllAttr:
            try:
                bsIndex = bsAllAttr[bsAllAttr.index(bsAttr) + 1]
                bsWeightIndex = bsIndex.split('[')[1].split(']')[0]
                mel.eval('blendShapeDeleteTargetGroup %s %d' % (
                    bsNode, int(bsWeightIndex)))
            except:
                mc.warning('---{' + bsNode + '}--- not has %s attr!' % bsAttr)

    @staticmethod
    def mergeBs( outputObj='', inputObj=[] ):
        mergeBSNode = mc.blendShape(outputObj, n='mergeBS')[0]
        for i in range(len(inputObj)):
            mc.blendShape(mergeBSNode, e=1, t=(outputObj, i, inputObj[i], 1.0))
            mc.setAttr(mergeBSNode + '.' + inputObj[i], 1)

        mc.delete(outputObj, ch=1)
        mc.delete(inputObj)
        return outputObj


class ExtractionLineTool(object):

    def __init__( self, PositionMould=1, visibilityMould=1 ):
        self.__obj = self.getObj()
        if self.__obj:
            self.limitCtrlTX, self.limitCtrlTY = self.getModBoundingBox()
        self.ETLSystemGrp = 'ETLSystemGrp'

    def getObj( self ):
        selMod = [i for i in mc.ls(sl=1, dag=1, tr=1) if mc.listRelatives(i, s=1, type='mesh')]
        return selMod

    def checkShader( self ):
        self.shaderList = list()
        if self.__obj:
            for obj in self.__obj:
                objShape = mc.listRelatives(obj, s=1)[0]
                try:
                    instGroupList = mc.listConnections(objShape + '.instObjGroups[*]', p=1) or []
                except:
                    instGroupList = list()

                try:
                    objGroupList = mc.listConnections(objShape + '.instObjGroups[0].objectGroups[*]', p=1) or []
                except:
                    objGroupList = list()

                objShaderList = instGroupList + objGroupList
                if objShaderList:
                    for i in objShaderList:
                        shadingEngineNode = i.split('.')
                        if mc.nodeType(shadingEngineNode[0]) == 'shadingEngine':
                            shader = mc.listConnections(shadingEngineNode[0] + '.surfaceShader')[0]
                            if mc.nodeType(shader) == 'RedshiftMaterial':
                                self.shaderList.append(shader)
                            else:
                                self.shaderList.append(self.createShaderNode(obj))

    def createShaderNode( self, obj ):
        shader = ExtractionLineTool.createShader(obj)
        layerNode = mc.shadingNode('layeredTexture', at=1)
        mc.connectAttr(layerNode + '.outColor', shader + '.diffuse_color', f=1)
        return shader

    def addFile( self, name='file', filePath='' ):
        fileNode = mc.shadingNode('file', isColorManaged=1, at=1, n=name)
        textureNode = mc.shadingNode('place2dTexture', au=1, n='PT_' + name)
        mc.connectAttr(textureNode + '.coverage', fileNode + '.coverage', f=1)
        mc.connectAttr(textureNode + '.translateFrame', fileNode + '.translateFrame', f=1)
        mc.connectAttr(textureNode + '.rotateFrame', fileNode + '.rotateFrame', f=1)
        mc.connectAttr(textureNode + '.mirrorU', fileNode + '.mirrorU', f=1)
        mc.connectAttr(textureNode + '.mirrorV', fileNode + '.mirrorV', f=1)
        mc.connectAttr(textureNode + '.stagger', fileNode + '.stagger', f=1)
        mc.connectAttr(textureNode + '.wrapU', fileNode + '.wrapU', f=1)
        mc.connectAttr(textureNode + '.wrapV', fileNode + '.wrapV', f=1)
        mc.connectAttr(textureNode + '.repeatUV', fileNode + '.repeatUV', f=1)
        mc.connectAttr(textureNode + '.offset', fileNode + '.offset', f=1)
        mc.connectAttr(textureNode + '.rotateUV', fileNode + '.rotateUV', f=1)
        mc.connectAttr(textureNode + '.noiseUV', fileNode + '.noiseUV', f=1)
        mc.connectAttr(textureNode + '.vertexUvOne', fileNode + '.vertexUvOne', f=1)
        mc.connectAttr(textureNode + '.vertexUvTwo', fileNode + '.vertexUvTwo', f=1)
        mc.connectAttr(textureNode + '.vertexUvThree', fileNode + '.vertexUvThree', f=1)
        mc.connectAttr(textureNode + '.vertexCameraOne', fileNode + '.vertexCameraOne', f=1)
        mc.connectAttr(textureNode + '.outUV', fileNode + '.uv', f=1)
        mc.connectAttr(textureNode + '.outUvFilterSize', fileNode + '.uvFilterSize', f=1)
        self.createCtrl(name=fileNode)
        mc.connectAttr(self.ETlCtrlName + '.ty', fileNode + '.alphaGain')
        return fileNode

    def conNode( self, newFile, layerNode, order=0 ):
        numList = mc.getAttr(layerNode + '.inputs', mi=1) or []
        niceList = list()
        for i in numList:
            con = mc.listConnections(layerNode + '.inputs[' + str(i) + '].color', s=1)
            if con:
                niceList.append(con[0])

        mc.removeMultiInstance(layerNode + '.inputs', b=1)
        niceList.insert(order, newFile)
        for node in enumerate(niceList):
            mc.connectAttr(node[1] + '.outColor', layerNode + '.inputs[' + str(node[0]) + '].color', f=1)
            mc.connectAttr(node[1] + '.outColor', layerNode + '.inputs[' + str(node[0]) + '].alpha', f=1)

        return nicelist

    def buildCtrl( self ):
        self.checkShader()
        if not mc.objExists(self.ETLSystemGrp):
            self.ETLSystemGrp = mc.createNode('transform', n=self.ETLSystemGrp)
        shaderDict = dict()
        for shader in self.shaderList:
            shaderTextureNode = mc.listConnections(shader + '.diffuse_color', s=1)
            for node in shaderTextureNode:
                self.ETLMainCtrlGrp = node + '_ETLMainCtrlGrp'
                if not mc.objExists(self.ETLMainCtrlGrp):
                    mc.createNode('transform', n=self.ETLMainCtrlGrp)
                textuerOrder = mc.getAttr(node + '.inputs', mi=1)
                textureList = list()
                if textuerOrder:
                    for i in textuerOrder:
                        con = mc.listConnections(node + '.inputs[' + str(i) + '].color', s=1)
                        if con:
                            textureList.append(con[0])

                    for texture in textureList:
                        self.ETLpart = texture + '_Offect'
                        if not mc.objExists(self.ETLpart):
                            self.createCtrl(name=texture)
                            mc.connectAttr(self.ETlCtrlName + '.ty', texture + '.alphaGain', f=1)

                else:
                    mc.delete(self.ETLMainCtrlGrp)
                shaderDict[shader] = textureList

        return shaderDict

    def getModBoundingBox( self ):
        objMaxX = max([abs(mc.xform(i, bb=1, q=1)[3]) for i in self.__obj])
        objMaxY = max([abs(mc.xform(i, bb=1, q=1)[4]) for i in self.__obj])
        return [objMaxX, objMaxY]

    def createCtrl( self, name ):
        deftValue = mc.getAttr(name + '.alphaGain')
        AllBsCtrl = mc.listRelatives(self.ETLMainCtrlGrp, c=1) or []
        AllBsCtrlChild = len(AllBsCtrl)
        if AllBsCtrlChild > 0:
            moveSpan = AllBsCtrlChild * self.limitCtrlTX
        else:
            moveSpan = 0.0
        if not mc.objExists(self.ETLpart):
            mc.group(n=self.ETLpart, em=1)
        ALineLimitCtrl = cs.Ctrl()
        ALineLimitCtrlGrpName, self.ETlCtrlName = ALineLimitCtrl.LimitCtrl(name=name, action='ETLine',
                                                                           ctrlPnt=ALineLimitCtrl.OctagonalCurvePnt,
                                                                           limitPnt=ALineLimitCtrl.RectangleCurvePnt,
                                                                           deftValue=deftValue)
        ALinePartChild = mc.listRelatives(self.ETLpart, c=1) or []
        if ALineLimitCtrlGrpName not in ALinePartChild:
            mc.parent(ALineLimitCtrlGrpName, self.ETLpart)
        ALineCtrlChild = mc.listRelatives(self.ETLMainCtrlGrp, c=1) or []
        if self.ETLpart not in ALineCtrlChild:
            mc.parent(self.ETLpart, self.ETLMainCtrlGrp)
        ETLSystemGrpChild = mc.listRelatives(self.ETLSystemGrp, c=1) or []
        if self.ETLMainCtrlGrp not in ETLSystemGrpChild:
            mc.parent(self.ETLMainCtrlGrp, self.ETLSystemGrp)
        mc.setAttr(self.ETLpart + '.tx', self.limitCtrlTX * 1.3 + moveSpan)
        mc.setAttr(self.ETLpart + '.ty', self.limitCtrlTY + self.limitCtrlTX)
        mc.setAttr(self.ETLpart + '.s', self.limitCtrlTX / 2, self.limitCtrlTX / 2, self.limitCtrlTX / 2)
        return 0

    @staticmethod
    def createShader( obj ):
        shader = '%s__RsShader__' % obj
        if not mc.objExists(shader):
            shader = mc.shadingNode('RedshiftMaterial', asShader=True, n=shader)
        sgNode = '%sSG' % shader
        if not mc.objExists(sgNode):
            sgNode = mc.sets(renderable=True, noSurfaceShader=True, empty=True, name=sgNode)
        mc.defaultNavigation(connectToExisting=True, source=shader, destination=sgNode)
        mc.select(obj, r=1)
        mc.sets(e=True, forceElement=sgNode)
        return shader


class TraceLineTool(object):

    def __init__( self, part='face', PLSN=1 ):
        self.__part = part
        self.PLSN = PLSN
        if self.PLSN:
            self.__obj = mc.listConnections(part + '.objects[*]', s=1) or None
            self.LineSetNode = self.__part
            self.PBSVNode = mc.listConnections(self.LineSetNode + '.lineData[0].brushSettings', s=1)[0] or None
            self.PBSHNode = mc.listConnections(self.LineSetNode + '.lineData[1].brushSettings', s=1)[0] or None
            self.PBDVNode = mc.listConnections(self.PBSVNode + '.brushDetails', s=1)[0] or None
            self.PBDHNode = mc.listConnections(self.PBSVNode + '.brushDetails', s=1)[0] or None
        else:
            self.__obj = self.getObj()
            self.__PLNode = 'PencilLineNode'
            self.__PLSetNode = 'PencilLineSet'
            self.PBDVNode = self.__part + '_PBD_Visible'
            self.PBDHNode = self.__part + '_PBD_Hidden'
            self.PBSVNode = self.__part + '_PBS_Visible'
            self.PBSHNode = self.__part + '_PBS_Hidden'
            self.LineSetNode = self.__part + '_LineSet'
        self.TraceLineSystemGrp = 'TraceLineSystemGrp'
        self.ELineLimitCtrlName = self.__part + '_ELineLimitCtrl'
        self.ELineMainCtrlGrp = self.__part + '_ELineMainCtrl_Grp'
        self.ELinePart = self.__part + '_ELineMainCtrl_Offect'
        return

    @property
    def PLNode( self ):
        return self.__PLNode

    @property
    def PLSetNode( self ):
        return self.__PLSetNode

    def getObj( self ):
        selMod = [i for i in mc.ls(sl=1, dag=1, tr=1) if mc.listRelatives(i, s=1, type='mesh')]
        return selMod

    def createPLNode( self ):
        if not mc.objExists(self.PLNode):
            mc.createNode('PencilLine', n='PencilLineNode')
        if not mc.objExists(self.PLSetNode):
            mc.createNode('objectSet', n='PencilLineSet')
        mc.sets(self.PLNode, e=1, fe=self.PLSetNode)

    def createLineNode( self ):
        if not mc.objExists(self.PBDVNode):
            mc.createNode('PencilBrushDetail', n=self.PBDVNode)
        if not mc.objExists(self.PBDHNode):
            mc.createNode('PencilBrushDetail', n=self.PBDHNode)
        if not mc.objExists(self.PBSVNode):
            mc.createNode('PencilBrushSettings', n=self.PBSVNode)
        if not mc.objExists(self.PBSHNode):
            mc.createNode('PencilBrushSettings', n=self.PBSHNode)
        if not mc.objExists(self.LineSetNode):
            mc.createNode('PencilLineSet', n=self.LineSetNode)
        mc.connectAttr(self.PBDVNode + '.message', self.PBSVNode + '.brushDetails', f=1)
        mc.connectAttr(self.PBDHNode + '.message', self.PBSHNode + '.brushDetails', f=1)
        mc.connectAttr(self.PBSVNode + '.message', self.LineSetNode + '.lineData[' + str(0) + '].brushSettings', f=1)
        mc.connectAttr(self.PBSHNode + '.message', self.LineSetNode + '.lineData[' + str(1) + '].brushSettings', f=1)

    def connectNode( self ):
        if self.__obj:
            self.limitCtrlTX, self.limitCtrlTY = self.getModBoundingBox()
            if not mc.objExists(self.TraceLineSystemGrp):
                mc.createNode('transform', n=self.TraceLineSystemGrp)
            if self.PLSN:
                deftValue = mc.getAttr(self.PBDVNode + '.srBezierControlPoints[1].srBezierRightHandleY')
            else:
                self.createPLNode()
                self.createLineNode()
                deftValue = 1
                PLNumList = mc.getAttr(self.__PLNode + '.lineSets', mi=1) or [0]
                isCon = mc.listConnections(self.LineSetNode + '.message', c=1) or []
                if self.__PLNode not in isCon:
                    mc.connectAttr(self.LineSetNode + '.message',
                                   self.__PLNode + '.lineSets[' + str(max(PLNumList) + 1) + ']', f=1)
                for i in self.__obj:
                    objMEssage = mc.listConnections(i + '.message', p=1) or []
                    for con in objMEssage:
                        conNode = con.split('.')
                        if mc.nodeType(conNode[0]) == 'PencilLineSet':
                            mc.disconnectAttr(i + '.message', con)

                    LineSetNumList = mc.getAttr(self.LineSetNode + '.objects', mi=1) or [0]
                    mc.connectAttr(i + '.message', self.LineSetNode + '.objects[' + str(max(LineSetNumList) + 1) + ']',
                                   f=1)

            self.createCtrl(deftValue)
            mc.connectAttr(self.ELineLimitCtrlName + '.ty', self.LineSetNode + '.on')

    def getModBoundingBox( self ):
        objMaxX = max([mc.xform(i, bb=1, q=1)[3] for i in self.__obj])
        objMaxY = max([mc.xform(i, bb=1, q=1)[4] for i in self.__obj])
        return [abs(objMaxX), abs(objMaxY)]

    def createCtrl( self, deftValue ):
        if mc.objExists(self.ELineLimitCtrlName):
            deftValue = mc.getAttr(self.ELineLimitCtrlName + '.ty')
        else:
            deftValue = deftValue
        if not mc.objExists(self.ELineMainCtrlGrp):
            mc.group(n=self.ELineMainCtrlGrp, em=1)
        AllBsCtrl = mc.listRelatives(self.TraceLineSystemGrp, c=1) or []
        AllBsCtrlChild = len(AllBsCtrl)
        if AllBsCtrlChild > 0:
            moveSpan = AllBsCtrlChild * self.limitCtrlTX
        else:
            moveSpan = 0.0
        if not mc.objExists(self.ELinePart):
            mc.group(n=self.ELinePart, em=1)
        ELineLimitCtrl = cs.Ctrl()
        ELineLimitCtrlGrpName, self.ELineLimitCtrlName = ELineLimitCtrl.LimitCtrl(name=self.__part, action='ELine',
                                                                                  ctrlPnt=ELineLimitCtrl.SquareCurvePnt,
                                                                                  limitPnt=ELineLimitCtrl.RectangleCurvePnt,
                                                                                  deftValue=deftValue)
        ELinePartChild = mc.listRelatives(self.ELinePart, c=1) or []
        if ELineLimitCtrlGrpName not in ELinePartChild:
            mc.parent(ELineLimitCtrlGrpName, self.ELinePart)
        ELineCtrlChild = mc.listRelatives(self.ELineMainCtrlGrp, c=1) or []
        if self.ELinePart not in ELineCtrlChild:
            mc.parent(self.ELinePart, self.ELineMainCtrlGrp)
        TraceLineSystemGrpChild = mc.listRelatives(self.TraceLineSystemGrp, c=1) or []
        if self.ELineMainCtrlGrp not in TraceLineSystemGrpChild:
            mc.parent(self.ELineMainCtrlGrp, self.TraceLineSystemGrp)
        mc.setAttr(self.ELinePart + '.tx', self.limitCtrlTX * 1.5 + moveSpan)
        mc.setAttr(self.ELinePart + '.ty', self.limitCtrlTY - self.limitCtrlTX)
        mc.setAttr(self.ELinePart + '.s', self.limitCtrlTX / 2, self.limitCtrlTX / 2, self.limitCtrlTX / 2)
        return 0


class AccessoryLine(object):

    def __init__( self, part='face', visibilityMould=1 ):
        self.__part = part
        self.__obj = self.getObj()
        if self.__obj:
            self.limitCtrlTX, self.limitCtrlTY = self.getModBoundingBox()
        self.ATSystemGrp = 'AccessoryLineSystemGrp'
        self.ATCtrlName = self.__part + '_ALine_Ctrl'
        self.ATMainCtrlGrp = self.__part + '_ALineLimitCtrlGrp'
        self.ATPart = self.__part + '_ALineMainCtrl_Offect'

    def getObj( self ):
        selMod = [i for i in mc.ls(sl=1, dag=1, tr=1) if mc.listRelatives(i, s=1, type='mesh')]
        return selMod

    def checkShader( self ):
        self.shaderList = list()
        self.objAlphaList = list()
        if self.__obj:
            for obj in self.__obj:
                objShape = mc.listRelatives(obj, s=1)[0]
                try:
                    instGroupList = mc.listConnections(objShape + '.instObjGroups[*]', p=1) or []
                except:
                    instGroupList = list()

                try:
                    objGroupList = mc.listConnections(objShape + '.instObjGroups[0].objectGroups[*]', p=1) or []
                except:
                    objGroupList = list()

                objShaderList = instGroupList + objGroupList
                if objShaderList:
                    for i in objShaderList:
                        shadingEngineNode = i.split('.')
                        if mc.nodeType(shadingEngineNode[0]) == 'shadingEngine':
                            shader = mc.listConnections(shadingEngineNode[0] + '.surfaceShader')[0]
                            if shader == 'lambert1' or mc.nodeType(shader) == 'RedshiftMaterial':
                                self.shaderList.append(self.createShader(obj))
                                self.objAlphaList.append(AccessoryLine.checkAlphaAttr(obj))
                            elif mc.nodeType(shader) == 'lambert':
                                self.shaderList.append(shader)
                                self.objAlphaList.append(AccessoryLine.checkAlphaAttr(obj))

            if not mc.objExists(self.ATSystemGrp):
                mc.createNode('transform', n=self.ATSystemGrp)

    def conShader( self ):
        self.checkShader()
        if self.shaderList and self.objAlphaList:
            self.createCtrl()
            for con in zip(self.objAlphaList, self.shaderList):
                mc.connectAttr(con[0], '%s.transparencyR' % con[1], f=1)
                mc.connectAttr(con[0], '%s.transparencyG' % con[1], f=1)
                mc.connectAttr(con[0], '%s.transparencyB' % con[1], f=1)
                mc.connectAttr(self.ATCtrlName + '.ty', con[0], f=1)

    @staticmethod
    def createShader( obj ):
        shader = '%s__shader__' % obj
        if not mc.objExists(shader):
            shader = mc.shadingNode('lambert', asShader=True, n=shader)
        sgNode = '%sSG' % shader
        if not mc.objExists(sgNode):
            sgNode = mc.sets(renderable=True, noSurfaceShader=True, empty=True, name=sgNode)
        mc.defaultNavigation(connectToExisting=True, source=shader, destination=sgNode)
        mc.select(obj, r=1)
        mc.sets(e=True, forceElement=sgNode)
        return shader

    @staticmethod
    def checkAlphaAttr( obj ):
        attr = '%s.alpha' % obj
        objShape = mc.listRelatives(obj, s=1)[0]
        if not mc.objExists(attr):
            mc.addAttr(obj, ln='alpha', at='double', min=0, max=1, dv=0)
        mc.setAttr(attr, e=1, k=1)
        cdn = '%sDisplayCD' % obj
        if not mc.objExists(cdn):
            cdn = mc.createNode('condition', n=cdn)
        mc.setAttr('%s.secondTerm' % cdn, 1)
        mc.setAttr('%s.operation' % cdn, 0)
        mc.setAttr('%s.colorIfTrueR' % cdn, 0)
        mc.setAttr('%s.colorIfFalseR' % cdn, 1)
        mc.connectAttr(attr, '%s.firstTerm' % cdn, f=1)
        mc.connectAttr('%s.outColorR' % cdn, '%s.lodVisibility' % objShape, f=1)
        return attr

    def getModBoundingBox( self ):
        objMaxX = max([mc.xform(i, bb=1, q=1)[3] for i in self.__obj])
        objMaxY = max([mc.xform(i, bb=1, q=1)[4] for i in self.__obj])
        return [abs(objMaxX), abs(objMaxY)]

    def createCtrl( self ):
        if mc.objExists(self.ATCtrlName):
            deftValue = mc.getAttr(self.ATCtrlName + '.ty')
        else:
            deftValue = 0
        if not mc.objExists(self.ATMainCtrlGrp):
            mc.group(n=self.ATMainCtrlGrp, em=1)
        AllBsCtrl = mc.listRelatives(self.ATSystemGrp, c=1) or []
        AllBsCtrlChild = len(AllBsCtrl)
        if AllBsCtrlChild > 0:
            moveSpan = AllBsCtrlChild * self.limitCtrlTX
        else:
            moveSpan = 0.0
        if not mc.objExists(self.ATPart):
            mc.group(n=self.ATPart, em=1)
        ALineLimitCtrl = cs.Ctrl()
        ALineLimitCtrlGrpName, self.ATCtrlName = ALineLimitCtrl.LimitCtrl(name=self.__part, action='ALine',
                                                                          ctrlPnt=ALineLimitCtrl.OctagonalCurvePnt,
                                                                          limitPnt=ALineLimitCtrl.RectangleCurvePnt,
                                                                          deftValue=deftValue)
        ALinePartChild = mc.listRelatives(self.ATPart, c=1) or []
        if ALineLimitCtrlGrpName not in ALinePartChild:
            mc.parent(ALineLimitCtrlGrpName, self.ATPart)
        ALineCtrlChild = mc.listRelatives(self.ATMainCtrlGrp, c=1) or []
        if self.ATPart not in ALineCtrlChild:
            mc.parent(self.ATPart, self.ATMainCtrlGrp)
        ATSystemGrpChild = mc.listRelatives(self.ATSystemGrp, c=1) or []
        if self.ATMainCtrlGrp not in ATSystemGrpChild:
            mc.parent(self.ATMainCtrlGrp, self.ATSystemGrp)
        mc.setAttr(self.ATPart + '.tx', self.limitCtrlTX * 1.2 + moveSpan)
        mc.setAttr(self.ATPart + '.ty', self.limitCtrlTY - self.limitCtrlTX * 1.5)
        mc.setAttr(self.ATPart + '.s', self.limitCtrlTX / 2, self.limitCtrlTX / 2, self.limitCtrlTX / 2)
        return 0


if __name__ == '__main__':
    a = ExtractionLineTool()
    a.buildCtrl()
