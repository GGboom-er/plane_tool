
# ================================================================ #
# WRetargetToolV_1_0.py
#
#     - W Retarget Tool  -
#         
# - Set Source object
# - Set Target object
#
# Written by: Walter Delgado
# Updated: oct/26/2024
# ================================================================ #



import maya.cmds as cmds
import maya.mel as mm
import time

def show_instruction(*args):
    if cmds.window("instructionWindow", exists=True):
        cmds.deleteUI("instructionWindow")
    about_window = cmds.window("instructionWindow", title="Instruction",menuBar = True, wh = [500, 100],s = False)
    cmds.columnLayout(adjustableColumn=True)
    
    # Create a label with your name
    cmds.text(label="Objects/character should have similar initial pose on the start frame\n")
    cmds.text(label="Remember to set the start frame and end frame according your need\n")
    
    # Add an OK button to close the About window
    cmds.button(label="close", command='cmds.deleteUI("instructionWindow")')
    
    cmds.showWindow(about_window)


def show_about(*args):
    # Create a new window for the 'About' information
    if cmds.window("aboutWindow", exists=True):
        cmds.deleteUI("aboutWindow")
    about_window = cmds.window("aboutWindow", title="About",menuBar = True, wh = [200, 100],s = False)
    cmds.columnLayout(adjustableColumn=True)
    
    # Create a label with your name
    cmds.text(label="Wretarget Tool V1.0")
    cmds.text(label="Created by: Walter Delgado")
    cmds.text(label="contact: wdemo.cgi@gmail.com")
    cmds.text(label="02 - Nov - 2024")
    
    # Add an OK button to close the About window
    cmds.button(label="close", command='cmds.deleteUI("aboutWindow")')
    
    cmds.showWindow(about_window)


