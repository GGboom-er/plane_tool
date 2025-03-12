# coding=utf-8
import re
from PySide2 import QtWidgets, QtCore, QtGui
import maya.OpenMayaUI as omui
from shiboken2 import wrapInstance
import maya.cmds as mc
import attrTools as atpk
import pymel.core as pm
import EnvInfo
reload(atpk)


def getMayaMainWindow():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_window_ptr), QtWidgets.QWidget)


class AttrToolsUi(QtWidgets.QMainWindow):
    def __init__(self, parent=getMayaMainWindow()):
        super(AttrToolsUi, self).__init__(parent)
        self.setWindowTitle('AttrToolsUi')
        self.MainCtrl = None
        self.ctrlList = list()
        self.attrList = list()
        self.addCtrlList = list()
        self.attritemList = list()
        self.ctrllitemList = list()
        self.resize(500, 700)
        self.setFixedSize(500,700)

        self.attrToolsClass = atpk.AttrToolsClass()
        self.eeinfo = EnvInfo.EnvInfoClass()
        self.bulidUI()
        self.extraToolUI()
    def bulidUI(self):
        self.mainWeight = QtWidgets.QWidget(self)
        self.setCentralWidget(self.mainWeight)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.mainWeight.setLayout(self.layout)
        self.layout.setAlignment(QtCore.Qt.AlignTop)

        self.tabWeight = QtWidgets.QTabWidget(self)
        self.tabWeight.setTabShape(QtWidgets.QTabWidget.Triangular)
        self.tabWeight.resize(500, 700)
        self.tabWeight.setFont(QtGui.QFont(u'Microsoft YaHei', 8.5))
        self.attrToolsTAB = QtWidgets.QWidget()
        self.attrToolsTabLayout = QtWidgets.QVBoxLayout(self.attrToolsTAB)
        self.tabWeight.addTab(self.attrToolsTAB,u'AttrTools')

        self.extraToolsTAB = QtWidgets.QWidget()
        self.extraToolstabLayout = QtWidgets.QVBoxLayout(self.extraToolsTAB)
        self.tabWeight.addTab(self.extraToolsTAB, u'ExtraTools')

        self.mainInfoLayout = QtWidgets.QHBoxLayout()
        # mainLabel = QtWidgets.QLabel()
        # mainLabel.setText('Name:')
        # mainLabel.setFont(QtGui.QFont("Microsoft YaHei", 8, QtGui.QFont.Bold))
        # self.mainInfoLayout.addWidget(mainLabel)

        self.ctrlName = QtWidgets.QLineEdit()
        self.ctrlName.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.ctrlName.setEnabled(0)
        self.ctrlName.setMaximumWidth(260)
        self.ctrlName.setAlignment(QtCore.Qt.AlignCenter)
        self.ctrlName.setStyleSheet("color:rgb(0,255,255);")

        selectMainCtrl = QtWidgets.QPushButton('select MainCtrl')
        selectMainCtrl.setFont(QtGui.QFont("Microsoft YaHei", 8, QtGui.QFont.Bold))
        selectMainCtrl.clicked.connect(self.selMainCtrlFn)
        self.mainInfoLayout.addWidget(self.ctrlName)
        self.mainInfoLayout.addWidget(selectMainCtrl)

        self.infoLayout = QtWidgets.QHBoxLayout()
        self.attrLW = self.attrListWeightFn()
        self.ctrlLW = self.ctrlListWeightFn()

        self.infoLayout.addWidget(self.attrLW)
        self.infoLayout.addWidget(self.ctrlLW)

        self.toolBoxWight = QtWidgets.QScrollArea()
        self.toolBoxWight.setFont(QtGui.QFont(u'Microsoft YaHei', 5))
        self.toolBoxWight.setStyleSheet('QScrollArea {border:none;}')
        self.toolBoxLayout = QtWidgets.QVBoxLayout()

        self.collapsibleBox = CollapsibleBox('ConnectAttr')
        collLayout = QtWidgets.QVBoxLayout()
        self.connectAttrUI = BulkConnectUI()
        collLayout.addWidget(self.connectAttrUI)
        self.collapsibleBox.setContentLayout(collLayout)

        self.attrToolsTabLayout.addLayout(self.mainInfoLayout)
        self.attrToolsTabLayout.addLayout(self.infoLayout)
        self.toolBoxLayout.addWidget(self.collapsibleBox)
        self.toolBoxLayout.addItem(self.spacerItem())

        self.toolBoxWight.setLayout(self.toolBoxLayout)

        self.attrToolsTabLayout.addWidget(self.toolBoxWight)
        self.layout.addWidget(self.tabWeight)
    def spacerItem(self):
        spacerItem = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        return spacerItem
    def extraToolUI(self):
        showCacheMeshBT = QtWidgets.QPushButton('Show_Cache_All_Mesh')
        showCacheMeshBT.clicked.connect(self.Show_Cache_All_MeshFn)
        breakdataAttrBt = QtWidgets.QPushButton('Break_data_Attr')
        breakdataAttrBt.clicked.connect(self.Break_data_AttrFn)
        condataAttrBt = QtWidgets.QPushButton('Connect_data_Attr')
        condataAttrBt.clicked.connect(self.Connect_data_AttrFn)
        selAttrToselObj = QtWidgets.QPushButton('sel_Attr_To_selObj')
        selAttrToselObj.clicked.connect(self.sel_Attr_To_selObjFn)
        restoreDefaultBt = QtWidgets.QPushButton('Restore_Default_Attr')
        restoreDefaultBt.clicked.connect(self.Restore_Default_AttrFn)

        self.extraToolstabLayout.addWidget(showCacheMeshBT)
        self.extraToolstabLayout.addWidget(breakdataAttrBt)
        self.extraToolstabLayout.addWidget(condataAttrBt)
        self.extraToolstabLayout.addWidget(selAttrToselObj)
        self.extraToolstabLayout.addWidget(restoreDefaultBt)

        self.extraToolstabLayout.addItem(self.spacerItem())

    def attrListWeightFn(self):
        attrLW = QtWidgets.QListWidget()
        attrLW.setSelectionMode(QtWidgets.QAbstractItemView.ContiguousSelection)
        attrLW.setMaximumWidth(260)
        attrLW.setMinimumWidth(260)
        attrLW.setMinimumHeight(400)

        attrLW.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        attrLW.customContextMenuRequested[QtCore.QPoint].connect(self.attrListWeightMenu)
        attrLW.setFont(QtGui.QFont('Courier', 10))
        attrLW.setAcceptDrops(1)
        attrLW.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)

        attrLW.setStyleSheet('QListWidget {border:none;}')
        attrLW.itemSelectionChanged.connect(self.getSelectAttrFn)
        attrLW.itemDoubleClicked.connect(self.bulkConnectFn)
        return attrLW

    def getSelectAttrFn(self):
        selectItem = self.attrLW.selectedItems()
        if selectItem:
            self.attrList = [i.text() for i in selectItem]
        return self.attrList

    def addAttrInfolistItem(self):
        self.attrLW.clear()
        if self.attrToolsClass.attrList:
            self.attritemList = list()
            for i in self.attrToolsClass.attrList:
                item = QtWidgets.QListWidgetItem(i)
                item.setTextAlignment(QtCore.Qt.AlignCenter)
                # item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                self.attrLW.addItem(item)
                self.attritemList.append(item)
        return self.attrToolsClass.attrList
    def attrListWeightMenu(self):
        popMenu = QtWidgets.QMenu()
        popMenu.setStyleSheet("QMenu{background:black;}"  # 选项背景颜色
                              "QMenu{border:1px solid lightgray;}"  # 设置整个菜单框的边界高亮厚度
                              "QMenu{border-color:black;}"  # 整个边框的颜色
                              "QMenu::item{padding:0px 5px 0px 5px;}"  # 以文字为标准，右边距文字40像素，左边同理
                              "QMenu::item{height:20px;}"  # 显示菜单选项高度
                              "QMenu::item{color:black;}"  # 选项文字颜色
                              "QMenu::item{background:white;}"  # 选项背景
                              "QMenu::item{margin:1px 1px 1px 1px;}"  # 每个选项四边的边界厚度，上，右，下，左
                              "QMenu::item:selected:enabled{background:lightgray;}"
                              "QMenu::item:selected:enabled{color:blue;}"  # 鼠标在选项上面时，文字的颜色
                              "QMenu::item:selected:!enabled{background:transparent;}"  # 鼠标在上面时，选项背景为不透明

                              "QMenu::separator{height:1px;}"  # 要在两个选项设置self.groupBox_menu.addSeparator()才有用
                              "QMenu::separator{width:50px;}"
                              "QMenu::separator{background:blue;}"
                              "QMenu::separator{margin:0px 0px 0px 0px;}")
        popMenu.addAction(QtWidgets.QAction(u'Add Sel ChannelBox Attr', self, triggered=self.addChannelBoxAttr))
        popMenu.addAction(QtWidgets.QAction(u'Del Attr', self, triggered=self.delAttr))
        popMenu.addAction(QtWidgets.QAction(u'Drive Connect', self, triggered=self.drive_connectAttrFn))
        popMenu.exec_(QtGui.QCursor.pos())
    def addChannelBoxAttr(self):
        channelBoxAttr = atpk.AttrToolsClass.getSelectedChannels(self.MainCtrl)
        oldAttrList = self.attrToolsClass.attrList
        for attr in channelBoxAttr:
            if attr not  in oldAttrList:
                self.attrToolsClass.attrList.append(attr)
        self.addAttrInfolistItem()
    def delAttr(self):
        selItemList = [i.text() for i in self.attrLW.selectedItems()]
        oldAttrList = self.attrToolsClass.attrList
        for selItem in selItemList:
            if selItem in oldAttrList:
                self.attrToolsClass.attrList.remove(selItem)
        self.addAttrInfolistItem()
    def bulkConnectFn(self):
        if not self.collapsibleBox.checked:
            self.collapsibleBox.on_pressed()
        currentItem = self.attrLW.currentItem().text()
        mainCtrlInfo = self.MainCtrl+'.'+currentItem
        self.connectAttrUI.attrName.setText(mainCtrlInfo)
        channelBoxSel = pm.mel.eval('global string $gChannelBoxName; $temp=$gChannelBoxName;')
        pm.channelBox(channelBoxSel, e=1, s='')
        self.connectAttrUI.show()

    def ctrlListWeightFn(self):
        ctrlLW = QtWidgets.QListWidget()
        ctrlLW.setSelectionMode(QtWidgets.QAbstractItemView.ContiguousSelection)
        ctrlLW.setMaximumWidth(200)
        ctrlLW.setMinimumHeight(400)
        ctrlLW.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        ctrlLW.customContextMenuRequested[QtCore.QPoint].connect(self.ctrlListWeightMenu)
        ctrlLW.customContextMenuRequested[QtCore.QPoint].connect(self.ctrlListWeightMenuB)
        ctrlLW.setFont(QtGui.QFont('Courier', 11))
        ctrlLW.setAcceptDrops(1)
        ctrlLW.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        ctrlLW.setStyleSheet('QListWidget {border:none;}')
        ctrlLW.itemSelectionChanged.connect(self.getSelectCtrlFn)
        ctrlLW.itemClicked.connect(self.bulkConnect_Drive_ctrl_Fn)
        return ctrlLW

    def getSelectCtrlFn(self):
        self.addCtrlList = [i.text() for i in self.ctrlLW.selectedItems()]
        mc.select(self.addCtrlList)
        self.ctrlCurrentItem = self.ctrlLW.currentItem().text()
        self.connectAttrUI.conCtrlName.setText(str(self.addCtrlList))
        self.connectAttrUI.conCtrlNameList = self.addCtrlList
        channelsSelAttr = atpk.AttrToolsClass.getSelectedChannels(self.ctrlCurrentItem)
        if channelsSelAttr:
            self.connectAttrUI.driveAttrName.setText(channelsSelAttr[-1])
        return self.addCtrlList
    def bulkConnect_Drive_ctrl_Fn(self):
        channelsSelAttr = atpk.AttrToolsClass.getSelectedChannels(self.ctrlCurrentItem)
        if channelsSelAttr:
            self.connectAttrUI.driveAttrName.setText(channelsSelAttr[-1])
    def addCtrllistItem(self):
        self.ctrlLW.clear()
        if not self.ctrlList:
            self.ctrlList = self.attrToolsClass.selCtrl[:-1]
        for i in self.ctrlList:
            item = QtWidgets.QListWidgetItem(i)
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            # item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            self.ctrlLW.addItem(item)
            self.ctrllitemList.append(item)

    def ctrlListWeightMenu(self,pos):
        popMenu = QtWidgets.QMenu()
        popMenu.setStyleSheet("QMenu{background:black;}"  # 选项背景颜色
                  "QMenu{border:1px solid lightgray;}"  # 设置整个菜单框的边界高亮厚度
                           "QMenu{border-color:black;}"  # 整个边框的颜色
                           "QMenu::item{padding:0px 5px 0px 5px;}"  # 以文字为标准，右边距文字40像素，左边同理
                           "QMenu::item{height:20px;}"  # 显示菜单选项高度
                           "QMenu::item{color:black;}"#选项文字颜色
                           "QMenu::item{background:white;}"  # 选项背景
                           "QMenu::item{margin:1px 1px 1px 1px;}"  # 每个选项四边的边界厚度，上，右，下，左
                           "QMenu::item:selected:enabled{background:lightgray;}"
                           "QMenu::item:selected:enabled{color:blue;}"  # 鼠标在选项上面时，文字的颜色
                           "QMenu::item:selected:!enabled{background:transparent;}"#鼠标在上面时，选项背景为不透明
 
                           "QMenu::separator{height:1px;}"  # 要在两个选项设置self.groupBox_menu.addSeparator()才有用
                           "QMenu::separator{width:50px;}"
                           "QMenu::separator{background:blue;}"
                           "QMenu::separator{margin:0px 0px 0px 0px;}")
        popMenu.addAction(QtWidgets.QAction(u'Add Attr and Connect', self, triggered=self.addAttr_conAttrFn))
        popMenu.addAction(QtWidgets.QAction(u'Add Attr', self, triggered=self.addAttrFn))
        popMenu.addAction(QtWidgets.QAction(u'Connect', self, triggered=self.connectAttrFn))
        popMenu.addAction(QtWidgets.QAction(u'Del ctrl', self, triggered=self.del_Ctrl))

        hitIndex = self.ctrlLW.indexAt(pos).column()
        if hitIndex > -1:
            popMenu.exec_(QtGui.QCursor.pos())
    def ctrlListWeightMenuB(self,pos):
        popMenu = QtWidgets.QMenu()
        popMenu.setStyleSheet("QMenu{background:black;}"  # 选项背景颜色
                  "QMenu{border:1px solid lightgray;}"  # 设置整个菜单框的边界高亮厚度
                           "QMenu{border-color:black;}"  # 整个边框的颜色
 
                           "QMenu::item{padding:0px 5px 0px 5px;}"  # 以文字为标准，右边距文字40像素，左边同理
                           "QMenu::item{height:20px;}"  # 显示菜单选项高度
                           "QMenu::item{color:black;}"#选项文字颜色
                           "QMenu::item{background:white;}"  # 选项背景
                           "QMenu::item{margin:1px 1px 1px 1px;}"  # 每个选项四边的边界厚度，上，右，下，左
 
                           "QMenu::item:selected:enabled{background:lightgray;}"
                           "QMenu::item:selected:enabled{color:yellow;}"  # 鼠标在选项上面时，文字的颜色
                           "QMenu::item:selected:!enabled{background:transparent;}"#鼠标在上面时，选项背景为不透明
                           "QMenu::separator{height:1px;}"  # 要在两个选项设置self.groupBox_menu.addSeparator()才有用
                           "QMenu::separator{width:50px;}"
                           "QMenu::separator{background:blue;}"
                           "QMenu::separator{margin:0px 0px 0px 0px;}")

        popMenu.addAction(QtWidgets.QAction(u'Add sel Ctrl', self, triggered=self.add_sel_Ctrl))
        hitIndex = self.ctrlLW.indexAt(pos).column()
        if hitIndex == -1:
            popMenu.exec_(QtGui.QCursor.pos())
    def add_sel_Ctrl(self):
        for ctrl in mc.ls(sl =1):
            if ctrl not in self.ctrlList:
                self.ctrlList.append(ctrl)

        self.addCtrllistItem()
    def del_Ctrl(self):
        selItem = self.ctrlLW.currentItem().text()
        if selItem in self.ctrlList:
            self.ctrlList.remove(selItem)
        self.addCtrllistItem()
    def addAttrFn(self, clearinfo=1):
        if self.MainCtrl :
            if not self.attrList:
                self.attrList = [i.text() for i in self.attritemList]
            if not self.addCtrlList:
                self.addCtrlList = [i.text() for i in self.ctrllitemList]

            attrInfo = self.attrToolsClass.getAttrInfo(self.MainCtrl, self.attrList)
            for ctrl in self.addCtrlList:
                self.attrToolsClass.createAttr(ctrl, attrInfo.values())
            if clearinfo:
                self.clearAttrList_ctrlList()

    def connectAttrFn(self):
        if self.MainCtrl:
            if not self.attrList:
                self.attrList = [i.text() for i in self.attritemList]
            if not self.addCtrlList:
                self.addCtrlList = [i.text() for i in self.ctrllitemList]
            for ctrl in self.addCtrlList:
                self.attrToolsClass.connectAttrFn(self.MainCtrl, ctrl, self.attrList)
            self.clearAttrList_ctrlList()
    def drive_connectAttrFn(self):
        if self.MainCtrl:
            if not self.attrList:
                self.attrList = [i.text() for i in self.attritemList]
            if not self.addCtrlList:
                self.addCtrlList = [i.text() for i in self.ctrllitemList]
            for ctrl in self.addCtrlList:
                self.attrToolsClass.connectAttrFn(ctrl,self.MainCtrl, self.attrList)
            self.clearAttrList_ctrlList()
    def addAttr_conAttrFn(self):
        self.addAttrFn(clearinfo=0)
        self.connectAttrFn()
        self.clearAttrList_ctrlList()

    def clearAttrList_ctrlList(self):
        self.attrList = []
        self.addCtrlList = []
        self.attrLW.clearSelection()
        self.ctrlLW.clearSelection()

    def selMainCtrlFn(self):
        if mc.ls(sl =1):
            self.attrToolsClass.selCtrl = None
            self.attrToolsClass.attrList = None
            if self.attrToolsClass.selCtrl:
                self.MainCtrl = self.attrToolsClass.selCtrl[-1]
                self.ctrlName.setText(self.MainCtrl)
                self.addAttrInfolistItem()
                self.addCtrllistItem()

    def Show_Cache_All_MeshFn(self):
        meshList = self.eeinfo.getMeshList()
        notSetAttrList = list()
        for obj in meshList:
            if not mc.getAttr(obj+'.v'):
                try:
                    mc.setAttr(obj+'.v',1)
                except:
                    mc.warning(obj+'==>>>not setAttr')
                    notSetAttrList.append(obj)
        print notSetAttrList
    def Break_data_AttrFn(self):
        self.eeinfo.breatDataAttr()
    def Connect_data_AttrFn(self):
        self.eeinfo.connectDataAttr()
    def sel_Attr_To_selObjFn(self):
        if mc.objExists('visData'):
            selAttr = self.attrToolsClass.getSelectedChannels('visData')
            if selAttr:
                obj = [i.split('__vis__')[0] for i in selAttr if mc.objExists(i.split('__vis__')[0])]
                mc.select(obj)
    def Restore_Default_AttrFn(self):
        obj = mc.ls(sl = 1)
        self.attrToolsClass.setDefaultsBySelect(obj,key =1,lock = 0)
