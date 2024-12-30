# _*_ coding:cp936 _*_
"""
Scripts :    python.tools.rigging.controllerManager
Author  :    JesseChou
Date    :    2021/4/10
QQ      :    375714316
E-Mail  :    JesseChou0612@gmail.com or 375714316@qq.com
"""
import json
import os
from PySide2 import QtWidgets, QtCore, QtGui
from maya import cmds
from python.core import getPath, matrix
from python.meta import groups, widgetConfig


class MainWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.__iconSize = 40
        self.__iconPath = None
        self.__configInfos = {}
        self.__widgetConfig = None
        self.__colorList = []
        self.__started = False
        self.createWidgets()
        self.createLayouts()
        self.createConnections()
        self.preset()
        self.setMinimumWidth(425)
        self.setWindowTitle(u'控制器管理器 Ver %s' % self.version)

    @property
    def version(self):
        return '2.0.1'

    @property
    def iconPath(self):
        if not self.__iconPath:
            self.__iconPath = '%sControllerCreator\\' % getPath.getPipelineToolkitPath('icons')
        return self.__iconPath

    @property
    def defaultIcon(self):
        return '%sppas.png' % self.iconPath

    @property
    def colorList(self):
        if not self.__colorList:
            self.__colorList = QtGui.QColor.colorNames()
        return self.__colorList

    @property
    def userWidgetConfig(self):
        if not self.__widgetConfig:
            self.__widgetConfig = widgetConfig.Configuration('ControllerManager')
        return self.__widgetConfig

    def createWidgets(self):
        # 创建所需控件
        self._mainScrollWT_ = QtWidgets.QWidget()
        self._mainScrollSA_ = QtWidgets.QScrollArea()
        self._mainScrollSA_.setWidget(self._mainScrollWT_)
        self._mainScrollSA_.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self._mainScrollSA_.setWidgetResizable(True)

        self._showUiLB_ = QtWidgets.QLabel(u'显示界面:')
        self._showColorCB_ = QtWidgets.QCheckBox(u'颜色')
        self._showConfigCB_ = QtWidgets.QCheckBox(u'参数')
        self._showAttributeCB_ = QtWidgets.QCheckBox(u'属性')

        def colorPanel():
            self._colorGB_ = QtWidgets.QGroupBox()
            self._colorGB_.setTitle(u'颜色设置')
            self._colorGB_.setAlignment(QtCore.Qt.AlignCenter)

            self._colorCB_ = QtWidgets.QComboBox()
            self._colorSL_ = QtWidgets.QSlider()
            self._colorSL_.setRange(0, len(self.colorList) - 1)
            self._colorSL_.setOrientation(QtCore.Qt.Orientation.Horizontal)
            self._favoriteLW_ = QtWidgets.QListWidget()
            self._favoriteLW_.setMinimumHeight(50)
            self._favoriteLW_.setViewMode(QtWidgets.QListView.IconMode)
            self._favoriteLW_.setProperty("isWrapping", True)
            self._favoriteLW_.setResizeMode(QtWidgets.QListView.Adjust)
            self._favoriteLW_.setMovement(QtWidgets.QListView.Static)

        def configPanel():
            self._nameGB_ = QtWidgets.QGroupBox()
            self._nameGB_.setTitle(u'参数设置')
            self._nameGB_.setAlignment(QtCore.Qt.AlignCenter)
            self._nameGB_.setMinimumHeight(250)
            self._nameLE_ = QtWidgets.QLineEdit()
            self._groupLE_ = QtWidgets.QLineEdit()
            self._groupCB_ = QtWidgets.QCheckBox('')

            self._directionxRB_ = QtWidgets.QRadioButton('x')
            self._directionyRB_ = QtWidgets.QRadioButton('y')
            self._directionzRB_ = QtWidgets.QRadioButton('z')
            self._directionBG_ = QtWidgets.QButtonGroup()
            self._directionBG_.addButton(self._directionxRB_)
            self._directionBG_.addButton(self._directionyRB_)
            self._directionBG_.addButton(self._directionzRB_)

            self._controlNoneRB_ = QtWidgets.QRadioButton(u'无')
            self._controlParentRB_ = QtWidgets.QRadioButton(u'父子')
            self._controlConstraintRB_ = QtWidgets.QRadioButton(u'约束')
            self._controlConnectRB_ = QtWidgets.QRadioButton(u'连接')
            self._controlTypeBG_ = QtWidgets.QButtonGroup()
            self._controlTypeBG_.addButton(self._controlNoneRB_)
            self._controlTypeBG_.addButton(self._controlParentRB_)
            self._controlTypeBG_.addButton(self._controlConstraintRB_)
            self._controlTypeBG_.addButton(self._controlConnectRB_)

            self._controlTranslateCB_ = QtWidgets.QCheckBox(u'位移')
            self._controlRotateCB_ = QtWidgets.QCheckBox(u'旋转')
            self._controlScaleCB_ = QtWidgets.QCheckBox(u'缩放')

            self._hierarchySelectRB_ = QtWidgets.QRadioButton(u'所选')
            self._hierarchyBelowRB_ = QtWidgets.QRadioButton(u'层级')
            self._hierarchyBG_ = QtWidgets.QButtonGroup()
            self._hierarchyBG_.addButton(self._hierarchySelectRB_)
            self._hierarchyBG_.addButton(self._hierarchyBelowRB_)

            self._controllerSizeDSB_ = QtWidgets.QDoubleSpinBox()
            self._controllerSizeDSB_.setRange(0.01, 10.0)
            self._controllerSizeDSB_.setSingleStep(0.1)
            self._controllerSizeSL_ = QtWidgets.QSlider()
            self._controllerSizeSL_.setRange(1, 1000)
            self._controllerSizeSL_.setOrientation(QtCore.Qt.Orientation.Horizontal)

            self._reductionDSB_ = QtWidgets.QDoubleSpinBox()
            self._reductionDSB_.setRange(0, 0.99)
            self._reductionDSB_.setSingleStep(0.05)
            self._reductionSL_ = QtWidgets.QSlider()
            self._reductionSL_.setRange(0, 99)
            self._reductionSL_.setOrientation(QtCore.Qt.Orientation.Horizontal)
            self._centerControllerCB_ = QtWidgets.QCheckBox(u'重心控制')
            self._addColorAttrCB_ = QtWidgets.QCheckBox(u'颜色控制')
            self._twistControllerCB_ = QtWidgets.QCheckBox(u'扭曲控制')

        def controllerPanel():
            self._controllerGB_ = QtWidgets.QGroupBox()
            self._controllerGB_.setTitle(u'控制器列表')
            self._controllerGB_.setAlignment(QtCore.Qt.AlignCenter)
            self._controllerLW_ = QtWidgets.QListWidget()
            self._controllerLW_.setMovement(QtWidgets.QListView.Static)
            self._controllerLW_.setViewMode(QtWidgets.QListView.IconMode)
            self._controllerLW_.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            self._controllerLW_.setGridSize(QtCore.QSize(self.__iconSize, self.__iconSize))
            self._controllerLW_.setProperty("isWrapping", True)
            self._controllerLW_.setMinimumHeight(200)
            self._controllerLW_.setResizeMode(QtWidgets.QListView.Adjust)

        def attrPanel():
            redMap = QtGui.QPixmap(5, 10)
            redMap.fill(QtGui.QColor('red'))

            greenMap = QtGui.QPixmap(5, 10)
            greenMap.fill(QtGui.QColor('green'))

            blueMap = QtGui.QPixmap(5, 10)
            blueMap.fill(QtGui.QColor('blue'))

            self._transformGB_ = QtWidgets.QGroupBox()
            self._transformGB_.setTitle(u'属性设置')
            self._transformGB_.setAlignment(QtCore.Qt.AlignCenter)
            self._transformGB_.setVisible(False)

            self._translateCB_ = QtWidgets.QCheckBox('T')
            self._translatexCB_ = QtWidgets.QCheckBox('X')
            self._translatexCB_.setIcon(redMap)
            self._translateyCB_ = QtWidgets.QCheckBox('Y')
            self._translateyCB_.setIcon(greenMap)
            self._translatezCB_ = QtWidgets.QCheckBox('Z')
            self._translatezCB_.setIcon(blueMap)

            self._rotateCB_ = QtWidgets.QCheckBox('R')
            self._rotatexCB_ = QtWidgets.QCheckBox('X')
            self._rotatexCB_.setIcon(redMap)
            self._rotateyCB_ = QtWidgets.QCheckBox('Y')
            self._rotateyCB_.setIcon(greenMap)
            self._rotatezCB_ = QtWidgets.QCheckBox('Z')
            self._rotatezCB_.setIcon(blueMap)

            self._scaleCB_ = QtWidgets.QCheckBox('S')
            self._scalexCB_ = QtWidgets.QCheckBox('X')
            self._scalexCB_.setIcon(redMap)
            self._scaleyCB_ = QtWidgets.QCheckBox('Y')
            self._scaleyCB_.setIcon(greenMap)
            self._scalezCB_ = QtWidgets.QCheckBox('Z')
            self._scalezCB_.setIcon(blueMap)

            self._transLine1_ = QtWidgets.QFrame()
            self._transLine1_.setFrameShape(QtWidgets.QFrame.HLine)
            self._transLine1_.setFrameShadow(QtWidgets.QFrame.Sunken)

            self._visibilityCB_ = QtWidgets.QCheckBox('V')
            self._customCB_ = QtWidgets.QCheckBox('Custom')

            self._getAttrPB_ = QtWidgets.QPushButton(u'获取属性')
            self._setAttrPB_ = QtWidgets.QPushButton(u'设置属性')

            self._displayGB_ = QtWidgets.QGroupBox()
            self._displayGB_.setTitle(u'显示信息')
            self._displayGB_.setAlignment(QtCore.Qt.AlignCenter)
            self._displayGB_.setVisible(False)

            self._handleCB_ = QtWidgets.QCheckBox(u'手柄')
            self._axisCB_ = QtWidgets.QCheckBox(u'轴向')
            self._rotatePivotCB_ = QtWidgets.QCheckBox(u'旋转轴心')
            self._scalePivotCB_ = QtWidgets.QCheckBox(u'缩放轴心')

            self._displayLine1_ = QtWidgets.QFrame()
            self._displayLine1_.setFrameShape(QtWidgets.QFrame.HLine)
            self._displayLine1_.setFrameShadow(QtWidgets.QFrame.Sunken)

            self._templateCB_ = QtWidgets.QCheckBox(u'模板')
            self._referenceCB_ = QtWidgets.QCheckBox(u'参考')
            self._hidePlaybackCB_ = QtWidgets.QCheckBox(u'拍屏隐藏')
            self._hidePlaybackCB_.setChecked(True)
            self._hideOutlinerCB_ = QtWidgets.QCheckBox(u'大纲隐藏')

            self._displayLine2_ = QtWidgets.QFrame()
            self._displayLine2_.setFrameShape(QtWidgets.QFrame.HLine)
            self._displayLine2_.setFrameShadow(QtWidgets.QFrame.Sunken)

            self._curveCvCB_ = QtWidgets.QCheckBox('CV')
            self._curveEpCB_ = QtWidgets.QCheckBox('EP')
            self._curveHullCB_ = QtWidgets.QCheckBox(u'外壳')
            self._geometryCB_ = QtWidgets.QCheckBox(u'模型')
            self._geometryCB_.setChecked(True)

            self._getDisplayPB_ = QtWidgets.QPushButton(u'获取显示')
            self._setDisplayPB_ = QtWidgets.QPushButton(u'设置显示')

        def plusPanel():
            pass

        colorPanel()
        configPanel()
        controllerPanel()
        attrPanel()
        plusPanel()

    def createLayouts(self):
        self._mainLayout_ = QtWidgets.QVBoxLayout(self)

        uiLayout = QtWidgets.QHBoxLayout()
        uiLayout.addWidget(self._showUiLB_)
        uiLayout.addWidget(self._showColorCB_)
        uiLayout.addWidget(self._showConfigCB_)
        uiLayout.addWidget(self._showAttributeCB_)
        uiLayout.addStretch(True)
        self._mainLayout_.addLayout(uiLayout)
        self._mainLayout_.addWidget(self._mainScrollSA_)

        mainLayout = QtWidgets.QVBoxLayout(self._mainScrollWT_)

        def colorLayout():
            colorLay = QtWidgets.QVBoxLayout(self._colorGB_)
            plusLay = QtWidgets.QHBoxLayout()
            plusLay.addWidget(self._colorCB_)
            plusLay.addWidget(self._colorSL_)
            colorLay.addLayout(plusLay)
            colorLay.addWidget(self._favoriteLW_)

        def configLayout():
            attrLay = QtWidgets.QFormLayout(self._nameGB_)
            attrLay.addRow(u'控制器名称:', self._nameLE_)

            groupLay = QtWidgets.QHBoxLayout()
            groupLay.addWidget(self._groupLE_)
            groupLay.addWidget(self._groupCB_)

            attrLay.addRow(u'附加组别:', groupLay)

            directionLay = QtWidgets.QHBoxLayout()
            directionLay.addWidget(self._directionxRB_)
            directionLay.addWidget(self._directionyRB_)
            directionLay.addWidget(self._directionzRB_)

            attrLay.addRow(u'控制器朝向:', directionLay)

            controlLay = QtWidgets.QHBoxLayout()
            controlLay.addWidget(self._controlNoneRB_)
            controlLay.addWidget(self._controlParentRB_)
            controlLay.addWidget(self._controlConstraintRB_)
            controlLay.addWidget(self._controlConnectRB_)

            attrLay.addRow(u'控制方式:', controlLay)

            axisLay = QtWidgets.QHBoxLayout()
            axisLay.addWidget(self._controlTranslateCB_)
            axisLay.addWidget(self._controlRotateCB_)
            axisLay.addWidget(self._controlScaleCB_)

            attrLay.addRow(u'控制属性:', axisLay)

            hierarchyLay = QtWidgets.QHBoxLayout()
            hierarchyLay.addWidget(self._hierarchySelectRB_)
            hierarchyLay.addWidget(self._hierarchyBelowRB_)

            attrLay.addRow(u'层级模式:', hierarchyLay)

            sizeLay = QtWidgets.QHBoxLayout()
            sizeLay.addWidget(self._controllerSizeDSB_)
            sizeLay.addWidget(self._controllerSizeSL_)

            attrLay.addRow(u'控制器尺寸:', sizeLay)

            reductionLay = QtWidgets.QHBoxLayout()
            reductionLay.addWidget(self._reductionDSB_)
            reductionLay.addWidget(self._reductionSL_)
            attrLay.addRow(u'尺寸衰减:', reductionLay)

            plusLay = QtWidgets.QHBoxLayout()
            plusLay.addWidget(self._centerControllerCB_)
            # plusLay.addWidget(self._addColorAttrCB_)
            plusLay.addWidget(self._twistControllerCB_)

            attrLay.addRow(u'附加设置:', plusLay)

        def controllerLayout():
            controllerLay = QtWidgets.QVBoxLayout(self._controllerGB_)
            controllerLay.addWidget(self._controllerLW_)

        def attrLayout():
            settingLay = QtWidgets.QHBoxLayout()

            attrLay = QtWidgets.QVBoxLayout(self._transformGB_)
            transformLay = QtWidgets.QHBoxLayout()

            translateLay = QtWidgets.QVBoxLayout()
            translateLay.addWidget(self._translateCB_)
            translateLay.addWidget(self._translatexCB_)
            translateLay.addWidget(self._translateyCB_)
            translateLay.addWidget(self._translatezCB_)

            rotateLay = QtWidgets.QVBoxLayout()
            rotateLay.addWidget(self._rotateCB_)
            rotateLay.addWidget(self._rotatexCB_)
            rotateLay.addWidget(self._rotateyCB_)
            rotateLay.addWidget(self._rotatezCB_)

            scaleLay = QtWidgets.QVBoxLayout()
            scaleLay.addWidget(self._scaleCB_)
            scaleLay.addWidget(self._scalexCB_)
            scaleLay.addWidget(self._scaleyCB_)
            scaleLay.addWidget(self._scalezCB_)

            transformLay.addLayout(translateLay)
            transformLay.addLayout(rotateLay)
            transformLay.addLayout(scaleLay)

            customLay = QtWidgets.QHBoxLayout()
            customLay.addWidget(self._visibilityCB_)
            customLay.addWidget(self._customCB_)

            buttonLay = QtWidgets.QHBoxLayout()
            buttonLay.addWidget(self._getAttrPB_)
            buttonLay.addWidget(self._setAttrPB_)

            attrLay.addLayout(transformLay)
            attrLay.addWidget(self._transLine1_)
            attrLay.addLayout(customLay)
            attrLay.addLayout(buttonLay)

            settingLay.addWidget(self._transformGB_)

            displayLay = QtWidgets.QVBoxLayout(self._displayGB_)
            checkBoxs = [self._handleCB_, self._axisCB_, self._rotatePivotCB_, self._scalePivotCB_, self._templateCB_,
                         self._referenceCB_, self._hidePlaybackCB_, self._hideOutlinerCB_, self._curveCvCB_,
                         self._curveEpCB_, self._curveHullCB_, self._geometryCB_]

            for i in range(len(checkBoxs) // 2):
                lay = QtWidgets.QHBoxLayout()
                lay.addWidget(checkBoxs[i * 2])
                lay.addWidget(checkBoxs[i * 2 + 1])
                if i == 2:
                    displayLay.addWidget(self._displayLine1_)
                    displayLay.addLayout(lay)
                elif i == 3:
                    displayLay.addLayout(lay)
                    displayLay.addWidget(self._displayLine2_)
                else:
                    displayLay.addLayout(lay)

            buttonLay = QtWidgets.QHBoxLayout()
            buttonLay.addWidget(self._getDisplayPB_)
            buttonLay.addWidget(self._setDisplayPB_)
            displayLay.addLayout(buttonLay)

            settingLay.addWidget(self._displayGB_)
            return settingLay

        colorLayout()
        configLayout()
        controllerLayout()
        settingLay = attrLayout()

        mainLayout.addWidget(self._colorGB_)
        mainLayout.addWidget(self._nameGB_)
        mainLayout.addWidget(self._controllerGB_)
        mainLayout.addLayout(settingLay)

    def createConnections(self):
        self._groupCB_.stateChanged.connect(self.changeGroupEnabled)
        self._controllerSizeDSB_.valueChanged.connect(self.sizeDsbChange)
        self._controllerSizeSL_.valueChanged.connect(self.sizeSlChange)
        self._reductionDSB_.valueChanged.connect(self.reductionDsbChange)
        self._reductionSL_.valueChanged.connect(self.reductionSlChange)
        self._colorCB_.currentIndexChanged.connect(self.changeColorCB)
        self._colorSL_.valueChanged.connect(self.changeColorSL)

        self._controlNoneRB_.toggled.connect(self.changeControlType)
        self._controlParentRB_.toggled.connect(self.changeControlType)
        self._controlConstraintRB_.toggled.connect(self.changeControlType)
        self._controlConnectRB_.toggled.connect(self.changeControlType)

        self._translateCB_.clicked.connect(self.changeTranslateMain)
        self._translatexCB_.clicked.connect(self.changeTranslateInfos)
        self._translateyCB_.clicked.connect(self.changeTranslateInfos)
        self._translatezCB_.clicked.connect(self.changeTranslateInfos)

        self._rotateCB_.clicked.connect(self.changeRotateMain)
        self._rotatexCB_.clicked.connect(self.changeRotateInfos)
        self._rotateyCB_.clicked.connect(self.changeRotateInfos)
        self._rotatezCB_.clicked.connect(self.changeRotateInfos)

        self._scaleCB_.clicked.connect(self.changeScaleMain)
        self._scalexCB_.clicked.connect(self.changeScaleInfos)
        self._scaleyCB_.clicked.connect(self.changeScaleInfos)
        self._scalezCB_.clicked.connect(self.changeScaleInfos)

        self._translateCB_.stateChanged.connect(self.setAttrs)
        self._translatexCB_.stateChanged.connect(self.setAttrs)
        self._translateyCB_.stateChanged.connect(self.setAttrs)
        self._translatezCB_.stateChanged.connect(self.setAttrs)

        self._rotateCB_.stateChanged.connect(self.setAttrs)
        self._rotatexCB_.stateChanged.connect(self.setAttrs)
        self._rotateyCB_.stateChanged.connect(self.setAttrs)
        self._rotatezCB_.stateChanged.connect(self.setAttrs)

        self._scaleCB_.stateChanged.connect(self.setAttrs)
        self._scalexCB_.stateChanged.connect(self.setAttrs)
        self._scaleyCB_.stateChanged.connect(self.setAttrs)
        self._scalezCB_.stateChanged.connect(self.setAttrs)

        self._visibilityCB_.stateChanged.connect(self.setAttrs)
        self._customCB_.stateChanged.connect(self.setAttrs)
        self._setAttrPB_.clicked.connect(self.setAttrs)
        self._getAttrPB_.clicked.connect(self.getAttrs)

        self._handleCB_.stateChanged.connect(self.setDisplay)
        self._axisCB_.stateChanged.connect(self.setDisplay)
        self._rotatePivotCB_.stateChanged.connect(self.setDisplay)
        self._scalePivotCB_.stateChanged.connect(self.setDisplay)
        self._templateCB_.stateChanged.connect(self.setDisplay)
        self._referenceCB_.stateChanged.connect(self.setDisplay)
        self._hidePlaybackCB_.stateChanged.connect(self.setDisplay)
        self._hideOutlinerCB_.stateChanged.connect(self.setDisplay)
        self._curveCvCB_.stateChanged.connect(self.setDisplay)
        self._curveEpCB_.stateChanged.connect(self.setDisplay)
        self._curveHullCB_.stateChanged.connect(self.setDisplay)
        self._geometryCB_.stateChanged.connect(self.setDisplay)

        self._getDisplayPB_.clicked.connect(self.getDisplay)
        self._setDisplayPB_.clicked.connect(self.setDisplay)

        self._controllerLW_.itemClicked.connect(self.create)
        self._favoriteLW_.clicked.connect(self.changeColorLW)

        self._showColorCB_.stateChanged.connect(self.switchColorPanelVis)
        self._showConfigCB_.stateChanged.connect(self.switchConfigPanelVis)
        self._showAttributeCB_.stateChanged.connect(self.switchAttributePanelVis)

        self._nameLE_.textChanged.connect(self.savePanelConfig)
        self._groupLE_.textChanged.connect(self.savePanelConfig)
        self._directionxRB_.toggled.connect(self.savePanelConfig)
        self._directionyRB_.toggled.connect(self.savePanelConfig)
        self._directionzRB_.toggled.connect(self.savePanelConfig)
        self._controlTranslateCB_.stateChanged.connect(self.savePanelConfig)
        self._controlRotateCB_.stateChanged.connect(self.savePanelConfig)
        self._controlScaleCB_.stateChanged.connect(self.savePanelConfig)
        self._hierarchySelectRB_.toggled.connect(self.changeHierarchy)
        self._hierarchyBelowRB_.toggled.connect(self.changeHierarchy)
        self._centerControllerCB_.stateChanged.connect(self.savePanelConfig)
        self._twistControllerCB_.stateChanged.connect(self.savePanelConfig)

    def preset(self):
        self.fillColorList()
        self._colorSL_.setValue(self.getConfig('color', 0))
        self._nameLE_.setText(self.getConfig('controlName', '#Ctr'))
        self._groupLE_.setText(self.getConfig('groupSuffix', 'Ext,Tra,Sdk,Oft'))
        self._groupCB_.setChecked(self.getConfig('groupEnabled', True))
        direction = self.getConfig('controlDirection', -2)
        item = {-2: self._directionxRB_, -3: self._directionyRB_, -4: self._directionzRB_}.get(direction)
        if item: item.setChecked(True)
        control = self.getConfig('controlType', -3)
        item = {-2: self._controlNoneRB_, -3: self._controlParentRB_, -4: self._controlConstraintRB_,
                -5: self._controlConnectRB_}.get(control)
        if item: item.setChecked(True)
        self._controlTranslateCB_.setChecked(self.getConfig('controlTranslate', True))
        self._controlRotateCB_.setChecked(self.getConfig('controlRotate', True))
        self._controlScaleCB_.setChecked(self.getConfig('controlScale', True))
        hierarchy = self.getConfig('hierarchy', -2)
        item = {-2: self._hierarchySelectRB_, -3: self._hierarchyBelowRB_}.get(hierarchy)
        if item: item.setChecked(True)
        self._controllerSizeDSB_.setValue(self.getConfig('controllerSize', 1.1))
        self._reductionDSB_.setValue(self.getConfig('reduction', 0.05))
        self._centerControllerCB_.setChecked(self.getConfig('centerController', False))
        self._twistControllerCB_.setChecked(self.getConfig('twistController', False))

        self.refreshControllerIcon()
        colorVis = self.getConfig('colorPanelVis', True)
        configVis = self.getConfig('configPanelVis', True)
        attrVis = self.getConfig('attributePanelVis', False)
        self._showConfigCB_.setChecked(configVis)
        self._colorGB_.setVisible(colorVis)
        self._showColorCB_.setChecked(colorVis)
        self._nameGB_.setVisible(configVis)
        self._showAttributeCB_.setChecked(attrVis)
        self._transformGB_.setVisible(attrVis)
        self._displayGB_.setVisible(attrVis)
        self.__started = True

    def getIcon(self, icon):
        path = icon.replace('&ICON_PATH&', self.iconPath)
        if not os.path.isfile(path):
            path = '%s%s' % (self.iconPath, icon)
            if not os.path.isfile(path):
                path = self.defaultIcon
        return QtGui.QIcon(path)

    def refreshControllerIcon(self):
        self._controllerLW_.clear()
        for i in range(1, 119):
            item = QtWidgets.QListWidgetItem()
            item.setIcon(self.getIcon('curve%03d.xpm' % i))
            item.setData(100, i)
            self._controllerLW_.addItem(item)

    def sizeDsbChange(self, *args):
        value = int(self._controllerSizeDSB_.value() * 100)
        self._controllerSizeSL_.setValue(value)
        self.savePanelConfig()

    def sizeSlChange(self, *args):
        value = self._controllerSizeSL_.value() * 0.01
        self._controllerSizeDSB_.setValue(value)
        self.savePanelConfig()

    def reductionDsbChange(self, *args):
        value = int(self._reductionDSB_.value() * 100)
        self._reductionSL_.setValue(value)
        self.savePanelConfig()

    def reductionSlChange(self, *args):
        value = self._reductionSL_.value() * 0.01
        self._reductionDSB_.setValue(value)
        self.savePanelConfig()

    def fillColorList(self):
        self._colorCB_.clear()
        for colorname in self.colorList:
            pixColor = QtGui.QPixmap(40, 15)
            pixColor.fill(QtGui.QColor(colorname))
            self._colorCB_.addItem(QtGui.QIcon(pixColor), '')
            self._colorCB_.setIconSize(QtCore.QSize(40, 15))
            self._colorCB_.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)

            item = QtWidgets.QListWidgetItem()
            item.setIcon(QtGui.QIcon(pixColor))
            self._favoriteLW_.addItem(item)
            self._favoriteLW_.setIconSize(QtCore.QSize(40, 15))

    def changeControlType(self, *args):
        # 更改控制方式
        if self._controlNoneRB_.isChecked() or self._controlParentRB_.isChecked():
            self._controlTranslateCB_.setEnabled(False)
            self._controlRotateCB_.setEnabled(False)
            self._controlScaleCB_.setEnabled(False)
        else:
            self._controlTranslateCB_.setEnabled(True)
            self._controlRotateCB_.setEnabled(True)
            self._controlScaleCB_.setEnabled(True)
        self.savePanelConfig()

    def changeTranslateMain(self, *args):
        self._translatexCB_.setChecked(self._translateCB_.isChecked())
        self._translateyCB_.setChecked(self._translateCB_.isChecked())
        self._translatezCB_.setChecked(self._translateCB_.isChecked())
        self.savePanelConfig()

    def changeTranslateInfos(self, *args):
        if self._translatexCB_.isChecked() and self._translateyCB_.isChecked() and self._translatezCB_.isChecked():
            self._translateCB_.setChecked(True)
        else:
            self._translateCB_.setChecked(False)
        self.savePanelConfig()

    def changeRotateMain(self, *args):
        self._rotatexCB_.setChecked(self._rotateCB_.isChecked())
        self._rotateyCB_.setChecked(self._rotateCB_.isChecked())
        self._rotatezCB_.setChecked(self._rotateCB_.isChecked())
        self.savePanelConfig()

    def changeRotateInfos(self, *args):
        if self._rotatexCB_.isChecked() and self._rotateyCB_.isChecked() and self._rotatezCB_.isChecked():
            self._rotateCB_.setChecked(True)
        else:
            self._rotateCB_.setChecked(False)
        self.savePanelConfig()

    def changeScaleMain(self, *args):
        self._scalexCB_.setChecked(self._scaleCB_.isChecked())
        self._scaleyCB_.setChecked(self._scaleCB_.isChecked())
        self._scalezCB_.setChecked(self._scaleCB_.isChecked())
        self.savePanelConfig()

    def changeScaleInfos(self, *args):
        if self._scalexCB_.isChecked() and self._scaleyCB_.isChecked() and self._scalezCB_.isChecked():
            self._scaleCB_.setChecked(True)
        else:
            self._scaleCB_.setChecked(False)
        self.savePanelConfig()

    def getChannelInfos(self):
        infos = {'tx': self._translatexCB_.isChecked(),
                 'ty': self._translateyCB_.isChecked(),
                 'tz': self._translatezCB_.isChecked(),
                 'rx': self._rotatexCB_.isChecked(),
                 'ry': self._rotateyCB_.isChecked(),
                 'rz': self._rotatezCB_.isChecked(),
                 'sx': self._scalexCB_.isChecked(),
                 'sy': self._scaleyCB_.isChecked(),
                 'sz': self._scalezCB_.isChecked(),
                 'v': self._visibilityCB_.isChecked(),
                 'c': self._customCB_.isChecked()}
        return infos

    def setAttrs(self, *args):
        infos = self.getChannelInfos()
        setSelectedTransformAttrs(infos)

    def getAttrs(self, *args):
        infos = getSelectedTransformAttrs()
        self._translatexCB_.setChecked(infos.get('tx', False))
        self._translateyCB_.setChecked(infos.get('ty', False))
        self._translatezCB_.setChecked(infos.get('tz', False))
        self._rotatexCB_.setChecked(infos.get('rx', False))
        self._rotateyCB_.setChecked(infos.get('ry', False))
        self._rotatezCB_.setChecked(infos.get('rz', False))
        self._scalexCB_.setChecked(infos.get('sx', False))
        self._scaleyCB_.setChecked(infos.get('sy', False))
        self._scalezCB_.setChecked(infos.get('sz', False))
        self._visibilityCB_.setChecked(infos.get('v', False))
        self._customCB_.setChecked(infos.get('c', False))
        self.changeTranslateInfos()
        self.changeRotateInfos()
        self.changeScaleInfos()

    def getDisplay(self, *args):
        infos = getSelectedDisplay()
        self._handleCB_.setChecked(infos.get('handle', False))
        self._axisCB_.setChecked(infos.get('axis', False))
        self._rotatePivotCB_.setChecked(infos.get('rotatePivot', False))
        self._scalePivotCB_.setChecked(infos.get('scalePivot', False))
        self._templateCB_.setChecked(infos.get('template', False))
        self._referenceCB_.setChecked(infos.get('reference', False))
        self._curveCvCB_.setChecked(infos.get('cv', False))
        self._curveEpCB_.setChecked(infos.get('ep', False))
        self._curveHullCB_.setChecked(infos.get('hull', False))
        self._geometryCB_.setChecked(infos.get('geometry', True))

    def getPanelDisplayInfos(self):
        infos = {'axis': self._axisCB_.isChecked(),
                 'cv': self._curveCvCB_.isChecked(),
                 'ep': self._curveEpCB_.isChecked(),
                 'geometry': self._geometryCB_.isChecked(),
                 'handle': self._handleCB_.isChecked(),
                 'hull': self._curveHullCB_.isChecked(),
                 'reference': self._referenceCB_.isChecked(),
                 'rotatePivot': self._rotatePivotCB_.isChecked(),
                 'scalePivot': self._scalePivotCB_.isChecked(),
                 'template': self._templateCB_.isChecked(),
                 'playback': self._hidePlaybackCB_.isChecked(),
                 'outliner': self._hideOutlinerCB_.isChecked()}
        return infos

    def setDisplay(self, *args):
        setSelectedDisplay(self.getPanelDisplayInfos())

    def getCurrentColor(self):
        value = self._colorSL_.value()
        if value != 0:
            color = QtGui.QColor(self.colorList[value])
            return [color.redF(), color.greenF(), color.blueF()]
        return 0

    def changeColor(self):
        color = self.getCurrentColor()
        setShapeColor(color)

    def changeColorCB(self, *args):
        index = self._colorCB_.currentIndex()
        self._colorSL_.setValue(index)
        self.changeColor()
        self.savePanelConfig()

    def changeColorSL(self, *args):
        index = self._colorSL_.value()
        self._colorCB_.setCurrentIndex(index)
        self.changeColor()
        self.savePanelConfig()

    def changeColorLW(self, *args):
        index = self._favoriteLW_.currentRow()
        self._colorCB_.setCurrentIndex(index)
        self.changeColor()

    def changeHierarchy(self, *args):
        state = self._hierarchyBelowRB_.isChecked()
        groupState = self._groupCB_.isChecked()
        self._twistControllerCB_.setEnabled(state and groupState)
        if not state:
            self._twistControllerCB_.setChecked(state)
        self._reductionDSB_.setEnabled(state)
        self._reductionSL_.setEnabled(state)
        self.savePanelConfig()

    def changeGroupEnabled(self, *args):
        value = self._groupCB_.isChecked()
        self._groupLE_.setEnabled(value)
        self._twistControllerCB_.setEnabled(value and self._hierarchyBelowRB_.isChecked())
        self.savePanelConfig()

    def getConfigInfos(self):
        if self._directionxRB_.isChecked():
            direction = 'x'
        if self._directionyRB_.isChecked():
            direction = 'y'
        if self._directionzRB_.isChecked():
            direction = 'z'

        if self._controlNoneRB_.isChecked():
            control = 'none'
        if self._controlParentRB_.isChecked():
            control = 'parent'
        if self._controlConstraintRB_.isChecked():
            control = 'constraint'
        if self._controlConnectRB_.isChecked():
            control = 'connect'

        if self._hierarchySelectRB_.isChecked():
            hierarchy = 'selected'
        if self._hierarchyBelowRB_.isChecked():
            hierarchy = 'below'

        tmps = self._nameLE_.text().split('#')
        self.__configInfos = {'prefix': tmps[0],
                              'postfix': tmps[-1],
                              'groups': self._groupLE_.text().split(','),
                              'groupEnable': self._groupCB_.isChecked(),
                              'direction': direction,
                              'control': control,
                              'hierarchy': hierarchy,
                              'controlT': self._controlTranslateCB_.isChecked(),
                              'controlR': self._controlRotateCB_.isChecked(),
                              'controlS': self._controlScaleCB_.isChecked(),
                              'size': self._controllerSizeDSB_.value(),
                              'reduction': self._reductionDSB_.value(),
                              'center': self._centerControllerCB_.isChecked(),
                              'colorAttr': self._addColorAttrCB_.isChecked(),
                              'twist': self._twistControllerCB_.isChecked(),
                              'color': self.getCurrentColor()}

    def createController(self, index):
        self.getConfigInfos()
        displayInfos = self.getPanelDisplayInfos()
        channelInfos = self.getChannelInfos()

        sels = cmds.ls(sl=1)
        if not sels:
            controller = Controller('', **self.__configInfos)
            controller.create(index)
            controller.setDisplay(**displayInfos)
            controller.setChannel(channelInfos)
        for sel in sels:
            controller = Controller(sel, **self.__configInfos)
            controller.create(index)
            controller.setDisplay(**displayInfos)
            controller.setChannel(channelInfos)

    def create(self, item):
        index = item.data(100)
        self.getConfigInfos()
        self.createController(index - 1)

    def switchColorPanelVis(self, *args):
        state = False
        if self._showColorCB_.isChecked():
            state = True
        self._colorGB_.setVisible(state)
        self.setConfig('colorPanelVis', state)
        self.saveConfig()

    def switchConfigPanelVis(self, *args):
        state = False
        if self._showConfigCB_.isChecked():
            state = True
        self._nameGB_.setVisible(state)
        self.setConfig('configPanelVis', state)
        self.saveConfig()

    def switchAttributePanelVis(self, *args):
        state = False
        if self._showAttributeCB_.isChecked():
            state = True
        self._transformGB_.setVisible(state)
        self._displayGB_.setVisible(state)
        self.setConfig('attributePanelVis', state)
        self.saveConfig()

    def savePanelConfig(self, *args):
        if self.__started:
            self.setConfig('color', self._colorSL_.value())
            self.setConfig('controlName', self._nameLE_.text())
            self.setConfig('groupSuffix', self._groupLE_.text())
            self.setConfig('groupEnabled', self._groupCB_.isChecked())
            self.setConfig('controlDirection', self._directionBG_.checkedId())
            self.setConfig('controlType', self._controlTypeBG_.checkedId())
            self.setConfig('controlTranslate', self._controlTranslateCB_.isChecked())
            self.setConfig('controlRotate', self._controlRotateCB_.isChecked())
            self.setConfig('controlScale', self._controlScaleCB_.isChecked())
            self.setConfig('hierarchy', self._hierarchyBG_.checkedId())
            self.setConfig('controllerSize', self._controllerSizeDSB_.value())
            self.setConfig('reduction', self._reductionDSB_.value())
            self.setConfig('centerController', self._centerControllerCB_.isChecked())
            self.setConfig('twistController', self._twistControllerCB_.isChecked())
            self.saveConfig()

    def getConfig(self, item, value=''):
        return self.userWidgetConfig.get(item, value)

    def setConfig(self, item, value):
        self.userWidgetConfig.set(item, value)

    def saveConfig(self):
        self.userWidgetConfig.save()


