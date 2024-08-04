import maya.cmds as cmds
import pymel.core as pm
import MuscleJointSystem as mjs
import maya.OpenMayaUI as omui
import random

qtVersion = cmds.about(qtVersion=True)

if qtVersion.startswith("4") or type(qtVersion) not in [str, unicode]:
    from PySide import QtGui
    from PySide import QtCore
    #from PySide import QtWidgets
    from PySide import QtUiTools
    import shiboken
    
else:
    from PySide2 import QtGui
    from PySide2 import QtCore
    from PySide2 import QtWidgets
    from PySide2 import QtUiTools
    import shiboken2

uifile_path = mjs.__path__[0].replace('\\','/')  + '/window.ui'

def loadui(uifile_path):
    uifile = QtCore.QFile(uifile_path)
    uifile.open(QtCore.QFile.ReadOnly)
    uiWindow = QtUiTools.QUiLoader().load(uifile, parentWidget=maya_main_window())
    uifile.close()
    return uiWindow
    
def maya_main_window():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return shiboken2.wrapInstance(long(main_window_ptr), QtWidgets.QWidget)
    
class MainWindow():
    
    def __init__(self):
        self.ui = loadui(uifile_path)
        self.ui.Mjs_CurveEditLayout.addWidget(self.getMayaCurveEditor())
        self.ui.setWindowFlags(QtCore.Qt.Dialog)
        #edit widget behaiver
        
        self.ui.Mjs_CreateNurb.clicked.connect(self.createNurbsMuscle)
        
        self.ui.Mjs_CreateDrv.clicked.connect(self.createControlSystem)
        self.ui.Mjs_CreateDrv_add.clicked.connect(self.addJointSystem)
        self.ui.Mjs_Dl.clicked.connect(self.deleteControlSystem)
        
        self.ui.Mjs_Dl_all.clicked.connect(self.deleteAll)
        
        self.ui.Mjs_Mirror.clicked.connect(self.realMirrorSystem)
        
        self.ui.Mjs_check.clicked.connect(self.checkRun)
        self.ui.Mjs_recheck.clicked.connect(self.checkRestore)
        self.ui.Mjs_refresh.clicked.connect(self.refreshFunction)
        self.ui.Mjs_refresh_hide.clicked.connect(self.refreshHiddenFuntion)
        self.ui.Mjs_refresh_hideshow.clicked.connect(self.refreshShowFuntion)
        self.ui.Mjs_refresh_hideshowAll.clicked.connect(self.refreshShowAll)
        self.ui.Mjs_rebind.clicked.connect(self.restoreBindPose)
        
        self.ui.Mjs_curveEdit_set.clicked.connect(self.curve_set_function)
        self.ui.Mjs_curveEdit_get.clicked.connect(self.get_remap_gradient_value)

        self.ui.Mjs_slider.valueChanged.connect(self.ui.Mjs_Slider_Num.setValue)
        self.ui.Mjs_Slider_Num.valueChanged.connect(self.ui.Mjs_slider.setValue)
        self.ui.Mjs_CurveEdit_SmoothSort_orig.activated.connect(self.curveEditor_d_changeSmooth)
        
        #ui_list
        self.ui.Mjs_list.setSelectionMode(self.ui.Mjs_list.ExtendedSelection)
        self.ui.Mjs_list.itemSelectionChanged.connect(self.refreshSlotsFuntion)
        self.ui.Mjs_list_2.setSelectionMode(self.ui.Mjs_list_2.ExtendedSelection)
        self.ui.Mjs_list_2.itemSelectionChanged.connect(self.refreshSlotsFuntion)
        
        #self.ui.AHA.stateChanged.connect(self.select_AHA)
    
    def getMayaCurveEditor(self,pull=0,push=0,save=[]):
        if cmds.window('MycurveEditorWindow',ex=True):
            cmds.deleteUI('MycurveEditor')
            cmds.deleteUI('MycurveEditorWindow')
        cmds.window('MycurveEditorWindow')
        cmds.columnLayout()
        cmds.gradientControlNoAttr('MycurveEditor')
        if pull == 1:
            cmds.optionVar(rm='pullLimit_mtj')
            for ii in range(len(save)):
                cmds.optionVar(stringValueAppend=['pullLimit_mtj', save[ii]])
            cmds.gradientControlNoAttr('MycurveEditor',e=True,optionVar='pullLimit_mtj')
        elif push == 1:
            pass
        else:
            cmds.optionVar(rm='falloffCurveOptionVar')
            cmds.optionVar(stringValueAppend=['falloffCurveOptionVar', '0,1,2'])
            cmds.optionVar(stringValueAppend=['falloffCurveOptionVar', '1,0,2'])
            cmds.gradientControlNoAttr('MycurveEditor',e=True,optionVar='falloffCurveOptionVar')
            
        getcontrol = omui.MQtUtil.findControl('MycurveEditor')
        getobjPyside = shiboken2.wrapInstance(long(getcontrol),QtWidgets.QWidget)
        return getobjPyside
    
    def mySelfRivet(self,name):
        shape = cmds.pickWalk(name,d='down')
        if cmds.objectType(shape) == 'nurbsSurface':
            info = cmds.createNode('pointOnSurfaceInfo',n=name+'_muscleDriver_rivetinfo')
            cmds.connectAttr(name+'.worldSpace',info+'.inputSurface')
            cmds.setAttr(info+'.parameterU',0.5)
            cmds.setAttr(info+'.parameterV',0.5)
            fourMatrix = cmds.createNode('fourByFourMatrix',n=name+'_muscleDriver_fourbyfour')
            cmds.connectAttr(info+'.normal.normalX',fourMatrix+'.in00')
            cmds.connectAttr(info+'.normal.normalY',fourMatrix+'.in01')
            cmds.connectAttr(info+'.normal.normalZ',fourMatrix+'.in02')
            
            cmds.connectAttr(info+'.tangentU.tangentUx',fourMatrix+'.in10')
            cmds.connectAttr(info+'.tangentU.tangentUy',fourMatrix+'.in11')
            cmds.connectAttr(info+'.tangentU.tangentUz',fourMatrix+'.in12')
            
            cmds.connectAttr(info+'.tangentV.tangentVx',fourMatrix+'.in20')
            cmds.connectAttr(info+'.tangentV.tangentVy',fourMatrix+'.in21')
            cmds.connectAttr(info+'.tangentV.tangentVz',fourMatrix+'.in22')
            
            cmds.connectAttr(info+'.position.positionX',fourMatrix+'.in30')
            cmds.connectAttr(info+'.position.positionY',fourMatrix+'.in31')
            cmds.connectAttr(info+'.position.positionZ',fourMatrix+'.in32')
            
            deMatrix = cmds.createNode('decomposeMatrix',n=name+'_muscleDriver_rivetDeNode')
            cmds.connectAttr(fourMatrix+'.output',deMatrix+'.inputMatrix')
            loc = cmds.spaceLocator(p=(0,0,0),n=name+'_muscleDriver_rivet_loc')[0]
            cmds.addAttr(loc,ln='parameterU',at='double',dv=0.5,min=0,max=1)
            cmds.setAttr(loc+'.parameterU',keyable=True,e=True,)
            cmds.addAttr(loc,ln='parameterV',at='double',dv=0.5,min=0,max=1)
            cmds.setAttr(loc+'.parameterV',keyable=True,e=True)
            cmds.connectAttr(deMatrix+'.outputTranslate',loc+'.translate')
            cmds.connectAttr(deMatrix+'.outputRotate',loc+'.rotate')
            cmds.connectAttr(loc+'.parameterU',info+'.parameterU')
            cmds.connectAttr(loc+'.parameterV',info+'.parameterV')
            cmds.setAttr(loc+'.localScaleX',0.2)
            cmds.setAttr(loc+'.localScaleY',0.2)
            cmds.setAttr(loc+'.localScaleZ',0.2)
            return loc
    
    def showUI(self):
        self.ui.show()
        self.refreshFunction()
        
    def closeUI(self):
        self.ui.close()
    
    def refreshHiddenFuntion(self):
        items = self.ui.Mjs_list.selectedItems()
        items2 = self.ui.Mjs_list_2.selectedItems()
        if items:
            objName = [i.text() for i in items]
            for ii in objName:
                cmds.setAttr(ii+'.visibility',0)
        if items2:
            objName = [i.text() for i in items2]
            for ii in objName:
                cmds.setAttr(ii+'.visibility',0)
        self.refreshFunction()
            
    def refreshShowFuntion(self):
        items = self.ui.Mjs_list.selectedItems()
        items2 = self.ui.Mjs_list_2.selectedItems()
        if items:
            objName = [i.text() for i in items]
            for hh in objName:
                cmds.setAttr(hh + '.visibility',1)
        if items2:
            objName = [i.text() for i in items2]
            for hh in objName:
                cmds.setAttr(hh + '.visibility',1)
        self.refreshFunction()
        
    def refreshShowAll(self):
        itemsNum = self.ui.Mjs_list.count()
        itemsNum2 = self.ui.Mjs_list_2.count()
        if itemsNum != 0:
            for ii in range(itemsNum):
                item = self.ui.Mjs_list.item(ii)
                cmds.setAttr(item.text()+'.visibility',1)
        if itemsNum2 != 0:
            for ii in range(itemsNum2):
                item = self.ui.Mjs_list_2.item(ii)
                cmds.setAttr(item.text()+'.visibility',1)
        self.refreshFunction()
        
    def refreshSlotsFuntion(self):
        cmds.select(cl=True)
        items = self.ui.Mjs_list.selectedItems()
        items2 = self.ui.Mjs_list_2.selectedItems()
        #print 'test'
        if items:
            target = [i.text() for i in items]
            cmds.select(target,r=True)
        if items2:
            target = [i.text() for i in items2]
            try:
                cmds.select(target,add=True)
            except:
                pass
        
    def refreshFunction(self):
        self.ui.Mjs_list.clear()
        self.ui.Mjs_list_2.clear()
        nurbs = cmds.ls('*_Mjs')
        if nurbs:
            for hh in nurbs:
                if '_L_' in hh:
                    self.ui.Mjs_list.addItem(hh)
                elif '_R_' in hh:
                    self.ui.Mjs_list_2.addItem(hh)
            itemsNum = self.ui.Mjs_list.count()
            itemsNum2 = self.ui.Mjs_list_2.count()
            if itemsNum != 0:
                for ii in range(itemsNum):
                    item = self.ui.Mjs_list.item(ii)
                    vis = cmds.getAttr(item.text()+'.visibility')
                    if vis == 0:
                        item.setTextColor(QtGui.QColor(103,103,103))
                    else:
                        item.setTextColor(QtGui.QColor(187,187,187))         
            if itemsNum2 != 0:
                for ii in range(itemsNum2):
                    item = self.ui.Mjs_list_2.item(ii)
                    vis = cmds.getAttr(item.text()+'.visibility')
                    if vis == 0:
                        item.setTextColor(QtGui.QColor(103,103,103))
                    else:
                        item.setTextColor(QtGui.QColor(187,187,187))

    def findJointifSkin(self,name):
        if name:
            sel = cmds.listConnections(name+'.worldMatrix',d=True)
            if sel:
                return 1
            else:
                return 0
                
    def checkAlljointState(self,value):
        if isinstance(value,int):
            sel = cmds.ls('*_joint_muscleDriver*')
            if sel :
                joint = []
                for h in sel:
                    if cmds.objectType(h) == 'joint':
                        joint.append(h)
                if joint:
                    for m in joint:
                        if value == 1:
                            if self.findJointifSkin(m) == 1:
                                cmds.setAttr(m+'.overrideColor',16)
                                if '_L_' in m :
                                    cmds.setAttr(m+'.side',1)
                                elif '_R_' in m:
                                    cmds.setAttr(m+'.side',2)
                                cmds.setAttr(m+'.type',18)
                                cmds.setAttr(m+'.otherType','Skin',typ='string')
                                cmds.setAttr(m+'.drawLabel',1)
                        elif value == 0:
                            cmds.setAttr(m+'.overrideColor',13)
                            cmds.setAttr(m+'.drawLabel',0)
        else :
            cmds.warning('input value must int!')
                #return joint

    def checkRun(self):
        self.checkAlljointState(1)
        
    def checkRestore(self):
        self.checkAlljointState(0)
    
    def vectorSubstraction(self,aa,bb):
        if len(aa) == 3 and len(bb) ==3:
            cc = []
            cc.append(aa[0]-bb[0])
            cc.append(aa[1]-bb[1])
            cc.append(aa[2]-bb[2])
            return cc
        else :
            cmds.warning('check your argument is vector list')
            
    def parentMatrixConstrain(self,aa,bb):
        parentnode = cmds.createNode('decomposeMatrix',n='parentMatrixConstrainNode')
        multynode = cmds.createNode('multMatrix',n='multMatrix_assist')
        cmds.connectAttr(aa+'.worldMatrix[0]',multynode+'.matrixIn[0]')
        cmds.connectAttr(bb+'.parentInverseMatrix[0]',multynode+'.matrixIn[1]')
        cmds.connectAttr(multynode+'.matrixSum',parentnode+'.inputMatrix')
        cmds.connectAttr(parentnode+'.outputTranslate',bb+'.translate')
        cmds.connectAttr(parentnode+'.outputRotate',bb+'.rotate')
        return [parentnode,multynode]
        
    def createNurbsMuscle(self):
        name = self.ui.Mjs_name_input.text()
        if len(cmds.ls('*' + name + '*')) == 0 and len(self.ui.Mjs_name_input.text()) != 0:
            sel = cmds.ls(sl=True,fl=True)
            if len(sel) == 2 and 'vtx' in sel[0] and 'vtx' in sel[1]:
                vertexA = cmds.xform(sel[0],ws=True,t=True,q=True)
                vertexB = cmds.xform(sel[1],ws=True,t=True,q=True)
                
                if vertexA[0] > 0 and vertexB[0] > 0:
                    name = self.ui.Mjs_name_input.text() + '_L'
                elif vertexA[0] < 0 and vertexB[0] < 0:
                    name = self.ui.Mjs_name_input.text() + '_R'
                else:
                    name = self.ui.Mjs_name_input.text() + '_L'
                    
                #create nurbs plan
                group = cmds.group(em=True,n=name+'_reverse')
                
                cmds.setAttr(group+'.tx',l=True,channelBox=False,keyable=False)
                cmds.setAttr(group+'.ty',l=True,channelBox=False,keyable=False)
                cmds.setAttr(group+'.tz',l=True,channelBox=False,keyable=False)
                cmds.setAttr(group+'.rx',l=True,channelBox=False,keyable=False)
                cmds.setAttr(group+'.ry',l=True,channelBox=False,keyable=False)
                cmds.setAttr(group+'.rz',l=True,channelBox=False,keyable=False)
                cmds.setAttr(group+'.sy',l=True,channelBox=False,keyable=False)
                cmds.setAttr(group+'.sz',l=True,channelBox=False,keyable=False)
                nurbs = cmds.nurbsPlane(p=(0,0,0),ax=(0,1,0),w=1,lr=4,d=1,u=1,v=1,ch=0,n=name+'_nurbs_Mjs')
                nurb = nurbs[0]
                cmds.setAttr(nurb+'.sx',l=True,channelBox=False,keyable=False)
                cmds.setAttr(nurb+'.sy',l=True,channelBox=False,keyable=False)
                cmds.setAttr(nurb+'.sz',l=True,channelBox=False,keyable=False)
                cmds.setAttr(nurb+'.tx',l=True,channelBox=False,keyable=False)
                cmds.setAttr(nurb+'.ty',l=True,channelBox=False,keyable=False)
                cmds.setAttr(nurb+'.tz',l=True,channelBox=False,keyable=False)
                cmds.setAttr(nurb+'.rx',l=True,channelBox=False,keyable=False)
                cmds.setAttr(nurb+'.ry',l=True,channelBox=False,keyable=False)
                cmds.setAttr(nurb+'.rz',l=True,channelBox=False,keyable=False)
                cmds.addAttr(nurb,ln='inherit',at='enum',en='off:on:')
                cmds.setAttr(nurb+'.inherit',keyable=True,e=True)
                cmds.connectAttr(nurb+'.inherit',group+'.inheritsTransform')
                #
                #cmds.addAttr(nurb,ln='length',at='double',min=0,dv=5)
                #cmds.setAttr(nurb+'.length',keyable=True,e=True)
                #cmds.addAttr(nurb,ln='width',at='double',min=0,dv=1)
                #cmds.setAttr(nurb+'.width',keyable=True,e=True)
                #cmds.connectAttr(nurb+'.length',nurbs[1]+'.lengthRatio')
                #cmds.connectAttr(nurb+'.width',nurbs[1]+'.width')
                #
                cmds.parent(nurb,group)
                groupAll = cmds.group(em=True,n=name+'_all')
                cmds.parent(group,groupAll)
                #move nurbs offset to vertex place
                nurbsvtxA = cmds.xform(nurb+'.cv[1][0:1]',ws=True,q=True,t=True)[:3]
                nurbsvtxB = cmds.xform(nurb+'.cv[0][0:1]',ws=True,q=True,t=True)[:3]
                nurbsvtxA[0] = 0.0
                nurbsvtxB[0] = 0.0
                offsetA = self.vectorSubstraction(vertexA,nurbsvtxA)
                offsetB = self.vectorSubstraction(vertexB,nurbsvtxB)
                cmds.move(offsetA[0],offsetA[1],offsetA[2],nurb+'.cv[1][0:1]',r=True)
                cmds.move(offsetB[0],offsetB[1],offsetB[2],nurb+'.cv[0][0:1]',r=True)
                cmds.select(nurb,r=True)
                self.refreshFunction()    
            else :
                cmds.warning('please select two vertex!')
        else :
            cmds.warning('please check if name exsits')
        
    def createControlSystem(self):
        sel = cmds.ls(sl=True)
        if sel:
            for uu in sel:
                try:
                    shape = cmds.listRelatives(uu,s=True)[0]
                except:
                    cmds.warning('select item not nurbs')
                if '_Mjs' in uu and cmds.objectType(shape) == 'nurbsSurface':
                    if len(cmds.ls(uu+'*muscleDriver*')) == 0 and '_Mjs' in uu:
                        #create arcLine
                        cvConvert = cmds.createNode('curveFromSurfaceIso',n=uu+'_loadCurve_Node')
                        cmds.setAttr(cvConvert+'.isoparmDirection',0)
                        cmds.setAttr(cvConvert+'.isoparmValue',0.5)
                        cmds.connectAttr(uu+'.worldSpace',cvConvert+'.inputSurface')
                        arcLine = cmds.circle(n=uu.split('_n')[0]+'_arcLine_muscleDriver',ch=0)[0]
                        cmds.connectAttr(cvConvert+'.outputCurve',arcLine+'Shape.create')
                        cmds.setAttr(arcLine+'.visibility',0)
                        arcLine_grp = cmds.group(em=True,n=arcLine+'_grp')
                        cmds.parent(arcLine,arcLine_grp)
                        cmds.parent(arcLine_grp,uu.split('_n')[0]+'_all')
                        
                        #copy orig length curve
                        arcOrig_grp = cmds.group(em=True,n=arcLine+'_orig_grp')
                        cmds.parent(arcOrig_grp,uu.split('_n')[0]+'_all')
                        arcOrig = cmds.duplicate(arcLine,n=arcLine+'_orig')[0]
                        cmds.parent(arcOrig,arcOrig_grp)
                        cmds.connectAttr(arcLine + 'Shape.worldSpace[0]',arcOrig+'Shape.create')
                        cmds.setAttr(arcOrig+'.visibility',0)
                        cmds.setAttr(arcOrig+'.visibility',l=True)
                        
                        #measure orig line length 
                        originfo = cmds.createNode('curveInfo',n=arcOrig+'_infoNode')
                        cmds.connectAttr(arcOrig + 'Shape.worldSpace[0]',originfo + '.inputCurve')
                        
                        #measure line length percent
                        infoNode = cmds.createNode('curveInfo',n=arcLine+'_infoNode')
                        cmds.connectAttr(arcLine+'Shape.worldSpace[0]',infoNode+'.inputCurve')
                        percentNode = cmds.createNode('multiplyDivide',n=arcLine+'_BehindAfter_Scale_Node')
                        lengthNum = cmds.getAttr(infoNode+'.arcLength')
                        
                        #orig and current curve calculate
                        cvScaleNode = cmds.createNode('multiplyDivide',n=uu.split('_n')[0]+'_orig_percent')
                        cmds.connectAttr(originfo+'.arcLength',cvScaleNode +'.input1.input1X')
                        cmds.connectAttr(infoNode+'.arcLength',cvScaleNode +'.input2.input2X')
                        cmds.setAttr(cvScaleNode+'.operation',2)
                        
                        #create global scale reverse compensate
                        cpsNode = cmds.createNode('multiplyDivide',n=uu+'_compensate_scale_Node')
                        cmds.connectAttr(infoNode+'.arcLength',cpsNode +'.input1.input1X')
                        cmds.setAttr(cpsNode+'.operation',2)
                        cmds.connectAttr(cvScaleNode+'.output.outputX',cpsNode+'.input2.input2X')
                        cmds.connectAttr(cpsNode+'.output.outputX',percentNode+'.input1X')
                        cmds.setAttr(percentNode+'.input2X',lengthNum)
                        cmds.setAttr(percentNode+'.operation',2)
                        
                        subNode = cmds.createNode('plusMinusAverage',n=arcLine+'_percentAdd_Node')
                        cmds.connectAttr(percentNode+'.output.outputX',subNode+'.input1D[1]')
                        cmds.setAttr(subNode+'.input1D[0]',1)
                        cmds.setAttr(subNode+'.operation',2)
                        
                        condition = cmds.createNode('condition',n=arcLine+'_pull_condition_Node')
                        cmds.setAttr(condition+'.firstTerm',0)
                        cmds.setAttr(condition+'.operation',5)
                        cmds.setAttr(condition+'.colorIfFalseR',0)
                        cmds.connectAttr(subNode+'.output1D',condition+'.secondTerm')
                        cmds.connectAttr(subNode+'.output1D',condition+'.colorIfTrue.colorIfTrueR')
                        
                        conditionPush = cmds.createNode('condition',n=arcLine+'_push_condition_Node')
                        cmds.setAttr(conditionPush+'.firstTerm',0)
                        cmds.setAttr(conditionPush+'.operation',5)
                        cmds.setAttr(conditionPush+'.colorIfFalseR',0)
                        cmds.connectAttr(subNode+'.output1D',conditionPush+'.secondTerm')
                        
                        #remap ness node
                        remapMD = cmds.createNode('multDoubleLinear',n=arcLine + '_push_remapReverse')
                        cmds.connectAttr(subNode+'.output1D',remapMD + '.input1')
                        cmds.setAttr(remapMD+'.input2',-1)
                        cmds.connectAttr(remapMD+'.output',conditionPush+'.colorIfFalse.colorIfFalseR')
                        
                        #create follicle
                        num = self.ui.Mjs_slider.value()
                        #num = 3
                        follgrp = cmds.group(em=True,n=uu.split('_n')[0]+'_revit_grp_muscleDriver')
                        jointgrp = cmds.group(em=True,n=uu.split('_n')[0]+'_joint_grp_muscleDriver')
                        cmds.parent(jointgrp,uu.split('_n')[0]+'_all')
                        cmds.parent(follgrp,uu.split('_n')[0]+'_all')
                        folScNode = cmds.createNode('decomposeMatrix',n=uu.split('_n')[0] + '_revit_dpm_Node')
                        cmds.connectAttr(uu.split('_n')[0]+'_all.worldMatrix[0]',folScNode+'.inputMatrix')
                        ratio = 0.0
                        for hh in range(num):
                            rivet = self.mySelfRivet(uu)
                            foll = cmds.rename(rivet,rivet+'_'+str(hh))
                            
                            if not ratio > 1: 
                                pass
                            else:
                                ratio = 1
                                
                            cmds.parent(foll,follgrp)
                            jnt = cmds.joint(n=uu+'_joint_muscleDriver_'+str(hh),p=(0,0,0),o=(0,0,0))
                            
                            #add joint attr
                            cmds.setAttr(jnt+'.overrideEnabled',1)
                            cmds.setAttr(jnt+'.overrideColor',13)
                            
                            cmds.addAttr(jnt,ln='RunTimeValue',at='double',dv=0)
                            cmds.setAttr(jnt+'.RunTimeValue',keyable=True,e=True)     
                            
                            cmds.addAttr(jnt,ln='offsetX',at='double',dv=0)
                            cmds.setAttr(jnt+'.offsetX',keyable=True,e=True)
                            cmds.addAttr(jnt,ln='offsetY',at='double',dv=0)
                            cmds.setAttr(jnt+'.offsetY',keyable=True,e=True)
                            cmds.addAttr(jnt,ln='offsetZ',at='double',dv=0)
                            cmds.setAttr(jnt+'.offsetZ',keyable=True,e=True)
                            cmds.addAttr(jnt,ln='slider',at='double',dv=ratio,min=0,max=1)
                            cmds.setAttr(jnt+'.slider',keyable=True,e=True)
                            
                            cmds.addAttr(jnt,ln='pullstrength',at='double',dv=1)
                            cmds.setAttr(jnt+'.pullstrength',keyable=True,e=True) 
                            cmds.addAttr(jnt,ln='PullMinValue',at='double',dv=0,max=999)
                            cmds.setAttr(jnt+'.PullMinValue',keyable=True,e=True)  
                            cmds.addAttr(jnt,ln='PullMaxValue',at='double',dv=999,max=999)
                            cmds.setAttr(jnt+'.PullMaxValue',keyable=True,e=True)  
                            
                            cmds.addAttr(jnt,ln='pushstrength',at='double',dv=0)
                            cmds.setAttr(jnt+'.pushstrength',keyable=True,e=True)
                            cmds.addAttr(jnt,ln='PushMinValue',at='double',dv=0,max=999)
                            cmds.setAttr(jnt+'.PushMinValue',keyable=True,e=True)  
                            cmds.addAttr(jnt,ln='PushMaxValue',at='double',dv=999,max=999)
                            cmds.setAttr(jnt+'.PushMaxValue',keyable=True,e=True)  
                            
                            cmds.addAttr(jnt,ln='ZupStrength',at='double',dv=0)
                            cmds.setAttr(jnt+'.ZupStrength',keyable=True,e=True)
                            cmds.addAttr(jnt,ln='ZupMinValue',at='double',dv=0,max=999)
                            cmds.setAttr(jnt+'.ZupMinValue',keyable=True,e=True)  
                            cmds.addAttr(jnt,ln='ZupMaxValue',at='double',dv=999,max=999)
                            cmds.setAttr(jnt+'.ZupMaxValue',keyable=True,e=True)  
                            
                            cmds.addAttr(jnt,ln='ZdownStrength',at='double',dv=0)
                            cmds.setAttr(jnt+'.ZdownStrength',keyable=True,e=True)
                            cmds.addAttr(jnt,ln='ZdownMinValue',at='double',dv=0,max=999)
                            cmds.setAttr(jnt+'.ZdownMinValue',keyable=True,e=True)  
                            cmds.addAttr(jnt,ln='ZdownMaxValue',at='double',dv=999,max=999)
                            cmds.setAttr(jnt+'.ZdownMaxValue',keyable=True,e=True)  
                            
                            cmds.addAttr(jnt,ln='slidPullAffect',at='double',dv=0)
                            cmds.setAttr(jnt+'.slidPullAffect',keyable=True,e=True)
                            cmds.addAttr(jnt,ln='slidPullMinValue',at='double',dv=0,max=999)
                            cmds.setAttr(jnt+'.slidPullMinValue',keyable=True,e=True)  
                            cmds.addAttr(jnt,ln='slidPullMaxValue',at='double',dv=999,max=999)
                            cmds.setAttr(jnt+'.slidPullMaxValue',keyable=True,e=True)  
                            
                            cmds.addAttr(jnt,ln='slidPushAffect',at='double',dv=0)
                            cmds.setAttr(jnt+'.slidPushAffect',keyable=True,e=True)
                            cmds.addAttr(jnt,ln='slidPushMinValue',at='double',dv=0,max=999)
                            cmds.setAttr(jnt+'.slidPushMinValue',keyable=True,e=True)  
                            cmds.addAttr(jnt,ln='slidPushMaxValue',at='double',dv=999,max=999)
                            cmds.setAttr(jnt+'.slidPushMaxValue',keyable=True,e=True)      
                            
                            cmds.connectAttr(subNode+'.output1D',jnt+'.RunTimeValue')  
                            
                            #pullScale
                            pullScaleNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_pull_scale')
                            cmds.connectAttr(jnt+'.pullstrength',pullScaleNode+'.input2')
                            
                            #pullLimit
                            pullLimitAdd = cmds.createNode('addDoubleLinear',n=jnt+ '_Pull_LimitTotal')
                            cmds.connectAttr(jnt+'.PullMinValue',pullLimitAdd+'.input1')
                            cmds.connectAttr(jnt+'.PullMaxValue',pullLimitAdd+'.input2')
                            
                            pullLimit = cmds.createNode('remapValue',n=jnt+'_Pull_Limit_Node')
                            cmds.connectAttr(condition+'.outColor.outColorR',pullLimit+'.inputValue')
                            cmds.connectAttr(jnt+'.PullMaxValue',pullLimit+'.outputMax')
                            cmds.connectAttr(pullLimitAdd+'.output',pullLimit+'.inputMax')
                            cmds.connectAttr(jnt+'.PullMinValue',pullLimit+'.inputMin')
                            
                            cmds.connectAttr(pullLimit+'.outValue',pullScaleNode+'.input1')
                            
                            #ZupScale
                            ZupScaleNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_Zup_scale')
                            cmds.connectAttr(condition+'.outColor.outColorR',ZupScaleNode+'.input1')
                            cmds.connectAttr(jnt+'.ZupStrength',ZupScaleNode+'.input2')
                            
                            #ZdownScale
                            ZdownScaleNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_Zdown_scale')
                            cmds.connectAttr(conditionPush+'.outColor.outColorR',ZdownScaleNode+'.input1')
                            cmds.connectAttr(jnt+'.ZdownStrength',ZdownScaleNode+'.input2')
                                        
                            #pushScale
                            pushScaleNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_push_scale')
                            cmds.connectAttr(jnt+'.pushstrength',pushScaleNode+'.input2')
                            
                            #push limit
                            pushLimitAdd = cmds.createNode('addDoubleLinear',n=jnt+ '_Push_LimitTotal')
                            cmds.connectAttr(jnt+'.PushMinValue',pushLimitAdd+'.input1')
                            cmds.connectAttr(jnt+'.PushMaxValue',pushLimitAdd+'.input2')
                            
                            pushLimit = cmds.createNode('remapValue',n=jnt+'_Push_Limit_Node')
                            cmds.connectAttr(conditionPush+'.outColor.outColorR',pushLimit+'.inputValue')
                            cmds.connectAttr(jnt+'.PushMaxValue',pushLimit+'.outputMax')
                            cmds.connectAttr(pushLimitAdd+'.output',pushLimit+'.inputMax')
                            cmds.connectAttr(jnt+'.PushMinValue',pushLimit+'.inputMin')
                            
                            cmds.connectAttr(pushLimit+'.outValue',pushScaleNode+'.input1')
                            
                            #sliderAffect
                            sliderPullNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_slider_pull')
                            cmds.connectAttr(condition+'.outColor.outColorR',sliderPullNode+'.input1')
                            cmds.connectAttr(jnt+'.slidPullAffect',sliderPullNode+'.input2')
                            
                            sliderPushNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_slider_push')
                            cmds.connectAttr(conditionPush+'.outColor.outColorR',sliderPushNode+'.input1')
                            cmds.connectAttr(jnt+'.slidPushAffect',sliderPushNode+'.input2')
                            
                            #sliderOffset
                            cmds.connectAttr(jnt+'.slider',foll+'.parameterU')
                            
                            #control V ratio value
                            if len(range(num)) == 1 :
                                cmds.setAttr(jnt+'.slider',0.5)
                            else:
                                ratio = ratio + (1/float(num-1))

                            jnt_pull_grp = cmds.group(em=True,n=jnt+'_pull_grp')
                            jnt_push_grp = cmds.group(em=True,n=jnt+'_push_grp')
                            jnt_zup_grp = cmds.group(em=True,n=jnt+'_Zup_grp')
                            jnt_zdown_grp = cmds.group(em=True,n=jnt+'_Zdown_grp')
                            jnt_spull_grp = cmds.group(em=True,n=jnt+'_slid_pull_grp')
                            jnt_spush_grp = cmds.group(em=True,n=jnt+'_slid_push_grp')
                            jnt_offset_grp = cmds.group(em=True,n=jnt+'_offset_grp')
                            jnt_spare_grp = cmds.group(em=True,n=jnt+'_spare_grp')
                            
                            cmds.parent(jnt,jointgrp)
                            cmds.parent(jnt_spare_grp,foll,r=True)
                            cmds.parent(jnt_offset_grp,jnt_spare_grp,r=True)
                            
                            cmds.parent(jnt_pull_grp,jnt_push_grp,r=True)
                            cmds.parent(jnt_push_grp,jnt_zup_grp,r=True)
                            cmds.parent(jnt_zup_grp,jnt_zdown_grp,r=True)
                            cmds.parent(jnt_zdown_grp,jnt_spush_grp,r=True)
                            cmds.parent(jnt_spush_grp,jnt_spull_grp,r=True)
                            cmds.parent(jnt_spull_grp,jnt_offset_grp,r=True)
                            cmds.connectAttr(pullScaleNode+'.output',jnt_pull_grp+'.translateX')
                            cmds.connectAttr(pushScaleNode+'.output',jnt_push_grp+'.translateX')
                            
                            cmds.connectAttr(ZupScaleNode+'.output',jnt_zup_grp+'.translateZ')
                            cmds.connectAttr(ZdownScaleNode+'.output',jnt_zdown_grp+'.translateZ')  
                                    
                            cmds.connectAttr(sliderPullNode+'.output',jnt_spull_grp+'.translateY')
                            cmds.connectAttr(sliderPushNode+'.output',jnt_spush_grp+'.translateY')
                            cmds.connectAttr(jnt+'.offsetX',jnt_offset_grp+'.translateX')
                            cmds.connectAttr(jnt+'.offsetY',jnt_offset_grp+'.translateY')
                            cmds.connectAttr(jnt+'.offsetZ',jnt_offset_grp+'.translateZ')
                            cmds.setAttr(jnt+'.jointOrientX',0)
                            cmds.setAttr(jnt+'.jointOrientY',0)
                            cmds.setAttr(jnt+'.jointOrientZ',0)
                            cmds.parentConstraint(jnt_pull_grp,jnt,mo=False)
                            #self.parentMatrixConstrain(jnt_pull_grp,jnt)
                            
                            #follicle scale compensate
                            cmds.connectAttr(folScNode+'.outputScale',foll+'.scale')
                        
                        #create reverse affect
                        cmds.setAttr(arcLine_grp+'.inheritsTransform',0)
                        cmds.setAttr(follgrp+'.inheritsTransform',0)
                        pm.mel.mprint('control system create successful!')
                    else:
                        cmds.warning('target Driver system already existed!')
                        cmds.select(cl=True)
                else:
                    cmds.warning('please select right nurbs!!!!!')
            cmds.select(cl=True)
        else:
            cmds.warning('please select target nurbs!!!!!')
                
                
    def deleteControlSystem(self):
        sel = cmds.ls(sl=True)
        if sel:
            for uu in sel:
                shape = cmds.listRelatives(uu,s=True)[0]
                if cmds.objectType(shape) == 'nurbsSurface' and '_Mjs' in uu:
                    control = cmds.ls(uu.split('_n')[0] + '*muscleDriver*')
                    if control:
                        cmds.delete(control)
                        pm.mel.mprint('delete successful!')
                    else:
                        cmds.warning('target not controlSystem existed')
                else:
                    cmds.warning('please select right nurbs')
        else :
            cmds.warning('not select!')
            
    def deleteAll(self):
        sel = cmds.ls(sl=True)
        if sel:
            for uu in sel:
                shape = cmds.listRelatives(uu,s=True)[0]
                if cmds.objectType(shape) == 'nurbsSurface' and '_Mjs' in uu:
                    control = cmds.ls(uu.split('_n')[0] + '*')
                    if control:
                        cmds.delete(control)
                        pm.mel.mprint('delete successful!')
                else:
                    cmds.warning('please select right nurbs')
            self.refreshFunction()
        else :
            cmds.warning('not select!')
                
    def orignalPosition_d_apply(self):
        sel = cmds.ls(sl=True)
        if sel:
            for uu in sel:
                shape = cmds.listRelatives(uu,s=True)[0]
                if cmds.objectType(shape) == 'nurbsSurface' and '_Mjs' in uu:
                    control = cmds.ls(uu.split('_nurbs_')[0] + '*Mjs_joint_muscleDriver_*')
                    if control:
                        joint = []
                        for aa in control:
                            if cmds.objectType(aa) == 'joint':
                                joint.append(aa)
                        jointNum = len(joint)
                        ScaleNum = cmds.getAttr(uu.split('_nurbs_')[0] + '_arcLine_muscleDriver_infoNode.arcLength') / 4
                        ratio = 0.0
                        for num in range(jointNum):
                            
                            if not ratio > 1: 
                                pass
                            else:
                                ratio = 1
                                
                            CVgrad = cmds.gradientControlNoAttr('MycurveEditor', q=True, valueAtPoint=ratio)
                            CVgrad = (CVgrad * ScaleNum * 2)
                            cmds.setAttr(joint[num] + '.offsetX',CVgrad)
                            
                            if len(range(jointNum)) == 1 :
                                cmds.setAttr(joint[num] + '.offsetX',0.0)
                            else:
                                ratio = ratio + (1/float(jointNum-1))
                        cmds.select(sel,r=True)
                                    
                    else :
                        cmds.warning('target not exist DriverSystem!')
                else:
                    cmds.warning('please select right nurbs')
        else :
            cmds.warning('not select!')

    def curveEditor_d_reset(self):
        cmds.optionVar(rm='falloffCurveOptionVar')
        
    def curveEditor_d_changeSmooth(self):
        num = self.ui.Mjs_CurveEdit_SmoothSort_orig.currentIndex()
        if num == 0:
            cmds.gradientControlNoAttr('MycurveEditor', e=True, currentKeyInterpValue=0)
        elif num == 1:
            cmds.gradientControlNoAttr('MycurveEditor', e=True, currentKeyInterpValue=1)
        elif num == 2:
            cmds.gradientControlNoAttr('MycurveEditor', e=True, currentKeyInterpValue=2)
        else:
            cmds.gradientControlNoAttr('MycurveEditor', e=True, currentKeyInterpValue=3)
        
    def realMirrorSystem(self):
        sel = cmds.ls(sl=True)
        if sel:
            for uu in sel:
                shape = cmds.listRelatives(uu,s=True)[0]
                if '_Mjs' in uu and cmds.objectType(shape) == 'nurbsSurface':
                    #divide
                    if len(cmds.ls(uu+'*muscleDriver*')) != 0:
                        if '_L_' in uu:
                            Newuu = uu.replace('_L_','_R_')
                            if len(cmds.ls(Newuu)) == 0 and len(cmds.ls(Newuu + '*muscleDriver*')) == 0:
                                self.realMirrorSystem_NotExist_detail(uu,Newuu)
                            elif len(cmds.ls(Newuu + '*muscleDriver*')) != 0:
                                self.realMirrorSystem_Exist_detail(uu,Newuu)
                            else:
                                cmds.warning('mirror target existed controlsystem')
                                
                        elif '_R_' in uu:
                            Newuu = uu.replace('_R_','_L_')
                            if len(cmds.ls(Newuu)) == 0 and len(cmds.ls(Newuu + '*muscleDriver*')) == 0:
                                self.realMirrorSystem_NotExist_detail(uu,Newuu)
                            elif len(cmds.ls(Newuu + '*muscleDriver*')) != 0:
                                self.realMirrorSystem_Exist_detail(uu,Newuu)
                            else:
                                cmds.warning('mirror target existed controlsystem')
                    else:
                        cmds.warning('select muscle not existed driversystem')
                        
                else:
                    cmds.warning('please select right nurbs')  
            self.refreshFunction()  
        else :
            cmds.warning('not select')
        
    def realMirrorSystem_NotExist_detail(self,old,new):
        #mirror muscle nurbs
        rootName = new.split('_n')[0]
        name = cmds.duplicate(old,rr=True)
        cmds.rename(name,new)
        group = cmds.group(em=True,n=rootName+'_reverse')
        
        cmds.setAttr(group+'.tx',l=True,channelBox=False,keyable=False)
        cmds.setAttr(group+'.ty',l=True,channelBox=False,keyable=False)
        cmds.setAttr(group+'.tz',l=True,channelBox=False,keyable=False)
        cmds.setAttr(group+'.rx',l=True,channelBox=False,keyable=False)
        cmds.setAttr(group+'.ry',l=True,channelBox=False,keyable=False)
        cmds.setAttr(group+'.rz',l=True,channelBox=False,keyable=False)
        
        cmds.connectAttr(new + '.inherit',group+'.inheritsTransform')
        cmds.parent(new,group)
        groupAll = cmds.group(em=True,n= rootName + '_all')
        cmds.parent(group,groupAll)
        self.vertexExchange(old,new)
        #cmds.makeIdentity(group,a=True,s=True,pn=True,n=False)
        cmds.setAttr(group+'.sy',l=True,channelBox=False,keyable=False)
        cmds.setAttr(group+'.sz',l=True,channelBox=False,keyable=False)
        
        #---------------------------mirror control system----------------------------
        
        
        #create arcLine
        cvConvert = cmds.createNode('curveFromSurfaceIso',n=new + '_loadCurve_Node')
        cmds.setAttr(cvConvert+'.isoparmDirection',0)
        cmds.setAttr(cvConvert+'.isoparmValue',0.5)
        cmds.connectAttr(new + '.worldSpace',cvConvert+'.inputSurface')
        arcLine = cmds.circle(n=rootName + '_arcLine_muscleDriver',ch=0)[0]
        cmds.connectAttr(cvConvert+'.outputCurve',arcLine+'Shape.create')
        cmds.setAttr(arcLine+'.visibility',0)
        arcLine_grp = cmds.group(em=True,n=arcLine+'_grp')
        cmds.parent(arcLine,arcLine_grp)
        cmds.parent(arcLine_grp,rootName +' _all')
        
        #copy orig length curve
        arcOrig_grp = cmds.group(em=True,n=arcLine+'_orig_grp')
        cmds.parent(arcOrig_grp,rootName + '_all')
        arcOrig = cmds.duplicate(arcLine,n=arcLine+'_orig')[0]
        cmds.parent(arcOrig,arcOrig_grp)
        cmds.connectAttr(arcLine + 'Shape.worldSpace[0]',arcOrig+'Shape.create')
        cmds.setAttr(arcOrig+'.visibility',0)
        cmds.setAttr(arcOrig+'.visibility',l=True)
        
        #measure orig line length 
        originfo = cmds.createNode('curveInfo',n=arcOrig+'_infoNode')
        cmds.connectAttr(arcOrig + 'Shape.worldSpace[0]',originfo + '.inputCurve')
        
        #measure line length percent
        infoNode = cmds.createNode('curveInfo',n=arcLine+'_infoNode')
        cmds.connectAttr(arcLine+'Shape.worldSpace[0]',infoNode+'.inputCurve')
        percentNode = cmds.createNode('multiplyDivide',n=arcLine+'_BehindAfter_Scale_Node')
        lengthNum = cmds.getAttr(infoNode+'.arcLength')
        
        #orig and current curve calculate
        cvScaleNode = cmds.createNode('multiplyDivide',n=rootName + '_orig_percent')
        cmds.connectAttr(originfo+'.arcLength',cvScaleNode +'.input1.input1X')
        cmds.connectAttr(infoNode+'.arcLength',cvScaleNode +'.input2.input2X')
        cmds.setAttr(cvScaleNode+'.operation',2)
        
        #create global scale reverse compensate
        cpsNode = cmds.createNode('multiplyDivide',n=new + '_compensate_scale_Node')
        cmds.connectAttr(infoNode+'.arcLength',cpsNode +'.input1.input1X')
        cmds.setAttr(cpsNode+'.operation',2)
        cmds.connectAttr(cvScaleNode+'.output.outputX',cpsNode+'.input2.input2X')
        cmds.connectAttr(cpsNode+'.output.outputX',percentNode+'.input1X')
        cmds.setAttr(percentNode+'.input2X',lengthNum)
        cmds.setAttr(percentNode+'.operation',2)
        
        subNode = cmds.createNode('plusMinusAverage',n=arcLine+'_percentAdd_Node')
        cmds.connectAttr(percentNode+'.output.outputX',subNode+'.input1D[1]')
        cmds.setAttr(subNode+'.input1D[0]',1)
        cmds.setAttr(subNode+'.operation',2)
        
        condition = cmds.createNode('condition',n=arcLine+'_pull_condition_Node')
        cmds.setAttr(condition+'.firstTerm',0)
        cmds.setAttr(condition+'.operation',5)
        cmds.setAttr(condition+'.colorIfFalseR',0)
        cmds.connectAttr(subNode+'.output1D',condition+'.secondTerm')
        cmds.connectAttr(subNode+'.output1D',condition+'.colorIfTrue.colorIfTrueR')
        
        conditionPush = cmds.createNode('condition',n=arcLine+'_push_condition_Node')
        cmds.setAttr(conditionPush+'.firstTerm',0)
        cmds.setAttr(conditionPush+'.operation',5)
        cmds.setAttr(conditionPush+'.colorIfFalseR',0)
        cmds.connectAttr(subNode+'.output1D',conditionPush+'.secondTerm')
        
        #remap ness node
        remapMD = cmds.createNode('multDoubleLinear',n=arcLine + '_push_remapReverse')
        cmds.connectAttr(subNode+'.output1D',remapMD + '.input1')
        cmds.setAttr(remapMD+'.input2',-1)
        cmds.connectAttr(remapMD+'.output',conditionPush+'.colorIfFalse.colorIfFalseR')

        #create follicle
        num = self.checkAlreadySystemJointNum(old)
        follgrp = cmds.group(em=True,n=rootName+'_revit_grp_muscleDriver')
        jointgrp = cmds.group(em=True,n=rootName+'_joint_grp_muscleDriver')
        cmds.parent(jointgrp,rootName+'_all')
        cmds.parent(follgrp,rootName+'_all')
        folScNode = cmds.createNode('decomposeMatrix',n=rootName + '_revit_dpm_Node')
        cmds.connectAttr(rootName+'_all.worldMatrix[0]',folScNode+'.inputMatrix')
        ratio = 0.0
        for hh in range(num):
            rivet = self.mySelfRivet(new)
            foll = cmds.rename(rivet,rivet+'_'+str(hh))
            
            if not ratio > 1: 
                pass
            else:
                ratio = 1
                
            cmds.parent(foll,follgrp)
            jnt = cmds.joint(n=new + '_joint_muscleDriver_'+str(hh),p=(0,0,0),o=(0,0,0))
            
            #add joint attr
            cmds.setAttr(jnt+'.overrideEnabled',1)
            cmds.setAttr(jnt+'.overrideColor',13)
            
            cmds.addAttr(jnt,ln='RunTimeValue',at='double',dv=0)
            cmds.setAttr(jnt+'.RunTimeValue',keyable=True,e=True)     
            
            cmds.addAttr(jnt,ln='offsetX',at='double',dv=0)
            cmds.setAttr(jnt+'.offsetX',keyable=True,e=True)
            cmds.addAttr(jnt,ln='offsetY',at='double',dv=0)
            cmds.setAttr(jnt+'.offsetY',keyable=True,e=True)
            cmds.addAttr(jnt,ln='offsetZ',at='double',dv=0)
            cmds.setAttr(jnt+'.offsetZ',keyable=True,e=True)
            cmds.addAttr(jnt,ln='slider',at='double',dv=ratio,min=0,max=1)
            cmds.setAttr(jnt+'.slider',keyable=True,e=True)
            
            cmds.addAttr(jnt,ln='pullstrength',at='double',dv=1)
            cmds.setAttr(jnt+'.pullstrength',keyable=True,e=True) 
            cmds.addAttr(jnt,ln='PullMinValue',at='double',dv=0,min=0,max=999)
            cmds.setAttr(jnt+'.PullMinValue',keyable=True,e=True)  
            cmds.addAttr(jnt,ln='PullMaxValue',at='double',dv=999,min=0,max=999)
            cmds.setAttr(jnt+'.PullMaxValue',keyable=True,e=True)  
            
            cmds.addAttr(jnt,ln='pushstrength',at='double',dv=0)
            cmds.setAttr(jnt+'.pushstrength',keyable=True,e=True)
            cmds.addAttr(jnt,ln='PushMinValue',at='double',dv=0,min=0,max=999)
            cmds.setAttr(jnt+'.PushMinValue',keyable=True,e=True)  
            cmds.addAttr(jnt,ln='PushMaxValue',at='double',dv=999,min=0,max=999)
            cmds.setAttr(jnt+'.PushMaxValue',keyable=True,e=True)  
            
            cmds.addAttr(jnt,ln='ZupStrength',at='double',dv=0)
            cmds.setAttr(jnt+'.ZupStrength',keyable=True,e=True)
            cmds.addAttr(jnt,ln='ZupMinValue',at='double',dv=0,min=0,max=999)
            cmds.setAttr(jnt+'.ZupMinValue',keyable=True,e=True)  
            cmds.addAttr(jnt,ln='ZupMaxValue',at='double',dv=999,min=0,max=999)
            cmds.setAttr(jnt+'.ZupMaxValue',keyable=True,e=True)  
            
            cmds.addAttr(jnt,ln='ZdownStrength',at='double',dv=0)
            cmds.setAttr(jnt+'.ZdownStrength',keyable=True,e=True)
            cmds.addAttr(jnt,ln='ZdownMinValue',at='double',dv=0,min=0,max=999)
            cmds.setAttr(jnt+'.ZdownMinValue',keyable=True,e=True)  
            cmds.addAttr(jnt,ln='ZdownMaxValue',at='double',dv=999,min=0,max=999)
            cmds.setAttr(jnt+'.ZdownMaxValue',keyable=True,e=True)  
            
            cmds.addAttr(jnt,ln='slidPullAffect',at='double',dv=0)
            cmds.setAttr(jnt+'.slidPullAffect',keyable=True,e=True)
            cmds.addAttr(jnt,ln='slidPullMinValue',at='double',dv=0,min=0,max=999)
            cmds.setAttr(jnt+'.slidPullMinValue',keyable=True,e=True)  
            cmds.addAttr(jnt,ln='slidPullMaxValue',at='double',dv=999,min=0,max=999)
            cmds.setAttr(jnt+'.slidPullMaxValue',keyable=True,e=True)  
            
            cmds.addAttr(jnt,ln='slidPushAffect',at='double',dv=0)
            cmds.setAttr(jnt+'.slidPushAffect',keyable=True,e=True)
            cmds.addAttr(jnt,ln='slidPushMinValue',at='double',dv=0,min=0,max=999)
            cmds.setAttr(jnt+'.slidPushMinValue',keyable=True,e=True)  
            cmds.addAttr(jnt,ln='slidPushMaxValue',at='double',dv=999,min=0,max=999)
            cmds.setAttr(jnt+'.slidPushMaxValue',keyable=True,e=True)  
            cmds.connectAttr(subNode+'.output1D',jnt+'.RunTimeValue')  
            
            try:
                cmds.getAttr(old+'_joint_muscleDriver_'+str(hh)+'.addname')
                cmds.addAttr(jnt,ln='addname',at='double',dv=1)
                cmds.setAttr(jnt+'.addname',keyable=True,e=True)
                cmds.setAttr(jnt+'.overrideColor',14)
            except:
                pass
            
            #pullScale
            pullScaleNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_pull_scale')
            cmds.connectAttr(jnt+'.pullstrength',pullScaleNode+'.input2')
            
            #pullLimit
            pullLimitAdd = cmds.createNode('addDoubleLinear',n=jnt+ '_Pull_LimitTotal')
            cmds.connectAttr(jnt+'.PullMinValue',pullLimitAdd+'.input1')
            cmds.connectAttr(jnt+'.PullMaxValue',pullLimitAdd+'.input2')
            
            pullLimit = cmds.createNode('remapValue',n=jnt+'_Pull_Limit_Node')
            cmds.connectAttr(condition+'.outColor.outColorR',pullLimit+'.inputValue')
            cmds.connectAttr(jnt+'.PullMaxValue',pullLimit+'.outputMax')
            cmds.connectAttr(pullLimitAdd+'.output',pullLimit+'.inputMax')
            cmds.connectAttr(jnt+'.PullMinValue',pullLimit+'.inputMin')
            
            cmds.connectAttr(pullLimit+'.outValue',pullScaleNode+'.input1')
            
            #ZupScale
            ZupScaleNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_Zup_scale')
            cmds.connectAttr(condition+'.outColor.outColorR',ZupScaleNode+'.input1')
            cmds.connectAttr(jnt+'.ZupStrength',ZupScaleNode+'.input2')
            
            #ZdownScale
            ZdownScaleNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_Zdown_scale')
            cmds.connectAttr(conditionPush+'.outColor.outColorR',ZdownScaleNode+'.input1')
            cmds.connectAttr(jnt+'.ZdownStrength',ZdownScaleNode+'.input2')
            
            #pushScale
            pushScaleNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_push_scale')
            cmds.connectAttr(jnt+'.pushstrength',pushScaleNode+'.input2')
            
            #push limit
            pushLimitAdd = cmds.createNode('addDoubleLinear',n=jnt+ '_Push_LimitTotal')
            cmds.connectAttr(jnt+'.PushMinValue',pushLimitAdd+'.input1')
            cmds.connectAttr(jnt+'.PushMaxValue',pushLimitAdd+'.input2')
            
            pushLimit = cmds.createNode('remapValue',n=jnt+'_Push_Limit_Node')
            cmds.connectAttr(conditionPush+'.outColor.outColorR',pushLimit+'.inputValue')
            cmds.connectAttr(jnt+'.PushMaxValue',pushLimit+'.outputMax')
            cmds.connectAttr(pushLimitAdd+'.output',pushLimit+'.inputMax')
            cmds.connectAttr(jnt+'.PushMinValue',pushLimit+'.inputMin')
            
            cmds.connectAttr(pushLimit+'.outValue',pushScaleNode+'.input1')
            
            #sliderAffect
            sliderPullNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_slider_pull')
            cmds.connectAttr(condition+'.outColor.outColorR',sliderPullNode+'.input1')
            cmds.connectAttr(jnt+'.slidPullAffect',sliderPullNode+'.input2')
            
            sliderPushNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_slider_push')
            cmds.connectAttr(conditionPush+'.outColor.outColorR',sliderPushNode+'.input1')
            cmds.connectAttr(jnt+'.slidPushAffect',sliderPushNode+'.input2')
            
            #sliderOffset
            cmds.connectAttr(jnt+'.slider',foll+'.parameterU')
            
            #control V ratio value
            if len(range(num)) == 1 :
                cmds.setAttr(jnt+'.slider',0.5)
            else:
                ratio = ratio + (1/float(num-1))
                
            jnt_pull_grp = cmds.group(em=True,n=jnt+'_pull_grp')
            jnt_push_grp = cmds.group(em=True,n=jnt+'_push_grp')
            jnt_zup_grp = cmds.group(em=True,n=jnt+'_Zup_grp')
            jnt_zdown_grp = cmds.group(em=True,n=jnt+'_Zdown_grp')
            jnt_spull_grp = cmds.group(em=True,n=jnt+'_slid_pull_grp')
            jnt_spush_grp = cmds.group(em=True,n=jnt+'_slid_push_grp')
            jnt_offset_grp = cmds.group(em=True,n=jnt+'_offset_grp')
            jnt_spare_grp = cmds.group(em=True,n=jnt+'_spare_grp')

            cmds.parent(jnt,jointgrp)
            cmds.parent(jnt_spare_grp,foll,r=True)
            cmds.parent(jnt_offset_grp,jnt_spare_grp,r=True)
            
            cmds.parent(jnt_pull_grp,jnt_push_grp,r=True)
            cmds.parent(jnt_push_grp,jnt_zup_grp,r=True)
            cmds.parent(jnt_zup_grp,jnt_zdown_grp,r=True)
            cmds.parent(jnt_zdown_grp,jnt_spush_grp,r=True)
            cmds.parent(jnt_spush_grp,jnt_spull_grp,r=True)
            cmds.parent(jnt_spull_grp,jnt_offset_grp,r=True)

            cmds.connectAttr(pullScaleNode+'.output',jnt_pull_grp+'.translateX')
            cmds.connectAttr(pushScaleNode+'.output',jnt_push_grp+'.translateX')
            cmds.connectAttr(sliderPullNode+'.output',jnt_spull_grp+'.translateY')
            cmds.connectAttr(sliderPushNode+'.output',jnt_spush_grp+'.translateY')
            cmds.connectAttr(jnt+'.offsetX',jnt_offset_grp+'.translateX')
            cmds.connectAttr(jnt+'.offsetY',jnt_offset_grp+'.translateY')
            
            #mirror reverse corrective
            if cmds.objExists(old+'_joint_muscleDriver_'+str(hh)+'_ozReverse'):
                cmds.connectAttr(jnt+'.offsetZ',jnt_offset_grp+'.translateZ')
            else:
                ozreverse = cmds.createNode('multDoubleLinear',n=jnt+'_ozReverse')
                cmds.connectAttr(jnt+'.offsetZ',ozreverse+'.input1')
                cmds.setAttr(ozreverse+'.input2',-1)
                cmds.connectAttr(ozreverse+'.output',jnt_offset_grp+'.translateZ')
                
            if cmds.objExists(old+'_joint_muscleDriver_'+str(hh)+'_zuReverse'):
                cmds.connectAttr(ZupScaleNode+'.output',jnt_zup_grp+'.translateZ')
            else:
                zureverse = cmds.createNode('multDoubleLinear',n=jnt+'_zuReverse')
                cmds.connectAttr(ZupScaleNode+'.output',zureverse+'.input1')
                cmds.setAttr(zureverse+'.input2',-1)
                cmds.connectAttr(zureverse+'.output',jnt_zup_grp+'.translateZ')
            
            if cmds.objExists(old+'_joint_muscleDriver_'+str(hh)+'_zdReverse'):
                cmds.connectAttr(ZdownScaleNode+'.output',jnt_zdown_grp+'.translateZ')
            else:
                zdreverse = cmds.createNode('multDoubleLinear',n=jnt+'_zdReverse')
                cmds.connectAttr(ZdownScaleNode+'.output',zdreverse+'.input1')
                cmds.setAttr(zdreverse+'.input2',-1)
                cmds.connectAttr(zdreverse+'.output',jnt_zdown_grp+'.translateZ')
                
            cmds.setAttr(jnt+'.jointOrientX',0)
            cmds.setAttr(jnt+'.jointOrientY',0)
            cmds.setAttr(jnt+'.jointOrientZ',0)
            cmds.parentConstraint(jnt_pull_grp,jnt,mo=False)
            #self.parentMatrixConstrain(jnt_pull_grp,jnt)
            
            #follicle scale compensate
            cmds.connectAttr(folScNode+'.outputScale',foll+'.scale')
            
        #create reverse affect
        cmds.setAttr(arcLine_grp+'.inheritsTransform',0)
        cmds.setAttr(follgrp+'.inheritsTransform',0)
        
        self.realMirrorSystem_Exist_detail(old,new)
        self.realMirrorSystem_Skin_detail(old,new)
        pm.mel.mprint('mirror target successful!!')
        
    def realMirrorSystem_Exist_detail(self,old,new):
        self.vertexExchange(old,new)
        num = self.checkAlreadySystemJointNum(old)
        mirrorNum = self.checkAlreadySystemJointNum(new)
        if num > mirrorNum:
            addnum = self.checkAddJoint(old) - self.checkAddJoint(new)
            if addnum > 0:
                self.addJointFunction(new,addnum)
        for i in range(num):
            if cmds.objExists(new+'_joint_muscleDriver_'+str(i)):
                pull = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.pullstrength')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.pullstrength',pull)
                
                pullMax = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.PullMaxValue')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.PullMaxValue',pullMax)
                pullMin = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.PullMinValue')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.PullMinValue',pullMin)
                
                push = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.pushstrength')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.pushstrength',push)
                
                pushMax = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.PushMaxValue')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.PushMaxValue',pushMax)
                pushMin = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.PushMinValue')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.PushMinValue',pushMin)

                zup = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.ZupStrength')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.ZupStrength',zup)
                zdown = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.ZdownStrength')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.ZdownStrength',zdown)
 
                zupMax = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.ZupMaxValue')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.ZupMaxValue',zupMax)
                zupMin = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.ZupMinValue')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.ZupMinValue',zupMin)
                
                zdownMax = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.ZdownMaxValue')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.ZdownMaxValue',zdownMax)
                zdownMin = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.ZdownMinValue')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.ZdownMinValue',zdownMin)

                ox = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.offsetX')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.offsetX',ox) 
                oy = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.offsetY')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.offsetY',oy)  
                oz = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.offsetZ')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.offsetZ',oz)  
                
                slid = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.slider')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.slider',slid)
                slidpull = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.slidPullAffect')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.slidPullAffect',slidpull)
                slidpush = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.slidPushAffect')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.slidPushAffect',slidpush)
                
                slidpullMax = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.slidPullMaxValue')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.slidPullMaxValue',slidpullMax)
                slidpullMin = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.slidPullMinValue')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.slidPullMinValue',slidpullMin)
                
                slidpushMax = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.slidPushMaxValue')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.slidPushMaxValue',slidpushMax)
                slidpushMin = cmds.getAttr(old+'_joint_muscleDriver_'+str(i)+'.slidPushMinValue')
                cmds.setAttr(new+'_joint_muscleDriver_'+str(i)+'.slidPushMinValue',slidpushMin)

                #bind pose refresh
                value = cmds.getAttr(old.split('_nurbs_Mjs')[0] + '_arcLine_muscleDriver_BehindAfter_Scale_Node.input2.input2X')
                cmds.setAttr(new.split('_nurbs_Mjs')[0] + '_arcLine_muscleDriver_BehindAfter_Scale_Node.input2.input2X',value)
                
                #get remap value
                #pull
                remapValueNum = len(cmds.getAttr(old + '_joint_muscleDriver_'+str(i)+'_Pull_Limit_Node.value',mi=True))
                for ss in range(remapValueNum):
                    ValueSMo = old+'_joint_muscleDriver_'+str(i)+'_Pull_Limit_Node.value[{0}]'.format(str(ss))
                    ValueSMn = new+'_joint_muscleDriver_'+str(i)+'_Pull_Limit_Node.value[{0}]'.format(str(ss))
                    
                    Position = cmds.getAttr(ValueSMo+'.value_Position')
                    FloatValue = cmds.getAttr(ValueSMo+'.value_FloatValue')
                    Interp = cmds.getAttr(ValueSMo+'.value_Interp')
                    
                    cmds.setAttr(ValueSMn+'.value_Position',Position)
                    cmds.setAttr(ValueSMn+'.value_FloatValue',FloatValue)
                    cmds.setAttr(ValueSMn+'.value_Interp',Interp)
                
                #push
                remapValueNum = len(cmds.getAttr(old + '_joint_muscleDriver_'+str(i)+'_Push_Limit_Node.value',mi=True))
                for ss in range(remapValueNum):
                    ValueSMo = old+'_joint_muscleDriver_'+str(i)+'_Push_Limit_Node.value[{0}]'.format(str(ss))
                    ValueSMn = new+'_joint_muscleDriver_'+str(i)+'_Push_Limit_Node.value[{0}]'.format(str(ss))
                    
                    Position = cmds.getAttr(ValueSMo+'.value_Position')
                    FloatValue = cmds.getAttr(ValueSMo+'.value_FloatValue')
                    Interp = cmds.getAttr(ValueSMo+'.value_Interp')
                    
                    cmds.setAttr(ValueSMn+'.value_Position',Position)
                    cmds.setAttr(ValueSMn+'.value_FloatValue',FloatValue)
                    cmds.setAttr(ValueSMn+'.value_Interp',Interp)
                
        self.realMirrorSystem_Skin_detail(old,new)
        pm.mel.mprint('Because existed mirrorDriverSystem so just attrbute with skinValue successful!')
 
    def realMirrorSystem_Skin_detail(self,old,new):
        skin = pm.mel.findRelatedSkinCluster(old)
        if skin != '':
            joints = cmds.skinCluster(skin,q=True,inf=True)
            mirrorJoint = []
            vertexs = cmds.ls(old+ '.cv[*]',fl=True)
            #create mirrorJoint List
            for hh in joints:
                if '_L' in hh:
                    mirrorJoint.append(hh.replace('_L','_R'))
                elif '_R' in hh:
                    mirrorJoint.append(hh.replace('_R','_L'))
                elif '_L' not in hh and '_R' not in hh:
                    mirrorJoint.append(hh)
            #get vertexWeight value
            a00 = cmds.skinPercent(skin, vertexs[0], query=True, value=True )
            a01 = cmds.skinPercent(skin, vertexs[1], query=True, value=True )
            a10 = cmds.skinPercent(skin, vertexs[2], query=True, value=True )
            a11 = cmds.skinPercent(skin, vertexs[3], query=True, value=True )
            
            #create mirror skin
            mirskin = pm.mel.findRelatedSkinCluster(new)
            if mirskin == '':
                mirskin = cmds.skinCluster(mirrorJoint,new,tsb=True,mi=5)[0]
            cmds.setAttr(mirskin+'.nw', 0)
            cmds.skinPercent(mirskin,new,prw=100,normalize=0 )
            
            #apply skin value
            for tt in range(len(mirrorJoint)):
                cmds.skinPercent(mirskin,new + '.cv[0][0]' , transformValue=[(mirrorJoint[tt],a01[tt])])
                cmds.skinPercent(mirskin,new + '.cv[0][1]' , transformValue=[(mirrorJoint[tt],a00[tt])])
                cmds.skinPercent(mirskin,new + '.cv[1][0]' , transformValue=[(mirrorJoint[tt],a11[tt])])
                cmds.skinPercent(mirskin,new + '.cv[1][1]' , transformValue=[(mirrorJoint[tt],a10[tt])])
            cmds.setAttr(mirskin+'.nw', 1)
            pm.mel.mprint('skinCluster Mirror successful!')
        
    def checkAlreadySystemJointNum(self,name):
        control = cmds.ls(name + '*_joint_muscleDriver_*')
        if control:
            joint = []
            for aa in control:
                if cmds.objectType(aa) == 'joint':
                    joint.append(aa)
            num = len(joint)
            return num
        else:
            cmds.warning('error!!')
            
    def checkAddJoint(self,name):
        control = cmds.ls(name + '*_joint_muscleDriver_*')
        if control:
            joint = []
            for aa in control:
                if cmds.objectType(aa) == 'joint':
                    joint.append(aa)
            num = 0
            for jj in joint:
                try:
                    value = cmds.getAttr(jj+'.addname')
                    num = num + 1
                except:
                    pass
            return num
        else:
            cmds.warning('error!!')
            
    def vertexExchange(self,old,name):
        a00 = cmds.xform(old+'.cv[0][0]',ws=True,q=True,t=True)
        a00[0] = a00[0] * -1
        a01 = cmds.xform(old+'.cv[0][1]',ws=True,q=True,t=True)
        a01[0] = a01[0] * -1
        b00 = cmds.xform(old+'.cv[1][0]',ws=True,q=True,t=True)
        b00[0] = b00[0] * -1
        b01 = cmds.xform(old+'.cv[1][1]',ws=True,q=True,t=True)
        b01[0] = b01[0] * -1
        
        cmds.xform(name+'.cv[0][0]',ws=True,t=(a01[0],a01[1],a01[2]))
        cmds.xform(name+'.cv[0][1]',ws=True,t=(a00[0],a00[1],a00[2]))
        cmds.xform(name+'.cv[1][0]',ws=True,t=(b01[0],b01[1],b01[2]))
        cmds.xform(name+'.cv[1][1]',ws=True,t=(b00[0],b00[1],b00[2]))

    def addJointSystem(self):
        sel = cmds.ls(sl=True)
        if sel:
            for uu in sel:
                try:
                    shape = cmds.listRelatives(uu,s=True)[0]
                except:
                    cmds.warning('select item not nurbs')
                if '_Mjs' in uu and cmds.objectType(shape) == 'nurbsSurface':
                    addNum = self.ui.Mjs_slider.value()
                    self.addJointFunction(uu,addNum)
                else:
                    cmds.warning('please select right nurbs!!!!!')
        else:
            cmds.warning('please select target nurbs!!!!!')
        
    def addJointFunction(self,name,addNum):
        if len(cmds.ls(name+'*muscleDriver*')) != 0:
            oirgName = name.split('_nurbs')[0]
            follgrp = oirgName + '_revit_grp_muscleDriver'
            num = self.checkAlreadySystemJointNum(name)
            subNode = oirgName + '_arcLine_muscleDriver'+ '_percentAdd_Node'
            condition = oirgName + '_arcLine_muscleDriver' + '_pull_condition_Node'
            conditionPush = oirgName + '_arcLine_muscleDriver' + '_push_condition_Node'
            jointgrp = oirgName + '_joint_grp_muscleDriver'
            folScNode = oirgName + '_revit_dpm_Node'
            
            for hh in range(addNum):
                rand = float(str(random.random())[:4])
                rivet = self.mySelfRivet(name)
                foll = cmds.rename(rivet,rivet+'_'+str(num))
                
                cmds.parent(foll,follgrp)
                jnt = cmds.joint(n=name+'_joint_muscleDriver_'+str(num),p=(0,0,0),o=(0,0,0))
                
                #add joint attr
                cmds.setAttr(jnt+'.overrideEnabled',1)
                cmds.setAttr(jnt+'.overrideColor',14)
                
                cmds.addAttr(jnt,ln='RunTimeValue',at='double',dv=0)
                cmds.setAttr(jnt+'.RunTimeValue',keyable=True,e=True)     
                
                cmds.addAttr(jnt,ln='offsetX',at='double',dv=0)
                cmds.setAttr(jnt+'.offsetX',keyable=True,e=True)
                cmds.addAttr(jnt,ln='offsetY',at='double',dv=0)
                cmds.setAttr(jnt+'.offsetY',keyable=True,e=True)
                cmds.addAttr(jnt,ln='offsetZ',at='double',dv=0)
                cmds.setAttr(jnt+'.offsetZ',keyable=True,e=True)
                cmds.addAttr(jnt,ln='slider',at='double',dv=rand,min=0,max=1)
                cmds.setAttr(jnt+'.slider',keyable=True,e=True)
                
                cmds.addAttr(jnt,ln='pullstrength',at='double',dv=1)
                cmds.setAttr(jnt+'.pullstrength',keyable=True,e=True) 
                cmds.addAttr(jnt,ln='PullMinValue',at='double',dv=0,min=0,max=999)
                cmds.setAttr(jnt+'.PullMinValue',keyable=True,e=True)  
                cmds.addAttr(jnt,ln='PullMaxValue',at='double',dv=999,min=0,max=999)
                cmds.setAttr(jnt+'.PullMaxValue',keyable=True,e=True)  
                
                cmds.addAttr(jnt,ln='pushstrength',at='double',dv=0)
                cmds.setAttr(jnt+'.pushstrength',keyable=True,e=True)
                cmds.addAttr(jnt,ln='PushMinValue',at='double',dv=0,min=0,max=999)
                cmds.setAttr(jnt+'.PushMinValue',keyable=True,e=True)  
                cmds.addAttr(jnt,ln='PushMaxValue',at='double',dv=999,min=0,max=999)
                cmds.setAttr(jnt+'.PushMaxValue',keyable=True,e=True)  
                
                cmds.addAttr(jnt,ln='ZupStrength',at='double',dv=0)
                cmds.setAttr(jnt+'.ZupStrength',keyable=True,e=True)
                cmds.addAttr(jnt,ln='ZupMinValue',at='double',dv=0,min=0,max=999)
                cmds.setAttr(jnt+'.ZupMinValue',keyable=True,e=True)  
                cmds.addAttr(jnt,ln='ZupMaxValue',at='double',dv=999,min=0,max=999)
                cmds.setAttr(jnt+'.ZupMaxValue',keyable=True,e=True)  
                
                cmds.addAttr(jnt,ln='ZdownStrength',at='double',dv=0)
                cmds.setAttr(jnt+'.ZdownStrength',keyable=True,e=True)
                cmds.addAttr(jnt,ln='ZdownMinValue',at='double',dv=0,min=0,max=999)
                cmds.setAttr(jnt+'.ZdownMinValue',keyable=True,e=True)  
                cmds.addAttr(jnt,ln='ZdownMaxValue',at='double',dv=999,min=0,max=999)
                cmds.setAttr(jnt+'.ZdownMaxValue',keyable=True,e=True)  
                
                cmds.addAttr(jnt,ln='slidPullAffect',at='double',dv=0)
                cmds.setAttr(jnt+'.slidPullAffect',keyable=True,e=True)
                cmds.addAttr(jnt,ln='slidPullMinValue',at='double',dv=0,min=0,max=999)
                cmds.setAttr(jnt+'.slidPullMinValue',keyable=True,e=True)  
                cmds.addAttr(jnt,ln='slidPullMaxValue',at='double',dv=999,min=0,max=999)
                cmds.setAttr(jnt+'.slidPullMaxValue',keyable=True,e=True)  
                
                cmds.addAttr(jnt,ln='slidPushAffect',at='double',dv=0)
                cmds.setAttr(jnt+'.slidPushAffect',keyable=True,e=True)
                cmds.addAttr(jnt,ln='slidPushMinValue',at='double',dv=0,min=0,max=999)
                cmds.setAttr(jnt+'.slidPushMinValue',keyable=True,e=True)  
                cmds.addAttr(jnt,ln='slidPushMaxValue',at='double',dv=999,min=0,max=999)
                cmds.setAttr(jnt+'.slidPushMaxValue',keyable=True,e=True)   
                cmds.connectAttr(subNode+'.output1D',jnt+'.RunTimeValue')
                
                cmds.addAttr(jnt,ln='addname',at='double',dv=1)
                cmds.setAttr(jnt+'.addname',keyable=True,e=True)    
                
                #pullScale
                pullScaleNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_pull_scale')
                cmds.connectAttr(jnt+'.pullstrength',pullScaleNode+'.input2')
                
                #pullLimit
                pullLimitAdd = cmds.createNode('addDoubleLinear',n=jnt+ '_Pull_LimitTotal')
                cmds.connectAttr(jnt+'.PullMinValue',pullLimitAdd+'.input1')
                cmds.connectAttr(jnt+'.PullMaxValue',pullLimitAdd+'.input2')
                
                pullLimit = cmds.createNode('remapValue',n=jnt+'_Pull_Limit_Node')
                cmds.connectAttr(condition+'.outColor.outColorR',pullLimit+'.inputValue')
                cmds.connectAttr(jnt+'.PullMaxValue',pullLimit+'.outputMax')
                cmds.connectAttr(pullLimitAdd+'.output',pullLimit+'.inputMax')
                cmds.connectAttr(jnt+'.PullMinValue',pullLimit+'.inputMin')
                
                cmds.connectAttr(pullLimit+'.outValue',pullScaleNode+'.input1')
                
                #ZupScale
                ZupScaleNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_Zup_scale')
                cmds.connectAttr(condition+'.outColor.outColorR',ZupScaleNode+'.input1')
                cmds.connectAttr(jnt+'.ZupStrength',ZupScaleNode+'.input2')
                
                #ZdownScale
                ZdownScaleNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_Zdown_scale')
                cmds.connectAttr(conditionPush+'.outColor.outColorR',ZdownScaleNode+'.input1')
                cmds.connectAttr(jnt+'.ZdownStrength',ZdownScaleNode+'.input2')
                
                
                #pushScale
                pushScaleNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_push_scale')
                cmds.connectAttr(jnt+'.pushstrength',pushScaleNode+'.input2')
                
                #push limit
                pushLimitAdd = cmds.createNode('addDoubleLinear',n=jnt+ '_Push_LimitTotal')
                cmds.connectAttr(jnt+'.PushMinValue',pushLimitAdd+'.input1')
                cmds.connectAttr(jnt+'.PushMaxValue',pushLimitAdd+'.input2')
                
                pushLimit = cmds.createNode('remapValue',n=jnt+'_Push_Limit_Node')
                cmds.connectAttr(conditionPush+'.outColor.outColorR',pushLimit+'.inputValue')
                cmds.connectAttr(jnt+'.PushMaxValue',pushLimit+'.outputMax')
                cmds.connectAttr(pushLimitAdd+'.output',pushLimit+'.inputMax')
                cmds.connectAttr(jnt+'.PushMinValue',pushLimit+'.inputMin')
                
                cmds.connectAttr(pushLimit+'.outValue',pushScaleNode+'.input1')
                
                #sliderAffect
                sliderPullNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_slider_pull')
                cmds.connectAttr(condition+'.outColor.outColorR',sliderPullNode+'.input1')
                cmds.connectAttr(jnt+'.slidPullAffect',sliderPullNode+'.input2')
                
                sliderPushNode = cmds.createNode('multDoubleLinear',n=jnt+'_percent_slider_push')
                cmds.connectAttr(conditionPush+'.outColor.outColorR',sliderPushNode+'.input1')
                cmds.connectAttr(jnt+'.slidPushAffect',sliderPushNode+'.input2')
                
                #sliderOffset
                cmds.connectAttr(jnt+'.slider',foll+'.parameterU')
                
                jnt_pull_grp = cmds.group(em=True,n=jnt+'_pull_grp')
                jnt_push_grp = cmds.group(em=True,n=jnt+'_push_grp')
                jnt_zup_grp = cmds.group(em=True,n=jnt+'_Zup_grp')
                jnt_zdown_grp = cmds.group(em=True,n=jnt+'_Zdown_grp')
                jnt_spull_grp = cmds.group(em=True,n=jnt+'_slid_pull_grp')
                jnt_spush_grp = cmds.group(em=True,n=jnt+'_slid_push_grp')
                jnt_offset_grp = cmds.group(em=True,n=jnt+'_offset_grp')
                jnt_spare_grp = cmds.group(em=True,n=jnt+'_spare_grp')
                cmds.parent(jnt,jointgrp)
                cmds.parent(jnt_spare_grp,foll,r=True)
                cmds.parent(jnt_offset_grp,jnt_spare_grp,r=True)
                
                cmds.parent(jnt_pull_grp,jnt_push_grp,r=True)
                cmds.parent(jnt_push_grp,jnt_zup_grp,r=True)
                cmds.parent(jnt_zup_grp,jnt_zdown_grp,r=True)
                cmds.parent(jnt_zdown_grp,jnt_spush_grp,r=True)
                cmds.parent(jnt_spush_grp,jnt_spull_grp,r=True)
                cmds.parent(jnt_spull_grp,jnt_offset_grp,r=True)
                cmds.connectAttr(pullScaleNode+'.output',jnt_pull_grp+'.translateX')
                cmds.connectAttr(pushScaleNode+'.output',jnt_push_grp+'.translateX')
                cmds.connectAttr(sliderPullNode+'.output',jnt_spull_grp+'.translateY')
                cmds.connectAttr(sliderPushNode+'.output',jnt_spush_grp+'.translateY')
                cmds.connectAttr(jnt+'.offsetX',jnt_offset_grp+'.translateX')
                cmds.connectAttr(jnt+'.offsetY',jnt_offset_grp+'.translateY')
                #cmds.connectAttr(jnt+'.offsetZ',jnt_offset_grp+'.translateZ')
                
                #mirror reverse corrective
                if cmds.objExists(name+'_joint_muscleDriver_'+str(0)+'_ozReverse'):
                    ozreverse = cmds.createNode('multDoubleLinear',n=jnt+'_ozReverse')
                    cmds.connectAttr(jnt+'.offsetZ',ozreverse+'.input1')
                    cmds.setAttr(ozreverse+'.input2',-1)
                    cmds.connectAttr(ozreverse+'.output',jnt_offset_grp+'.translateZ')
                else:
                    cmds.connectAttr(jnt+'.offsetZ',jnt_offset_grp+'.translateZ')
                    
                if cmds.objExists(name+'_joint_muscleDriver_'+str(0)+'_zuReverse'):
                    zureverse = cmds.createNode('multDoubleLinear',n=jnt+'_zuReverse')
                    cmds.connectAttr(ZupScaleNode+'.output',zureverse+'.input1')
                    cmds.setAttr(zureverse+'.input2',-1)
                    cmds.connectAttr(zureverse+'.output',jnt_zup_grp+'.translateZ')
                else:
                    cmds.connectAttr(ZupScaleNode+'.output',jnt_zup_grp+'.translateZ')
                
                if cmds.objExists(name+'_joint_muscleDriver_'+str(0)+'_zdReverse'):
                    zdreverse = cmds.createNode('multDoubleLinear',n=jnt+'_zdReverse')
                    cmds.connectAttr(ZdownScaleNode+'.output',zdreverse+'.input1')
                    cmds.setAttr(zdreverse+'.input2',-1)
                    cmds.connectAttr(zdreverse+'.output',jnt_zdown_grp+'.translateZ')
                else:
                    cmds.connectAttr(ZdownScaleNode+'.output',jnt_zdown_grp+'.translateZ')
                    
                cmds.setAttr(jnt+'.jointOrientX',0)
                cmds.setAttr(jnt+'.jointOrientY',0)
                cmds.setAttr(jnt+'.jointOrientZ',0)
                cmds.parentConstraint(jnt_pull_grp,jnt,mo=False)
                
                
                #follicle scale compensate
                cmds.connectAttr(folScNode+'.outputScale',foll+'.scale')

                num = num + 1 
                
            pm.mel.mprint('Add Joint Over!!!')
                
        else:
            cmds.warning('select Muscle not existing DriverSystem')
            
    def restoreBindPose(self):
        sel = cmds.ls(sl=True)
        if sel:
            for uu in sel:
                shape = cmds.listRelatives(uu,s=True)[0]
                if cmds.objectType(shape) == 'nurbsSurface' and '_Mjs' in uu and len(cmds.ls(uu+'*muscleDriver*')) != 0:
                    value = cmds.getAttr(uu.split('_nurbs_Mjs')[0] + '_arcLine_muscleDriver_infoNode.arcLength')
                    cmds.setAttr(uu.split('_nurbs_Mjs')[0] + '_arcLine_muscleDriver_BehindAfter_Scale_Node.input2.input2X',value)
                    pm.mel.mprint('already restored successful!')
                else:
                    cmds.warning('please select right nurbs')
        else :
            cmds.warning('not select!')
            
    def curve_set_function(self):
        num = self.ui.Mjs_CurveEdit_sort_name.currentIndex()
        if num == 0:
            self.orignalPosition_d_apply()
            
    def get_remap_gradient_value(self):
        sel = cmds.ls(sl=True)
        if sel:
            if cmds.objectType(sel[0]) == 'joint' and '_Mjs' in sel[0]:
                pullNode = sel[0] + '_Pull_Limit_Node'
                pushNode = sel[0] + '_Push_Limit_Node'
                num = self.ui.Mjs_CurveEdit_sort_name.currentIndex()
                if num == 1:
                    pullNumLong = cmds.getAttr(pullNode + '.value',mi=True)
                    pullNum = []
                    for ss in pullNumLong:
                        pullNum.append(int(ss))
                    cmds.optionVar(rm='pullLimit_mtj')
                    for ss in pullNum:
                        ValueName = pullNode + '.value[{0}]'.format(str(ss))
                        aa = cmds.getAttr(ValueName+'.value_Position')
                        bb = cmds.getAttr(ValueName+'.value_FloatValue')
                        cc = cmds.getAttr(ValueName+'.value_Interp')
                        cmds.optionVar(stringValueAppend=['pullLimit_mtj', '{0},{1},{2}'.format(str(bb),str(aa),str(cc))])
                    saveVar = cmds.optionVar(q='pullLimit_mtj')
                    print saveVar
                    self.ui.Mjs_CurveEditLayout.addWidget(self.getMayaCurveEditor(pull=1,save=saveVar))
                elif num == 2:
                    pass
        else:
            self.ui.Mjs_CurveEditLayout.addWidget(self.getMayaCurveEditor())

        