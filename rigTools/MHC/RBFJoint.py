# -*- coding: utf-8 -*-
import maya.cmds as cmds
import maya.OpenMayaUI as omui
import math
try:
    from PySide6 import QtWidgets, QtCore, QtGui
    from shiboken6 import wrapInstance
except ImportError:
    if cmds.about(batch=True):
        print("Error: 无法导入 PySide6 或 shiboken6。请确保在 Maya 2025 或支持的环境中运行。")
    else:
        cmds.error("无法导入 PySide6 或 shiboken6。请确保在 Maya 2025 或支持的环境中运行。")
    raise ImportError("缺少 PySide6/shiboken6 依赖项。")

def ensure_plugin_loaded(plugin_name):
    if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
        try:
            cmds.loadPlugin(plugin_name)
            if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
                raise RuntimeError("尝试加载插件失败")
        except Exception as e:
            raise RuntimeError("无法加载必需的插件 '{}': {}".format(plugin_name, e))
    return True

class RBFSystemController:
    ATTR_RADIUS = "rbfRadius"
    ATTR_SECTIONS = "rbfSections"
    ATTR_START_AXIS = "rbfStartAxis"
    ATTR_BASE_NAME = "rbfBaseName"
    ATTR_FOLLOW = "follow"
    PLACER_PREFIX = "RBF_Placer_"
    HELPER_PREFIX = "RBF_SecondaryHelper_"
    BLEND_MATRIX_PREFIX = "RBF_BlendMatrix_"

    @staticmethod
    def find_all_systems():
        return cmds.ls("{}*".format(RBFSystemController.PLACER_PREFIX), type='joint', long=True)

    @staticmethod
    def _get_sorted_secondary_joints(main_driver_joint):
        if not cmds.objExists(main_driver_joint):
            return []
        children = cmds.listRelatives(main_driver_joint, children=True, type='joint', fullPath=True) or []
        if not cmds.attributeQuery(RBFSystemController.ATTR_BASE_NAME, node=main_driver_joint, exists=True):
            return []
        base_name = cmds.getAttr("{}.{}".format(main_driver_joint, RBFSystemController.ATTR_BASE_NAME))
        prefix = "{}{}_".format(RBFSystemController.HELPER_PREFIX, base_name)
        valid = []
        for c in children:
            sn = c.split('|')[-1]
            if sn.startswith(prefix):
                try:
                    idx = int(sn[len(prefix):])
                    valid.append((idx, c))
                except ValueError:
                    pass
        valid.sort(key=lambda x: x[0])
        return [p for _, p in valid]

    @staticmethod
    def create_system(selected_joint, radius, sections, start_axis_index):
        ensure_plugin_loaded('matrixNodes')
        if not cmds.objExists(selected_joint):
            raise ValueError("选中骨骼不存在: {}".format(selected_joint))
        base_name = selected_joint.split('|')[-1].split(':')[-1]
        driver_name = "{}{}".format(RBFSystemController.PLACER_PREFIX, base_name)
        if cmds.objExists(driver_name):
            cmds.warning("系统已存在: {}".format(driver_name))
            return cmds.ls(driver_name, long=True)[0]
        parent_of_selected = cmds.listRelatives(selected_joint, parent=True, fullPath=True)
        if parent_of_selected:
            main_driver_joint = cmds.createNode('joint', n=driver_name, p=parent_of_selected[0])
        else:
            main_driver_joint = cmds.createNode('joint', n=driver_name)
        main_driver_joint = cmds.ls(main_driver_joint, long=True)[0]
        cmds.setAttr("{}.displayLocalAxis".format(main_driver_joint), True)
        cmds.addAttr(main_driver_joint, ln=RBFSystemController.ATTR_BASE_NAME, dt="string")
        cmds.setAttr("{}.{}".format(main_driver_joint, RBFSystemController.ATTR_BASE_NAME), base_name, type="string", lock=True)
        cmds.addAttr(main_driver_joint, ln=RBFSystemController.ATTR_RADIUS, nn="Radius", at='double', dv=radius, min=0.001, k=True)
        cmds.addAttr(main_driver_joint, ln=RBFSystemController.ATTR_SECTIONS, nn="Sections", at='long', dv=sections, min=1, k=True)
        cmds.addAttr(main_driver_joint, ln=RBFSystemController.ATTR_START_AXIS, nn="Start Axis", at='enum', en='Y:Z:', dv=start_axis_index, k=True)
        if not cmds.attributeQuery(RBFSystemController.ATTR_FOLLOW, node=main_driver_joint, exists=True):
            cmds.addAttr(main_driver_joint, ln=RBFSystemController.ATTR_FOLLOW, nn="Follow (Rotation)", at='double', dv=0.5, k=True)
        RBFSystemController._zero_trs(main_driver_joint)
        blend_matrix_node = cmds.createNode('blendMatrix', n="{}{}".format(RBFSystemController.BLEND_MATRIX_PREFIX, base_name))
        try:
            opm = cmds.getAttr("{}.offsetParentMatrix".format(selected_joint))
            opm_vals = opm[0] if isinstance(opm, (list, tuple)) and isinstance(opm[0], (list, tuple)) else opm
            cmds.setAttr("{}.inputMatrix".format(blend_matrix_node), *opm_vals, type="matrix")
        except Exception:
            pass
        cmds.connectAttr("{}.offsetParentMatrix".format(selected_joint), "{}.target[0].targetMatrix".format(blend_matrix_node), f=True)
        cmds.setAttr("{}.target[0].translateWeight".format(blend_matrix_node), 1.0)
        cmds.connectAttr("{}.{}".format(main_driver_joint, RBFSystemController.ATTR_FOLLOW), "{}.target[0].rotateWeight".format(blend_matrix_node), f=True)
        cmds.connectAttr("{}.outputMatrix".format(blend_matrix_node), "{}.offsetParentMatrix".format(main_driver_joint), f=True)
        RBFSystemController.update_placement(main_driver_joint)
        return main_driver_joint

    @staticmethod
    def delete_system(main_driver_joint):
        if main_driver_joint and cmds.objExists(main_driver_joint):
            conns = []
            if cmds.attributeQuery("offsetParentMatrix", node=main_driver_joint, exists=True):
                c = cmds.listConnections("{}.offsetParentMatrix".format(main_driver_joint), s=True, d=False) or []
                conns.extend(c)
            for n in list(set(conns)):
                if cmds.objExists(n) and n.startswith(RBFSystemController.BLEND_MATRIX_PREFIX):
                    try:
                        cmds.delete(n)
                    except Exception:
                        pass
            if cmds.objExists(main_driver_joint):
                try:
                    cmds.delete(main_driver_joint)
                except Exception:
                    pass

    @staticmethod
    def get_system_attributes(main_driver_joint):
        if not cmds.objExists(main_driver_joint):
            return None
        m = {RBFSystemController.ATTR_RADIUS: "radius",
             RBFSystemController.ATTR_SECTIONS: "sections",
             RBFSystemController.ATTR_START_AXIS: "start_axis",
             RBFSystemController.ATTR_FOLLOW: "follow"}
        out = {}
        for a, k in m.items():
            if cmds.attributeQuery(a, node=main_driver_joint, exists=True):
                try:
                    out[k] = cmds.getAttr("{}.{}".format(main_driver_joint, a))
                except Exception:
                    pass
        return out if out else None

    @staticmethod
    def update_placement(main_driver_joint):
        if not cmds.objExists(main_driver_joint):
            return
        attrs = RBFSystemController.get_system_attributes(main_driver_joint)
        if not attrs:
            return
        radius = attrs.get("radius", 1.0)
        target_sections = max(1, int(attrs.get("sections", 1)))
        start_axis_index = attrs.get("start_axis", 0)
        existing = RBFSystemController._get_sorted_secondary_joints(main_driver_joint)
        if target_sections > len(existing):
            if cmds.attributeQuery(RBFSystemController.ATTR_BASE_NAME, node=main_driver_joint, exists=True):
                base = cmds.getAttr("{}.{}".format(main_driver_joint, RBFSystemController.ATTR_BASE_NAME))
                prefix = "{}{}_".format(RBFSystemController.HELPER_PREFIX, base)
                for i in range(len(existing), target_sections):
                    jn = "{}{:02d}".format(prefix, i + 1)
                    nj = cmds.createNode('joint', n=jn, p=main_driver_joint,ss =1)
                    RBFSystemController._zero_trs(nj)
        elif target_sections < len(existing):
            cmds.delete(existing[target_sections:])
        existing = RBFSystemController._get_sorted_secondary_joints(main_driver_joint)
        ang = (2.0 * math.pi) / target_sections if target_sections > 0 else 0
        off = (math.pi / 2.0) if start_axis_index == 1 else 0.0
        for idx, j in enumerate(existing):
            if not cmds.objExists(j):
                continue
            a = (float(idx) * ang) + off
            posX = 0.0
            posY = radius * math.cos(a)
            posZ = radius * math.sin(a)
            try:
                cmds.setAttr("{}.translateX".format(j), posX)
                cmds.setAttr("{}.translateY".format(j), posY)
                cmds.setAttr("{}.translateZ".format(j), posZ)
            except Exception:
                pass

    @staticmethod
    def _zero_trs(node):
        for attr in ['translate', 'rotate']:
            for ax in 'XYZ':
                try:
                    if cmds.getAttr("{}.{}{}".format(node, attr, ax), settable=True):
                        cmds.setAttr("{}.{}{}".format(node, attr, ax), 0)
                except Exception:
                    pass
        for ax in 'XYZ':
            try:
                if cmds.getAttr("{}.scale{}".format(node, ax), settable=True):
                    cmds.setAttr("{}.scale{}".format(node, ax), 1)
            except Exception:
                pass
        if cmds.attributeQuery("jointOrientX", node=node, exists=True):
            for ax in 'XYZ':
                try:
                    if cmds.getAttr("{}.jointOrient{}".format(node, ax), settable=True):
                        cmds.setAttr("{}.jointOrient{}".format(node, ax), 0)
                except Exception:
                    pass