class Curve(object):
    def __init__(self, **kwargs):
        self.__name = kwargs.get('name', kwargs.get('n', 'curve'))
        self.__shape = None
        self.__degree = kwargs.get('degree', kwargs.get('d', 1))
        self.__knots = kwargs.get('knots', kwargs.get('k', []))
        self.__form = kwargs.get('form', kwargs.get('f', 0))
        self.__spans = kwargs.get('spans', kwargs.get('sp', 0))
        self.__points = kwargs.get('points', kwargs.get('p', []))
        self.color = kwargs.get('color', kwargs.get('c', 0))
        self.translate = kwargs.get('translate', kwargs.get('t', [0.0, 0.0, 0.0]))
        self.rotate = kwargs.get('rotate', kwargs.get('r', [0.0, 0.0, 0.0]))
        self.scale = kwargs.get('scale', kwargs.get('s', [1.0, 1.0, 1.0]))

    def __repr__(self):
        return self.name

    @property
    def degree(self):
        return self.__degree

    @property
    def knots(self):
        return self.__knots

    @property
    def form(self):
        return self.__form

    @property
    def spans(self):
        return self.__spans

    @property
    def points(self):
        return self.getTransformPoints(self.translate, self.rotate, self.scale)

    @property
    def basePoints(self):
        return self.__points

    @property
    def isExists(self):
        if cmds.objExists(self.name):
            shapes = cmds.listRelatives(self.name, s=1, f=1)
            for shape in shapes:
                if cmds.nodeType(shape) == 'nurbsCurve':
                    self.__shape = shape
                    return True
        return False

    @property
    def name(self):
        return self.__name

    @property
    def shape(self):
        return self.__shape

    @property
    def multiplier(self):
        return {'x': [-1, 1, 1],
                'y': [1, -1, 1],
                'z': [1, 1, -1]}

    def getTransformPoints(self, t=[0.0, 0.0, 0.0], r=[0.0, 0.0, 0.0], s=[1.0, 1.0, 1.0]):
        # 获取变换后的点信息
        transformPoints = []
        if t == [0.0, 0.0, 0.0] and r == [0.0, 0.0, 0.0] and s == [1.0, 1.0, 1.0]:
            transformPoints = self.basePoints
        else:
            matr = matrix.Matrix.compose(t, r, s)
            for point in self.basePoints:
                pnt = matrix.Point(*point) * matr
                transformPoints.append([pnt.x, pnt.y, pnt.z])
        return transformPoints

    def getInfos(self):
        # 获取曲线信息
        if self.isExists:
            curveInfo = cmds.createNode('curveInfo')
            cmds.connectAttr('%s.worldSpace' % self.shape, '%s.inputCurve' % curveInfo, f=1)
            self.__knots = cmds.getAttr('%s.knots[*]' % curveInfo)
            self.__form = cmds.getAttr('%s.form' % self.shape)
            self.__spans = cmds.getAttr('%s.spans' % self.shape)
            self.__degree = cmds.getAttr('%s.degree' % self.shape)
            if self.__form == 2:
                cvNum = self.__spans
            else:
                cvNum = self.__spans + self.__degree
            self.__points = [cmds.xform('%s.cv[%d]' % (self.shape, i), q=1, ws=1, t=1) for i in range(cvNum)]
            cmds.delete(curveInfo)

    def create(self):
        curve = cmds.curve(d=self.degree, k=self.knots, p=self.points)
        self.setName(curve)
        self.setColor(self.color)

    def setColor(self, color):
        if self.isExists:
            setColor(self.shape, color)

    def setName(self, curve):
        if cmds.objExists(curve):
            newName = self.getUniqueName(self.__name)
            self.__name = cmds.rename(curve, newName)
            shapeName = '%sShape' % self.name
            shapes = cmds.listRelatives(self.name, s=1, typ='nurbsCurve')
            if shapes:
                if shapeName not in shapes:
                    self.__shape = cmds.rename(shapes[0], shapeName)

    def rename(self, name):
        if self.isExists:
            newName = self.getUniqueName(name)
            self.__name = cmds.rename(self.name, newName)
            shapeName = '%sShape' % self.name
            shapes = cmds.listRelatives(self.name, s=1, typ='nurbsCurve')
            if shapes:
                if shapeName not in shapes:
                    self.__shape = cmds.rename(shapes[0], shapeName)

    def getUniqueName(self, name):
        newName = name
        i = 1
        while cmds.objExists(newName):
            newName = '%s%d' % (self.__name, i)
            i += 1
        return newName

    def getReversePoints(self, axis='x'):
        # 获取反转后的点信息
        points = []
        multiplier = self.multiplier.get(axis.lower(), None)
        if multiplier and self.isExists:
            for i in range(len(self.points)):
                points.append([self.points[i][x] * multiplier[x] for x in range(3)])
        return points

    def setPoints(self, points):
        if len(self.points) == len(points):
            self.__points = points
            return True
        return False

    def setPointToCurve(self, points=None):
        points = points or self.points
        for i in range(len(points)):
            cmds.xform('%s.cv[%d]' % (self.shape, i), ws=1, t=points[i])

    def reverse(self, axis='x'):
        # 反转曲线
        points = self.getReversePoints(axis)
        if points:
            self.__points = points
            self.setPointToCurve()

    def mirror(self, target, axis='x'):
        # 镜像曲线
        tarCrv = Curve(n=target)
        if tarCrv.isExists:
            tarCrv.getInfos()
            points = self.getReversePoints(axis)
            if tarCrv.setPoints(points):
                tarCrv.setPointToCurve()

    def parent(self, obj):
        if cmds.objExists(obj) and self.isExists:
            if obj not in cmds.listRelatives(obj, f=False, c=True):
                cmds.parent(self.name, obj)

    def lockAttrs(self, attrs):
        if self.isExists:
            for attr in attrs:
                cmds.setAttr('%s.%s' % (self.name, attr), e=1, l=1, k=0, cb=0)

    def setCurveDisplay(self, mode, state):
        attr = {'handle': 'displayHandle',
                'axis': 'displayLocalAxis',
                'rotatePivot': 'displayRotatePivot',
                'scalePivot': 'displayScalePivot',
                'playback': 'hideOnPlayback',
                'outliner': 'hiddenInOutliner'}.get(mode)
        if self.isExists and attr:
            cmds.setAttr('%s.%s' % (self.name, attr), state)
            if mode == 'reference':
                cmds.setAttr('%s.overrideDisplayType' % self.name, 2 if state else 0)

    def setHandleVis(self, state=False):
        self.setCurveDisplay('handle', state)

    def setAxisVis(self, state=False):
        self.setCurveDisplay('axis', state)

    def setRotatePivot(self, state=False):
        self.setCurveDisplay('rotatePivot', state)

    def setScalePivot(self, state=False):
        self.setCurveDisplay('scalePivot', state)

    def setPlaybackDisplay(self, state=True):
        self.setCurveDisplay('playback', state)

    def setOutlinerDisplay(self, state=False):
        self.setCurveDisplay('outliner', state)

    def setShapeDisplay(self, mode, state):
        attr = {'cv': 'dispCV',
                'ep': 'dispEP',
                'hull': 'dispHull',
                'geometry': 'dispGeometry',
                'template': 'template',
                'reference': 'overrideEnabled'}.get(mode)
        if self.isExists and attr:
            if mode != 'reference':
                cmds.setAttr('%s.%s' % (self.shape, attr), state)
            else:
                cmds.setAttr('%s.%s' % (self.shape, attr), True)
                cmds.setAttr('%s.overrideDisplayType' % self.shape, 2 if state else 0)

    def setCvVis(self, state=False):
        self.setShapeDisplay('cv', state)

    def setEpVis(self, state=False):
        self.setShapeDisplay('ep', state)

    def setHullVis(self, state=False):
        self.setShapeDisplay('hull', state)

    def setGeometryVis(self, state=False):
        self.setShapeDisplay('geometry', state)

    def setTemplateDisplay(self, state=False):
        self.setShapeDisplay('template', state)

    def setReferenceDisplay(self, state=False):
        self.setShapeDisplay('reference', state)

    def setDisplay(self, **kwargs):
        curveDisplay = {'handle': kwargs.get('handle', kwargs.get('h', False)),
                        'axis': kwargs.get('axis', kwargs.get('a', False)),
                        'rotatePivot': kwargs.get('rotatePivot', kwargs.get('rp', False)),
                        'scalePivot': kwargs.get('scalePivot', kwargs.get('sp', False)),
                        'playback': kwargs.get('playback', kwargs.get('p', True)),
                        'outliner': kwargs.get('outliner', kwargs.get('o', False))
                        }
        shapeDisplay = {'cv': kwargs.get('cv', False),
                        'ep': kwargs.get('ep', False),
                        'hull': kwargs.get('hull', False),
                        'geometry': kwargs.get('geometry', kwargs.get('g', True)),
                        'template': kwargs.get('template', kwargs.get('t', False)),
                        'reference': kwargs.get('reference', kwargs.get('r', False))
                        }
        for key, value in curveDisplay.iteritems():
            self.setCurveDisplay(key, value)
        for key, value in shapeDisplay.iteritems():
            self.setShapeDisplay(key, value)

    def setChannel(self, infos):
        setChannelAttrs(self.name, infos)


