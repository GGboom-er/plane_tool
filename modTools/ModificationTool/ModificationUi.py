#!/usr/bin/env python
# encoding:utf-8
from PySide2 import QtWidgets, QtCore, QtGui
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui
import maya.cmds as mc, maya.mel as mm, os, re,sys, ModificationSystem as ms ,facialTextureSysteam as fts
reload(ms)
reload(fts)
'''
import mayaTools.ModificationTool.ModificationUi as mmm
reload(mmm)
mmm.show()
'''
def getMayaMainWindow():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_window_ptr), QtWidgets.QMainWindow)
class ModificationWin(QtWidgets.QMainWindow):

    def __init__(self, parent=getMayaMainWindow()):
        super(ModificationWin, self).__init__(parent)
        self.savepath = None
        self.prefix = None
        self.camRotateDict = {'Normal':[0,0,0],'UP':[-45,0,0], 'Down':[45,0,0], 'Left':[0,45,0], 'Right':[0,-45,0],
                                 'Left_Up':[-45,45,0], 'Right_Up':[-45,-45,0],'Left_Down':[45,45,0], 'Right_Down':[45,-45,0]}
        self.setWindowTitle('ModificationWin')
        self.setObjectName('ModificationWin')
        self.setFixedSize(310, 718)
        self.__baseCameraList = ['Normal','UP', 'Down', 'Left', 'Right', 'Left_Up', 'Right_Up','Left_Down', 'Right_Down']
        self.__recomCameraList = []
        self.camView = 'Facial_aix_Camera'
        self.createLayout()
        self.createWeight()
        self.createButton()
    def createLayout(self):
        self.toolBoxWight = QtWidgets.QScrollArea(self)
        self.toolBoxWight.resize(310, 768)
        self.toolBoxWight.setFont(QtGui.QFont('Microsoft YaHei', 10.5))
        self.toolBoxWight.setStyleSheet('QScrollArea {border:none;}')
        self.toolBoxLayout = QtWidgets.QVBoxLayout()
        bulidRemodCam = QtWidgets.QPushButton('创建修型相机')
        bulidRemodCam.setFont(QtGui.QFont('Microsoft YaHei', 10.5))
        bulidRemodCam.clicked.connect(self.add_fix_cameraFn)
        self.toolBoxLayout.addWidget(bulidRemodCam)
        self.BSCB = CollapsibleBox('造型修正')
        self.toolBoxLayout.addWidget(self.BSCB)
        self.ATCB = CollapsibleBox('显隐设置')
        self.toolBoxLayout.addWidget(self.ATCB)
        self.ELCB = CollapsibleBox('层贴图设置')
        self.toolBoxLayout.addWidget(self.ELCB)
        self.CameraBSCB = CollapsibleBox('镜头造型修正')
        self.toolBoxLayout.addWidget(self.CameraBSCB)
        self.FTCB = CollapsibleBox('角色表情贴图')
        self.toolBoxLayout.addWidget(self.FTCB)
        spacerItem = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.toolBoxWight.setLayout(self.toolBoxLayout)
        self.toolBoxLayout.addItem(spacerItem)

    def createWeight(self):
        self.BSCB.setContentLayout(self.BSCBui())
        self.ATCB.setContentLayout(self.ATCBui())
        self.ELCB.setContentLayout(self.ELCBui())
        self.CameraBSCB.setContentLayout(self.CameraBSCBui())
        self.FTCB.setContentLayout(self.Facial_Texture_Ui())

    def createButton(self):
        pass

    def BSCBui(self):
        layout = QtWidgets.QVBoxLayout()
        Hlayout = QtWidgets.QHBoxLayout()
        Vlayout = QtWidgets.QVBoxLayout()
        self.BSlistWeight = QtWidgets.QListWidget()
        self.BSlistWeight.setMaximumWidth(99)
        self.BSlistWeight.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.BSlistWeight.customContextMenuRequested[QtCore.QPoint].connect(self.BSListWidgetContext)
        self.BSlistWeight.setFont(QtGui.QFont('Courier', 10))
        self.BSlistWeight.setAcceptDrops(1)
        self.BSlistWeight.setStyleSheet('QListWidget {border:none;}')
        self.BSlistWeight.itemChanged.connect(self.itemChangeTextFn)
        self.BSlistWeight.currentItemChanged.connect(self.itemCameraFn)
        self.BSlistWeight.itemDoubleClicked.connect(self.itemDouClickedFn)
        self.camListItem()
        self.bsAttrNameUi = QtWidgets.QLineEdit()
        self.bsAttrNameUi.setPlaceholderText('Input BSAttr Name')
        self.bsAttrNameUi.setFixedHeight(30)
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.bsAttrNameUi.setFont(font)
        self.bsAttrNameUi.setStyleSheet("""
            QLineEdit {
                color: red;
            }
            QLineEdit:placeholder {
                color: grey;
            }
        """)
        self.checkDrive = QtWidgets.QCheckBox(u"创建单独控制驱动")
        self.BSbt = QtWidgets.QPushButton(u'开始修型')
        self.BSbt.setStyleSheet('QPushButton {background: grey; font-size: 18px;'
                                'color: black; border-width: 3px; border-radius: 5px;'
                                'font-weight: bold;}'
                                'QPushButton:hover {background: lightgray;}')
        self.BSbt.clicked.connect(self.BSbtFn)
        mirrorBSbt = QtWidgets.QPushButton(u'镜像修型')
        mirrorBSbt.setStyleSheet('QPushButton{font-size:15px;}')
        mirrorBSbt.clicked.connect(self.mirrorBSbtFn)
        DelBSbt = QtWidgets.QPushButton(u'删除修型')
        DelBSbt.setStyleSheet('QPushButton{font-size:15px;}')
        DelBSbt.clicked.connect(self.DelBSbtFn)
        spacerItem = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)

        Vlayout.addWidget(self.bsAttrNameUi)
        Vlayout.addWidget(self.checkDrive)
        Vlayout.addWidget(self.BSbt)
        Vlayout.addWidget(mirrorBSbt)
        Vlayout.addWidget(DelBSbt)
        Vlayout.addItem(spacerItem)
        Hlayout.addWidget(self.BSlistWeight)
        Hlayout.addLayout(Vlayout)
        layout.addLayout(Hlayout)
        return layout

    @property
    def baseCameraList(self):
        return self.__baseCameraList

    @baseCameraList.setter
    def baseCameraList(self, obj):
        self.__baseCameraList = obj

    @property
    def recomCameraList(self):
        return self.__recomCameraList

    @recomCameraList.setter
    def recomCameraList(self, obj):
        self.__recomCameraList = obj

    def camListItem(self):
        for camName in self.baseCameraList:
            item = QtWidgets.QListWidgetItem(camName)
            item.setForeground(QtGui.QColor('coral'))
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            item.setFont(QtGui.QFont('Microsoft YaHei', 10.5))
            self.BSlistWeight.addItem(item)

        for i in self.recomCameraList:
            item = QtWidgets.QListWidgetItem(i)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            self.BSlistWeight.addItem(item)

    def itemChangeTextFn(self, item):
        camList = self.baseCameraList + self.recomCameraList
        if item.text() not in camList:
            item.setText(item.text())
            if self.douCliceItemName in self.baseCameraList:
                index = self.baseCameraList.index(self.douCliceItemName)
                self.baseCameraList.pop(index)
                self.baseCameraList.insert(index, item.text())
            elif self.douCliceItemName in self.recomCameraList:
                index = self.recomCameraList.index(self.douCliceItemName)
                self.recomCameraList.remove(index)
                self.recomCameraList.insert(index, item.text())
        else:
            item.setText(self.douCliceItemName)

    def itemDouClickedFn(self, item):
        self.douCliceItemName = item.text()

    def itemCameraFn(self, item):
        cameName = item.text()
        if not mc.window(self.camView, exists=1):
            self.camViewWindow = mc.window(self.camView)
            mc.window(self.camViewWindow,e =1,title=self.camView, w=800, h=1000,tlc=[0,0] )
            pane_layout = mc.paneLayout()
            self.view = mc.modelPanel(p=pane_layout, mbv=0,label=self.camView,modelEditor=True)
            mc.modelEditor(self.view, edit=True, camera=mc.listRelatives(self.camView,s =1)[0], displayTextures=True,
                             displayAppearance='smoothShaded',
                             useDefaultMaterial=False,
                             polymeshes=True,
                             nurbsCurves=False, nurbsSurfaces=False,
                             dynamics=False, fluids=False, hairSystems=False,
                             follicles=False, nCloths=False, nParticles=False,
                             nRigids=False, dynamicConstraints=False, locators=False,
                             manipulators=False, dimensions=False, handles=False, pivots=False,
                             textures=False, joints=False,sel = False)
        if mc.objExists(self.camView):
            mc.xform(self.camView, ws=1, ro=self.camRotateDict[cameName])
            self.bsAttrNameUi.setText(cameName)
        else:
            mc.warning("Don't Exist %s Camera" % self.camView)
        mc.showWindow(self.camViewWindow)
    def ATCBui(self):
        layout = QtWidgets.QVBoxLayout()
        hlayoutA = QtWidgets.QHBoxLayout()
        hlayoutB = QtWidgets.QHBoxLayout()
        ALbt = QtWidgets.QPushButton('设置模型显隐')
        ALbt.setStyleSheet('QPushButton{font-size:15px;}')
        ALbt.clicked.connect(self.ALbtFn)
        DelALbt = QtWidgets.QPushButton('删除显示设置')
        DelALbt.setStyleSheet('QPushButton{font-size:15px;}')
        DelALbt.clicked.connect(self.DelALbtFn)
        hlayoutA.addWidget(ALbt)
        hlayoutA.addWidget(DelALbt)
        PLbt = QtWidgets.QPushButton('设置Pencil显隐')
        PLbt.setStyleSheet('QPushButton{font-size:15px;}')
        PLbt.clicked.connect(self.PLbtFn)
        DelPLbt = QtWidgets.QPushButton('删除显示设置')
        DelPLbt.setStyleSheet('QPushButton{font-size:15px;}')
        DelPLbt.clicked.connect(self.DelALbtFn)
        hlayoutB.addWidget(PLbt)
        hlayoutB.addWidget(DelPLbt)
        layout.addLayout(hlayoutA)
        layout.addLayout(hlayoutB)
        return layout

    def ELCBui(self):
        layout = QtWidgets.QVBoxLayout()
        AddELbt = QtWidgets.QPushButton('载入贴图')
        AddELbt.setStyleSheet('QPushButton{font-size:15px;}')
        AddELbt.clicked.connect(self.AddELbtFn)
        DelELbt = QtWidgets.QPushButton(u'选择layerTexture清理无用连接')
        DelELbt.setStyleSheet('QPushButton{font-size:15px;}')
        DelELbt.clicked.connect(self.DelELbtFn)
        layout.addWidget(AddELbt)
        layout.addWidget(DelELbt)
        return layout

    def CameraBSCBui(self):
        layout = QtWidgets.QVBoxLayout()

        self.CBSbt = QtWidgets.QPushButton(u'开始修型')
        self.CBSbt.setStyleSheet('QPushButton{font-size:15px;}')
        self.CBSbt.setStyleSheet('QPushButton{background:grey;font-size:18px;color:black;border-radius:5px;}QPushButton:hover{background:lightgray;}')
        self.CBSbt.clicked.connect(self.BSbtFn)
        reBSbt = QtWidgets.QPushButton(u'修改造型')
        reBSbt.setStyleSheet('QPushButton{font-size:15px;}')
        DelBSbt = QtWidgets.QPushButton(u'删除修型')
        DelBSbt.setStyleSheet('QPushButton{font-size:15px;}')

        layout.addWidget(self.CBSbt)
        layout.addWidget(reBSbt)
        layout.addWidget(DelBSbt)
        return layout

    def Facial_Texture_Ui(self):
        layout = QtWidgets.QVBoxLayout()
        self.FTBT = QtWidgets.QPushButton(u'表情贴图制作工具')
        self.FTBT.clicked.connect(self.FTBTFn)
        layout.addWidget(self.FTBT)
        return layout
    def BSbtFn(self):
        bsText = self.BSbt.text()
        if bsText == u'开始修型':
            self.createFixMod = ms.BSModifiTool(BSpart = self.bsAttrNameUi.text(),
                                                createDrive = self.checkDrive.isChecked(),
                                                dirvenName = self.camView,dirveValue = 1.0,
                                                dirAttr = self.bsAttrNameUi.text(),
                                                oldDirveValue = 45.0)
            if self.createFixMod._BSModifiTool__obj:
                self.createFixMod.createBS()
                self.BSbt.setText(u'BS修型中---')
                self.BSbt.setStyleSheet('QPushButton {background: grey; font-size: 18px;'
                                    'color: red; border-width: 3px; border-radius: 5px;'
                                    'font-weight: bold;}'
                                    'QPushButton:hover {background: lightgray;}')

        else:
            self.createFixMod.buildConnectCtrl()
            self.bsAttrNameUi.setText('')
            self.BSbt.setText(u'开始修型')

            self.BSbt.setStyleSheet('QPushButton {background: grey; font-size: 18px;'
                                'color: black; border-width: 3px; border-radius: 5px;'
                                'font-weight: bold;}'
                                'QPushButton:hover {background: lightgray;}')

    def add_fix_cameraFn(self, driveName='Head_M' ):
        if mc.objExists(driveName):
            driveSysteam = 'Facial_aix_Systeam_Grp'
            if not mc.objExists(driveSysteam):
                file_path = os.path.dirname(__file__)+r"\Facial_aix_Systeam.ma"
                mc.file(file_path, i=True, ignoreVersion=True, ra=True, mergeNamespacesOnClash=False, namespace=":",
                        options="v=0;", pr=True, loadReferenceDepth="all")
            driveNamePnt = mc.xform(driveName, ws=1, t=1, q=1)
            mc.xform(driveSysteam, ws=1, t=[driveNamePnt[0],driveNamePnt[1]*1.02,driveNamePnt[2]])
            cameraOft = 'Facial_aix_Camera_Oft'
            if mc.objExists(cameraOft):
                mc.setAttr(cameraOft + '.tz', driveNamePnt[1] * 0.8)
                cameraName = 'Facial_aix_Camera'
                if mc.objExists(cameraName):
                    mc.xform(cameraName, piv=driveNamePnt, ws=1)
                    cameraNull = 'Facial_aix_Systeam_Null'
                    if mc.objExists(cameraNull):
                        mc.parentConstraint(driveName, cameraNull, mo=1)
                        if mc.objExists('Reference') and (driveSysteam not in mc.listRelatives('Reference',c =1)):
                            mc.parent(driveSysteam, 'Reference')
                        else:
                            return 0
                    else:
                        return 0
                else:
                    return 0
        else:
            return 0

    def mirrorBSbtFn(self):
        print u'镜像修型'

    def DelBSbtFn(self):
        selected_BSnodeList = mc.ls(selection=True,type = 'blendShape')
        selected_attrList = mc.channelBox('mainChannelBox', query=True, selectedHistoryAttributes=True)
        for bsnode in selected_BSnodeList:
            for attr in selected_attrList:
                ms.BSModifiTool.removeBS(bsnode,attr)
    def ALbtFn(self):
        print u'设置模型显隐'

    def ELbtFn(self):
        print u'贴图控制'

    def PLbtFn(self):
        print '设置Pencil显隐'

    def DelALbtFn(self):
        print '删除显示设置'

    def DelPLbtFn(self):
        print '删除显示设置'

    def AddELbtFn(self):
        print '载入贴图'

    def DelELbtFn(self):
        print u'清理layerTexture'
        layered_textures = mc.ls(sl=1, type='layeredTexture')
        for i in layered_textures:
            fts.clean_layered_textures(i)
    def showSencePLSN(self):
        indexTab = self.tabWeight.currentIndex()
        if indexTab == 2:
            self.addPLSNItem()

    def addPLSNItem(self):
        PLSNList = mc.ls(type='PencilLineSet')
        self.sencePLSNListWeight.clear()
        for i in PLSNList:
            item = QtWidgets.QListWidgetItem(i)
            self.sencePLSNListWeight.addItem(item)

    def selectPLSN(self):
        selectPLSN = self.sencePLSNListWeight.currentItem().text()
        mc.select(selectPLSN)
        mm.eval('editSelected')

    def BSListWidgetContext(self):
        popMenu = QtWidgets.QMenu()
        popMenu.addAction(QtWidgets.QAction(u'添加修型相机', self, triggered=self.addCameraFn))
        popMenu.addAction(QtWidgets.QAction(u'删除当前相机', self, triggered=self.delcameraFn))
        popMenu.addAction(QtWidgets.QAction(u'清除所有相机', self, triggered=self.reCameraFn))
        popMenu.exec_(QtGui.QCursor.pos())

    def addCameraFn(self):
        print '添加修型相机'

    def delcameraFn(self):
        print '删除当前相机'

    def reCameraFn(self):
        print '清除所有相机'

    def FTBTFn( self ):
        if mc.window('facialTextureUi', q=1, ex=1):
            mc.deleteUI('facialTextureUi')
        self.facialTextureUi = FacialTextureClass(parent=getMayaMainWindow())
        self.facialTextureUi.show()

    def closeEvent(self, event):
        if self.camView:
            if mc.window(self.camView, q=1, ex=1):
                mc.deleteUI(self.camView)
        try:
            self.facialTextureUi.close()
        except:
            pass