def maya_main_window():
    p = omui.MQtUtil.mainWindow()
    if p:
        return wrapInstance(int(p), QtWidgets.QWidget)
    return None

class RBFMasterUI_V9_5(QtWidgets.QDialog):
    ui_instance = None
    FILTER_TOKENS = ['All', '_L', '_M', '_R', 'Arm', 'Leg', 'Elbow', 'Hand']

    @classmethod
    def show_ui(cls):
        if cls.ui_instance:
            cls.ui_instance.close()
            cls.ui_instance.deleteLater()
        cls.ui_instance = cls(parent=maya_main_window())
        cls.ui_instance.show()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("RBF 骨骼驱动系统 V9.5 (Maya 2025)")
        self.setMinimumSize(400, 550)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Window)
        self._is_updating_ui = False
        self.setStyleSheet(self.get_style_sheet())
        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self.populate_system_list()

    def create_widgets(self):
        self.filter_combo = QtWidgets.QComboBox()
        self.filter_combo.addItems(self.FILTER_TOKENS)
        self.systems_list_widget = QtWidgets.QListWidget()
        self.systems_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.systems_list_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.create_system_btn = QtWidgets.QPushButton("➕ 基于当前选择创建系统")
        self.create_system_btn.setObjectName("executeButton")
        self.refresh_list_btn = QtWidgets.QPushButton("🔄 刷新列表")
        self.delete_all_btn = QtWidgets.QPushButton("🔥 删除全部系统")
        self.delete_all_btn.setObjectName("dangerButton")
        self.params_group = QtWidgets.QGroupBox("◆ 参数设置")
        self.params_group.setEnabled(False)
        self.radius_label = QtWidgets.QLabel("半径")
        self.radius_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.radius_slider.setRange(0, 200)
        self.radius_spinbox = QtWidgets.QDoubleSpinBox()
        self.radius_spinbox.setRange(0.0, 9999.0)
        self.radius_spinbox.setSingleStep(0.1)
        self.radius_spinbox.setDecimals(1)
        self.radius_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.quantity_label = QtWidgets.QLabel("数量")
        self.quantity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.quantity_slider.setRange(1, 8)
        self.quantity_spinbox = QtWidgets.QSpinBox()
        self.quantity_spinbox.setRange(1, 9999)
        self.quantity_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.axis_label = QtWidgets.QLabel("轴向")
        self.axis_combo = QtWidgets.QComboBox()
        self.axis_combo.addItems(["Y", "Z"])

    def create_layouts(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        top_btn_layout = QtWidgets.QGridLayout()
        top_btn_layout.addWidget(self.create_system_btn, 0, 0, 1, 2)
        top_btn_layout.addWidget(self.refresh_list_btn, 1, 0)
        top_btn_layout.addWidget(self.delete_all_btn, 1, 1)
        filter_layout = QtWidgets.QHBoxLayout()
        filter_layout.addWidget(QtWidgets.QLabel("筛选:"))
        filter_layout.addWidget(self.filter_combo)
        list_group = QtWidgets.QGroupBox("场景中的RBF系统")
        list_layout = QtWidgets.QVBoxLayout()
        list_layout.addLayout(filter_layout)
        list_layout.addWidget(self.systems_list_widget)
        list_group.setLayout(list_layout)
        params_layout = QtWidgets.QGridLayout()
        params_layout.addWidget(self.radius_label, 0, 0)
        params_layout.addWidget(self.radius_slider, 0, 1)
        params_layout.addWidget(self.radius_spinbox, 0, 2)
        params_layout.addWidget(self.quantity_label, 1, 0)
        params_layout.addWidget(self.quantity_slider, 1, 1)
        params_layout.addWidget(self.quantity_spinbox, 1, 2)
        params_layout.setColumnStretch(1, 1)
        params_layout.setColumnMinimumWidth(0, 40)
        params_layout.setColumnMinimumWidth(2, 50)
        self.params_group.setLayout(params_layout)
        axis_layout = QtWidgets.QHBoxLayout()
        axis_layout.addWidget(self.axis_label)
        axis_layout.addWidget(self.axis_combo, 1)
        main_layout.addLayout(top_btn_layout)
        main_layout.addWidget(list_group, 1)
        main_layout.addWidget(self.params_group)
        main_layout.addLayout(axis_layout)

    def create_connections(self):
        self.create_system_btn.clicked.connect(self._on_create_system)
        self.refresh_list_btn.clicked.connect(lambda: self.populate_system_list())
        self.delete_all_btn.clicked.connect(self._on_delete_all_systems)
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        self.systems_list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.systems_list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.systems_list_widget.selectionModel().selectionChanged.connect(self._on_system_selection_changed)
        self.radius_slider.valueChanged.connect(self._sync_radius_spinbox_from_slider)
        self.radius_spinbox.valueChanged.connect(self._sync_radius_slider_from_spinbox)
        self.quantity_slider.valueChanged.connect(self.quantity_spinbox.setValue)
        self.quantity_spinbox.valueChanged.connect(self._sync_quantity_slider_from_spinbox)
        self.radius_slider.valueChanged.connect(self._process_ui_update)
        self.quantity_slider.valueChanged.connect(self._process_ui_update)
        self.radius_slider.sliderPressed.connect(self._open_undo_chunk)
        self.radius_slider.sliderReleased.connect(self._close_undo_chunk)
        self.quantity_slider.sliderPressed.connect(self._open_undo_chunk)
        self.quantity_slider.sliderReleased.connect(self._close_undo_chunk)
        self.radius_spinbox.editingFinished.connect(self._process_ui_update_with_undo)
        self.quantity_spinbox.editingFinished.connect(self._process_ui_update_with_undo)
        self.axis_combo.currentIndexChanged.connect(self._process_ui_update_with_undo)

    def _open_undo_chunk(self):
        cmds.undoInfo(openChunk=True)

    def _close_undo_chunk(self):
        cmds.undoInfo(closeChunk=True)

    def _process_ui_update_with_undo(self):
        if self.sender() == self.axis_combo and self.axis_combo.currentIndex() == -1:
            return
        self._open_undo_chunk()
        try:
            self._process_ui_update()
        finally:
            self._close_undo_chunk()

    def _sync_radius_spinbox_from_slider(self, val):
        self.radius_spinbox.setValue(val / 10.0)

    def _sync_radius_slider_from_spinbox(self, val):
        v = int(val * 10)
        if v > self.radius_slider.maximum():
            self.radius_slider.setMaximum(v)
        self.radius_slider.setValue(v)

    def _sync_quantity_slider_from_spinbox(self, val):
        if val > self.quantity_slider.maximum():
            self.quantity_slider.setMaximum(val)
        self.quantity_slider.setValue(val)

    def _on_filter_changed(self, text):
        t = text.lower()
        for i in range(self.systems_list_widget.count()):
            it = self.systems_list_widget.item(i)
            vis = (t == 'all' or t in it.text().lower())
            it.setHidden(not vis)

    def _get_visible_items(self):
        return [self.systems_list_widget.item(i) for i in range(self.systems_list_widget.count()) if not self.systems_list_widget.item(i).isHidden()]

    def _delete_systems_by_items(self, items_to_delete, ctx):
        if not items_to_delete:
            cmds.warning("没有可删除的系统 ({})。".format(ctx))
            return
        r = QtWidgets.QMessageBox.warning(self, '确认删除', "您确定要删除 {} 个系统及其关联的矩阵节点吗？({})".format(len(items_to_delete), ctx), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Cancel)
        if r == QtWidgets.QMessageBox.Yes:
            self._open_undo_chunk()
            try:
                for it in items_to_delete:
                    RBFSystemController.delete_system(it.data(QtCore.Qt.UserRole))
            finally:
                self._close_undo_chunk()
            self.populate_system_list()

    def _on_delete_all_systems(self):
        all_items = [self.systems_list_widget.item(i) for i in range(self.systems_list_widget.count())]
        self._delete_systems_by_items(all_items, "场景中的全部")

    def populate_system_list(self, select_specific=None):
        self._is_updating_ui = True
        if select_specific:
            sel = set(select_specific)
        else:
            sel = {self.systems_list_widget.item(i).data(QtCore.Qt.UserRole) for i in range(self.systems_list_widget.count()) if self.systems_list_widget.item(i).isSelected()}
        self.systems_list_widget.clear()
        to_sel = []
        for p in RBFSystemController.find_all_systems():
            if not cmds.objExists(p):
                continue
            item = QtWidgets.QListWidgetItem(p.split('|')[-1])
            item.setData(QtCore.Qt.UserRole, p)
            self.systems_list_widget.addItem(item)
            if p in sel:
                to_sel.append(item)
        if to_sel:
            self.systems_list_widget.clearSelection()
            for it in to_sel:
                it.setSelected(True)
            self.systems_list_widget.scrollToItem(to_sel[0])
        self._is_updating_ui = False
        self._on_filter_changed(self.filter_combo.currentText())
        self._on_system_selection_changed()

    def _on_create_system(self):
        sel = cmds.ls(selection=True, type='transform', long=True)
        if not sel:
            cmds.warning("请先选择一个父对象（骨骼或控制器）。")
            return
        nd = None
        self._open_undo_chunk()
        try:
            nd = RBFSystemController.create_system(sel[0], 3.0, 4, 0)
        except Exception as e:
            cmds.warning("RBF系统创建失败，操作已撤销。错误: {}".format(e))
            cmds.undo()
            nd = None
        finally:
            self._close_undo_chunk()
        if nd:
            self.populate_system_list(select_specific=[nd])
            cmds.select(nd)

    def _on_item_double_clicked(self, item):
        p = item.data(QtCore.Qt.UserRole)
        if p and cmds.objExists(p):
            cmds.select(p, r=True)

    def _on_system_selection_changed(self):
        if self._is_updating_ui:
            return
        items = self.systems_list_widget.selectedItems()
        self.params_group.setEnabled(bool(items))
        if not items:
            self._is_updating_ui = True
            self.radius_spinbox.setSpecialValueText("")
            self.quantity_spinbox.setSpecialValueText("")
            self.axis_combo.setCurrentIndex(-1)
            self._is_updating_ui = False
            return
        self._is_updating_ui = True
        all_attrs = []
        for it in items:
            p = it.data(QtCore.Qt.UserRole)
            if p and cmds.objExists(p):
                a = RBFSystemController.get_system_attributes(p)
                if a:
                    all_attrs.append(a)
        if not all_attrs:
            self.params_group.setEnabled(False)
            self._is_updating_ui = False
            return
        radii = {a.get("radius") for a in all_attrs if a.get("radius") is not None}
        sections = {a.get("sections") for a in all_attrs if a.get("sections") is not None}
        axes = {a.get("start_axis") for a in all_attrs if a.get("start_axis") is not None}
        self._set_widget_state(self.radius_spinbox, self.radius_slider, radii)
        self._set_widget_state(self.quantity_spinbox, self.quantity_slider, sections)
        if len(axes) == 1:
            self.axis_combo.setCurrentIndex(list(axes)[0])
        else:
            self.axis_combo.setCurrentIndex(-1)
        self._is_updating_ui = False

    def _set_widget_state(self, spinbox, slider, values):
        spinbox.setSpecialValueText("")
        slider.setEnabled(True)
        if len(values) == 1:
            spinbox.setValue(list(values)[0])
        else:
            spinbox.setSpecialValueText("---")

    def _process_ui_update(self):
        if self._is_updating_ui:
            return
        s = self.sender()
        items = self.systems_list_widget.selectedItems()
        if not items:
            return
        attr, val = None, None
        if s in [self.radius_slider, self.radius_spinbox]:
            attr = RBFSystemController.ATTR_RADIUS
            val = self.radius_spinbox.value()
            if self.radius_spinbox.specialValueText():
                self.radius_spinbox.setSpecialValueText("")
        elif s in [self.quantity_slider, self.quantity_spinbox]:
            attr = RBFSystemController.ATTR_SECTIONS
            val = self.quantity_spinbox.value()
            if self.quantity_spinbox.specialValueText():
                self.quantity_spinbox.setSpecialValueText("")
        elif s == self.axis_combo and self.axis_combo.currentIndex() != -1:
            attr = RBFSystemController.ATTR_START_AXIS
            val = self.axis_combo.currentIndex()
        if attr is not None:
            for it in items:
                drv = it.data(QtCore.Qt.UserRole)
                if cmds.objExists(drv):
                    try:
                        cmds.setAttr("{}.{}".format(drv, attr), val)
                        RBFSystemController.update_placement(drv)
                    except Exception:
                        pass

    def _show_context_menu(self, position):
        menu = QtWidgets.QMenu()
        items = self.systems_list_widget.selectedItems()
        if items:
            menu.addAction("🗑️ 删除 {} 个选中项".format(len(items)), lambda: self._delete_systems_by_items(items, "选中项"))
        menu.addSeparator()
        tok = self.filter_combo.currentText()
        if tok != 'All':
            vis = self._get_visible_items()
            if vis:
                menu.addAction("🗑️ 删除 {} 个筛选项 ('{}')".format(len(vis), tok), lambda: self._delete_systems_by_items(vis, "筛选: '{}'".format(tok)))
        menu.addAction("🔥🔥 删除全部 {} 个系统".format(self.systems_list_widget.count()), self._on_delete_all_systems)
        menu.exec(self.systems_list_widget.mapToGlobal(position))

    def get_style_sheet(self):
        return """
        QDialog { background-color: #3c3c3c; color: #f0f0f0; }
        QGroupBox { font-size: 14px; font-weight: bold; color: #f0f0f0; border: 1px solid #555; border-radius: 8px; margin-top: 10px; padding: 15px 5px 5px 5px; }
        QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; left: 10px; }
        QLabel, QRadioButton { font-size: 12px; color: #cccccc; }
        QComboBox { background-color: #2b2b2b; border: 1px solid #555; border-radius: 3px; padding: 4px; }
        QListWidget { background-color: #2b2b2b; border: 1px solid #555; border-radius: 5px; font-size: 13px; outline: 0; }
        QListWidget::item:selected { background-color: #ff6666; color: #fff; }
        QPushButton { background-color: #555; color: #f0f0f0; border: 1px solid #666; border-radius: 5px; padding: 8px 12px; font-size: 13px; font-weight: bold; }
        QPushButton:hover { background-color: #6a6a6a; }
        QPushButton:pressed, QPushButton#executeButton:pressed, QPushButton#dangerButton:pressed { background-color: #4a4a4a; }
        QPushButton#executeButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #62b9ff, stop:1 #3a8dff); }
        QPushButton#dangerButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff7e7e, stop:1 #ff4d4d); }
        QDoubleSpinBox, QSpinBox { background-color: #3a3a3a; border: 1px solid #555; border-radius: 3px; padding: 4px; }
        QDoubleSpinBox[specialValueText="---"], QSpinBox[specialValueText="---"] { color: #888; font-style: italic; }
        QSlider::groove:horizontal { border: 1px solid #555; height: 4px; background: #2b2b2b; margin: 2px 0; border-radius: 2px; }
        QSlider::handle:horizontal { background: #ccc; border: 1px solid #bbb; width: 14px; height: 14px; margin: -6px 0; border-radius: 7px; }
        """

if __name__ == "__main__":
    try:
        ensure_plugin_loaded('matrixNodes')
    except RuntimeError as e:
        cmds.warning("启动时预加载插件失败: {}".format(e))
    RBFMasterUI_V9_5.show_ui()