class Controller(object):
    def __init__(self, obj, **kwargs):
        self.__kwargs = kwargs
        self.__name = obj
        self.__size = kwargs.get('size', kwargs.get('siz', 1.05))
        self.__groups = kwargs.get('groups', kwargs.get('g', []))
        self.__groupEnable = kwargs.get('groupEnable', kwargs.get('ge', False))
        self.__hierarchy = kwargs.get('hierarchy', kwargs.get('h', 'selected'))
        self.__reduction = kwargs.get('reduction', kwargs.get('red', 0))
        self.__prefix = kwargs.get('prefix', kwargs.get('pre', ''))
        self.__postfix = kwargs.get('postfix', kwargs.get('post', 'Ctr'))
        self.__color = kwargs.get('color', kwargs.get('c', 0))
        self.__direction = kwargs.get('direction', kwargs.get('d', 'y')).lower()
        self.__parent = kwargs.get('parent', kwargs.get('p', None))
        self.__sign = kwargs.get('sign', False)
        self.__control = kwargs.get('control', kwargs.get('con', 'parent'))
        self.__controlT = kwargs.get('controlTranslate', kwargs.get('ct', True))
        self.__controlR = kwargs.get('controlRotate', kwargs.get('cr', True))
        self.__controlS = kwargs.get('controlScale', kwargs.get('cs', True))
        self.__center = kwargs.get('center', kwargs.get('cen', False))
        self.__centerIndex = kwargs.get('centerIndex', kwargs.get('ci', 29))
        self.__centerColor = kwargs.get('centerColor', kwargs.get('cc', self.__color))
        self.__twist = kwargs.get('twist', kwargs.get('ts', False))
        self.__twistIndex = kwargs.get('twistIndex', kwargs.get('ti', 20))
        self.__twistColor = kwargs.get('twistColor', kwargs.get('tc', self.__color))

        self.__curveConfigInfos = []
        self.__curve = None
        self.objectExists = False
        self.objectCenter = [0, 0, 0]
        self.objectTranslate = [0, 0, 0]
        self.objectRotate = [0, 0, 0]
        self.objectScale = [1, 1, 1]
        self.objectHierarchy = []
        self.groups = []
        self.topNode = None
        self.centerCurve = None
        self.twistCurve = None
        self.getTransformInfos()

    @property
    def curveConfigPath(self):
        configPath = '%s/ControllerCreator.json' % getPath.getPipelineToolkitPath('config')
        if os.path.isfile(configPath):
            return configPath
        return None

    @property
    def curveConfigInfos(self):
        if not self.__curveConfigInfos:
            if self.curveConfigPath:
                with open(self.curveConfigPath, 'r') as f:
                    self.__curveConfigInfos = json.load(f)
        return self.__curveConfigInfos

    @property
    def curve(self):
        return self.__curve

    def getTransformInfos(self):
        if cmds.objExists(self.__name):
            self.objectExists = True
            self.objectHierarchy = getChildren(self.__name)
        else:
            self.objectExists = False
            self.objectHierarchy = []

        infos = getTransformInfos(self.__name)
        self.objectCenter = infos.get('center')
        self.objectTranslate = infos.get('translate')
        self.objectRotate = infos.get('rotate')
        self.objectScale = infos.get('size')

    def getControllerName(self, mode=0):
        # 获取控制器名称
        """
        :mode mode: 0
        :return: 基础控制器名称
        :mode mode: 1
        :return: 重心控制器名称
         :mode mode: 0
        :return: 扭曲控制器名称
        """
        name = ''
        items = [self.__prefix, self.__name, self.__postfix]
        if mode == 1:
            items = [self.__prefix, self.__name, 'Center', self.__postfix]
        if mode == 2:
            items = [self.__prefix, self.__name, 'Twist', self.__postfix]

        for item in items:
            if self.__sign:
                if name:
                    name += '_%s' % item
                else:
                    name += item
            else:
                name += item
        return name

    def getCreateInfos(self, index):
        # 获取创建信息
        infos = {}
        if index < len(self.curveConfigInfos):
            infos = self.curveConfigInfos[index]
            infos['name'] = self.getControllerName()
            infos['color'] = self.__color
            infos['scale'] = [x * self.__size * 0.5 for x in self.objectScale]
            if self.__direction == 'x':
                infos['rotate'] = [0.0, 0.0, 90.0]
            if self.__direction == 'z':
                infos['rotate'] = [90.0, 0.0, 0.0]
        return infos

    def create(self, index):
        # 创建曲线
        infos = self.getCreateInfos(index)
        if infos:
            self.__curve = Curve(**infos)
            self.curve.create()
            self.topNode = self.curve
            if self.__groupEnable:
                if self.__groups:
                    self.groups = groups.groups(self.curve, self.curve, self.__groups, [0, 0, 0], self.__sign)
                    self.topNode = self.groups[-1]
            if self.__parent:
                if cmds.objExists(self.__parent):
                    if self.topNode not in cmds.listRelatives(self.__parent, c=1):
                        cmds.parent(self.topNode, self.__parent)
            if self.__center:
                self.centerController()
                self.centerCurve.parent(self.curve)
                cmds.connectAttr('%s.t' % self.centerCurve, '%s.rotatePivot' % self.curve, f=1)
                cmds.connectAttr('%s.t' % self.centerCurve, '%s.scalePivot' % self.curve, f=1)
            if self.__twist:
                if not self.twistCurve:
                    self.twistController()
                    twistGrp = groups.groups(self.twistCurve, self.twistCurve, ['Tra', 'Oft'], [0, 0, 0], self.__sign)
                    cmds.parent(twistGrp[-1], self.curve)
                    reverseNode = cmds.createNode('multiplyDivide', n='%sRotReverseMD' % self.curve)
                    cmds.setAttr('%s.input1' % reverseNode, -1, -1, -1, type='double3')
                    cmds.connectAttr('%s.r' % self.twistCurve, '%s.input2' % reverseNode, f=1)
                    cmds.connectAttr('%s.output' % reverseNode, '%s.r' % twistGrp[-2], f=1)
                cmds.connectAttr('%s.r' % self.twistCurve, '%s.r' % self.groups[-2], f=1)
            if self.objectExists:
                cmds.xform(self.topNode, ws=1, t=self.objectCenter, ro=self.objectRotate)
                self.applyControl()
                if self.__hierarchy == 'below':
                    for item in self.objectHierarchy:
                        child = item.keys()[0]
                        kw = {k: v for k, v in self.__kwargs.iteritems()}
                        kw['size'] = self.__size * (1 - self.__reduction)
                        kw['parent'] = self.curve
                        newCurve = Controller(child, **kw)
                        newCurve.twistCurve = self.twistCurve
                        newCurve.objectHierarchy = item.get(child)
                        newCurve.create(index)

    def centerController(self):
        # 添加重心控制器
        infos = self.getCreateInfos(self.__centerIndex)
        infos['name'] = self.getControllerName(1)
        infos['color'] = self.__centerColor
        self.centerCurve = Curve(**infos)
        self.centerCurve.create()
        self.centerCurve.lockAttrs(['%s%s' % (x, y) for x in 'rs' for y in 'xyz'] + ['v'])

    def twistController(self):
        # 添加扭曲控制器
        infos = self.getCreateInfos(self.__twistIndex)
        infos['name'] = self.getControllerName(2)
        infos['rotate'] = [0, 0, 0]
        infos['color'] = self.__twistColor
        self.twistCurve = Curve(**infos)
        self.twistCurve.create()
        self.twistCurve.lockAttrs(['%s%s' % (x, y) for x in 'ts' for y in 'xyz'] + ['v'])

    def applyControl(self):
        if self.__control == 'parent':
            if self.__name not in cmds.listRelatives(self.curve, c=1):
                cmds.parent(self.__name, self.curve)
        if self.__control == 'constraint':
            if self.__controlS:
                cmds.scaleConstraint(self.curve, self.__name, w=1, mo=1)
            if self.__controlT and self.__controlR:
                cmds.parentConstraint(self.curve, self.__name, w=1, mo=1)
            elif self.__controlT:
                cmds.pointConstraint(self.curve, self.__name, w=1, mo=1)
            elif self.__controlR:
                cmds.orientConstraint(self.curve, self.__name, w=1, mo=1)

        if self.__control == 'connection':
            if self.__controlT:
                cmds.connectAttr('%s.t' % self.curve, '%s.t' % self.__name, f=1)
            if self.__controlR:
                cmds.connectAttr('%s.r' % self.curve, '%s.r' % self.__name, f=1)
            if self.__controlS:
                cmds.connectAttr('%s.s' % self.curve, '%s.s' % self.__name, f=1)

    def setDisplay(self, **kwargs):
        self.curve.setDisplay(**kwargs)

    def setChannel(self, infos):
        self.curve.setChannel(infos)


