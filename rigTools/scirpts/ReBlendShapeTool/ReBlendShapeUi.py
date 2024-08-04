"""
    PS:crate lights ctrl,you can select color and delete light.
    Bottom slide bar the joint size can be controlled.
    2020.7.14
    by:GGboomer
"""


import re
import blendShapeTest as bst
import GetNameSpace
import addBSprefix as bsp
from PySide2 import QtWidgets, QtCore
import maya.OpenMayaUI as omui
from shiboken2 import wrapInstance
import maya.cmds as mc


def getMayaMainWindow():
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(long(main_window_ptr), QtWidgets.QWidget)


class ReBlendShapeWin(QtWidgets.QDialog):
    """docstring for lightUi"""

    def __init__(self, parent=getMayaMainWindow()):
        super(ReBlendShapeWin, self).__init__(parent)
        self.DomakeList = list()
        self.setWindowTitle('ReBlendShapeWin')
        self.resize(250, 80)

        self.OldobjNameList = GetNameSpace.GetNameSpace()[0]
        self.Spacename = GetNameSpace.GetNameSpace()[1]

        self.bulidUI()
        if self.Spacename == '':
            self.nameSpace.setText('_____Get_Prefix______')

    def bulidUI(self):
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.nameSpace = QtWidgets.QLineEdit()
        self.nameSpace.textChanged.connect(self.getnameSpace)
        self.nameSpace.resize(100, 50)
        self.nameSpace.setText(self.Spacename)

        createBtn = QtWidgets.QPushButton('Do Make')
        createBtn.clicked.connect(self.DoMake)
        self.layout.addWidget(self.nameSpace, 1, 0)
        self.layout.addWidget(createBtn, 0, 2)

        self.Hlayout = QtWidgets.QHBoxLayout(self)
        self.AdBsprefix = QtWidgets.QLineEdit()
        self.AdBsprefix.resize(100, 50)

        self.AdBsprefix.setText('fr_,vfx_,prefix_')
        self.AdBSBtn = QtWidgets.QPushButton('Add BS ')
        self.AdBSBtn.clicked.connect(self.PrefixList)
        self.AdBSBtn.setEnabled(0)
        self.AdBsprefix.textChanged.connect(self.setbtn)
        self.Hlayout.addWidget(self.AdBsprefix, 0, 0)
        self.Hlayout.addWidget(self.AdBSBtn, 0, 0)
        self.layout.addLayout(self.Hlayout)

        self.nomathName = QtWidgets.QTreeWidget()
        self.nomathName.setHeaderHidden(1)

        self.matchTreeWeight = QtWidgets.QTreeWidget()

        header = self.matchTreeWeight.headerItem()
        header.setText(0, 'Match Prefix Name')

    def getnameSpace(self):
        self.Spacename = self.nameSpace.text()
        return self.Spacename

    def DoMake(self):
        reload(bst)
        reload(bsp)
        # print self.nameSpace.text()
        self.OldobjNameList = GetNameSpace.GetNameSpace()[0]
        if self.Spacename == '_____Get_Prefix______':
            self.OldobjNameList = [i.split(self.nameSpace.text())[-1] for i in
                                   self.OldobjNameList]
        else:
            pass
        if self.OldobjNameList != []:
            self.bst = bst.ReModTool(self.OldobjNameList, self.Spacename)
            if self.bst.nomathObjList:
                for i in self.bst.nomathObjList:
                    if i not in self.DomakeList:
                        self.DomakeList.append(i)
            self.refresh_tree_widget(self.nomathName, self.DomakeList, self.selectObj)
            self.nomathUI()
        return

    def nomathUI(self):
        if self.bst.nomathObjList:
            self.layout.addWidget(self.nomathName, 1)

    def refresh_tree_widget(self, treeweight, childlist, clickerF):
        treeweight.clear()
        items = list()
        for i in range(len(childlist)):
            item = self.createTreeWidgetItem(childlist[i])
            treeweight.itemClicked.connect(clickerF)
            treeweight.addTopLevelItem(item)
            items.append(item)
        return items

    def createTreeWidgetItem(self, name):
        item = QtWidgets.QTreeWidgetItem(name)
        return item

    def selectObj(self):
        item = self.nomathName.currentItem()
        name = item.text(0)
        try:
            mc.select(name, self.nameSpace.text() + name)
        except:
            pass
        finally:
            try:
                mc.select(name)
            except:
                mc.select(self.nameSpace.text() + name)

    def setbtn(self):
        self.AdBSBtn.setEnabled(1)
        # try:
        #     self.AdBSBtn.setEnabled(1)
        #     reload(bsp)
        #     if self.AdBSBtn.isEnabled():
        #
        #         # self.AdBsprefix.setText(selobj)
        #         self.match,self.matchObj = bsp.getMatchObj(prefix = self.AdBsprefix.text())
        #         items = self.refresh_tree_widget(self.matchTreeWeight, self.match,self.getMatchPrefix)
        #         self.addChilditem(items,self.matchObj)
        #     self.layout.addWidget(self.matchTreeWeight)
        # except:
        #     pass

    def getMatchPrefix(self, prefix, match):
        pass

    def addChilditem(self, items, children):
        if children:

            for i in range(len(items)):
                if children[i]:

                    child = QtWidgets.QTreeWidgetItem(children[i])
                    items[i].addChild(child)
                else:
                    continue

    def PrefixList(self):
        reload(bsp)
        reload(bst)
        delimiter = r'[,\s;|]+'
        prefixList = re.split(delimiter, self.AdBsprefix.text())
        obj = mc.ls(sl=1)

        self.prefixMatchList, nomatchObjList = bsp.checkPrefix(prefix=prefixList, obj=obj)
        if self.prefixMatchList:
            for i in self.prefixMatchList:
                mc.select(i[-1])

                selMod, selObjInfo = bst.ReModTool.getDeformInfo()
                if selObjInfo[0]['bsNodeList']:
                    for bsname in selObjInfo[0]['bsNodeList']:
                        bsInfo = bst.ReModTool.getBelndShapeInfo([bsname])[0]
                        for bsAttr in range(len(i) - 1):
                            aliasAttrlist = mc.aliasAttr(bsname, q=1) or []
                            newaliasAttr = int(re.findall('\d', aliasAttrlist[-1])[0]) + 1
                            if i[bsAttr] in bsInfo['bsAttr'].keys():
                                mc.blendShape(bsname, e=1, rm=1, t=(i[bsAttr],
                                                                    (aliasAttrlist.index(i[bsAttr])) / 2,
                                                                    i[bsAttr],
                                                                    1.0))
                                newaliasAttr = (aliasAttrlist.index(i[bsAttr])) / 2

                            mc.blendShape(n=bsname, e=1, t=(i[-1],
                                                            newaliasAttr,
                                                            i[bsAttr], 1.0))

                            try:
                                mc.setAttr(bsname + '.' + i[bsAttr], bsInfo['bsAttr'][i[bsAttr]]['value'])
                            except:
                                mc.setAttr(bsname + '.' + i[bsAttr], 1)
                            try:

                                mc.connectAttr(bsInfo['bsAttr'][i[bsAttr]]['Attrconnect'], bsname + '.' + i[bsAttr],
                                               f=1)
                                mc.setAttr(bsname + '.' + i[bsAttr], l=bsInfo['bsAttr'][i[bsAttr]]['lock'])
                            except:
                                pass
                else:
                    newbsNode = mc.blendShape(i[:-1], i[-1], n=i[-1] + '__ExtraBS__', en=1, foc=1)[0]
                    for i in i[:-1]:
                        mc.setAttr(newbsNode + '.' + i, 1)

    def bulidBShape(self):
        pass


if __name__ == '__main__':
    try:
        win.close()
        win.deleteLater()
    except:
        pass
    win = ReBlendShapeWin()
    win.show()
