#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CurveFromTubes - Maya 2025 compatible refactor
作者: 参考原作者 + 重构: GGboom (适配 Maya2025)
目标: 支持 Maya2025 (Python3, PySide6/shiboken6, API 2.0 迭代器行为)
说明: 保持原逻辑，修复 Python2 -> Python3, PySide2 -> PySide6, Maya API next() 等问题
"""

import time
import traceback
import itertools
from functools import partial
# Maya/ PyMel / OpenMaya
import maya.api.OpenMaya as Newom   # Maya Python API 2.0 (OpenMaya) - API 2.0
from pymel.core import *            # PyMel（注意: 在大规模工程可替换为 maya.cmds + OpenMaya）
import maya.OpenMayaUI as apiUI

# -------------------------
# 版本检测（Maya Year integer）
# -------------------------
try:
    vers = int(str(versions.current())[0:4])
except Exception:
    # 保守回退到 2025（如果无法读取版本），可按需调整
    vers = 2025

# -------------------------
# PySide / shiboken 兼容导入 (PySide6/shiboken6 优先，回退到 PySide2/shiboken2)
# -------------------------
PYSIDE_VERSION = None
try:
    # Maya 2025 -> PySide6 / shiboken6
    from PySide6.QtCore import *      # noqa: F401,F403
    from PySide6.QtGui import *       # noqa: F401,F403
    from PySide6.QtWidgets import *   # noqa: F401,F403
    from shiboken6 import wrapInstance
    PYSIDE_VERSION = 6
except Exception:
    try:
        # 兼容旧版本 Maya（PySide2/shiboken2）
        from PySide2.QtCore import *    # noqa: F401,F403
        from PySide2.QtGui import *     # noqa: F401,F403
        from PySide2.QtWidgets import * # noqa: F401,F403
        from shiboken2 import wrapInstance
        PYSIDE_VERSION = 2
    except Exception as e:
        # 无可用 PySide，抛错（Maya 环境通常会包含其一）
        raise ImportError("无法导入 PySide6 或 PySide2: %s" % str(e))

# -------------------------
# getMayaWindow - 获取 Maya 主窗口 (用于 wrapInstance)
# -------------------------
def getMayaWindow():
    """ 返回 Maya 主窗口的 QWidget (shiboken wrapInstance)
        Get Maya main window as QWidget (wrapInstance)
    """
    try:
        ptr = apiUI.MQtUtil.mainWindow()
        if ptr is not None:
            # 在 Python3 中用 int() 转换指针；在旧 Python2 里 int() 可兼容 long
            return wrapInstance(int(ptr), QWidget)
    except Exception:
        traceback.print_exc()
    return None

# -------------------------
# 主 UI 类 (AboutWindow + CurveFromTubes)
# -------------------------
class AboutWindow(QWidget):
    def __init__(self, parent=None):
        super(AboutWindow, self).__init__(parent)
        hPanel = 30
        # sizeHint 可能依赖 parent
        try:
            self.xAw = parent.sizeHint().width()
            self.yAw = parent.sizeHint().height()
        except Exception:
            self.xAw = 300
            self.yAw = 150
        self.setWindowFlags(Qt.Window)
        self.setWindowTitle('About')
        try:
            self.mainMenuRect = parent.geometry()
            self.move(self.mainMenuRect.center() + QPoint((self.xAw) / 2, -(self.yAw / 2 + hPanel)))
        except Exception:
            pass
        self.textBrowser = QTextBrowser(self)
        self.textBrowser.setGeometry(QRect(10, 10, self.xAw - 20, self.yAw - 20))
        self.textBrowser.setObjectName("textBrowser")
        self.textBrowser.setText(
            "Curves from tubes v1.0\n\nAuthor: \nAnton Jukov\n\nRefactor: GGboom\nContact: https://github.com/GGboom-er"
        )
        self.verticalLayoutAw = QVBoxLayout(self)
        self.verticalLayoutAw.addWidget(self.textBrowser)

    def sizeHint(self):
        return QSize(300, 150)


class CurveFromTubes(QWidget):
    def __init__(self, parent=None):
        super(CurveFromTubes, self).__init__(parent)
        # [star3, star5, border, star2]
        self.maps = [[8, 0, 0, 0], [0, 2, 0, 0], [4, 1, 0, 0], [4, 0, 1, 0],
                     [0, 1, 1, 0], [0, 0, 1, 0], [4, 0, 0, 0], [0, 0, 0, 0], [0, 0, 1, 4]]
        self.x = 200
        self.y = 250

        self.setWindowFlags(Qt.Window)
        self.setWindowTitle('CFT v1.0')
        try:
            self.maya_win_rect = parent.geometry()
            self.move(self.maya_win_rect.center() + QPoint(-100, -200))
        except Exception:
            pass

        # --- UI 控件 ---
        self.createCurves_btn = QPushButton('创建曲线', self)
        self.createCurves_btn.clicked.connect(partial(self.createCurvesFromTubes, 'default'))

        self.groupBox = QGroupBox('偏好:', self)
        self.preference_grd = QGridLayout(self.groupBox)
        self.thresholdCurvePoints = QLabel(self.groupBox)
        self.thresholdCurvePoints.setText("          CV阈值:")
        self.thresholdCurvePointsVal = QLineEdit(self.groupBox)
        self.thresholdCurvePointsVal.setText('0.01')
        self.reverseCurve_chb = QCheckBox(self.groupBox)
        self.reverseCurve_chb.setText('反转曲线:')
        self.reverseCurve_chb.setChecked(False)

        # wire
        self.createCurvesWithWire_btn = QPushButton('创建曲线 + 线框', self)
        self.createCurvesWithWire_btn.clicked.connect(partial(self.createCurvesFromTubes, 'wire'))
        self.wirePreference_grBox = QGroupBox('线框偏好:', self)
        self.wirePreference_grd = QGridLayout(self.wirePreference_grBox)
        self.distanceLabel = QLabel(self)
        self.distanceLabel.setText("      衰减距离:")
        self.distanceVal = QLineEdit(self)
        self.distanceVal.setText('50')

        # joints
        self.createCurvesWithJoints_btn = QPushButton('创建曲线 + 骨骼', self)
        self.createCurvesWithJoints_btn.clicked.connect(partial(self.createCurvesFromTubes, 'joints'))
        self.jointPreference_grBox = QGroupBox('骨骼偏好:', self)
        self.jointPreference_grd = QGridLayout(self.jointPreference_grBox)
        self.amountJoint_chb = QCheckBox(self.jointPreference_grBox)
        self.amountJoint_chb.setText('骨骼数量:')
        self.amountJoint_chb.setChecked(True)
        self.amountJoint_chb.clicked.connect(self.stepJoint_chanched)
        self.stepJoint_chb = QCheckBox(self.jointPreference_grBox)
        self.stepJoint_chb.setText('骨骼步数:')
        self.stepJoint_chb.clicked.connect(self.amountJoint_chanched)
        self.amountJoint_val = QLineEdit(self.jointPreference_grBox)
        self.amountJoint_val.setText('10')
        self.stepJoint_val = QLineEdit(self.jointPreference_grBox)
        self.stepJoint_val.setText('5')
        self.jointOrient_lbl = QLabel(self.jointPreference_grBox)
        self.jointOrient_lbl.setText("骨骼朝向:")
        self.jointOrient_cBox = QComboBox(self.jointPreference_grBox)
        for it in ('zyx', 'xyz', 'yzx', 'zxy', 'yxz', 'xzy', 'none'):
            self.jointOrient_cBox.addItem(it)
        self.secondaryAxisOrient_lbl = QLabel(self.jointPreference_grBox)
        self.secondaryAxisOrient_lbl.setText("次级坐标朝向:")
        self.secondaryAxisOrient_cBox = QComboBox(self.jointPreference_grBox)
        for it in ('Y上', 'X上', 'X下', 'Y下', 'Z上', 'Z下', '无'):
            self.secondaryAxisOrient_cBox.addItem(it)

        # delete / about
        self.deleteTrash_btn = QPushButton('删除垃圾', self)
        self.deleteTrash_btn.clicked.connect(self.deleteTrash)
        self.aboutScript_btn = QPushButton('关于', self)
        self.aboutScript_btn.clicked.connect(self.aboutScript)

        # layouts
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

    def sizeHint(self):
        return QSize(self.x, self.y)

    def stepJoint_chanched(self):
        self.stepJoint_chb.setChecked(False)
        self.amountJoint_chb.setChecked(True)

    def amountJoint_chanched(self):
        self.amountJoint_chb.setChecked(False)
        self.stepJoint_chb.setChecked(True)

    def closeEvent(self, close):
        try:
            self.aboutMenu.close()
        except Exception:
            pass

    def aboutScript(self):
        try:
            self.aboutMenu.close()
        except Exception:
            pass
        self.aboutMenu = AboutWindow(self)
        self.aboutMenu.show()

    def deleteTrash(self):
        deleteReady = False
        try:
            if getattr(self, 'forDelete', None) and len(self.forDelete) != 0:
                deleteReady = True
        except Exception:
            deleteReady = False
        if deleteReady:
            for d in self.forDelete:
                try:
                    delete(d)
                except Exception:
                    continue
        else:
            print('Object to delete is not found!')

    # -------------------------
    # 主流程: createCurvesFromTubes
    # -------------------------
    def createCurvesFromTubes(self, mode='default'):
        t = time.time()
        print('\n\n[CurveFromTubes] start...')
        # 开始 undo chunk
        undoInfo(openChunk=True)
        try:
            self.threshold = float(self.thresholdCurvePointsVal.text())
        except Exception:
            print('Incorrect input! Default values are used.')
            self.threshold = 0.01

        # 选择几何体（transform / mesh） - 使用 PyMel ls
        self.sel = ls(sl=True, o=True, tr=True, s=True)
        self.geometryFromSelect = []
        for self.s in self.sel:
            try:
                stype = self.s.type()
            except Exception:
                continue
            if stype == 'transform':
                shp = self.s.getShape()
                if shp:
                    if shp.type() == 'mesh':
                        self.geometryFromSelect.append(self.s)
                        if len(self.s.getChildren()) > 1:
                            self.MeshInGroup(self.s, self.geometryFromSelect)
                    elif shp.type() == 'nurbsCurve':
                        self.MeshInGroup(self.s, self.geometryFromSelect)
                elif shp is None:
                    self.MeshInGroup(self.s, self.geometryFromSelect)
            elif stype == 'mesh':
                self.geometryFromSelect.append(self.s)
        # 去重
        self.geometryFromSelect = list(set(self.geometryFromSelect))

        # 创建组
        gr = group(empty=True, name='curvesFromTubes_grp')
        wireGr = None
        jointsGr = None
        if mode == 'wire':
            wireGr = group(empty=True, name='wireBase_grp')
        if mode == 'joints':
            jointsGr = group(empty=True, name='joints_grp')

        self.forDelete = []
        badTopology = []

        # 遍历每个选择的几何
        for g in self.geometryFromSelect:
            try:
                dagPath = g.__apimdagpath__()   # PyMel to MFn DAG path
                obj = dagPath.node()
                fullName = dagPath.fullPathName()
                name = fullName.split('|')[-1]
            except Exception:
                print('Failed to get dag path for', g)
                continue

            # duplicate, unparent
            try:
                dupl = duplicate(g, name=name + '_tube')[0]
                if dupl not in self.forDelete:
                    self.forDelete.append(dupl)
                dupl.setParent(None)
            except Exception:
                print('Failed to duplicate', g)
                continue

            # poly shell separation
            try:
                shellsNum = polyEvaluate(g, shell=1)
            except Exception:
                shellsNum = 1

            if shellsNum > 1 and mode == 'default':
                try:
                    shellsGlobal = polySeparate(dupl, ch=0)
                except Exception:
                    if dupl not in self.forDelete:
                        self.forDelete.append(dupl)
                    continue
                # rename separated shells (保留旧逻辑命名规则)
                x = 1
                for shGl in shellsGlobal:
                    if len(shellsGlobal) < 10:
                        suffix = '_000' + str(x) + '_tube'
                    elif len(shellsGlobal) < 100:
                        suffix = '_00' + str(x) + '_tube'
                    elif len(shellsGlobal) < 1000:
                        suffix = '_0' + str(x) + '_tube'
                    else:
                        suffix = '_' + str(x) + '_tube'
                    try:
                        shGl.rename(name + suffix)
                        parent(shGl, w=True)
                    except Exception:
                        pass
                    x += 1
                if dupl not in self.forDelete:
                    self.forDelete.append(dupl)
                shellsGlobal = list(shellsGlobal)
            elif shellsNum == 1:
                shellsGlobal = [dupl]
            else:
                # shellsNum >1 and mode != default -> skip
                shellsGlobal = []

            # build selection list for MItSelectionList
            omShellsGlobal = Newom.MSelectionList()
            for shGl in shellsGlobal:
                try:
                    omShellsGlobal.add(shGl.fullPath())
                except Exception:
                    pass
            omShellsGlobalIt = Newom.MItSelectionList(omShellsGlobal)
            while not omShellsGlobalIt.isDone():
                try:
                    plane = 0
                    try:
                        self.shGlDagPath = omShellsGlobalIt.getDagPath()
                        self.PyShGlObj = PyNode(self.shGlDagPath.fullPathName())
                    except Exception:
                        omShellsGlobalIt.next()
                        continue

                    # check mesh topology
                    try:
                        bad = self.checkMesh(self.shGlDagPath)
                    except Exception:
                        bad = 1
                    if bad == 1:
                        if g not in badTopology:
                            badTopology.append(g)
                        if self.PyShGlObj not in self.forDelete:
                            self.forDelete.append(self.PyShGlObj)
                        omShellsGlobalIt.next()
                        continue

                    # find stars and borders
                    try:
                        self.star5 = self.getVertexStars(self.shGlDagPath, 5)
                        self.star3 = self.getVertexStars(self.shGlDagPath, 3)
                        self.star2 = self.getVertexStars(self.shGlDagPath, 2, 'Border')
                        self.border = self.getBorderEdges(self.shGlDagPath)
                    except Exception:
                        omShellsGlobalIt.next()
                        continue

                    borderKey = 1 if len(self.border) != 0 else 0
                    shells = []
                    self.loopsForCut = []

                    if [len(self.star3), len(self.star5), borderKey, len(self.star2)] in self.maps:
                        # TORUS special handling
                        if [len(self.star3), len(self.star5), borderKey, len(self.star2)] == [0, 0, 0, 0]:
                            # find loops on torus and split shortest
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
                                L1 = round(self.ComponentInfo(self.loopsTorus[0], 'edge', 'length', self.shGlDagPath), 10)
                                L2 = round(self.ComponentInfo(self.loopsTorus[1], 'edge', 'length', self.shGlDagPath), 10)
                                if L1 == min(L1, L2):
                                    polySplitEdge(list(map(lambda x: self.PyShGlObj.e[x], self.loopsTorus[0])))
                                else:
                                    polySplitEdge(list(map(lambda x: self.PyShGlObj.e[x], self.loopsTorus[1])))
                        elif [len(self.star3), len(self.star5), borderKey, len(self.star2)] == [0, 0, 1, 4]:
                            plane = 1

                        # star5 loops
                        if self.star5:
                            for self.st5 in self.star5:
                                self.loopVtx = self.ComponentInfo(self.st5, 'vtx', 'toVtx', self.shGlDagPath)
                                self.loopEdge = self.ComponentInfo(self.loopVtx, 'vtx', 'toContainedEdges', self.shGlDagPath)
                                self.loopsForCut.append(self.loopEdge)

                        # star3 paths
                        if self.star3:
                            self.pathes = []
                            for self.st3 in self.star3:
                                self.edgesSt3 = self.ComponentInfo(self.st3, 'vtx', 'toEdge', self.shGlDagPath)
                                for self.edSt3 in self.edgesSt3:
                                    self.loop = []
                                    self.loopVtx = []
                                    self.toEdgeLoop(self.edSt3, self.loop, self.loopVtx, self.shGlDagPath)
                                    if any([(x in self.star3 and x != self.st3) for x in self.loopVtx]):
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
                            self.capsLoops = list(filter(lambda x: round(float(x.split(':')[0]), 10) in lengths, dictLength))
                            self.capsLoops = list(map(lambda x: x.split(':')[-1].split('|')[:-1], self.capsLoops))
                            self.capsLoops = [list(map(lambda x: int(x), y)) for y in self.capsLoops]
                            self.loopsForCut.append(self.capsLoops)

                        tubes = []
                        if self.loopsForCut:
                            self.loopsForCutPy = list(map(lambda x: self.PyShGlObj.e[x], list(itertools.chain(*self.loopsForCut))))
                            polySplitEdge(self.loopsForCutPy)
                            nameTube = self.PyShGlObj.name().split('|')[-1] + '_shell'
                            tubeShells = []
                            try:
                                tubeShells = polySeparate(self.PyShGlObj, ch=0)
                            except Exception:
                                if g not in badTopology:
                                    badTopology.append(g)
                                if self.PyShGlObj not in self.forDelete:
                                    self.forDelete.append(self.PyShGlObj)
                            if tubeShells:
                                for tSh in tubeShells:
                                    parent(tSh, w=True)
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

                        # 对于每个 tube 生成中心曲线
                        if tubes:
                            for tube in tubes:
                                try:
                                    tubeSelList = Newom.MSelectionList()
                                    tubeSelList.add(tube.fullPath())
                                    self.tubeDagPath = tubeSelList.getDagPath(0)
                                    # plane-case or border-case 路径查找
                                    if plane == 1:
                                        self.planeStartVtx = self.star2[0]
                                        self.planeStartEdges = self.ComponentInfo(self.planeStartVtx, 'vtx', 'toEdge', self.tubeDagPath)
                                        if len(self.planeStartEdges) == 2:
                                            self.start1 = []
                                            self.startVtx1 = []
                                            self.toEdgeLoop(self.planeStartEdges[0], self.start1, self.startVtx1, self.tubeDagPath)
                                            self.start2 = []
                                            self.startVtx2 = []
                                            self.toEdgeLoop(self.planeStartEdges[1], self.start2, self.startVtx2, self.tubeDagPath)
                                            self.planeL1 = round(self.ComponentInfo(self.start1, 'edge', 'length', self.tubeDagPath), 10)
                                            self.planeL2 = round(self.ComponentInfo(self.start2, 'edge', 'length', self.tubeDagPath), 10)
                                            if self.planeL1 == min(self.planeL1, self.planeL2):
                                                self.start = self.start1
                                                self.startVtx = self.startVtx1
                                            else:
                                                self.start = self.start2
                                                self.startVtx = self.startVtx2
                                            self.planeEndVtx = [x for x in self.star2 if x not in self.startVtx][0]
                                            self.planeEndEdges = self.ComponentInfo(self.planeEndVtx, 'vtx', 'toEdge', self.tubeDagPath)
                                            if len(self.planeEndEdges) == 2:
                                                self.end1 = []
                                                self.endVtx1 = []
                                                self.toEdgeLoop(self.planeEndEdges[0], self.end1, self.endVtx1, self.tubeDagPath)
                                                self.end2 = []
                                                self.endVtx2 = []
                                                self.toEdgeLoop(self.planeEndEdges[1], self.end2, self.endVtx2, self.tubeDagPath)
                                                self.planeEndL1 = round(self.ComponentInfo(self.end1, 'edge', 'length', self.tubeDagPath), 10)
                                                self.planeEndL2 = round(self.ComponentInfo(self.end2, 'edge', 'length', self.tubeDagPath), 10)
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
                                        self.toEdgeLoop(self.borderEdges[0], self.start, self.startVtx, self.tubeDagPath)
                                        self.end = [i for i in self.borderEdges if i not in self.start]

                                    # ring marching
                                    self.rings = [self.start, ]
                                    self.face_done = []
                                    self.RingByRing(self.start, self.end, self.rings, self.face_done, self.tubeDagPath)

                                    centers = []
                                    for self.ring in self.rings:
                                        center = self.CentralPosition(self.ring, 'edge', self.tubeDagPath)
                                        # center is [x,y,z]
                                        centers.append(center[:3])

                                    nameCurv = tube.name().split('|')[-1].split('_tube')[0] + '_crv'
                                    if tube not in self.forDelete:
                                        self.forDelete.append(tube)

                                    if len(centers) > 3:
                                        curv = curve(p=centers, ws=True, n=nameCurv)
                                    else:
                                        curv = curve(p=centers, ws=True, n=nameCurv, d=1)
                                    if self.reverseCurve_chb.isChecked():
                                        try:
                                            curv.reverse()
                                        except Exception:
                                            pass

                                    # remove small-distance CVs
                                    curveSelList = Newom.MSelectionList()
                                    curveSelList.add(curv.fullPath())
                                    curveDagPath = curveSelList.getDagPath(0)
                                    curveFn = Newom.MFnNurbsCurve(curveDagPath)
                                    badPoints = []
                                    for prevPoint in range(curveFn.numCVs - 1):
                                        prevPointPos = curveFn.cvPosition(prevPoint, Newom.MSpace.kWorld)
                                        currPointPos = curveFn.cvPosition(prevPoint + 1, Newom.MSpace.kWorld)
                                        vect = Newom.MVector(currPointPos - prevPointPos)
                                        if vect.length() < self.threshold:
                                            badPoints.append(prevPoint + 1)
                                    # map to PyMel CVs and delete
                                    badPointsPy = [curv.cv[x] for x in badPoints]
                                    if badPointsPy:
                                        delete(badPointsPy)

                                    # only keep curve if length > threshold
                                    if curveFn.length() > self.threshold:
                                        curv.setRotatePivot(curv.getCV(0, space='world'))
                                        # wire mode
                                        if mode == 'wire':
                                            try:
                                                curv.rename(nameCurv + str(int(time.time())))
                                                try:
                                                    self.dropoffDistanceWire = float(self.distanceVal.text())
                                                except Exception:
                                                    print('Incorrect input! Default dropoff used.')
                                                    self.dropoffDistanceWire = 50.0
                                                wireForCurve = wire(g, w=curv)[0]
                                                wire(wireForCurve, edit=True, dds=(0, self.dropoffDistanceWire))
                                                wireBase = listConnections(wireForCurve.attr('baseWire[0]'))[0]
                                                if wireGr:
                                                    parent(wireBase, wireGr)
                                                curv.rename(nameCurv)
                                                wireBase.rename(nameCurv + 'BaseWire')
                                            except Exception:
                                                traceback.print_exc()

                                        # joints mode
                                        if mode == 'joints':
                                            try:
                                                numEP = curv.numEPs()
                                                self.duplCurv = duplicate(curv, n=nameCurv + '_dupl')[0]
                                                if self.amountJoint_chb.isChecked():
                                                    try:
                                                        numberJoint = int(self.amountJoint_val.text())
                                                    except Exception:
                                                        print('Incorrect input! Default numberJoint used.')
                                                        numberJoint = 15
                                                elif self.stepJoint_chb.isChecked():
                                                    lengthCurv = self.duplCurv.length()
                                                    try:
                                                        step = float(self.stepJoint_val.text())
                                                    except Exception:
                                                        print('Incorrect input! Default step used.')
                                                        step = 3.0
                                                    if lengthCurv <= step:
                                                        numberJoint = 1
                                                    else:
                                                        numberJoint = int(lengthCurv / step)
                                                else:
                                                    numberJoint = 15

                                                k = float(numEP) / float(numberJoint)
                                                if k < 2:
                                                    k = 1
                                                else:
                                                    k = int(k)

                                                rebuildCurve(self.duplCurv, ch=False, rpo=True, rt=False, end=True,
                                                             kr=False, kcp=False, kep=True, kt=True, s=numberJoint * k,
                                                             d=3, tol=0.01)
                                                select(cl=True)
                                                joints = []
                                                j = 1
                                                for i in range(0, numberJoint * k + 1, k):
                                                    point = pointPosition(self.duplCurv.ep[i], w=True)
                                                    jnt = joint(p=point, name=name + '_' + str(j) + '_jnt')
                                                    joints.append(jnt)
                                                    j += 1
                                                if joints and jointsGr:
                                                    parent(joints[0], jointsGr)
                                                orientJ = str(self.jointOrient_cBox.currentText())
                                                secAxis = str(self.secondaryAxisOrient_cBox.currentText())
                                                if joints:
                                                    joint(joints[0], e=True, oj=orientJ, secondaryAxisOrient=secAxis, ch=1, zso=1)
                                                    joint(joints[-1], e=True, oj='none', ch=1, zso=1)
                                                if hasattr(self, 'duplCurv'):
                                                    self.forDelete.append(self.duplCurv)
                                            except Exception:
                                                traceback.print_exc()

                                        parent(curv, gr)
                                    else:
                                        if g not in badTopology:
                                            badTopology.append(g)
                                        if curv not in self.forDelete:
                                            self.forDelete.append(curv)
                                except Exception:
                                    if g not in badTopology:
                                        badTopology.append(g)
                                    if tube not in self.forDelete:
                                        self.forDelete.append(tube)
                    else:
                        if g not in badTopology:
                            badTopology.append(g)
                        if self.PyShGlObj not in self.forDelete:
                            self.forDelete.append(self.PyShGlObj)
                    omShellsGlobalIt.next()
                except Exception:
                    # 保证循环继续
                    traceback.print_exc()
                    try:
                        omShellsGlobalIt.next()
                    except Exception:
                        break

        # 清理
        try:
            delete(self.forDelete)
        except Exception:
            pass

        if badTopology:
            print('Contains bad topology for script:')
            for bT in badTopology:
                print(bT)

        if gr.getChildren():
            select(gr)
        else:
            print('Proper geometry not found!')
            try:
                delete(gr)
            except Exception:
                pass
            if mode == 'wire' and wireGr:
                try:
                    delete(wireGr)
                except Exception:
                    pass
            elif mode == 'joints' and jointsGr:
                try:
                    delete(jointsGr)
                except Exception:
                    pass

        self.forDelete = []
        undoInfo(closeChunk=True)
        print('[CurveFromTubes] runtime: %.3f s' % (time.time() - t))

    # -------------------------
    # 辅助函数（几乎保持原逻辑，仅修复 Python3 / API 差异）
    # -------------------------
    def toEdgeLoop(self, index, result, vtxLoop, obj):
        indexError = 'Error: Incorrect input ID component!!!'
        objError = 'Error: Incorrect input obj!!!'
        try:
            try:
                index = list(set(index))
            except TypeError:
                index = [index, ]
        except Exception:
            return indexError

        try:
            api_t = obj.apiType()
            if api_t == 110 or api_t == 296:
                objGood = True
            else:
                objGood = False
        except Exception:
            return objError

        if objGood:
            for i in index:
                if i not in result:
                    result.append(i)
                    faces = self.ComponentInfo(i, 'edge', 'toFace', obj)
                    edges = self.ComponentInfo(faces, 'face', 'toEdge', obj)
                    vtx = self.ComponentInfo(i, 'edge', 'toVtx', obj)
                    for v in vtx:
                        if v not in vtxLoop:
                            vtxLoop.append(v)
                            edgesVtx = [x for x in self.ComponentInfo(v, 'vtx', 'toEdge', obj) if x not in edges]
                            if len(edgesVtx) == 1:
                                self.toEdgeLoop(edgesVtx[0], result, vtxLoop, obj)

    def RingByRing(self, start, end, rings, face_done, obj):
        startVtx = self.ComponentInfo(start, 'edge', 'toVtx', obj)
        startFaceAll = self.ComponentInfo(start, 'edge', 'toFace', obj)
        self.startFace = [i for i in startFaceAll if i not in face_done]
        vtx = self.ComponentInfo(self.startFace, 'face', 'toVtx', obj)
        self.next_loop_vtx = [i for i in vtx if i not in startVtx]
        self.next_loop = self.ComponentInfo(self.next_loop_vtx, 'vtx', 'toContainedEdges', obj)
        rings.append(self.next_loop)
        face_done.extend(startFaceAll)
        if sorted(self.next_loop) != sorted(end):
            self.RingByRing(self.next_loop, end, rings, face_done, obj)

    def CentralPosition(self, index, componentType, obj):
        """ 返回 component 的中心点 (x,y,z) 列表
            Return center position [x, y, z] for given components
        """
        meshFn = Newom.MFnMesh(obj)
        verts = self.ComponentInfo(index, componentType, 'toVtx', obj)
        n = len(verts)
        if n == 0:
            return [0.0, 0.0, 0.0]
        vertsPos = []
        for v in verts:
            p = meshFn.getPoint(v, Newom.MSpace.kWorld)
            vertsPos.append((p.x, p.y, p.z))
        # 平均
        avg = [sum(coord) / float(n) for coord in zip(*vertsPos)]
        return avg

    def DeleteReplayFromList(self, lst):
        newList = []
        for l in lst:
            if l not in newList:
                newList.append(l)
        return newList

    def ComponentInfo(self, index, componentType, command, obj):
        """ 多用途组件查询 (vertex/edge/face)：
            command: toEdge, toFace, toVtx, toContainedEdges, toEdgePerimeter, length
            componentType: 'vtx', 'face', 'edge'
        """
        indexError = 'Error: Incorrect input ID component!!!'
        objError = 'Error: Incorrect input obj!!!'
        try:
            try:
                index = list(set(index))
            except TypeError:
                index = [index, ]
        except Exception:
            return indexError

        try:
            api_t = obj.apiType()
            if api_t == 110 or api_t == 296:
                objGood = True
            else:
                objGood = False
        except Exception:
            return objError

        if not objGood:
            return objError

        result = []
        items = []
        meshFn = Newom.MFnMesh(obj)

        if componentType == 'face':
            faceIt = Newom.MItMeshPolygon(obj)
            if command == 'toEdgePerimeter':
                self.edges = self.ComponentInfo(index, 'face', 'toEdge', obj)
                edgeIt = Newom.MItMeshEdge(obj)
                for edge in self.edges:
                    face = self.ComponentInfo(edge, 'edge', 'toFace', obj)
                    for f in face:
                        if f not in index:
                            items.append(edge)
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
                length = 0.0
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
            if command == 'toContainedEdges':
                for i in index:
                    vtxIt.setIndex(i)
                    self.edges = vtxIt.getConnectedEdges()
                    edgesIt = Newom.MItMeshEdge(obj)
                    for edge in self.edges:
                        edgesIt.setIndex(edge)
                        edgeVtx0 = edgesIt.vertexId(0)
                        edgeVtx1 = edgesIt.vertexId(1)
                        if edgeVtx0 in index and edgeVtx1 in index:
                            items.append(edge)
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

    def getBorderEdges(self, obj):
        edgesIt = Newom.MItMeshEdge(obj)
        index = []
        while not edgesIt.isDone():
            if edgesIt.onBoundary():
                index.append(edgesIt.index())
            # API 2.0: 使用无参 next()
            edgesIt.next()
        return index

    def getVertexStars(self, obj, star, mode='notBorder'):
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

    def checkMesh(self, obj):
        """ 检查拓扑是否适合脚本 (face vertex count >4 / lamina / loose verts / edge >2 faces)
            Return 1 when bad topology found, else 0
        """
        faceIt = Newom.MItMeshPolygon(obj)
        while not faceIt.isDone():
            if faceIt.polygonVertexCount() > 4:
                return 1
            if faceIt.isLamina():
                return 1
            # 统一使用无参 next()（兼容 Maya2020.3 及以后）
            faceIt.next()

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

    def MeshInGroup(self, grp, result, vis=0):
        """ 根据 group (transform) 收集组内 mesh（保留原逻辑）
        """
        name = grp.longName()
        nameSplit = name.split('|')
        n = len(nameSplit)
        # 过滤 intermediate objects
        mesh_list = list(filter(lambda i: i.intermediateObject.get() == 0, ls(typ='mesh')))
        if mesh_list and vis == 1:
            mesh_list = ls(mesh_list, v=1, fl=1)
        for m in mesh_list:
            path = m.longName()
            pathSplit = path.split('|')
            if len(pathSplit) > n:
                j = 0
                for i in range(n):
                    if nameSplit[i] == pathSplit[i]:
                        j += 1
                if j == n:
                    result.append(m.getParent())


# -------------------------
# 启动 UI（如果已有实例则先关闭）
# -------------------------
try:
    CFT.close()
except Exception:
    pass

maya_win = getMayaWindow()
CFT = CurveFromTubes(maya_win)
CFT.show()