def setShapeColor(color):
    # 设置控制器颜色
    sels = cmds.ls(sl=1)
    if sels:
        for obj in sels:
            shapes = cmds.listRelatives(obj, s=1)
            if shapes:
                for shape in shapes:
                    setColor(shape, color)
            else:
                setColor(obj, color)
    return None


def setColor(obj, color=None):
    # 设置物体颜色显示
    if not color:
        cmds.setAttr('%s.ove' % obj, 0)
    else:
        cmds.setAttr('%s.ove' % obj, 1)
        if type(color) == int:
            cmds.setAttr('%s.overrideRGBColors' % obj, False)
            cmds.setAttr('%s.ovc' % obj, color - 1)
        else:
            cmds.setAttr('%s.overrideRGBColors' % obj, True)
            cmds.setAttr('%s.overrideColorRGB' % obj, *color, type='double3')
    return None


def getSelectedTransformAttrs():
    infos = {}
    objs = cmds.ls(sl=1)
    if objs:
        for attr in ['%s%s' % (x, y) for x in 'trs' for y in 'xyz'] + ['v']:
            infos[attr] = cmds.getAttr('%s.%s' % (objs[0], attr), l=True)
        infos['c'] = False
        for attr in cmds.listAttr(objs[0], ud=1) or []:
            value = cmds.getAttr('%s.%s' % (objs[0], attr), l=True)
            if value:
                infos['c'] = value
                break
    return infos