class CollapsibleBox(QtWidgets.QWidget):

    def __init__(self, title='', parent=None):
        super(CollapsibleBox, self).__init__(parent)
        self.toggle_button = QtWidgets.QToolButton(text=title, checkable=True, checked=True)
        self.toggle_button.setStyleSheet('QToolButton {font-size:18px;}QToolButton:checked { background-color: #808080; }')
        self.toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
        self.toggle_button.pressed.connect(self.on_pressed)
        self.toggle_animation = QtCore.QParallelAnimationGroup(self)
        self.content_area = QtWidgets.QScrollArea(maximumHeight=0, minimumHeight=0)
        self.content_area.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.content_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggle_button)
        lay.addWidget(self.content_area)
        self.toggle_animation.addAnimation(QtCore.QPropertyAnimation(self, 'minimumHeight'))
        self.toggle_animation.addAnimation(QtCore.QPropertyAnimation(self, 'maximumHeight'))
        self.toggle_animation.addAnimation(QtCore.QPropertyAnimation(self.content_area, 'maximumHeight'))

    @QtCore.Slot()
    def on_pressed( self ):

        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow)
        self.toggle_animation.setDirection(
            QtCore.QAbstractAnimation.Forward if checked else QtCore.QAbstractAnimation.Backward)
        self.toggle_animation.start()

    def setContentLayout(self, layout):
        lay = self.content_area.layout()
        del lay
        self.content_area.setLayout(layout)
        collapsed_height = self.sizeHint().height() - self.content_area.maximumHeight()
        content_height = layout.sizeHint().height()
        for i in range(self.toggle_animation.animationCount()):
            animation = self.toggle_animation.animationAt(i)
            animation.setDuration(100)
            animation.setStartValue(collapsed_height)
            animation.setEndValue(collapsed_height + content_height)

        content_animation = self.toggle_animation.animationAt(self.toggle_animation.animationCount() - 1)
        content_animation.setDuration(100)
        content_animation.setStartValue(0)
        content_animation.setEndValue(content_height)
