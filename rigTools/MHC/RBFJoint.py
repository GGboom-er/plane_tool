#!/usr/bin/env python
# -*- coding: utf-8 -*-


"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: RBFJoint.py
@date: 2025/8/4 23:52
@desc: 
"""

import maya.cmds as cmds
import maya.OpenMayaUI as omui
from PySide6 import QtWidgets, QtCore, QtGui
from shiboken6 import wrapInstance
import math

class RBFSystemController:
    ATTR_RADIUS, ATTR_SECTIONS, ATTR_START_AXIS, ATTR_BASE_NAME = "rbfRadius", "rbfSections", "rbfStartAxis", "rbfBaseName"
    PLACER_PREFIX, HELPER_PREFIX = "RBF_Placer_", "RBF_SecondaryHelper_"

    @staticmethod
    def find_all_systems():
        return cmds.ls(f"{RBFSystemController.PLACER_PREFIX}*", type='joint')

    @staticmethod
    def _get_sorted_secondary_joints( main_driver_joint ):
        children = cmds.listRelatives(main_driver_joint, children=True, type='joint', fullPath=True) or []
        base_name = cmds.getAttr(f"{main_driver_joint}.{RBFSystemController.ATTR_BASE_NAME}");
        prefix = f"{RBFSystemController.HELPER_PREFIX}{base_name}_";
        valid_joints = []
        for child in children:
            short_name = child.split('|')[-1]
            if short_name.startswith(prefix):
                try:
                    valid_joints.append((int(short_name.split('_')[-1]), child))
                except (ValueError, IndexError):
                    cmds.warning(f"发现命名不规范的节点，已忽略: {short_name}")
        valid_joints.sort(key=lambda pair: pair[0]);
        return [joint_path for index, joint_path in valid_joints]

    @staticmethod
    def create_system( parent_joint, radius, sections, start_axis_index ):
        if not cmds.objExists(parent_joint): cmds.error(f"父骨骼 '{parent_joint}' 不存在。"); return None
        children = cmds.listRelatives(parent_joint, children=True, type='joint', fullPath=True) or []
        for child in children:
            if child.split('|')[-1].startswith(RBFSystemController.PLACER_PREFIX): cmds.warning(
                f"骨骼 '{parent_joint}' 下已存在RBF设置。"); cmds.select(child); return None
        base_name = parent_joint.split('|')[-1].split(':')[-1]
        main_driver_joint = cmds.createNode('joint', name=f"{RBFSystemController.PLACER_PREFIX}{base_name}",
                                            parent=parent_joint);
        main_driver_joint = cmds.ls(main_driver_joint, long=True)[0]
        cmds.addAttr(main_driver_joint, ln=RBFSystemController.ATTR_BASE_NAME, dt="string");
        cmds.setAttr(f"{main_driver_joint}.{RBFSystemController.ATTR_BASE_NAME}", base_name, type="string", lock=True)
        cmds.addAttr(main_driver_joint, ln=RBFSystemController.ATTR_RADIUS, nn="Radius", at='double', dv=radius,
                     min=0.001, k=True)
        cmds.addAttr(main_driver_joint, ln=RBFSystemController.ATTR_SECTIONS, nn="Sections", at='long', dv=sections,
                     min=1, k=True)
        cmds.addAttr(main_driver_joint, ln=RBFSystemController.ATTR_START_AXIS, nn="Start Axis", at='enum', en='Y:Z:',
                     dv=start_axis_index, k=True)
        RBFSystemController._reset_joint_transforms(main_driver_joint);
        RBFSystemController.update_placement(main_driver_joint);
        return main_driver_joint

    @staticmethod
    def delete_system( main_driver_joint ):
        if main_driver_joint and cmds.objExists(main_driver_joint): cmds.delete(main_driver_joint)

    @staticmethod
    def get_system_attributes( main_driver_joint ):
        if not cmds.objExists(main_driver_joint): return None
        return {"radius"    : cmds.getAttr(f"{main_driver_joint}.{RBFSystemController.ATTR_RADIUS}"),
                "sections"  : cmds.getAttr(f"{main_driver_joint}.{RBFSystemController.ATTR_SECTIONS}"),
                "start_axis": cmds.getAttr(f"{main_driver_joint}.{RBFSystemController.ATTR_START_AXIS}")}

    @staticmethod
    def update_placement( main_driver_joint ):
        if not cmds.objExists(main_driver_joint): return
        attrs = RBFSystemController.get_system_attributes(main_driver_joint)
        if not attrs: return
        radius, target_sections, start_axis_index = attrs["radius"], max(1, int(attrs["sections"])), attrs["start_axis"]
        existing_joints = RBFSystemController._get_sorted_secondary_joints(main_driver_joint)
        if target_sections > len(existing_joints):
            base_name = cmds.getAttr(f"{main_driver_joint}.{RBFSystemController.ATTR_BASE_NAME}");
            prefix = f"{RBFSystemController.HELPER_PREFIX}{base_name}_"
            for i in range(len(existing_joints), target_sections): RBFSystemController._reset_joint_transforms(
                cmds.createNode('joint', name=f"{prefix}{i + 1:02d}", parent=main_driver_joint))
        elif target_sections < len(existing_joints):
            cmds.delete(existing_joints[target_sections:])
        existing_joints = RBFSystemController._get_sorted_secondary_joints(main_driver_joint)
        angle_inc = (2.0 * math.pi) / target_sections if target_sections > 0 else 0;
        offset = (math.pi / 2.0) if start_axis_index == 1 else 0.0
        for index, joint_long_path in enumerate(existing_joints):
            if not cmds.objExists(joint_long_path): continue
            angle = (float(index) * angle_inc) + offset
            cmds.setAttr(f"{joint_long_path}.translateX", 0);
            cmds.setAttr(f"{joint_long_path}.translateY", radius * math.cos(angle));
            cmds.setAttr(f"{joint_long_path}.translateZ", radius * math.sin(angle))

    @staticmethod
    def _reset_joint_transforms( joint ):
        for attr in ['translate', 'rotate', 'jointOrient']:
            for axis in ['X', 'Y', 'Z']:
                try:
                    cmds.setAttr(f"{joint}.{attr}{axis}", 0)
                except:
                    pass
        for axis in ['X', 'Y', 'Z']:
            try:
                cmds.setAttr(f"{joint}.scale{axis}", 1)
            except:
                pass

def maya_main_window(): return wrapInstance(int(omui.MQtUtil.mainWindow()), QtWidgets.QWidget)


class RBFMasterUI_V9_2(QtWidgets.QDialog):
    ui_instance = None
    FILTER_TOKENS = ['All', '_L', '_M', '_R', 'Arm', 'Leg', 'Elbow', 'Hand']

    @staticmethod
    def show_ui():
        if RBFMasterUI_V9_2.ui_instance: RBFMasterUI_V9_2.ui_instance.close(); RBFMasterUI_V9_2.ui_instance.deleteLater()
        RBFMasterUI_V9_2.ui_instance = RBFMasterUI_V9_2(parent=maya_main_window())
        RBFMasterUI_V9_2.ui_instance.show()

    def __init__( self, parent=None ):
        super().__init__(parent)
        self.setWindowTitle("RBF 骨骼驱动系统 V9.2 (Maya 2025)");
        self.setMinimumSize(400, 550)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Window);
        self._is_updating_ui = False
        self.setStyleSheet(self.get_style_sheet());
        self.create_widgets();
        self.create_layouts();
        self.create_connections()
        self.populate_system_list()

    def create_widgets( self ):
        self.filter_combo = QtWidgets.QComboBox();
        self.filter_combo.addItems(self.FILTER_TOKENS)
        self.systems_list_widget = QtWidgets.QListWidget();
        self.systems_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.systems_list_widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.create_system_btn = QtWidgets.QPushButton("➕ 基于当前选择创建系统");
        self.create_system_btn.setObjectName("executeButton")
        self.refresh_list_btn = QtWidgets.QPushButton("🔄 刷新列表");
        self.delete_all_btn = QtWidgets.QPushButton("🔥 删除全部系统");
        self.delete_all_btn.setObjectName("dangerButton")
        self.params_group = QtWidgets.QGroupBox("◆ 参数设置");
        self.params_group.setEnabled(False)
        self.radius_label = QtWidgets.QLabel("半径");
        self.radius_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.radius_slider.setRange(0, 200);
        self.radius_spinbox = QtWidgets.QDoubleSpinBox()
        self.radius_spinbox.setRange(0.0, 9999.0);
        self.radius_spinbox.setSingleStep(0.1);
        self.radius_spinbox.setDecimals(1)
        self.radius_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.quantity_label = QtWidgets.QLabel("数量");
        self.quantity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.quantity_slider.setRange(1, 8);
        self.quantity_spinbox = QtWidgets.QSpinBox()
        self.quantity_spinbox.setRange(1, 9999);
        self.quantity_spinbox.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.axis_label = QtWidgets.QLabel("轴向");
        self.axis_combo = QtWidgets.QComboBox();
        self.axis_combo.addItems(["Y", "Z"])

    def create_layouts( self ):
        main_layout = QtWidgets.QVBoxLayout(self);
        top_btn_layout = QtWidgets.QGridLayout()
        top_btn_layout.addWidget(self.create_system_btn, 0, 0, 1, 2)
        top_btn_layout.addWidget(self.refresh_list_btn, 1, 0);
        top_btn_layout.addWidget(self.delete_all_btn, 1, 1)
        filter_layout = QtWidgets.QHBoxLayout();
        filter_layout.addWidget(QtWidgets.QLabel("筛选:"));
        filter_layout.addWidget(self.filter_combo)
        list_group = QtWidgets.QGroupBox("场景中的RBF系统");
        list_layout = QtWidgets.QVBoxLayout()
        list_layout.addLayout(filter_layout);
        list_layout.addWidget(self.systems_list_widget);
        list_group.setLayout(list_layout)
        params_layout = QtWidgets.QGridLayout()
        params_layout.addWidget(self.radius_label, 0, 0);
        params_layout.addWidget(self.radius_slider, 0, 1);
        params_layout.addWidget(self.radius_spinbox, 0, 2)
        params_layout.addWidget(self.quantity_label, 1, 0);
        params_layout.addWidget(self.quantity_slider, 1, 1);
        params_layout.addWidget(self.quantity_spinbox, 1, 2)
        params_layout.setColumnStretch(1, 1);
        params_layout.setColumnMinimumWidth(0, 40);
        params_layout.setColumnMinimumWidth(2, 50)
        self.params_group.setLayout(params_layout)
        axis_layout = QtWidgets.QHBoxLayout();
        axis_layout.addWidget(self.axis_label);
        axis_layout.addWidget(self.axis_combo, 1)
        main_layout.addLayout(top_btn_layout);
        main_layout.addWidget(list_group, 1);
        main_layout.addWidget(self.params_group);
        main_layout.addLayout(axis_layout)

    def create_connections( self ):
        self.create_system_btn.clicked.connect(self._on_create_system)
        self.refresh_list_btn.clicked.connect(self.populate_system_list)
        self.delete_all_btn.clicked.connect(self._on_delete_all_systems)
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)
        self.systems_list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)  # [NEW] 双击连接
        self.systems_list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.systems_list_widget.selectionModel().selectionChanged.connect(self._on_system_selection_changed)
        self.radius_slider.valueChanged.connect(self._sync_radius_spinbox_from_slider);
        self.radius_spinbox.valueChanged.connect(self._sync_radius_slider_from_spinbox)
        self.quantity_slider.valueChanged.connect(self.quantity_spinbox.setValue);
        self.quantity_spinbox.valueChanged.connect(self._sync_quantity_slider_from_spinbox)
        self.radius_slider.valueChanged.connect(self._process_ui_update);
        self.quantity_slider.valueChanged.connect(self._process_ui_update)
        self.radius_slider.sliderPressed.connect(self._open_undo_chunk);
        self.radius_slider.sliderReleased.connect(self._close_undo_chunk)
        self.quantity_slider.sliderPressed.connect(self._open_undo_chunk);
        self.quantity_slider.sliderReleased.connect(self._close_undo_chunk)
        self.radius_spinbox.editingFinished.connect(self._process_ui_update_with_undo);
        self.quantity_spinbox.editingFinished.connect(self._process_ui_update_with_undo)
        self.axis_combo.currentIndexChanged.connect(self._process_ui_update_with_undo)

    def _open_undo_chunk( self ):
        cmds.undoInfo(openChunk=True)

    def _close_undo_chunk( self ):
        cmds.undoInfo(closeChunk=True)

    def _process_ui_update_with_undo( self ):
        self._open_undo_chunk(); self._process_ui_update(); self._close_undo_chunk()

    def _sync_radius_spinbox_from_slider( self, val ):
        self.radius_spinbox.setValue(val / 10.0)

    def _sync_radius_slider_from_spinbox( self, val ):
        if val * 10 > self.radius_slider.maximum(): self.radius_slider.setMaximum(int(val * 10))
        self.radius_slider.setValue(int(val * 10))

    def _sync_quantity_slider_from_spinbox( self, val ):
        if val > self.quantity_slider.maximum(): self.quantity_slider.setMaximum(val)
        self.quantity_slider.setValue(val)

    def _on_filter_changed( self, text ):
        filter_text = text.lower()
        for i in range(self.systems_list_widget.count()):
            item = self.systems_list_widget.item(i);
            item_text = item.text().lower()
            item.setHidden(not (filter_text == 'all' or filter_text in item_text))

    def _get_visible_items( self ):
        return [self.systems_list_widget.item(i) for i in range(self.systems_list_widget.count()) if
                not self.systems_list_widget.item(i).isHidden()]

    def _delete_systems_by_items( self, items_to_delete, context_text ):
        if not items_to_delete: cmds.warning(f"没有可删除的系统 ({context_text})。"); return
        reply = QtWidgets.QMessageBox.critical(self, '严重警告',
                                               f"您确定要删除 {len(items_to_delete)} 个系统吗？({context_text})\n此操作将无法撤销！",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel,
                                               QtWidgets.QMessageBox.Cancel)
        if reply == QtWidgets.QMessageBox.Yes:
            self._open_undo_chunk();
            [RBFSystemController.delete_system(item.data(QtCore.Qt.UserRole)) for item in items_to_delete];
            self._close_undo_chunk();
            self.populate_system_list()

    def _on_delete_all_systems( self ):
        self._delete_systems_by_items(
            [self.systems_list_widget.item(i) for i in range(self.systems_list_widget.count())], "场景中的全部")

    def populate_system_list( self ):
        self._is_updating_ui = True
        selected_data = {item.data(QtCore.Qt.UserRole) for item in self.systems_list_widget.selectedItems()}
        self.systems_list_widget.clear();
        new_items_to_select = []
        for system in RBFSystemController.find_all_systems():
            item = QtWidgets.QListWidgetItem(system.split('|')[-1]);
            item.setData(QtCore.Qt.UserRole, system)
            self.systems_list_widget.addItem(item)
            if system in selected_data: new_items_to_select.append(item)
        for item in new_items_to_select: item.setSelected(True)
        self._is_updating_ui = False;
        self._on_filter_changed(self.filter_combo.currentText())
        if not self.systems_list_widget.selectedItems(): self._on_system_selection_changed()

    def _on_create_system( self ):
        selected = cmds.ls(selection=True, type='joint')
        if not selected: cmds.warning("请先选择一个父骨骼。"); return
        self._open_undo_chunk();
        new_driver = RBFSystemController.create_system(selected[0], 3.0, 4, 0);
        self._close_undo_chunk()
        if new_driver:
            self.systems_list_widget.clearSelection()
            new_item = QtWidgets.QListWidgetItem(new_driver.split('|')[-1]);
            new_item.setData(QtCore.Qt.UserRole, new_driver)
            self.systems_list_widget.addItem(new_item);
            new_item.setSelected(True);
            self.systems_list_widget.scrollToItem(new_item)
            self._on_system_selection_changed();
            cmds.select(new_driver)

    def _on_item_double_clicked( self, item ):
        """[NEW] 双击列表项时，在场景中选择对应的主骨骼。"""
        driver_joint = item.data(QtCore.Qt.UserRole)
        if driver_joint and cmds.objExists(driver_joint):
            cmds.select(driver_joint, replace=True)

    def _on_system_selection_changed( self ):
        if self._is_updating_ui: return
        selected_items = self.systems_list_widget.selectedItems()
        self.params_group.setEnabled(bool(selected_items))
        if not selected_items: return
        self._is_updating_ui = True
        all_attrs = [RBFSystemController.get_system_attributes(item.data(QtCore.Qt.UserRole)) for item in selected_items
                     if item.data(QtCore.Qt.UserRole) and cmds.objExists(item.data(QtCore.Qt.UserRole))]
        if not all_attrs: self.params_group.setEnabled(False); self._is_updating_ui = False; return
        radii = {attrs["radius"] for attrs in all_attrs};
        sections = {attrs["sections"] for attrs in all_attrs};
        axes = {attrs["start_axis"] for attrs in all_attrs}
        self._set_widget_state(self.radius_spinbox, self.radius_slider, radii)
        self._set_widget_state(self.quantity_spinbox, self.quantity_slider, sections)
        if len(axes) == 1:
            self.axis_combo.setCurrentIndex(list(axes)[0])
        else:
            self.axis_combo.setCurrentIndex(-1)
        self._is_updating_ui = False

    def _set_widget_state( self, spinbox, slider, values ):
        """[FIX] 不再禁用滑块，以允许用户通过拖动滑块来解决混合状态。"""
        spinbox.setSpecialValueText("");
        slider.setEnabled(True)
        if len(values) == 1:
            spinbox.setValue(list(values)[0])
        else:
            spinbox.setSpecialValueText("---")

    def _process_ui_update( self ):
        if self._is_updating_ui: return
        sender = self.sender();
        selected_items = self.systems_list_widget.selectedItems()
        if not selected_items: return

        attr_to_update, new_value = None, None
        if sender in [self.radius_slider, self.radius_spinbox]:
            attr_to_update, new_value = RBFSystemController.ATTR_RADIUS, self.radius_spinbox.value()
            if self.radius_spinbox.specialValueText(): self.radius_spinbox.setSpecialValueText("")
        elif sender in [self.quantity_slider, self.quantity_spinbox]:
            attr_to_update, new_value = RBFSystemController.ATTR_SECTIONS, self.quantity_spinbox.value()
            if self.quantity_spinbox.specialValueText(): self.quantity_spinbox.setSpecialValueText("")
        elif sender == self.axis_combo:
            attr_to_update, new_value = RBFSystemController.ATTR_START_AXIS, self.axis_combo.currentIndex()

        if attr_to_update is not None:
            for item in selected_items:
                driver = item.data(QtCore.Qt.UserRole)
                if cmds.objExists(driver):
                    cmds.setAttr(f"{driver}.{attr_to_update}", new_value)
                    RBFSystemController.update_placement(driver)

    def _show_context_menu( self, position ):
        menu = QtWidgets.QMenu();
        selected_items = self.systems_list_widget.selectedItems()
        if selected_items: menu.addAction(f"🗑️ 删除 {len(selected_items)} 个选中项",
                                          lambda: self._delete_systems_by_items(selected_items, "选中项"))
        menu.addSeparator()
        filter_token = self.filter_combo.currentText()
        if filter_token != 'All':
            visible_items = self._get_visible_items()
            if visible_items: menu.addAction(f"🗑️ 删除 {len(visible_items)} 个筛选项 ('{filter_token}')",
                                             lambda: self._delete_systems_by_items(visible_items,
                                                                                   f"筛选: '{filter_token}'"))
        menu.addAction(f"🔥🔥 删除全部 {self.systems_list_widget.count()} 个系统", self._on_delete_all_systems)
        menu.exec(self.systems_list_widget.mapToGlobal(position))

    def get_style_sheet( self ):
        return """
        QDialog{background-color:#3c3c3c;color:#f0f0f0} QGroupBox{font-size:14px;font-weight:bold;color:#f0f0f0;border:1px solid #555;border-radius:8px;margin-top:10px;padding:15px 5px 5px 5px}
        QGroupBox::title{subcontrol-origin:margin;subcontrol-position:top left;padding:0 5px;left:10px} QLabel, QRadioButton{font-size:12px;color:#cccccc}
        QComboBox{background-color:#2b2b2b;border:1px solid #555;border-radius:3px;padding:4px}
        QListWidget{background-color:#2b2b2b;border:1px solid #555;border-radius:5px;font-size:13px;outline:0} QListWidget::item:selected{background-color:#ff6666;color:#fff}
        QPushButton{background-color:#555;color:#f0f0f0;border:1px solid #666;border-radius:5px;padding:8px 12px;font-size:13px;font-weight:bold}
        QPushButton:hover{background-color:#6a6a6a}
        QPushButton:pressed, QPushButton#executeButton:pressed, QPushButton#dangerButton:pressed {background-color:#4a4a4a}
        QPushButton#executeButton{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #62b9ff,stop:1 #3a8dff)}
        QPushButton#dangerButton{background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ff7e7e,stop:1 #ff4d4d)}
        QDoubleSpinBox,QSpinBox{background-color:#3a3a3a;border:1px solid #555;border-radius:3px;padding:4px} QDoubleSpinBox[specialValueText="---"],QSpinBox[specialValueText="---"]{color:#888;font-style:italic}
        QSlider::groove:horizontal{border:1px solid #555;height:4px;background:#2b2b2b;margin:2px 0;border-radius:2px} QSlider::handle:horizontal{background:#ccc;border:1px solid #bbb;width:14px;height:14px;margin:-6px 0;border-radius:7px}
        """


# --- 启动脚本 ---
if __name__ == "__main__":
    RBFMasterUI_V9_2.show_ui()