def setSelectedTransformAttrs(infos):
    objs = cmds.ls(sl=1)
    for obj in objs:
        setChannelAttrs(obj, infos)


def setChannelAttrs(obj, infos):
    for attr in ['%s%s' % (x, y) for x in 'trs' for y in 'xyz'] + ['v']:
        lock = infos.get(attr, False)
        cmds.setAttr('%s.%s' % (obj, attr), l=lock, k=not lock)
    lock = infos.get('c', False)
    for attr in cmds.listAttr(obj, ud=1) or []:
        cmds.setAttr('%s.%s' % (obj, attr), l=lock, k=not lock)


def getSelectedDisplay():
    infos = {}
    objs = cmds.ls(sl=1)
    if objs:
        infos = {'handle': cmds.getAttr('%s.displayHandle' % objs[0]),
                 'axis': cmds.getAttr('%s.displayLocalAxis' % objs[0]),
                 'rotatePivot': cmds.getAttr('%s.displayRotatePivot' % objs[0]),
                 'scalePivot': cmds.getAttr('%s.displayScalePivot' % objs[0]),
                 'hidePlayback': cmds.getAttr('%s.hideOnPlayback' % objs[0]),
                 'hideOutliner': cmds.getAttr('%s.hiddenInOutliner' % objs[0])}
        shapes = cmds.listRelatives(objs[0], s=1) or []
        for shape in shapes:
            infos['template'] = cmds.getAttr('%s.template' % shape)
            if cmds.getAttr('%s.overrideEnabled' % shape) and cmds.getAttr('%s.overrideDisplayType' % shape) == 2:
                infos['reference'] = True
            else:
                infos['reference'] = False
            if cmds.nodeType(shape) == 'nurbsCurve':
                infos['cv'] = cmds.getAttr('%s.dispCV' % shape)
                infos['ep'] = cmds.getAttr('%s.dispEP' % shape)
                infos['hull'] = cmds.getAttr('%s.dispHull' % shape)
                infos['geometry'] = cmds.getAttr('%s.dispGeometry' % shape)
                break
    return infos