class FileDropLineEdit(QtWidgets.QLineEdit):
    def __init__( self, parent=None ):
        super(FileDropLineEdit, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setReadOnly(True)
        self.setStyleSheet("QLineEdit { font-size: 8pt; color: lightblue; }")

    def dragEnterEvent( self, event ):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent( self, event ):
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            self.setText(file_path)

    def mouseDoubleClickEvent( self, event ):
        current_text = self.text()
        print  current_text
        # 判断路径是否为文件夹
        if os.path.isdir(current_text):
            default_folder_path = current_text
        # 判断路径是否为文件
        elif os.path.isfile(current_text):
            default_folder_path = os.path.dirname(current_text)
        else:
            default_folder_path = ""

        # 打开文件选择对话框
        filePath, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select File", default_folder_path)
        if filePath:
            self.setText(filePath)

class FacialTextureClass(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(FacialTextureClass, self).__init__(parent=parent)
        FacialTextureClass.instance = self
        self.DefaultPath = r's:\Project\wmrs\sourceimages\chr'
        self.ctrlDict = {
            'L_BrowInnerIn': 'EyeBrowInner_L.squeeze', 'R_BrowInnerIn': 'EyeBrowInner_R.squeeze',
            'L_Eyelid': 'EyeBrowInner_L.translateY', 'R_Eyelid': 'EyeBrowInner_R.translateY',
            'L_BrowRegionDown': 'EyeBrowRegion_L.translateY', 'R_BrowRegionDown': 'EyeBrowRegion_R.translateY',
            'L_Wrinkle': 'NoseSide_L.translateY', 'R_Wrinkle': 'NoseSide_R.translateY',
            'L_Nose': 'NoseRegion_M.Side_NoseRegion_Shadow', 'R_Nose': 'NoseRegion_M.Side_NoseRegion_Shadow',
            'M_Nose_B': 'NoseRegion_M.Under_NoseRegion_Shadow',
            'M_Lips_B': 'LipRegion_M.LipRegion_Shadow'
        }
        self.setObjectName('facialTextureUi')
        self.row_groups = []  # 用于记录每次添加的子QTableWidget
        self.buttons = [
            ('BrowInner', {"L_BrowInnerIn": "PATH","R_BrowInnerIn": "PATH"}),
            ('Eyelid', {"L_Eyelid": "PATH", "R_Eyelid": "PATH"}),
            ('BrowRegionDown', {"L_BrowRegionDown": "PATH", "R_BrowRegionDown": "PATH"}),
            ('Wrinkle', {"L_Wrinkle": "PATH", "R_Wrinkle": "PATH"}),
            ('Nose', {"M_Nose_B": "PATH", "L_Nose": "PATH", "R_Nose": "PATH"}),
            ('Lips', {"M_Lips_B": "PATH"})
        ]
        self.initUI()
    def initUI(self):
        # 设置窗口标题和尺寸
        self.setWindowTitle('表情贴图')
        self.setGeometry(300, 300, 600, 850)  # 默认容纳12行的内容及其分割线高度

        # 创建主布局
        self.mainLayout = QtWidgets.QVBoxLayout()

        # 创建顶部布局和控件
        topLayout = QtWidgets.QHBoxLayout()
        self.chrName = QtWidgets.QLabel(u"角色名称")
        self.chrName.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
        self.chrName.setStyleSheet('QLabel{background:grey;font-size:22px;color:yellow;border-radius:5px;}')
        self.chrName.setAlignment(QtCore.Qt.AlignCenter)
        topLayout.addWidget(self.chrName)

        self.textureLayerName = QtWidgets.QLabel("LayerTexture_Node_Name")
        self.textureLayerName.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
        self.textureLayerName.setStyleSheet('QLabel{background:grey;font-size:18px;color:red;border-radius:5px;}')
        self.textureLayerName.setAlignment(QtCore.Qt.AlignCenter)
        topLayout.addWidget(self.textureLayerName)
        topButton = QtWidgets.QPushButton(u"选择角色头部层材质节点", self)
        topButton.clicked.connect(self.getTextureLayerNodeFn)
        topLayout.addWidget(topButton)
        self.mainLayout.addLayout(topLayout)

        # 创建主QTableWidget
        self.mainTableWidget = QtWidgets.QTableWidget()
        self.mainTableWidget.setColumnCount(1)  # 设置一列，用于包含子QTableWidget
        self.mainTableWidget.horizontalHeader().setVisible(False)
        self.mainTableWidget.verticalHeader().setVisible(False)
        self.mainTableWidget.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)

        initialLayout = QtWidgets.QHBoxLayout()
        initialLayout.addWidget(QtWidgets.QLabel("表情驱动部位:"))
        initialLayout.addWidget(QtWidgets.QLabel("表情贴图路径:"))

        initialWidget = QtWidgets.QWidget()
        initialWidget.setLayout(initialLayout)

        initialRow = self.mainTableWidget.rowCount()
        self.mainTableWidget.insertRow(initialRow)
        self.mainTableWidget.setCellWidget(initialRow, 0, initialWidget)

        self.mainLayout.addWidget(self.mainTableWidget)

        # 创建按钮布局
        self.buttonLayout = QtWidgets.QHBoxLayout()
        for name, data in self.buttons:
            button = QtWidgets.QPushButton(name, self)
            button.clicked.connect(self.createAddCustomTableFunction(name, data, button))
            button.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            button.customContextMenuRequested.connect(self.createShowContextMenuFunction(button))
            self.buttonLayout.addWidget(button)
        self.mainLayout.addLayout(self.buttonLayout)

        # 添加底部按钮
        bottomButtonA = QtWidgets.QPushButton(u"规范贴图路径", self)
        bottomButtonA.clicked.connect(self.StandardizeTexturePath)
        self.mainLayout.addWidget(bottomButtonA)

        # 添加底部按钮
        bottomButton = QtWidgets.QPushButton(u"创建驱动", self)
        bottomButton.clicked.connect(self.createDirve)
        self.mainLayout.addWidget(bottomButton)

        # 设置窗口的主要布局
        self.setLayout(self.mainLayout)

    def createShowContextMenuFunction(self, button):
        return lambda pos: self.showContextMenu(pos, button)

    def createAddCustomTableFunction(self, title, data, button):
        return lambda: self.addCustomTable(title, data, button)
    def showContextMenu(self, pos, button):
        contextMenu = QtWidgets.QMenu(self)
        deleteAction = contextMenu.addAction("删除驱动")
        deleteAction.triggered.connect(lambda: self.deleteGroup(button))
        contextMenu.exec_(button.mapToGlobal(pos))

    def addCustomTable( self, title, data, button ):
        if self.chrName.text() not in [u'存一下文件确保文件符合命名规范',
                                       u'角色名称'] and self.textureLayerName.text() not in ['select textureLayerNode',
                                                                                             'LayerTexture_Node_Name']:
            # 创建一个新的子QTableWidget
            subTableWidget = QtWidgets.QTableWidget()
            subTableWidget.setColumnCount(3)  # 设置三列
            subTableWidget.verticalHeader().setVisible(False)  # 隐藏行号
            subTableWidget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)  # 去除右边的滚动条
            subTableWidget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)  # 去除下边的滚动条

            subTableWidget.horizontalHeader().setVisible(False)
            subTableWidget.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
            subTableWidget.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            subTableWidget.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
            subTableWidget.horizontalHeader().setSectionResizeMode(2,
                                                                   QtWidgets.QHeaderView.ResizeToContents)  # 最后一列宽度设置

            # 添加标题行
            title_row_position = subTableWidget.rowCount()
            subTableWidget.insertRow(title_row_position)
            titleItem = QtWidgets.QTableWidgetItem(title)
            titleItem.setFlags(titleItem.flags() & ~QtCore.Qt.ItemIsSelectable & ~QtCore.Qt.ItemIsEditable)  # 设置标题行不可编辑
            titleItem.setBackground(QtCore.Qt.lightGray)
            titleItem.setFont(QtGui.QFont("Arial", 12, QtGui.QFont.Bold))
            titleItem.setForeground(QtGui.QBrush(QtGui.QColor("black")))
            subTableWidget.setSpan(title_row_position, 0, 1, 3)
            subTableWidget.setItem(title_row_position, 0, titleItem)

            # 插入额外的行函数
            def insert_extra_row( table, text ):
                extra_row_position = table.rowCount()
                table.insertRow(extra_row_position)
                extraItem1 = QtWidgets.QTableWidgetItem("NodeName==>")
                extraItem1.setFlags(extraItem1.flags() & ~QtCore.Qt.ItemIsSelectable & ~QtCore.Qt.ItemIsEditable)
                extraItem1.setBackground(QtCore.Qt.black)
                extraItem1.setForeground(QtCore.Qt.white)  # 设置字体颜色为白色
                extraItem1.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Normal))

                extraItem2 = QtWidgets.QTableWidgetItem(text)
                extraItem2.setTextAlignment(QtCore.Qt.AlignCenter)
                extraItem2.setFlags(extraItem2.flags() & ~QtCore.Qt.ItemIsSelectable & ~QtCore.Qt.ItemIsEditable)
                extraItem2.setBackground(QtCore.Qt.black)

                table.setItem(extra_row_position, 0, extraItem1)
                table.setSpan(extra_row_position, 0, 1, 1)
                table.setItem(extra_row_position, 1, extraItem2)
                table.setSpan(extra_row_position, 1, 1, 2)
                return extra_row_position

            for part, path in data.items():
                if path == 'PATH':
                    path = self.DefaultPath + r'\\' + self.chrName.text() + r'\rig\facial\\' + part + '.tif'

                    # 插入额外行
                    extra_row_position = insert_extra_row(subTableWidget, part)

                    row_position = subTableWidget.rowCount()
                    subTableWidget.insertRow(row_position)

                    partItem = QtWidgets.QTableWidgetItem(part)
                    partItem.setFlags(
                        partItem.flags() & ~QtCore.Qt.ItemIsSelectable & ~QtCore.Qt.ItemIsEditable)  # 设置第一列不可编辑
                    pathItem = FileDropLineEdit()  # 使用自定义的FileDropLineEdit
                    pathItem.setText(path)

                    lastColumnItem = QtWidgets.QTableWidgetItem(u"载入")  # 最后一列
                    lastColumnItem.setFlags(
                        lastColumnItem.flags() & ~QtCore.Qt.ItemIsSelectable & ~QtCore.Qt.ItemIsEditable)  # 设置不可选中、不可编辑
                    lastColumnItem.setTextAlignment(QtCore.Qt.AlignCenter)

                    partItem.setTextAlignment(QtCore.Qt.AlignCenter)
                    subTableWidget.setItem(row_position, 0, partItem)
                    subTableWidget.setCellWidget(row_position, 1, pathItem)
                    subTableWidget.setItem(row_position, 2, lastColumnItem)  # 添加最后一列

                    partItem.setData(QtCore.Qt.UserRole, (part, path))

                    # 只绑定第一列的点击事件
                    partItem.setFlags(partItem.flags() | QtCore.Qt.ItemIsSelectable)
                    partItem.setData(QtCore.Qt.UserRole, (part, path))
                    subTableWidget.setItem(row_position, 0, partItem)

                    # 记录额外行的位置
                    subTableWidget.setProperty("extra_row_position_{}".format(row_position), extra_row_position)

            subTableWidget.cellDoubleClicked.connect(
                lambda row, col: self.printFunction(subTableWidget, row, col))  # 双击事件
            subTableWidget.cellClicked.connect(self.partItemClicked)

            # 添加分割线
            separator_row_position = subTableWidget.rowCount()
            subTableWidget.insertRow(separator_row_position)
            subTableWidget.setRowHeight(separator_row_position, 10)  # 设置分割行高度

            separator = QtWidgets.QTableWidgetItem("")
            separator.setFlags(
                separator.flags() & ~QtCore.Qt.ItemIsSelectable & ~QtCore.Qt.ItemIsEditable)  # 设置不可选择且不可编辑
            separator.setBackground(QtCore.Qt.black)  # 设置背景颜色以区分

            subTableWidget.setSpan(separator_row_position, 0, 1, 3)  # 跨越三列
            subTableWidget.setItem(separator_row_position, 0, separator)

            # 将子QTableWidget添加到主QTableWidget中
            row_position = self.mainTableWidget.rowCount()
            self.mainTableWidget.insertRow(row_position)
            self.mainTableWidget.setCellWidget(row_position, 0, subTableWidget)

            # 设置主QTableWidget行的高度，以适应子QTableWidget的内容
            subTableWidgetHeight = subTableWidget.verticalHeader().length() + subTableWidget.horizontalHeader().height()
            self.mainTableWidget.setRowHeight(row_position, subTableWidgetHeight + 10)  # 稍微增加一点高度

            # 记录子QTableWidget
            self.row_groups.append((button, subTableWidget))
        else:
            mc.warning(u'----------确保文件名正确以及layeredTexture节点存在----------')

    def printFunction( self, subTableWidget, row, column ):
        if column == 2:  # 检查是否双击的是最后一列
            fileNodes = mc.ls(sl=True, type='file')
            if fileNodes:
                filePath = mc.getAttr(fileNodes[0] + '.fileTextureName')
                subTableWidget.cellWidget(row, 1).setText(filePath)
                extra_row_position = subTableWidget.property("extra_row_position_{}".format(row))
                if extra_row_position is not None:
                    subTableWidget.item(extra_row_position, 1).setText(fileNodes[0])

    def deleteGroup(self, button):
        for btn, subTableWidget in self.row_groups:
            if btn == button:
                index = self.mainTableWidget.indexAt(subTableWidget.pos())
                if index.isValid():
                    row = index.row()
                    self.mainTableWidget.removeRow(row)
                    self.row_groups.remove((btn, subTableWidget))
                break

    def partItemClicked(self, row, column):
        if column == 0:
            item = self.sender().item(row, column)
            data = item.data(QtCore.Qt.UserRole)
            if data:
                channel_box = mm.eval('$temp=$gChannelBoxName')
                if data[0] in self.ctrlDict.keys():
                    mc.select(cl=1)
                    mc.select(self.ctrlDict[data[0]].split('.')[0])
                    mc.channelBox(channel_box, edit=True, select=[self.ctrlDict[data[0]]])
                for button, subTableWidget in self.row_groups:
                    for i in range(subTableWidget.rowCount()):
                        subTableWidget.setRangeSelected(QtWidgets.QTableWidgetSelectionRange(i, 0, i, 1), False)

    def getTextureLayerNodeFn(self):
        self.textureLayerNode = mc.ls(sl=1, type='layeredTexture') or ['select textureLayerNode']
        if self.textureLayerNode:
            self.textureLayerName.setText(self.textureLayerNode[0])
        self.filePath = mc.file(q=True, sceneName=True).split('/')[-1] or [u'存一下文件确保文件符合命名规范']
        if self.filePath:
            self.chrName.setText(self.filePath.split('_')[2])

    def getAllTableData( self ):
        self.data_dict = {}
        for button, subTableWidget in self.row_groups:
            title = subTableWidget.item(0, 0).text()
            row_data = {}
            row = 1
            while row < subTableWidget.rowCount():
                part_item = subTableWidget.item(row, 0)
                path_item = subTableWidget.cellWidget(row, 1)
                if part_item and path_item:
                    part = part_item.text()
                    path = path_item.text()
                    # 获取插入的新增行的第二列信息
                    extra_row_position = subTableWidget.property("extra_row_position_{}".format(row))
                    if extra_row_position is not None:
                        extra_info_item = subTableWidget.item(extra_row_position, 1)
                        extra_info = extra_info_item.text() if extra_info_item else ""
                    else:
                        extra_info = ""
                    row_data[part] = {"path": path, "nodeName": extra_info}
                    row += 1  # 跳过正常行
                row += 1  # 跳过分隔行
            self.data_dict[title] = row_data
    def createDirve( self ):
        self.getAllTableData()
        fts.addDirveAttr()
        fileNode = list()
        for dirve, infos in self.data_dict.items():
            for name, info in infos.items():
                ctrlName = self.ctrlDict[name].split('.')[0]
                textureNode = info['nodeName']
                path = info['path']
                textureNode = fts.create_and_connect_file_node(nodeName=textureNode, texture_path=path)
                fileNode.append(textureNode)
                if dirve == 'Eyelid':
                    textureNodeList = list()
                    if 'BrowRegionDown' in self.data_dict:
                        textureNodeList.append(textureNode)
                        BrowRegionDownInfo =self.data_dict['BrowRegionDown'][name.replace('Eyelid','BrowRegionDown')]
                        BrowRegionDownNodeName = fts.create_and_connect_file_node(nodeName=BrowRegionDownInfo['nodeName'], texture_path=BrowRegionDownInfo['path'])
                        textureNodeList.append(BrowRegionDownNodeName)
                        fileNode.append(textureNode)
                        fts.EyeLidDirveFn(EyeLid = ctrlName,EyeBrowRegion =ctrlName.replace('EyeBrowInner','EyeBrowRegion'),textureNode = textureNodeList)
                    else:
                        textureNodeList.append(textureNode)
                        fts.EyeLidDirveFn(EyeLid = ctrlName,textureNode = [textureNode])
                elif dirve == 'BrowRegionDown':
                    continue
                elif dirve == 'BrowInner':
                    fts.BrowLnnerDirveFn(ctrlName = ctrlName,textureNode = textureNode)
                elif dirve == 'Wrinkle':
                    fts.WrinkleDirveFn(ctrlName,textureNode)
                elif dirve == 'Nose':
                    fts.NoseDirveFn(ctrlName = ctrlName,textureNode = textureNode,type = name)
                elif dirve == 'Lips':
                    fts.LipsDirveFn(ctrlName = ctrlName,textureNode = textureNode)
        fts.insert_files_to_layered_texture(self.textureLayerName.text(),fileNode)

    def setAllTableData( self, data_dict ):
        for button, subTableWidget in self.row_groups:
            title = subTableWidget.item(0, 0).text()
            if title in data_dict:
                row_data = data_dict[title]
                row = 2
                for part, details in row_data.items():
                    if row < subTableWidget.rowCount():
                        part_item = subTableWidget.item(row, 0)
                        path_item = subTableWidget.cellWidget(row, 1)
                        if part_item and path_item:
                            part_item.setText(part)
                            path_item.setText(details.get("path", ""))
                            extra_info = details.get("nodeName", "")
                            extra_row_position = subTableWidget.property("extra_row_position_{}".format(row))
                            if extra_row_position is not None:
                                extra_info_item = subTableWidget.item(extra_row_position, 1)
                                if extra_info_item:
                                    extra_info_item.setText(extra_info)
                        row += 1  # 跳过正常行
                    row += 1  # 跳过分隔行
    def StandardizeTexturePath( self ):

        self.getAllTableData()
        for dirve, infos in self.data_dict.items():
            for name, info in infos.items():
                sorcepath = info['path']
                path = self.DefaultPath + r'\\' + self.chrName.text() + r'\rig\facial\\' + name + '.tif'
                if os.path.abspath(sorcepath) != os.path.abspath(path):
                    fts.copy_and_rename_file(sorcepath,path)
                else:
                    if not os.path.exists(path) :
                        sorcepath = os.path.dirname(__file__) + r'\normals.tif'
                        fts.copy_and_rename_file(sorcepath, path)
                fts.create_and_connect_file_node(path,info['nodeName'])
                fts.insert_files_to_layered_texture(self.textureLayerName.text(), [info['nodeName']])
                self.data_dict[dirve][name]['path'] = path
        self.setAllTableData(self.data_dict)
def show():
    if mc.window('ModificationWin', q=1, ex=1):
        mc.deleteUI('ModificationWin')
    win = ModificationWin()
    win.show()
    return win




