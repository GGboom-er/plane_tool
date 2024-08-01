#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: getMeshCenterCurve.py
@date: 2024/3/29 19:26
@desc: 
"""
'CurveFromTubes'

import time
import maya.api.OpenMaya as Newom
from pymel.core import *
import itertools
from functools import partial
import maya.OpenMayaUI as apiUI

vers = '2017-2019'
if int(str(versions.current())[0:4]) == 2020:
    vers = 2020

try:
    from PySide2.QtCore import *
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *
    from PySide2 import __version__
    from shiboken2 import wrapInstance
except ImportError:
    from PySide.QtCore import *
    from PySide.QtGui import *
    from PySide import __version__
    from shiboken import wrapInstance


def getMayaWindow():
    ptr = apiUI.MQtUtil.mainWindow()
    if ptr is not None:
        return wrapInstance(long(ptr), QWidget)


class AboutWindow(QWidget):
    def __init__( self, parent=None ):
        super(AboutWindow, self).__init__(parent)
        hPanel = 30
        self.xAw = parent.sizeHint().width()
        self.yAw = parent.sizeHint().height()
        self.setWindowFlags(Qt.Window)
        self.setWindowTitle('About')
        self.mainMenuRect = parent.geometry()
        self.move(self.mainMenuRect.center() + QPoint((self.xAw) / 2, -(self.yAw / 2 + hPanel)))
        self.textBrowser = QTextBrowser(self)
        self.textBrowser.setGeometry(QRect(10, 10, self.xAw - 20, self.yAw - 20))
        self.textBrowser.setObjectName("textBrowser")
        self.textBrowser.setText(
            "Curves from tubes v1.0\n\nAuthor: \nAnton Jukov\ne-mail: \nJukov.CG@gmail.com \nArtStation:\nhttps://www.artstation.com/jukovcg")

        self.verticalLayoutAw = QVBoxLayout(self)

        self.verticalLayoutAw.addWidget(self.textBrowser)

    def sizeHint( self ):
        # return QSize(self.xAw, self.yAw)
        return QSize(300, 150)


class CurveFromTubes(QWidget):
    def __init__( self, parent=None ):
        super(CurveFromTubes, self).__init__(parent)
        # [star3, star5, border, star2]
        self.maps = [[8, 0, 0, 0], [0, 2, 0, 0], [4, 1, 0, 0], [4, 0, 1, 0], [0, 1, 1, 0], [0, 0, 1, 0], [4, 0, 0, 0],
                     [0, 0, 0, 0], [0, 0, 1, 4]]
        self.x = 200
        self.y = 250

        self.setWindowFlags(Qt.Window)
        self.setWindowTitle('CFT v1.0')
        self.maya_win_rect = parent.geometry()
        self.move(self.maya_win_rect.center() + QPoint(-100, -200))

        self.createCurves_btn = QPushButton(u'创建曲线', self)
        self.createCurves_btn.clicked.connect(partial(self.createCurvesFromTubes, 'default'))

        self.groupBox = QGroupBox(u'偏好:', self)

        self.preference_grd = QGridLayout(self.groupBox)

        self.thresholdCurvePoints = QLabel(self.groupBox)
        self.thresholdCurvePoints.setText(u"          CV阈值:")

        self.thresholdCurvePointsVal = QLineEdit(self.groupBox)
        self.thresholdCurvePointsVal.setText('0.01')

        self.reverseCurve_chb = QCheckBox(self.groupBox)
        self.reverseCurve_chb.setText(u'反转曲线:')
        self.reverseCurve_chb.setChecked(False)

        # ----------------------------------------

        self.createCurvesWithWire_btn = QPushButton(u'创建曲线 + 线框', self)
        self.createCurvesWithWire_btn.clicked.connect(partial(self.createCurvesFromTubes, 'wire'))

        self.wirePreference_grBox = QGroupBox(u'线框偏好:', self)

        self.wirePreference_grd = QGridLayout(self.wirePreference_grBox)

        self.distanceLabel = QLabel(self)
        self.distanceLabel.setText(u"      衰减距离:")

        self.distanceVal = QLineEdit(self)
        self.distanceVal.setText('50')

        # -------------------------------------------

        self.createCurvesWithJoints_btn = QPushButton(u'创建曲线 + 骨骼', self)
        self.createCurvesWithJoints_btn.clicked.connect(partial(self.createCurvesFromTubes, 'joints'))

        self.jointPreference_grBox = QGroupBox(u'骨骼偏好:', self)

        self.jointPreference_grd = QGridLayout(self.jointPreference_grBox)

        self.amountJoint_chb = QCheckBox(self.jointPreference_grBox)
        self.amountJoint_chb.setText(u'骨骼数量:')
        self.amountJoint_chb.setChecked(True)
        self.amountJoint_chb.clicked.connect(self.stepJoint_chanched)

        self.stepJoint_chb = QCheckBox(self.jointPreference_grBox)
        self.stepJoint_chb.setText(u'骨骼步数:')
        self.stepJoint_chb.clicked.connect(self.amountJoint_chanched)

        self.amountJoint_val = QLineEdit(self.jointPreference_grBox)
        self.amountJoint_val.setText('10')

        self.stepJoint_val = QLineEdit(self.jointPreference_grBox)
        self.stepJoint_val.setText('5')

        self.jointOrient_lbl = QLabel(self.jointPreference_grBox)
        self.jointOrient_lbl.setText(u"骨骼朝向:")

        self.jointOrient_cBox = QComboBox(self.jointPreference_grBox)
        self.jointOrient_cBox.addItem('zyx')
        self.jointOrient_cBox.addItem('xyz')
        self.jointOrient_cBox.addItem('yzx')
        self.jointOrient_cBox.addItem('zxy')
        self.jointOrient_cBox.addItem('yxz')
        self.jointOrient_cBox.addItem('xzy')
        self.jointOrient_cBox.addItem('none')

        self.secondaryAxisOrient_lbl = QLabel(self.jointPreference_grBox)
        self.secondaryAxisOrient_lbl.setText(u"次级坐标朝向:")

        self.secondaryAxisOrient_cBox = QComboBox(self.jointPreference_grBox)
        self.secondaryAxisOrient_cBox.addItem(u'Y上')
        self.secondaryAxisOrient_cBox.addItem(u'X上')
        self.secondaryAxisOrient_cBox.addItem(u'X下')
        self.secondaryAxisOrient_cBox.addItem(u'Y下')
        self.secondaryAxisOrient_cBox.addItem(u'Z上')
        self.secondaryAxisOrient_cBox.addItem(u'Z下')
        self.secondaryAxisOrient_cBox.addItem(u'无')

        # -----------------------------------------------------

        self.deleteTrash_btn = QPushButton(u'删除垃圾', self)
        self.deleteTrash_btn.clicked.connect(self.deleteTrash)

        self.aboutScript_btn = QPushButton(u'关于', self)
        self.aboutScript_btn.clicked.connect(self.aboutScript)

        self.horizontalLayout = QHBoxLayout(self)
        self.verticalLayout = QVBoxLayout(self)

        self.verticalLayout.addWidget(self.createCurves_btn)
        self.verticalLayout.addWidget(self.groupBox)
        self.preference_grd.addWidget(self.thresholdCurvePoints, 0, 0)
        self.preference_grd.addWidget(self.thresholdCurvePointsVal, 0, 1)
        self.preference_grd.addWidget(self.reverseCurve_chb, 1, 0)

        self.verticalLayout.addWidget(self.createCurvesWithWire_btn)
        self.verticalLayout.addWidget(self.wirePreference_grBox)
        self.wirePreference_grd.addWidget(self.distanceLabel, 0, 0)
        self.wirePreference_grd.addWidget(self.distanceVal, 0, 1)

        self.verticalLayout.addWidget(self.createCurvesWithJoints_btn)
        self.verticalLayout.addWidget(self.jointPreference_grBox)
        self.jointPreference_grd.addWidget(self.amountJoint_chb, 0, 0)
        self.jointPreference_grd.addWidget(self.stepJoint_chb, 1, 0)
        self.jointPreference_grd.addWidget(self.amountJoint_val, 0, 1)
        self.jointPreference_grd.addWidget(self.stepJoint_val, 1, 1)
        self.jointPreference_grd.addWidget(self.jointOrient_lbl, 2, 0)
        self.jointPreference_grd.addWidget(self.jointOrient_cBox, 2, 1)
        self.jointPreference_grd.addWidget(self.secondaryAxisOrient_lbl, 3, 0)
        self.jointPreference_grd.addWidget(self.secondaryAxisOrient_cBox, 3, 1)

        self.verticalLayout.addWidget(self.deleteTrash_btn)
        self.verticalLayout.addWidget(self.aboutScript_btn)
        self.horizontalLayout.addLayout(self.verticalLayout)

    def sizeHint( self ):
        return QSize(self.x, self.y)

    def stepJoint_chanched( self ):
        self.stepJoint_chb.setChecked(False)
        self.amountJoint_chb.setChecked(True)

    def amountJoint_chanched( self ):
        self.amountJoint_chb.setChecked(False)
        self.stepJoint_chb.setChecked(True)

    def closeEvent( self, close ):
        try:
            self.aboutMenu.close()
        except:
            pass

    def aboutScript( self ):
        try:
            self.aboutMenu.close()
        except:
            pass
        self.aboutMenu = AboutWindow(self)
        self.aboutMenu.show()

    def deleteTrash( self ):
        deleteReady = 0
        try:
            if self.forDelete or len(self.forDelete) != 0:
                deleteReady = 1
        except:
            pass
        if deleteReady == 1:
            for d in self.forDelete:
                try:
                    delete(d)
                except:
                    continue
        else:
            print
            ' Object to delete is not found!'

    def createCurvesFromTubes( self, mode='default' ):
        t = time.time()
        print
        '\n\n'
        # Select tubes
        undoInfo(openChunk=1)
        try:
            self.threshold = float(self.thresholdCurvePointsVal.text())
        except:
            print
            'Incorrect input! Deafult values are used.'
            self.threshold = 0.01
        self.sel = ls(sl=1, o=1, tr=1, s=1)
        self.geometryFromSelect = []
        for self.s in self.sel:
            if self.s.type() == 'transform':
                if self.s.getShape():
                    if self.s.getShape().type() == 'mesh':
                        self.geometryFromSelect.append(self.s)
                        if len(self.s.getChildren()) > 1:
                            self.MeshInGroup(self.s, self.geometryFromSelect)
                    elif self.s.getShape().type() == 'nurbsCurve':
                        self.MeshInGroup(self.s, self.geometryFromSelect)
                elif self.s.getShape() == None:
                    self.MeshInGroup(self.s, self.geometryFromSelect)
            elif self.s.type() == 'mesh':
                self.geometryFromSelect.append(self.s)
        self.geometryFromSelect = list(set(self.geometryFromSelect))

        # Create group for curves
        gr = group(empty=1, name='curvesFromTubes_grp')
        if mode == 'wire':
            wireGr = group(empty=1, name='wireBase_grp')
        if mode == 'joints':
            jointsGr = group(empty=1, name='joints_grp')
        self.forDelete = []
        badTopology = []

        # Start workikg with each tube
        for g in self.geometryFromSelect:
            # Get info about tube (name, path, obj)
            dagPath = g.__apimdagpath__()
            obj = dagPath.node()
            fullName = dagPath.fullPathName()
            name = fullName.split('|')[-1]

            # Duplicate tube, rename, unparent
            dupl = duplicate(g, name=name + '_tube')[0]
            if dupl not in self.forDelete:
                self.forDelete.append(dupl)
            dupl.setParent(None)

            # Separate combine tubes
            shellsNum = polyEvaluate(g, shell=1)
            if shellsNum > 1 and mode == 'default':
                try:
                    shellsGlobal = polySeparate(dupl, ch=0)
                except:
                    if dupl not in self.forDelete:
                        self.forDelete.append(dupl)
                    continue
                x = 1
                if len(shellsGlobal) < 10:
                    for shGl in shellsGlobal:
                        shGl.rename(name + '_000' + str(x) + '_tube')
                        parent(shGl, w=1)
                        x += 1
                    if dupl not in self.forDelete:
                        self.forDelete.append(dupl)
                elif len(shellsGlobal) >= 10 and len(shellsGlobal) < 100:
                    for shGl in shellsGlobal:
                        shGl.rename(name + '_00' + str(x) + '_tube')
                        parent(shGl, w=1)
                        x += 1
                    if dupl not in self.forDelete:
                        self.forDelete.append(dupl)
                elif len(shellsGlobal) >= 100:
                    for shGl in shellsGlobal:
                        shGl.rename(name + '_0' + str(x) + '_tube')
                        parent(shGl, w=1)
                        x += 1
                    if dupl not in self.forDelete:
                        self.forDelete.append(dupl)
                elif len(shellsGlobal) >= 1000:
                    for shGl in shellsGlobal:
                        shGl.rename(name + '_' + str(x) + '_tube')
                        parent(shGl, w=1)
                        x += 1
                    if dupl not in self.forDelete:
                        self.forDelete.append(dupl)
            elif shellsNum == 1:
                shellsGlobal = [dupl, ]
            elif shellsNum > 1 and mode != 'default':
                shellsGlobal = []
            omShellsGlobal = Newom.MSelectionList()
            for shGl in shellsGlobal:
                omShellsGlobal.add(shGl.fullPath())
            omShellsGlobalIt = Newom.MItSelectionList(omShellsGlobal)
            while not omShellsGlobalIt.isDone():
                plane = 0
                self.shGlDagPath = omShellsGlobalIt.getDagPath()
                self.PyShGlObj = PyNode(self.shGlDagPath.fullPathName())
                if self.checkMesh(self.shGlDagPath) == 1:
                    if g not in badTopology:
                        badTopology.append(g)
                    self.forDelete.append(self.PyShGlObj)
                else:
                    # Find stars and borders
                    self.star5 = self.getVertexStars(self.shGlDagPath, 5)
                    self.star3 = self.getVertexStars(self.shGlDagPath, 3)
                    self.star2 = self.getVertexStars(self.shGlDagPath, 2, 'Border')
                    self.border = self.getBorderEdges(self.shGlDagPath)
                    if len(self.border) == 0:
                        borderKey = 0
                    else:
                        borderKey = 1
                    shells = []
                    self.loopsForCut = []
                    if [len(self.star3), len(self.star5), borderKey, len(self.star2)] in self.maps:
                        if [len(self.star3), len(self.star5), borderKey, len(self.star2)] == [0, 0, 0, 0]:
                            self.vTorus = 0
                            self.edgesTorus = self.ComponentInfo(self.vTorus, 'vtx', 'toEdge', self.shGlDagPath)
                            self.loopsTorus = []
                            for self.edgeTorus in self.edgesTorus:
                                self.loopTorus = []
                                self.loopTorusVtx = []
                                self.toEdgeLoop(self.edgeTorus, self.loopTorus, self.loopTorusVtx, self.shGlDagPath)
                                self.loopsTorus.append(sorted(self.loopTorus))
                            self.loopsTorus = self.DeleteReplayFromList(self.loopsTorus)
                            if len(self.loopsTorus) == 2:
                                self.L1 = round(
                                    self.ComponentInfo(self.loopsTorus[0], 'edge', 'length', self.shGlDagPath), 10)
                                self.L2 = round(
                                    self.ComponentInfo(self.loopsTorus[1], 'edge', 'length', self.shGlDagPath), 10)
                                if self.L1 == min(self.L1, self.L2):
                                    polySplitEdge(map(lambda x: self.PyShGlObj.e[x], self.loopsTorus[0]))
                                else:
                                    polySplitEdge(map(lambda x: self.PyShGlObj.e[x], self.loopsTorus[1]))
                        elif [len(self.star3), len(self.star5), borderKey, len(self.star2)] == [0, 0, 1, 4]:
                            plane = 1
                        if self.star5:
                            for self.st5 in self.star5:
                                self.loopVtx = self.ComponentInfo(self.st5, 'vtx', 'toVtx', self.shGlDagPath)
                                self.loopEdge = self.ComponentInfo(self.loopVtx, 'vtx', 'toContainedEdges',
                                                                   self.shGlDagPath)
                                self.loopsForCut.append(self.loopEdge)
                        if self.star3:
                            self.pathes = []
                            for self.st3 in self.star3:
                                self.edgesSt3 = self.ComponentInfo(self.st3, 'vtx', 'toEdge', self.shGlDagPath)
                                for self.edSt3 in self.edgesSt3:
                                    self.loop = []
                                    self.loopVtx = []
                                    self.toEdgeLoop(self.edSt3, self.loop, self.loopVtx, self.shGlDagPath)
                                    if filter(lambda x: x in self.star3 and x != self.st3, self.loopVtx):
                                        self.pathes.append(sorted(self.loop))
                            self.pathes = self.DeleteReplayFromList(self.pathes)
                            lengths = []
                            dictLength = []
                            for self.path in self.pathes:
                                length = round(self.ComponentInfo(self.path, 'edge', 'length', self.shGlDagPath), 10)
                                dL = str(length) + ':'
                                for p in self.path:
                                    dL = dL + str(p) + '|'
                                lengths.append(length)
                                dictLength.append(dL)
                            self.capsLoops = []
                            lengths = sorted(lengths)[:len(self.star3)]
                            self.capsLoops = filter(lambda x: round(float(x.split(':')[0]), 10) in lengths, dictLength)
                            self.capsLoops = map(lambda x: x.split(':')[-1].split('|')[:-1], self.capsLoops)
                            self.capsLoops = map(lambda y: map(lambda x: int(x), y), self.capsLoops)
                            self.loopsForCut.append(self.capsLoops)
                        tubes = []
                        if self.loopsForCut:
                            self.loopsForCutPy = map(lambda x: self.PyShGlObj.e[x],
                                                     list(itertools.chain(*self.loopsForCut)))
                            polySplitEdge(self.loopsForCutPy)
                            nameTube = self.PyShGlObj.name().split('|')[-1] + '_shell'
                            tubeShells = []
                            try:
                                tubeShells = polySeparate(self.PyShGlObj, ch=0)
                            except:
                                if g not in badTopology:
                                    badTopology.append(g)
                                if self.PyShGlObj not in self.forDelete:
                                    self.forDelete.append(self.PyShGlObj)
                            if tubeShells:
                                for tSh in tubeShells:
                                    parent(tSh, w=1)
                                    tShSelList = Newom.MSelectionList()
                                    tShSelList.add(tSh.fullPath())
                                    self.tShDagPath = tShSelList.getDagPath(0)
                                    if self.getVertexStars(self.tShDagPath, 5):
                                        if tSh not in self.forDelete:
                                            self.forDelete.append(tSh)
                                        continue
                                    elif self.getVertexStars(self.tShDagPath, 3, 'Border'):
                                        if tSh not in self.forDelete:
                                            self.forDelete.append(tSh)
                                        continue
                                    else:
                                        tSh.rename(nameTube)
                                        tubes.append(tSh)
                                        continue
                                if self.PyShGlObj not in self.forDelete:
                                    self.forDelete.append(self.PyShGlObj)
                        else:
                            tubes.append(self.PyShGlObj)
                        if tubes:
                            for tube in tubes:
                                tubeSelList = Newom.MSelectionList()
                                tubeSelList.add(tube.fullPath())
                                self.tubeDagPath = tubeSelList.getDagPath(0)
                                try:
                                    if plane == 1:
                                        self.planeStartVtx = self.star2[0]
                                        self.planeStartEdges = self.ComponentInfo(self.planeStartVtx, 'vtx', 'toEdge',
                                                                                  self.tubeDagPath)
                                        if len(self.planeStartEdges) == 2:
                                            self.start1 = []
                                            self.startVtx1 = []
                                            self.toEdgeLoop(self.planeStartEdges[0], self.start1, self.startVtx1,
                                                            self.tubeDagPath)
                                            self.start2 = []
                                            self.startVtx2 = []
                                            self.toEdgeLoop(self.planeStartEdges[1], self.start2, self.startVtx2,
                                                            self.tubeDagPath)
                                            self.planeL1 = round(
                                                self.ComponentInfo(self.start1, 'edge', 'length', self.tubeDagPath), 10)
                                            self.planeL2 = round(
                                                self.ComponentInfo(self.start2, 'edge', 'length', self.tubeDagPath), 10)
                                            if self.planeL1 == min(self.planeL1, self.planeL2):
                                                self.start = self.start1
                                                self.startVtx = self.startVtx1
                                            else:
                                                self.start = self.start2
                                                self.startVtx = self.startVtx2
                                            self.planeEndVtx = filter(lambda x: x not in self.startVtx, self.star2)[0]
                                            self.planeEndEdges = self.ComponentInfo(self.planeEndVtx, 'vtx', 'toEdge',
                                                                                    self.tubeDagPath)
                                            if len(self.planeEndEdges) == 2:
                                                self.end1 = []
                                                self.endVtx1 = []
                                                self.toEdgeLoop(self.planeEndEdges[0], self.end1, self.endVtx1,
                                                                self.tubeDagPath)
                                                self.end2 = []
                                                self.endVtx2 = []
                                                self.toEdgeLoop(self.planeEndEdges[1], self.end2, self.endVtx2,
                                                                self.tubeDagPath)
                                                self.planeEndL1 = round(
                                                    self.ComponentInfo(self.end1, 'edge', 'length', self.tubeDagPath),
                                                    10)
                                                self.planeEndL2 = round(
                                                    self.ComponentInfo(self.end2, 'edge', 'length', self.tubeDagPath),
                                                    10)
                                                if self.planeEndL1 == min(self.planeEndL1, self.planeEndL2):
                                                    self.end = self.end1
                                                    self.endVtx = self.endVtx1
                                                else:
                                                    self.end = self.end2
                                                    self.endVtx = self.endVtx2
                                    else:
                                        self.borderEdges = self.getBorderEdges(self.tubeDagPath)
                                        self.start = []
                                        self.startVtx = []
                                        self.toEdgeLoop(self.borderEdges[0], self.start, self.startVtx,
                                                        self.tubeDagPath)
                                        self.end = filter(lambda i: i not in self.start, self.borderEdges)
                                    self.rings = [self.start, ]
                                    self.face_done = []
                                    self.RingByRing(self.start, self.end, self.rings, self.face_done, self.tubeDagPath)
                                    centers = []
                                    for self.ring in self.rings:
                                        center = self.CentralPosition(self.ring, 'edge', self.tubeDagPath)
                                        centers.append(center[:3])
                                    nameCurv = tube.name().split('|')[-1].split('_tube')[0] + '_crv'
                                    self.forDelete.append(tube)
                                    if len(centers) > 3:
                                        curv = curve(p=centers, ws=1, n=nameCurv)
                                    else:
                                        curv = curve(p=centers, ws=1, n=nameCurv, d=1)
                                    if self.reverseCurve_chb.isChecked():
                                        curv.reverse()
                                    curveSelList = Newom.MSelectionList()
                                    curveSelList.add(curv.fullPath())
                                    curveDagPath = curveSelList.getDagPath(0)
                                    curveFn = Newom.MFnNurbsCurve(curveDagPath)
                                    badPoints = []
                                    for prevPoint in xrange(curveFn.numCVs - 1):
                                        prevPointPos = curveFn.cvPosition(prevPoint, Newom.MSpace.kWorld)
                                        currPointPos = curveFn.cvPosition(prevPoint + 1, Newom.MSpace.kWorld)
                                        vect = Newom.MVector(currPointPos - prevPointPos)
                                        if vect.length() < self.threshold:
                                            badPoints.append(prevPoint + 1)
                                    badPoints = map(lambda x: curv.cv[x], badPoints)
                                    delete(badPoints)
                                    if curveFn.length() > self.threshold:
                                        curv.setRotatePivot(curv.getCV(0, space='world'))
                                        try:
                                            if mode == 'wire':
                                                curv.rename(nameCurv + str(int(time.time())))
                                                try:
                                                    self.dropoffDistanceWire = float(self.distanceVal.text())
                                                except:
                                                    print
                                                    'Incorrect input! Deafult values are used.'
                                                    self.dropoffDistanceWire = 50
                                                wireForCurve = wire(g, w=curv)[0]
                                                wire(wireForCurve, edit=1, dds=(0, self.dropoffDistanceWire))
                                                wireBase = listConnections(wireForCurve.attr('baseWire[0]'))[0]
                                                parent(wireBase, wireGr)
                                                curv.rename(nameCurv)
                                                wireBase.rename(nameCurv + 'BaseWire')
                                        except:
                                            pass
                                        try:
                                            if mode == 'joints':
                                                numEP = curv.numEPs()
                                                self.duplCurv = duplicate(curv, n=nameCurv + '_dupl')[0]
                                                if self.amountJoint_chb.isChecked():
                                                    try:
                                                        numberJoint = int(self.amountJoint_val.text())
                                                    except:
                                                        print
                                                        'Incorrect input! Deafult values are used.'
                                                        numberJoint = 15
                                                elif self.stepJoint_chb.isChecked():
                                                    lengthCurv = self.duplCurv.length()
                                                    try:
                                                        step = float(self.stepJoint_val.text())
                                                    except:
                                                        print
                                                        'Incorrect input! Deafult values are used.'
                                                        step = 3
                                                    if lengthCurv <= step:
                                                        numberJoint = 1
                                                    else:
                                                        numberJoint = int(lengthCurv / step)
                                                k = float(numEP) / float(numberJoint)
                                                if k < 2:
                                                    k = 1
                                                else:
                                                    k = int(k)
                                                rebuildCurve(self.duplCurv, ch=False, rpo=True, rt=False, end=True,
                                                             kr=False, kcp=False, kep=True, kt=True, s=numberJoint * k,
                                                             d=3, tol=0.01)
                                                select(cl=1)
                                                joints = []
                                                j = 1
                                                for i in range(0, numberJoint * k + 1, k):
                                                    point = pointPosition(self.duplCurv.ep[i], w=1)
                                                    jnt = joint(p=point, name=name + '_' + str(j) + '_jnt')
                                                    joints.append(jnt)
                                                    j += 1
                                                parent(joints[0], jointsGr)
                                                orientJ = self.jointOrient_cBox.currentText()
                                                secAxis = self.secondaryAxisOrient_cBox.currentText()
                                                joint(joints[0], e=1, oj=orientJ, secondaryAxisOrient=secAxis, ch=1,
                                                      zso=1)
                                                joint(joints[-1], e=1, oj='none', ch=1, zso=1)
                                                self.forDelete.append(self.duplCurv)
                                        except:
                                            pass
                                        parent(curv, gr)
                                    else:
                                        if g not in badTopology:
                                            badTopology.append(g)
                                        self.forDelete.append(curv)
                                except:
                                    if g not in badTopology:
                                        badTopology.append(g)
                                    self.forDelete.append(tube)
                        else:
                            if g not in badTopology:
                                badTopology.append(g)
                            self.forDelete.append(self.PyShGlObj)
                    else:
                        if g not in badTopology:
                            badTopology.append(g)
                        if self.PyShGlObj not in self.forDelete:
                            self.forDelete.append(self.PyShGlObj)
                omShellsGlobalIt.next()
        delete(self.forDelete)
        if badTopology:
            print
            '      Contains bad topology for script:'
            for bT in badTopology:
                print
                bT
        if gr.getChildren():
            select(gr)
        else:
            print
            'Proper geometry not found!'
            delete(gr)
            if mode == 'wire':
                delete(wireGr)
            elif mode == 'joints':
                delete(jointsGr)
        self.forDelete = []
        undoInfo(closeChunk=1)
        print
        'Script runtime: ' + str(time.time() - t)

    def toEdgeLoop( self, index, result, vtxLoop, obj ):
        indexError = 'Error: Incorrect input ID component!!!'
        objError = 'Error: Incorrect input obj!!!'
        objGood = 0
        try:
            try:
                index = list(set(index))
            except TypeError:
                index = [index, ]
        except:
            return indexError

        try:
            if obj.apiType() == 110 or obj.apiType() == 296:
                objGood = 1
        except:
            return objError
        if objGood == 1:
            for self.i in index:
                if self.i not in result:
                    result.append(self.i)
                    self.faces = self.ComponentInfo(self.i, 'edge', 'toFace', obj)
                    edges = self.ComponentInfo(self.faces, 'face', 'toEdge', obj)
                    self.vtx = self.ComponentInfo(self.i, 'edge', 'toVtx', obj)
                    for self.v in self.vtx:
                        if self.v not in vtxLoop:
                            vtxLoop.append(self.v)
                            self.edgesVtx = filter(lambda x: x not in edges,
                                                   self.ComponentInfo(self.v, 'vtx', 'toEdge', obj))
                            if len(self.edgesVtx) == 1:
                                self.toEdgeLoop(self.edgesVtx[0], result, vtxLoop, obj)

    def RingByRing( self, start, end, rings, face_done, obj ):
        startVtx = self.ComponentInfo(start, 'edge', 'toVtx', obj)
        startFaceAll = self.ComponentInfo(start, 'edge', 'toFace', obj)
        self.startFace = filter(lambda i: i not in face_done, startFaceAll)
        vtx = self.ComponentInfo(self.startFace, 'face', 'toVtx', obj)
        self.next_loop_vtx = filter(lambda i: i not in startVtx, vtx)
        self.next_loop = self.ComponentInfo(self.next_loop_vtx, 'vtx', 'toContainedEdges', obj)
        rings.append(self.next_loop)
        face_done.extend(startFaceAll)
        if sorted(self.next_loop) != sorted(end):
            self.RingByRing(self.next_loop, end, rings, face_done, obj)

    def CentralPosition( self, index, componentType, obj ):
        # componentType - vtx, face, edge, uv
        meshFn = Newom.MFnMesh(obj)
        verts = self.ComponentInfo(index, componentType, 'toVtx', obj)
        n = len(verts)
        vertsPos = []
        for v in verts:
            vertsPos.append(meshFn.getPoint(v, Newom.MSpace.kWorld))
        return map(lambda x: x / n, map(sum, zip(*vertsPos)))

    def DeleteReplayFromList( self, lst ):
        newList = []
        for l in lst:
            if l not in newList:
                newList.append(l)
        return newList

    def ComponentInfo( self, index, componentType, command, obj ):
        # comand - toEdge, toFace, toVtx, toContainedEdges, toEdgePerimeter, length
        # componentType - vtx, face, edge, uv
        indexError = 'Error: Incorrect input ID component!!!'
        objError = 'Error: Incorrect input obj!!!'
        objGood = 0
        try:
            try:
                index = list(set(index))
            except TypeError:
                index = [index, ]
        except:
            return indexError

        try:
            if obj.apiType() == 110 or obj.apiType() == 296:
                objGood = 1
        except:
            return objError
        if objGood == 1:
            result = []
            items = []
            meshFn = Newom.MFnMesh(obj)
            if componentType == 'face':
                faceIt = Newom.MItMeshPolygon(obj)
                if command == 'toEdgePerimeter':
                    self.edges = self.ComponentInfo(index, 'face', 'toEdge', obj)
                    edgeIt = Newom.MItMeshEdge(obj)
                    for self.edge in self.edges:
                        face = self.ComponentInfo(self.edge, 'edge', 'toFace', obj)
                        for f in face:
                            if f not in index:
                                items.append(self.edge)
                elif command == 'toFace':
                    for i in index:
                        faceIt.setIndex(i)
                        items.extend(faceIt.getConnectedFaces())
                elif command == 'toEdge':
                    for i in index:
                        faceIt.setIndex(i)
                        items.extend(faceIt.getEdges())
                elif command == 'toVtx':
                    for i in index:
                        faceIt.setIndex(i)
                        items.extend(faceIt.getVertices())

            elif componentType == 'edge':
                edgeIt = Newom.MItMeshEdge(obj)
                if command == 'toFace':
                    for i in index:
                        edgeIt.setIndex(i)
                        items.extend(edgeIt.getConnectedFaces())
                elif command == 'length':
                    length = 0
                    for i in index:
                        edgeIt.setIndex(i)
                        length += edgeIt.length(Newom.MSpace.kWorld)
                    return length
                elif command == 'toEdge':
                    for i in index:
                        edgeIt.setIndex(i)
                        items.extend(edgeIt.getConnectedEdges())
                elif command == 'toVtx':
                    for i in index:
                        edgeIt.setIndex(i)
                        items.append(edgeIt.vertexId(0))
                        items.append(edgeIt.vertexId(1))
                elif command == 'toEdgePerimeter':
                    self.faces = self.ComponentInfo(index, 'edge', 'toFace', obj)
                    items.extend(self.ComponentInfo(self.faces, 'face', 'toEdgePerimeter', obj))
            elif componentType == 'vtx':
                vtxIt = Newom.MItMeshVertex(obj)
                for i in index:
                    vtxIt.setIndex(i)
                if command == 'toContainedEdges':
                    for i in index:
                        vtxIt.setIndex(i)
                        self.edges = vtxIt.getConnectedEdges()
                        edgesIt = Newom.MItMeshEdge(obj)
                        for self.edge in self.edges:
                            edgesIt.setIndex(self.edge)
                            edgeVtx0 = edgesIt.vertexId(0)
                            edgeVtx1 = edgesIt.vertexId(1)
                            if edgeVtx0 in index and edgeVtx1 in index:
                                items.append(self.edge)
                elif command == 'toFace':
                    for i in index:
                        vtxIt.setIndex(i)
                        items.extend(vtxIt.getConnectedFaces())
                elif command == 'toEdge':
                    for i in index:
                        vtxIt.setIndex(i)
                        items.extend(vtxIt.getConnectedEdges())
                elif command == 'toVtx':
                    for i in index:
                        vtxIt.setIndex(i)
                        items.extend(vtxIt.getConnectedVertices())
            items = list(set(items))
            result.extend(items)
            return result

    def getBorderEdges( self, obj ):
        self.edges = Newom.MItMeshEdge(obj)
        index = []
        while not self.edges.isDone():
            if self.edges.onBoundary():
                index.append(self.edges.index())
            self.edges.next()
        return index

    def getVertexStars( self, obj, star, mode='notBorder' ):
        vtx = Newom.MItMeshVertex(obj)
        index = []
        while not vtx.isDone():
            n = vtx.numConnectedEdges()
            if star == 5:
                if n > 4:
                    if mode == 'Border':
                        index.append(vtx.index())
                    elif mode == 'notBorder':
                        if not vtx.onBoundary():
                            index.append(vtx.index())
            elif star == 3:
                if n == 3:
                    if not vtx.onBoundary():
                        index.append(vtx.index())
                if mode == 'Border':
                    if n == 2:
                        index.append(vtx.index())
            elif star == 2:
                if n == 2:
                    if mode == 'Border':
                        if vtx.onBoundary():
                            index.append(vtx.index())
                    else:
                        if not vtx.onBoundary():
                            index.append(vtx.index())
            vtx.next()
        return index

    def checkMesh( self, obj ):
        faceIt = Newom.MItMeshPolygon(obj)
        while not faceIt.isDone():
            if faceIt.polygonVertexCount() > 4:
                return 1
            elif faceIt.isLamina():
                return 1
            else:
                if vers == 2020:
                    faceIt.next()
                else:
                    faceIt.next(None)
        vtxIt = Newom.MItMeshVertex(obj)
        while not vtxIt.isDone():
            if vtxIt.numConnectedEdges() == 0 or vtxIt.numConnectedEdges() == 1:
                return 1
            vtxIt.next()
        edgeIt = Newom.MItMeshEdge(obj)
        while not edgeIt.isDone():
            if edgeIt.numConnectedFaces() > 2:
                return 1
            edgeIt.next()
        return 0

    def MeshInGroup( self, grp, result, vis=0 ):
        name = grp.longName()
        nameSplit = name.split('|')
        n = len(nameSplit)
        mesh = filter(lambda i: i.intermediateObject.get() == 0, ls(typ='mesh'))
        if mesh and vis == 1:
            mesh = ls(mesh, v=1, fl=1)
        for m in mesh:
            path = m.longName()
            pathSplit = path.split('|')
            if len(pathSplit) > n:
                j = 0
                for i in range(n):
                    if nameSplit[i] == pathSplit[i]:
                        j += 1
                if j == n:
                    result.append(m.getParent())


try:
    CFT.close()
except:
    pass

maya = getMayaWindow()
CFT = CurveFromTubes(maya)
CFT.show()