class CopyAnimation():

    def __init__(self):
        window_name =  "WretargetTool V1.0"
        window_title =  "WretargetTool"
        
        filePath = cmds.file(q=True, sn=True)
        edits = filePath.split("/")
        nameFile = "/"+edits[-1]
        self.pathLoadCtrl = filePath[:-len(nameFile)]
        
        if cmds.window(window_name,q = True, exists = True):
            cmds.deleteUI(window_name)
        WindowTest = cmds.window(window_name, title = "WretargetTool V1.0",menuBar = True, wh = [500, 400], s = False)
        #menu
        fileMenu = cmds.menu(label = "Info")
        instructionOption = cmds.menuItem(label = "Instruction", command=show_instruction)
        aboutOption = cmds.menuItem(label = "About", command=show_about)
        cmds.setParent('..')
        
        #main column
        Column = cmds.columnLayout(adj = True, w = 200)
        cmds.text(label = "", h = 10)
        cmds.text(label = "Set animation Range")
        cmds.text(label = "", h = 10)
        #row frame selection
        rowFrame  = cmds.rowLayout(numberOfColumns = 4, columnWidth2 = (50, 50))
        cmds.text(label = "", w =  75)
        self.StartFrameField = cmds.intFieldGrp(numberOfFields = 1, label = "Start Frame", columnAlign2 = ["left", "left"], cw2 = [70, 50], width = 130, v1 = 0)
        self.EndFrameField = cmds.intFieldGrp(numberOfFields = 1, label = "End Frame", columnAlign2 = ["left", "left"], cw2 = [70, 50], width = 130, v1 = 20)
        self.StartFrame = cmds.intFieldGrp(self.StartFrameField, q = True, v1 = True)
        self.EndFrame = cmds.intFieldGrp(self.EndFrameField, q = True, v1 = True)
        self.FrameTime = self.EndFrame - self.StartFrame
        self.referenceFullTime = self.FrameTime  #Needed for estimated progress in Copy All function, changuing according num of objects
        cmds.text(label = "")
        
        cmds.setParent('..')
        cmds.text(label = "", h = 10)
        cmds.text(label = "Select Source and target Objects")
        cmds.text(label = "", h = 10)
        #row obj selection A
        RowA = cmds.rowLayout(numberOfColumns = 3)
        self.SrcObjectA = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Select Source Obj", bc = self.SelectSrcObjectA, cw3 = [1, 100, 50])
        self.TgtObjectA = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Select Target Obj", bc = self.SelectTgtObjectA, cw3 = [1, 100, 50])
        self.BttnObjectA = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Copy Anim", bc = self.ButtonCopyAnimA, cw3 = [1, 0, 50])
        
        #row obj selection B
        cmds.setParent('..')
        RowB = cmds.rowLayout(numberOfColumns = 3)
        self.SrcObjectB = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Select Source Obj", bc = self.SelectSrcObjectB, cw3 = [1, 100, 50])
        self.TgtObjectB = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Select Target Obj", bc = self.SelectTgtObjectB, cw3 = [1, 100, 50])
        self.BttnObjectB = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Copy Anim", bc = self.ButtonCopyAnimB, cw3 = [1, 0, 50])
        #row obj selection C
        cmds.setParent('..')
        RowC = cmds.rowLayout(numberOfColumns = 3)
        self.SrcObjectC = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Select Source Obj", bc = self.SelectSrcObjectC, cw3 = [1, 100, 50])
        self.TgtObjectC = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Select Target Obj", bc = self.SelectTgtObjectC, cw3 = [1, 100, 50])
        self.BttnObjectC = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Copy Anim", bc = self.ButtonCopyAnimC , cw3 = [1, 0, 50])
        #row obj selection D
        cmds.setParent('..')
        RowD = cmds.rowLayout(numberOfColumns = 3)
        self.SrcObjectD = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Select Source Obj", bc = self.SelectSrcObjectD, cw3 = [1, 100, 50])
        self.TgtObjectD = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Select Target Obj", bc = self.SelectTgtObjectD, cw3 = [1, 100, 50])
        self.BttnObjectD = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Copy Anim", bc = self.ButtonCopyAnimD, cw3 = [1, 0, 50])
        
        #row for delete placeholders and Copy All buttons
        cmds.setParent('..')
        cmds.text(label = "" )
        RowCopyAll  = cmds.rowLayout(numberOfColumns = 4, columnWidth2 = (50, 50))
        cmds.text(label = "", w =  75)
        self.DeletePlaceHolders = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Delete Place Holders", bc = self.DeletePlaceHolders, cw3 = [1, 0, 50])
        cmds.text(label = "", w = 210)
        self.CopyAll = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Copy All", bc = self.CopyAll, cw3 = [1, 0, 50], backgroundColor = (.5, .8, .2))
        
        #row for setting export options
        cmds.setParent('..')
        cmds.text(label = "", h = 10)
        cmds.text(label = "Export Options")
        cmds.text(label = "(Target objects must be indicated previously)")
        cmds.text(label = "", h = 10)
        
        RowExportOptions  = cmds.rowLayout(numberOfColumns = 4, columnWidth2 = (50, 50))
        self.DestinationFolder = cmds.textFieldButtonGrp(label = "Destination Folder", text = self.pathLoadCtrl, buttonLabel = "...", bc = self.SetDestinationFolder, cw3 = [100, 250, 50])
        
        cmds.setParent('..')
        RowExportOptions  = cmds.rowLayout(numberOfColumns = 4, columnWidth2 = (50, 50))
        self.CheckBackeAnim = cmds.checkBoxGrp(numberOfCheckBoxes = 1, label = "BakeAnimation", columnWidth2 = [83, 50], v1 = True)
        self.OptionMenuAxis = cmds.optionMenuGrp(label = "Up Axis", cw2 = [40, 80])
        cmds.menuItem(label = "Y")
        cmds.menuItem(label = "Z")
        self.FileType = cmds.optionMenuGrp(label = "File Type", cw2 = [50, 80])
        cmds.menuItem(label = "Binary")
        cmds.menuItem(label = "ASCII")
        self.FBXVersion = cmds.optionMenuGrp(label = "FBX Version", cw2 = [60, 80])
        cmds.menuItem(label = "FBX2020")
        cmds.menuItem(label = "FBX2019")
        cmds.menuItem(label = "FBX2018")
        cmds.setParent('..')
        self.BttnExport = cmds.textFieldButtonGrp(label = "", text = "", buttonLabel = "Export", bc = self.ButtonExport, cw3 = [210, 0, 100], backgroundColor = (.8, .5, .2))
        
        #Progress Bar
        self.ProgressControl = cmds.progressBar(width = 300, maxValue = self.referenceFullTime)
        self.remainingTime = cmds.text(label = "", w = 210)
        
        cmds.showWindow(WindowTest)
    
    
    #BUTTONS COMMANDS
    
    #Copy Animation command    
    def CopyAnim(self, source="", target="", ValidObj = 1, initTime = 0):
        #defining frame range
        self.StartFrame = cmds.intFieldGrp(self.StartFrameField, q = True, v1 = True)
        self.EndFrame = cmds.intFieldGrp(self.EndFrameField, q = True, v1 = True)
        self.FrameTime = self.EndFrame - self.StartFrame
        #copying animation using attributes values
        if cmds.objExists(source):
            if cmds.objExists(target):
                
                #holdMatrixSrc = cmds.shadingNode('holdMatrix', asUtility = True, n = source + 'holdMatrix')
                #cmds.connectAttr(source + '.worldInverseMatrix[0]',holdMatrixSrc + '.inMatrix', f = 1)
                
                """
                decompMxMaster = cmds.shadingNode('decomposeMatrix',asUtility = 1, n = target +  'decompMx')
                cmds.connectAttr(target + '.worldInverseMatrix[0]', decompMxMaster + '.inputMatrix' )
                compMatrix = cmds.shadingNode('composeMatrix',asUtility = 1, n = target +  'compMx')
                cmds.connectAttr(decompMxMaster + '.outputRotate', compMatrix + '.inputRotate')
                holdMatrixTgt = cmds.shadingNode('holdMatrix', asUtility = True, n = target + 'holdMatrix')
                cmds.connectAttr(compMatrix + '.outputMatrix',holdMatrixTgt + '.inMatrix', f = 1)
                """
                cmds.currentTime(self.StartFrame)
                
                locGrpSrc1 = cmds.group(em = True, n = source + '_locGrpSrc1')
                locGrpSrc2 = cmds.group(locGrpSrc1, n = source + '_locGrpSrc2')
                cmds.delete(cmds.pointConstraint(source, locGrpSrc2))
                try:
                    sourceFather = cmds.listRelatives(source, p = True)[0]
                    cmds.parentConstraint(sourceFather, locGrpSrc2, mo = True)
                except:
                    pass
                cmds.parentConstraint(source, locGrpSrc1, mo = True)
                
                
                locGrpTgt1 = cmds.group(em = True, n = target + '_locGrpTgt1')
                locGrpTgt2 = cmds.group(locGrpTgt1, n = target + '_locGrpTgt2')
                cmds.delete(cmds.pointConstraint(target, locGrpTgt2))
                
                locGrpTgt3 = cmds.group(em = True, n = target + '_locGrpTgt3')
                cmds.delete(cmds.parentConstraint(target, locGrpTgt3))
                try:
                    sourceFatherTgt = cmds.listRelatives(target, p = True)[0]
                    cmds.parent(locGrpTgt2,sourceFatherTgt )
                    cmds.parent(locGrpTgt3,sourceFatherTgt )
                except:
                    print(target + ' is parented to world')
                cmds.parentConstraint(locGrpTgt1, locGrpTgt3, mo = True)
                
                for i in range(self.StartFrame, self.EndFrame):
                    #print(i)
                    startTime = time.time()
                    cmds.currentTime(i)
                    """
                    if i == self.StartFrame:
                        cmds.disconnectAttr(source + '.worldInverseMatrix[0]',holdMatrixSrc + '.inMatrix')
                        cmds.disconnectAttr(compMatrix + '.outputMatrix',holdMatrixTgt + '.inMatrix')
                    """
                    
                    
                    multMatrix1 = cmds.shadingNode('multMatrix', asUtility = True, n = source + 'multMatrix')
                    cmds.connectAttr(locGrpSrc1 + '.worldMatrix[0]',multMatrix1 + '.matrixIn[0]', f = 1)
                    cmds.connectAttr(locGrpSrc2 + '.worldInverseMatrix[0]',multMatrix1 + '.matrixIn[1]', f = 1)
                    """
                    multMatrix2 = cmds.shadingNode('multMatrix', asUtility = True, n = source + 'multMatrix2')
                    cmds.connectAttr(multMatrix1 + '.matrixSum',multMatrix2 + '.matrixIn[0]', f = 1)
                    cmds.connectAttr(holdMatrixTgt + '.outMatrix',multMatrix2 + '.matrixIn[1]', f = 1)
                    """
                    decompMxMaster = cmds.shadingNode('decomposeMatrix',asUtility = 1, n = source +  'decompMx')
                    cmds.connectAttr(multMatrix1 + '.matrixSum', decompMxMaster + '.inputMatrix' )
                    
                    
                    
                    cmds.connectAttr(decompMxMaster + '.outputRotate', locGrpTgt1 + '.r', f = 1)
                    cmds.connectAttr(decompMxMaster + '.outputTranslate', locGrpTgt1 + '.t', f = 1)
                    
                    
                    
                    #iteration for every attribute
                    for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
                    #for attrMx, attr in zip(['outputTranslateX', 'outputTranslateY','outputTranslateZ','outputRotateX', 'outputRotateY', 'outputRotateZ', 'outputScaleX', 'outputScaleY', 'outputScaleZ'],['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']):
                        try:                            
                            valueAttr = cmds.getAttr(locGrpTgt3+"."+attr)
                            #print(valueAttr)
                            cmds.setAttr(target+"."+attr, valueAttr)
                            cmds.setKeyframe(target, attribute = attr)
                            
                        except:
                            pass
                    endTime = time.time()
                    #total estimated time: number of frames * unit working time * number of valid objects to operate
                    TotalEstimatedTime = self.FrameTime*(endTime-startTime)*ValidObj
                    EstimatedRemainingTime = TotalEstimatedTime + initTime - endTime
                    #Text for remaining Time
                    RemainingTimeLabel = "Estimated remaining Time: "+str(EstimatedRemainingTime)+" seg"
                    #cmds.text(self.remainingTime,edit = True, label = RemainingTimeLabel)
                    #Progress Bar update
                    cmds.progressBar(self.ProgressControl, edit = True, step = 1)
                    
                    #deleting nodes
                    """
                    if i == 5:
                        break
                    """
                    #cmds.delete(compMatrix)
                    #cmds.delete(multMatrix2)
                    #cmds.delete(decompMxMaster)
                cmds.delete(locGrpSrc1)
                cmds.delete(locGrpSrc2)
                
                cmds.delete(locGrpTgt3)
                cmds.delete(locGrpTgt1)
                cmds.delete(locGrpTgt2)
                    #cmds.delete(multMatrix1)
                    
                    
                #cmds.delete(holdMatrixTgt)
                print("Animation copied from: "+source+" to: "+target+"\n"),
                
                
                #Reset progress Bar
                if ValidObj == 1:
                    cmds.progressBar(self.ProgressControl, edit = True, endProgress = True)
            else:
                cmds.warning("No target Selected")
        else:
            cmds.warning("No source Selected")
        
    #Delete placeHolders command
    def DeletePlaceHolders(self):
        #Defining list of objects
        PlaceHolderList = []
        ObjectFieldList = [self.SrcObjectA, self.SrcObjectB, self.SrcObjectC, self.SrcObjectD]
        ObjectFieldTgt = [self.TgtObjectA, self.TgtObjectB, self.TgtObjectC, self.TgtObjectD]
        for object in ObjectFieldList:
            PlaceHolderList.append(cmds.textFieldButtonGrp(object, q = True, text = True))
        """
        for obj, objField in zip(PlaceHolderList, ObjectFieldList):
            if cmds.objExists(obj):
                cmds.delete(obj)
                cmds.textFieldButtonGrp(objField, edit = True, tx="")
        """
        
        for objTgt, objField in zip(ObjectFieldTgt, ObjectFieldList):
            cmds.textFieldButtonGrp(objField, edit = True, tx="")
            cmds.textFieldButtonGrp(objTgt, edit = True, tx="")
    #Destination folder command
    def SetDestinationFolder(self):
        Path = cmds.fileDialog2(fileMode = 3, dialogStyle = 2, caption = "Choose directory")[0]
        cmds.textFieldButtonGrp(self.DestinationFolder, edit = True, tx= Path)
        print("Set destination folder")
            
    #CopyAll command
    def CopyAll(self):
        #Calling objects selected
        srcList = []
        tgtList = []
        ObjectFieldListSrc = [self.SrcObjectA, self.SrcObjectB, self.SrcObjectC, self.SrcObjectD]
        ObjectFieldListTgt = [self.TgtObjectA, self.TgtObjectB, self.TgtObjectC, self.TgtObjectD] 
        
        for object in ObjectFieldListSrc:
            srcList.append(cmds.textFieldButtonGrp(object, q = True, text = True))
            
        for object in ObjectFieldListTgt:
            tgtList.append(cmds.textFieldButtonGrp(object, q = True, text = True))
        
        #Getting number of valid objects for estimated time progress
        ValidObjects = 0
        for i in range(4):
            if cmds.objExists(srcList[i]):
                if cmds.objExists(tgtList[i]):
                    ValidObjects += 1
        #Updating Size of progress Barr
        self.StartFrame = cmds.intFieldGrp(self.StartFrameField, q = True, v1 = True)
        self.EndFrame = cmds.intFieldGrp(self.EndFrameField, q = True, v1 = True)
        self.FrameTime = self.EndFrame - self.StartFrame
        self.referenceFullTime = ValidObjects*self.FrameTime
        cmds.progressBar(self.ProgressControl, edit = True, maxValue = self.referenceFullTime)
        
        #Sending to CopyAnim function
        initialTime = time.time() #start time for all Actions
        for src,tgt in zip(srcList, tgtList):
            self.CopyAnim(source = src, target = tgt, ValidObj = ValidObjects, initTime = initialTime)
        #Reset progress Bar
        cmds.progressBar(self.ProgressControl, edit = True, endProgress = True)
    #Export command
    def ButtonExport(self):
        #Setting Export Parameters
        CheckBakeValue = cmds.checkBoxGrp(self.CheckBackeAnim, q = True, v1 = True)
        UpAxisValue = cmds.optionMenuGrp(self.OptionMenuAxis, q = True, value = True)
        FileTypeValue = cmds.optionMenuGrp(self.FileType, q = True, value = True)
        FBXversionIndex = cmds.optionMenuGrp(self.FBXVersion, q = True, value = True)
        
        mm.eval("FBXExportUpAxis %s" %UpAxisValue)
        
        if FileTypeValue == "Binary":
            mm.eval("FBXExportInAscii -v 0")
        else:
            mm.eval("FBXExportInAscii -v 1")
        
        mm.eval("FBXExportFileVersion -v %s00" %FBXversionIndex)
        
        mel.eval("FBXExportBakeComplexAnimation -v %i" %CheckBakeValue)
        
        #determine namespace from objects
        ListObjectExportName = []
        ObjectFieldListTgt = [self.TgtObjectA, self.TgtObjectB, self.TgtObjectC, self.TgtObjectD] 
        for object in ObjectFieldListTgt:
            objTarget = cmds.textFieldButtonGrp(object, q = True, text = True)
            if cmds.objExists(objTarget):
                nameSpace = objTarget.rpartition(':')[0]
                ListObjectExportName.append(nameSpace)
            
            
        #Exporting Objects
        ExportPath = cmds.textFieldButtonGrp(self.DestinationFolder, q = True, tx = True)
        for ObjName in ListObjectExportName:  
            cmds.select(ObjName+":"+ObjName+"_geo", r = True)
            cmds.select(ObjName+":Jnts_grp", tgl = True)
            MainPath = ExportPath+"/"+ObjName
            cmds.file(MainPath, force = True, options = "v=0;", typ = "FBX export", pr = True,  es = True)
            cmds.select(cl = True)
            print("%s Exported" %ObjName),
    #Buttons commands for copy Animation
    def ButtonCopyAnimA(self):
        #defining source and target objects selected
        SrcObj = cmds.textFieldButtonGrp(self.SrcObjectA, q = True, text = True)
        TargetObj = cmds.textFieldButtonGrp(self.TgtObjectA, q = True, text = True)
        #Updating Size of progress Barr
        self.StartFrame = cmds.intFieldGrp(self.StartFrameField, q = True, v1 = True)
        self.EndFrame = cmds.intFieldGrp(self.EndFrameField, q = True, v1 = True)
        self.FrameTime = self.EndFrame - self.StartFrame
        self.referenceFullTime = self.FrameTime
        cmds.progressBar(self.ProgressControl, edit = True, maxValue = self.referenceFullTime)
        #Operate mean function for copying animation
        initialTime = time.time() #start time for all Actions
        self.CopyAnim(source = SrcObj, target = TargetObj, initTime = initialTime)
    def ButtonCopyAnimB(self):
        #defining source and target objects selected
        SrcObj = cmds.textFieldButtonGrp(self.SrcObjectB, q = True, text = True)
        TargetObj = cmds.textFieldButtonGrp(self.TgtObjectB, q = True, text = True)
        #Updating Size of progress Barr
        self.StartFrame = cmds.intFieldGrp(self.StartFrameField, q = True, v1 = True)
        self.EndFrame = cmds.intFieldGrp(self.EndFrameField, q = True, v1 = True)
        self.FrameTime = self.EndFrame - self.StartFrame
        self.referenceFullTime = self.FrameTime
        cmds.progressBar(self.ProgressControl, edit = True, maxValue = self.referenceFullTime)
        #Operate mean function for copying animation
        initialTime = time.time() #start time for all Actions
        self.CopyAnim(source = SrcObj, target = TargetObj, initTime = initialTime)
    def ButtonCopyAnimC(self):
        #defining source and target objects selected
        SrcObj = cmds.textFieldButtonGrp(self.SrcObjectC, q = True, text = True)
        TargetObj = cmds.textFieldButtonGrp(self.TgtObjectC, q = True, text = True)
        #Updating Size of progress Barr
        self.StartFrame = cmds.intFieldGrp(self.StartFrameField, q = True, v1 = True)
        self.EndFrame = cmds.intFieldGrp(self.EndFrameField, q = True, v1 = True)
        self.FrameTime = self.EndFrame - self.StartFrame
        self.referenceFullTime = self.FrameTime
        cmds.progressBar(self.ProgressControl, edit = True, maxValue = self.referenceFullTime)
        #Operate mean function for copying animation
        initialTime = time.time() #start time for all Actions
        self.CopyAnim(source = SrcObj, target = TargetObj, initTime = initialTime)
    def ButtonCopyAnimD(self):
        #defining source and target objects selected
        SrcObj = cmds.textFieldButtonGrp(self.SrcObjectD, q = True, text = True)
        TargetObj = cmds.textFieldButtonGrp(self.TgtObjectD, q = True, text = True)
        #Updating Size of progress Barr
        self.StartFrame = cmds.intFieldGrp(self.StartFrameField, q = True, v1 = True)
        self.EndFrame = cmds.intFieldGrp(self.EndFrameField, q = True, v1 = True)
        self.FrameTime = self.EndFrame - self.StartFrame
        self.referenceFullTime = self.FrameTime
        cmds.progressBar(self.ProgressControl, edit = True, maxValue = self.referenceFullTime)
        #Operate mean function for copying animation
        initialTime = time.time() #start time for all Actions
        self.CopyAnim(source = SrcObj, target = TargetObj, initTime = initialTime)

    #Buttons commands for Selection
    def SelectSrcObjectA(self):
        cmds.textFieldButtonGrp(self.SrcObjectA, edit = True, tx = cmds.ls(sl = True)[0])
    def SelectTgtObjectA(self):
        cmds.textFieldButtonGrp(self.TgtObjectA, edit = True, tx = cmds.ls(sl = True)[0])
    def SelectSrcObjectB(self):
        cmds.textFieldButtonGrp(self.SrcObjectB, edit = True, tx = cmds.ls(sl = True)[0])
    def SelectTgtObjectB(self):
        cmds.textFieldButtonGrp(self.TgtObjectB, edit = True, tx = cmds.ls(sl = True)[0])
    def SelectSrcObjectC(self):
        cmds.textFieldButtonGrp(self.SrcObjectC, edit = True, tx = cmds.ls(sl = True)[0])
    def SelectTgtObjectC(self):
        cmds.textFieldButtonGrp(self.TgtObjectC, edit = True, tx = cmds.ls(sl = True)[0])
    def SelectSrcObjectD(self):
        cmds.textFieldButtonGrp(self.SrcObjectD, edit = True, tx = cmds.ls(sl = True)[0])
    def SelectTgtObjectD(self):
        cmds.textFieldButtonGrp(self.TgtObjectD, edit = True, tx = cmds.ls(sl = True)[0])
        
CopyAnimation()
