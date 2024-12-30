# coding=utf-8
from PySide2 import QtWidgets, QtCore, QtGui
from shiboken2 import wrapInstance
import maya.OpenMayaUI as  omui
import dialogWin
import getTimeInfo
import CutTime

from python.meta import widgetConfig
import maya.cmds as mc
import os,re

def getMayaMainWindow():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_window_ptr), QtWidgets.QWidget)
class CutTimeWin(QtWidgets.QMainWindow):
    def __init__(self, parent = getMayaMainWindow()):
        super(CutTimeWin, self).__init__(parent)
        self.savepath =None
        self.prefix =None
        self.__cfg = widgetConfig.Configuration('CutTimeInfo')
        self.setObjectName('CutTimeWin')
        self.r_CutTimeInfo()
        self.resize(389, 700)
        self.setWindowTitle('CutTimeWin')
        self._timeInfo = {}
        self.winInfo = []
        self.fpsDict = {'game':'15','film':'24','pal':'25','ntsc':'30','show':'48','palf':'50','ntscf':'60'}
        self.fps = mc.currentUnit(t = 1, q = 1)
        self.buildLayout()
        self.getfileName()
    def createCutTimeInfo(self):
        self.__cfg.set('path', str(self.savepath))
        self.__cfg.save()
    def r_CutTimeInfo(self):
        self.savepath = self.__cfg.get('path','')
    def buildLayout(self):
        self.mainWeight = QtWidgets.QWidget(self)
        self.setCentralWidget(self.mainWeight)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.mainWeight.setLayout(self.layout)
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.importFileWinLayout = QtWidgets.QHBoxLayout()
        self.saveFileWinLayout = QtWidgets.QHBoxLayout()
        self.importLabel = QtWidgets.QLabel()
        self.importLabel.setText('存储路径:')
        self.importLabel.setFont(QtGui.QFont("Microsoft YaHei", 10, QtGui.QFont.Bold))
        self.saveLabel = QtWidgets.QLabel()
        self.saveLabel.setText('镜头场次:')
        self.saveLabel.setFont(QtGui.QFont("Microsoft YaHei", 10, QtGui.QFont.Bold))
        selectFilePathBT = QtWidgets.QPushButton('选择路径')
        selectFilePathBT.setFont(QtGui.QFont("Microsoft YaHei", 10, QtGui.QFont.Bold))
        selectFilePathBT.clicked.connect(self.getfilePath)
        TollHelpBt = QtWidgets.QPushButton('工具帮助')
        TollHelpBt.clicked.connect(self.ToolHelpFn)
        TollHelpBt.setFont(QtGui.QFont("Microsoft YaHei", 10, QtGui.QFont.Bold))
        self.saveFileText = QtWidgets.QLineEdit()
        self.saveFileText.textChanged.connect(self.changeCamPrefixFn)
        self.importFileText = QtWidgets.QLineEdit()
        self.importFileText.setText(self.savepath)
        self.importFileText.textChanged.connect(self.changeSavePath)
        self.importFileWinLayout.addWidget(self.importLabel)
        self.importFileWinLayout.addWidget(self.importFileText)
        self.importFileWinLayout.addWidget(selectFilePathBT)
        self.saveFileWinLayout.addWidget(self.saveLabel)
        self.saveFileWinLayout.addWidget(self.saveFileText)
        self.saveFileWinLayout.addWidget(TollHelpBt)
        self.layout.addLayout(self.importFileWinLayout)
        self.layout.addLayout(self.saveFileWinLayout)
        self.domake = QtWidgets.QPushButton('拆分文件')
        self.domake.setFont(QtGui.QFont("Microsoft YaHei",10,QtGui.QFont.Bold))
        self.domake.clicked.connect(self.cutTimeInfo)
        self.analysisInfoBt = QtWidgets.QPushButton('分析场景Camera')
        self.analysisInfoBt.setFont(QtGui.QFont("Microsoft YaHei", 10, QtGui.QFont.Bold))
        self.analysisInfoBt.clicked.connect(self.analysisFileCutTimeInfo)
        self.infoLayout = QtWidgets.QHBoxLayout()
        self.camlistWeight = self.camlistWeightFn()
        camListItem = self.addlistItem()
        self.keyinfoWeight = self.keyinfoWeightFn()
        self.infoLayout.addWidget(self.camlistWeight)
        self.infoLayout.addWidget(self.keyinfoWeight)
        self.layout.addLayout(self.infoLayout)
        self.layout.addWidget(self.analysisInfoBt)
        self.layout.addWidget(self.domake)
    def ToolHelpFn(self):
        self.dialog_fault = QtWidgets.QDialog(self)
        self.dialog_fault.setWindowTitle('CutTimeHelp')
        self.dialog_fault.resize(717,934)
        self.dialog_fault.setFixedSize(717,934)
        self.dialog_fault.move(0,0)
        url_father = os.path.dirname(os.path.abspath(__file__))
        image_path = url_father + "/CutTimeHelp.png"
        pic = QtGui.QPixmap(image_path)
        label_pic = QtWidgets.QLabel("show", self.dialog_fault)
        label_pic.setPixmap(pic)
        self.dialog_fault.exec_()
    def changeSavePath(self):
        self.savepath = self.importFileText.text()
        self.__cfg.set('path', str(self.savepath))
        self.__cfg.save()
    def changeCamPrefixFn(self):
        self.prefix = self.saveFileText.text()
    def camlistWeightFn(self):
        camlistWeight = QtWidgets.QListWidget()
        camlistWeight.setMaximumWidth(100)
        camlistWeight.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        camlistWeight.customContextMenuRequested[QtCore.QPoint].connect(self.myListWidgetContext)
        camlistWeight.setFont(QtGui.QFont('Courier', 17))
        camlistWeight.setAcceptDrops(1)
        camlistWeight.setEditTriggers(QtWidgets.QAbstractItemView.DoubleClicked)
        camlistWeight.setStyleSheet('QListWidget {border:none;}')
        camlistWeight.itemClicked.connect(self.itemclick)
        camlistWeight.itemDoubleClicked.connect(self.itemDouClickedFn)
        camlistWeight.itemChanged.connect(self.itemChangeTextFn)
        return camlistWeight
    def keyinfoWeightFn(self):
        keyinfoWeight = QtWidgets.QTableWidget()
        keyinfoWeight.setFont(QtGui.QFont("Times", 10, QtGui.QFont.Black))
        keyinfoWeight.setBackgroundRole(QtGui.QPalette.ColorRole(1))
        keyinfoWeight.setColumnCount(3)
        keyinfoWeight.setHorizontalHeaderLabels(['CurrentKey', 'HoldKey', ''])
        keyinfoWeight.horizontalHeader().resizeSection(2, 26)
        keyinfoWeight.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        keyinfoWeight.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        keyinfoWeight.setStyleSheet('QTableWidget {border:none;}')
        keyinfoWeight.resize(2, 20)
        return keyinfoWeight
    def myListWidgetContext(self):
        popMenu = QtWidgets.QMenu()
        popMenu.addAction(QtWidgets.QAction(u'添加镜头', self, triggered = self.addcamDialogShow))
        popMenu.addAction(QtWidgets.QAction(u'删除镜头', self, triggered = self.delcam))
        popMenu.addAction(QtWidgets.QAction(u'增加镜头序列', self, triggered = self.addCamNumFn))
        popMenu.addAction(QtWidgets.QAction(u'导入镜头数据', self, triggered = self.importInfoWinFn))
        popMenu.addAction(QtWidgets.QAction(u'导出镜头数据', self, triggered = self.exportTimeInfo))
        popMenu.addAction(QtWidgets.QAction(u'清除所有镜头', self, triggered = self.recam))
        popMenu.exec_(QtGui.QCursor.pos())
    def importInfoWinFn(self):
        self.imet = dialogWin.importCamInfoTextEditDialog(self)
        self.imet.readbutton.clicked.connect(self.importInfoFn)
        self.imet.exec_()
    def importInfoFn(self):
        if self.imet.textEdit.data:
            self._timeInfo = eval(self.imet.textEdit.data)
            self.addlistItem()
        self.imet.close()
    def exportTimeInfo(self):
        exportfilePath = QtWidgets.QFileDialog(self)
        exportfilePathName = exportfilePath.getSaveFileName(self,"导出镜头信息",self.savepath+'/Info',"Text Files(*.txt)") or None
        if exportfilePathName[0]:
            with open(exportfilePathName[0], "w") as f:
                f.write(str(self._timeInfo))
    def addcam(self, newCamName,numbox):
        if numbox:
            step = 1
            if self.num > int(newCamName)+1:
                step = -1
            numCam = ['cam' + "{:0>3d}".format(int(i)) for i in range(self.num, int(newCamName)+1,step)]
        else:
            newCamNum = 'cam' + "{:0>3d}".format(int(newCamName))
            numCam = [newCamNum]

        for i in numCam:
            if i not in self._timeInfo.keys():
                self._timeInfo[i] = [(0, 1)]
            else:
                mc.warning('Has Exiting Camera:%s'%i)
            self.addlistItem()
    def addcamDialogShow(self):
        try:
            maxCam = max(self._timeInfo.keys())
        except:
            maxCam = 'cam000'
        self.num = int(re.findall('\d+', maxCam)[0])+1
        newCamName = "{:0>3d}".format(int(self.num))
        self.addCamdialog = dialogWin.dialogWin(self.addcam, winName = '添加镜头号', hint = '添加连续镜头号', defaultName = newCamName,getparent = self)
        self.addCamdialog.exec_()
    def delcam(self):
        item = self.camlistWeight.currentItem()
        if item:
            a = self.camlistWeight.takeItem(self.camlistWeight.row(item))
            del self._timeInfo[a.text()]
    def recam(self):
        self.camlistWeight.clear()
        self.keyinfoWeight.clear()
        self._timeInfo.clear()
    def itemclick(self, item):
        self.cuttrnCam = str(item.text())
        info = self._timeInfo[str(self.cuttrnCam)]
        info.sort()
        self.settableWeightFn(info)
    def settableWeightFn(self,info):
        row = len(info)
        self.keyinfoWeight.clear()
        self.keyinfoWeight.setRowCount(row + 1)
        self.keyinfoWeight.setHorizontalHeaderLabels(['CurrentKey', 'HoldKey', ''])
        self.keyinfoWeight.setEditTriggers(QtCore.QAbstractItemModel.NoLayoutChangeHint)

        addBtn = QtWidgets.QPushButton('√')
        addBtn.clicked.connect(self.addBtnFn)
        self.keyinfoWeight.setCellWidget(row, 2, addBtn)
        for i in range(len(info)):
            delBtn = QtWidgets.QPushButton('X')
            delBtn.clicked.connect(self.delBtnFn)
            for j in range(2):
                tableItem = QtWidgets.QLineEdit(str(info[i][j]))
                tableItem.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
                tableItem.setValidator(QtGui.QIntValidator())
                tableItem.setFont(QtGui.QFont('Courier', 15))
                tableItem.textChanged.connect(self.saveInfo)
                self.keyinfoWeight.setCellWidget(i, j, tableItem)

            self.keyinfoWeight.setCellWidget(i, 2, delBtn)
    def saveInfo(self):
        row = self.keyinfoWeight.rowCount()
        info = [(self.keyinfoWeight.cellWidget(i, 0).text(), self.keyinfoWeight.cellWidget(i, 1).text())
                for i in range(row)
                if self.keyinfoWeight.cellWidget(i, 0) or self.keyinfoWeight.cellWidget(i, 1)]
        self._timeInfo[self.cuttrnCam] = info
    def addCamNumFn(self):
        inputNum,okPressed =  QtWidgets.QInputDialog.getInt(self,u'添加镜头序号','序号:',0)
        if okPressed:
            if self._timeInfo:
                newtimeInfo = {}
                camList = self._timeInfo.keys()
                camNumList = ['cam' + "{:0>3d}".format(int(re.findall('\d+', i)[0])+inputNum) for i in camList]
                camNumList.sort()
                camList.sort()
                for i in range(0,len(camNumList)):
                    newtimeInfo[camNumList[i]] = self._timeInfo.pop(camList[i])
                self._timeInfo = newtimeInfo
            else:
                mc.warning(u'工具中未定义拆分镜头！')
            allCam = self.addlistItem()
        return allCam
    def delBtnFn(self):
        button = self.sender()
        buttonpos = button.mapToGlobal(QtCore.QPoint(0, 0)) - self.keyinfoWeight.mapToGlobal(QtCore.QPoint(0, 0))
        item = self.keyinfoWeight.indexAt(buttonpos)
        self.keyinfoWeight.removeRow(item.row())
        del (self._timeInfo[self.cuttrnCam][item.row()])
    def addBtnFn(self):
        button = self.sender()
        buttonpos = button.mapToGlobal(QtCore.QPoint(0, 0)) - self.keyinfoWeight.mapToGlobal(QtCore.QPoint(0, 0))
        item = self.keyinfoWeight.indexAt(buttonpos)
        self.keyinfoWeight.insertRow(item.row())
        for j in range(2):
            tableItem = QtWidgets.QLineEdit()
            tableItem.setText(str(j))
            tableItem.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
            tableItem.setValidator(QtGui.QIntValidator())
            tableItem.setFont(QtGui.QFont('Courier', 15))
            tableItem.textChanged.connect(self.saveInfo)
            self.keyinfoWeight.setCellWidget(item.row(), j, tableItem)
        delBtn = QtWidgets.QPushButton('X')
        delBtn.clicked.connect(self.delBtnFn)
        self.keyinfoWeight.setCellWidget(item.row(), 2, delBtn)
        self._timeInfo[self.cuttrnCam].append((0,0))
    def addlistItem(self):
        if self._timeInfo :
            camList = self._timeInfo.keys()
            self.camlistWeight.clear()
            camList.sort()
            self.itemList = []
            for i in camList:
                item = QtWidgets.QListWidgetItem(i)
                item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                self.camlistWeight.addItem(item)
                self.itemList.append(item)
        else:
            self.camlistWeight.clear()
            camList = []
        return camList
    def itemChangeTextFn(self,item):
        camList = self._timeInfo.keys()
        if item.text() not in camList:
            self._timeInfo[item.text()] = self._timeInfo[self.cuttrnCam]
            self._timeInfo.pop(self.douCliceItemName)
        elif item.text() != self.douCliceItemName:
            mc.warning('Has Exiting Camera:%s' % item.text())
            item.setText(self.douCliceItemName)
    def itemDouClickedFn(self,item):
        self.douCliceItemName = item.text()
    def analysisFileCutTimeInfo(self):
        self._timeInfo = CutTime.CutTimeDef.getCameraKeys()[2]
        self.addlistItem()
    def getfilePath(self):
        item = QtWidgets.QFileDialog()
        self.savepath = item.getExistingDirectory() or ''
        self.importFileText.setText(str(self.savepath))
        self.createCutTimeInfo()
    def getfileName(self):
        sencename = mc.file(q =1,sn =1)
        fileName = sencename.split('/')[-1]
        self.prefix = fileName.split('_')[0]
        self.saveFileText.setText(self.prefix)
    def cutTimeInfo(self):
        if self.savepath:
            if self.prefix:
                if self._timeInfo:
                    self.prefix = self.saveFileText.text()
                    self.savepath = self.importFileText.text()
                    a = getTimeInfo.CutTimeTool(self.savepath,self.prefix,self._timeInfo,fps = self.fpsDict[self.fps])
                    a.getTimeInfo()
                else:
                    mc.warning(u'未获取镜头信息!!')
            else:
                mc.warning(u'未指定镜头场次!!')
        else:
            mc.warning(u'未指定文件拆分存储路径!!')
def show():
    if mc.window('CutTimeWin',q =1,ex =1):
        mc.deleteUI('CutTimeWin')
    win = CutTimeWin()
    win.show()
if __name__ == '__main__':
    try:
        win.close()
        win.deleteLater()
    except:
        pass
    win = CutTimeWin()
    win.show()