def setSelectedDisplay(infos):
    objs = cmds.ls(sl=1)
    for obj in objs:
        for shape in cmds.listRelatives(obj, s=1) or []:
            if cmds.nodeType(shape) == 'nurbsCurve':
                cmds.setAttr('%s.dispCV' % shape, infos.get('cv'))
                cmds.setAttr('%s.dispEP' % shape, infos.get('ep'))
                cmds.setAttr('%s.dispHull' % shape, infos.get('hull'))
                cmds.setAttr('%s.dispGeometry' % shape, infos.get('geometry', True))
            cmds.setAttr('%s.template' % shape, infos.get('template'))
            if infos.get('reference'):
                cmds.setAttr('%s.overrideEnabled' % shape, True)
                cmds.setAttr('%s.overrideDisplayType' % shape, 2)
            else:
                cmds.setAttr('%s.overrideDisplayType' % shape, 0)
        cmds.setAttr('%s.displayHandle' % obj, infos.get('handle'))
        cmds.setAttr('%s.displayLocalAxis' % obj, infos.get('axis'))
        cmds.setAttr('%s.displayRotatePivot' % obj, infos.get('rotatePivot'))
        cmds.setAttr('%s.displayScalePivot' % obj, infos.get('scalePivot'))
        cmds.setAttr('%s.hideOnPlayback' % obj, infos.get('playback', False))
        cmds.setAttr('%s.hiddenInOutliner' % obj, infos.get('outliner', False))
    return None