class BulkConnectUI(QtWidgets.QDialog):
    def __init__(self,parent=getMayaMainWindow()):
        super(BulkConnectUI, self).__init__(parent)
        self.conCtrlNameList = []
        self.setWindowTitle('BulkConnectUI')
        self.completionList = ['visibility', 'lodVisibility', 'overrideEnabled']
        self.resize(350, 150)
        self.bulidUI()

    def bulidUI(self):
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        AHboxLayout = self.AHboxLayoutFn()
        CHboxLayout = self.CHboxLayoutFn()
        BHboxLayout = self.BHboxLayoutFn()
        connectPB = QtWidgets.QPushButton('Connect')
        connectPB.clicked.connect(self.connectAttrFn)


        self.layout.addLayout(AHboxLayout)
        self.layout.addLayout(CHboxLayout)
        self.layout.addLayout(BHboxLayout)
        self.layout.addWidget(connectPB)

    def AHboxLayoutFn(self):
        AHboxLayout = QtWidgets.QHBoxLayout()
        aLabel = QtWidgets.QLabel()
        aLabel.setText('AttrName:')
        aLabel.setFont(QtGui.QFont("Microsoft YaHei", 8, QtGui.QFont.Bold))
        AHboxLayout.addWidget(aLabel)

        self.attrName = QtWidgets.QLineEdit()
        self.attrName.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.attrName.setEnabled(0)
        self.attrName.setMaximumWidth(330)
        self.attrName.setAlignment(QtCore.Qt.AlignCenter)
        self.attrName.setStyleSheet("color:rgb(0,255,255);")

        AHboxLayout.addWidget(self.attrName)
        return AHboxLayout

    def BHboxLayoutFn(self):
        BHboxLayout = QtWidgets.QHBoxLayout()
        bLabel = QtWidgets.QLabel()
        bLabel.setText('DriveName:')
        bLabel.setFont(QtGui.QFont("Microsoft YaHei", 8, QtGui.QFont.Bold))
        BHboxLayout.addWidget(bLabel)

        self.driveAttrName = QtWidgets.QLineEdit()
        self.driveAttrName.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.driveAttrName.setMaximumWidth(330)
        self.driveAttrName.setClearButtonEnabled(1)
        self.driveAttrName.setPlaceholderText('input connect Attr')
        self.driveAttrName.setAlignment(QtCore.Qt.AlignCenter)
        self.driveAttrName.setStyleSheet("color:rgb(0,255,255);")

        restr = QtCore.QRegExp('[a-zA-Z]+$')
        re_validato = QtGui.QRegExpValidator(restr, self)
        self.driveAttrName.setValidator(re_validato)
        self.driveAttrName.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.completer = QtWidgets.QCompleter(self.completionList)
        self.completer.setFilterMode(QtCore.Qt.MatchContains)

        self.completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)

        self.driveAttrName.setCompleter(self.completer)
        BHboxLayout.addWidget(self.driveAttrName)
        return BHboxLayout

    def CHboxLayoutFn(self):
        CHboxLayout = QtWidgets.QHBoxLayout()
        cLabel = QtWidgets.QLabel()
        cLabel.setText('DriveCtrl:')
        cLabel.setFont(QtGui.QFont("Microsoft YaHei", 8, QtGui.QFont.Bold))
        CHboxLayout.addWidget(cLabel)

        self.conCtrlName = QtWidgets.QLineEdit()
        self.conCtrlName.setFont(QtGui.QFont("Arial", 10, QtGui.QFont.Bold))
        self.conCtrlName.setEnabled(0)
        self.conCtrlName.setMaximumWidth(330)
        self.conCtrlName.setAlignment(QtCore.Qt.AlignCenter)
        self.conCtrlName.setStyleSheet("color:rgb(0,255,255);")

        CHboxLayout.addWidget(self.conCtrlName)

        return CHboxLayout

    def connectAttrFn(self):
        mainInfo = self.attrName.text()
        ctrlList =  self.conCtrlName.text()
        attr = self.driveAttrName.text()
        if ctrlList and mainInfo and ctrlList == str(self.conCtrlNameList):
            for ctrl in self.conCtrlNameList:
                mc.connectAttr(mainInfo,ctrl+'.'+attr,f =1)

class CollapsibleBox(QtWidgets.QWidget):

    def __init__(self, title='', checked = False,parent=None):
        super(CollapsibleBox, self).__init__(parent)
        self.checked = False
        self.toggle_button = QtWidgets.QToolButton(text=title, checkable=True, checked=self.checked)
        self.toggle_button.setStyleSheet('QToolButton {font-size:15px;}')
        self.toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
        self.toggle_button.clicked.connect(self.on_pressed)
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

    def on_pressed(self):
        #self.checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(QtCore.Qt.DownArrow if not self.checked else QtCore.Qt.RightArrow)
        self.toggle_animation.setDirection(
            QtCore.QAbstractAnimation.Forward if not self.checked else QtCore.QAbstractAnimation.Backward)
        self.toggle_animation.start()
        self.checked = not self.checked
        return self.checked
    on_pressed = QtCore.Slot()(on_pressed)

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


if __name__ == '__main__':
    pass
    '''
        import attrToolsUI as atpkUI
        reload(atpkUI)
        try:
            win.close()
            win.deleteLater()
        except:
            pass
        win = atpkUI.AttrToolsUi()
        win.show()
    '''