def getTransformInfos(obj):
    # 获取指定物体的位置信息
    if cmds.objExists(obj):
        if cmds.nodeType(obj) == 'transform':
            bbs = cmds.xform(obj, q=1, bb=1)
            lenX = bbs[3] - bbs[0]
            lenY = bbs[4] - bbs[1]
            lenZ = bbs[5] - bbs[2]
            center = [bbs[0] + lenX * .5, bbs[1] + lenY * .5, bbs[2] + lenZ * .5]
            shapes = cmds.listRelatives(obj, s=1)
            if shapes:
                if cmds.nodeType(shapes[0]) == 'clusterHandle':
                    center = [center[0] - .25, center[1] - .25, center[2] - .25]
        else:
            center = cmds.xform(obj, q=1, ws=1, t=1)
            lenX, lenY, lenZ = 1, 1, 1
        infos = {'translate': cmds.xform(obj, q=1, ws=1, t=1),
                 'rotate': cmds.xform(obj, q=1, ws=1, ro=1),
                 'center': center,
                 'size': [lenX, lenY, lenZ]}
    else:
        infos = {'translate': [0, 0, 0],
                 'rotate': [0, 0, 0],
                 'center': [0, 0, 0],
                 'size': [1, 1, 1]}
    return infos


def getChildren(obj):
    infos = []
    children = cmds.listRelatives(obj, c=1) or []
    for child in children:
        if cmds.ls(child, typ='transform'):
            infos.append({child: getChildren(child)})
    return infos


def showInMaya():
    from python.core import mayaPyside
    return mayaPyside.showInMaya(MainWindow, n='ControllerManagerToolWindow', t=u'控制器管理器')


# ==========================================暂时无用==========================================
def catchImage(path):
    # 获取当前曲线拍屏截图
    base = cmds.lookThru(q=1)
    grid = cmds.grid(tgl=1, q=1)
    camera = cmds.camera(n='playblastCamera')
    cmds.setAttr('%s.t' % camera[0], 2.392, 2.785, 4.041, type='double3')
    cmds.setAttr('%s.r' % camera[0], -31.538, 30.2, 0, type='double3')
    cmds.lookThru(camera[0])
    cmds.grid(tgl=0)
    cmds.playblast(cf=path, fmt='image', wh=[32, 32], qlt=100, c='xpm', p=100, v=0, fr=1, orn=0)
    cmds.grid(tgl=grid)
    cmds.lookThru(base)
    cmds.delete(camera)


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec_())
