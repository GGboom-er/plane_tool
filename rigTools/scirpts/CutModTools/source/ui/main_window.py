# -*- coding: utf-8 -*-
"""
main_window.py — CutMod 工具主窗口

基于 PySide2/Qt 构建的用户界面，提供：
- 网格选择与预览
- 绑定模式选择（Matrix / Constraint）
- 权重阈值 / 排除骨骼配置
- 分析预览（各骨骼面分布）
- 执行 / 撤销 / 删除操作
"""

import maya.cmds as cmds
import maya.OpenMayaUI as omui
import logging
from functools import partial

try:
    from PySide2 import QtCore, QtWidgets, QtGui
    from shiboken2 import wrapInstance
except ImportError:
    from PySide6 import QtCore, QtWidgets, QtGui
    from shiboken6 import wrapInstance

from CutModTools.source.core.weight_analyzer import WeightAnalyzer
from CutModTools.source.core.mesh_cutter import MeshCutter, delete_cutmod
from CutModTools.source.core.binding import Binder
from CutModTools.source.core.snapshot import SnapshotManager

logger = logging.getLogger("CutMod")

WINDOW_TITLE = "CutMod — 模型切分工具 v1.2"
WINDOW_OBJECT = "cutModToolWindow"


def get_maya_main_window():
    """获取 Maya 主窗口指针"""
    main_window_ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)


class CutModWindow(QtWidgets.QDialog):
    """CutMod 工具主窗口"""

    _instance = None

    @classmethod
    def display(cls):
        """显示窗口（单例模式）"""
        if cls._instance is not None:
            try:
                cls._instance.close()
                cls._instance.deleteLater()
            except Exception:
                pass

        cls._instance = cls(parent=get_maya_main_window())
        cls._instance.show()
        return cls._instance

    def __init__(self, parent=None):
        super(CutModWindow, self).__init__(parent)

        self.setObjectName(WINDOW_OBJECT)
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumWidth(420)
        self.setMinimumHeight(560)
        self.setWindowFlags(
            self.windowFlags() | QtCore.Qt.Tool)

        # 状态
        self._meshes = []               # 多个目标网格
        self._mesh_face_maps = {}       # {mesh_name: face_map}
        self._all_cut_results = None
        self._snapshot_mgr = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        """构建界面布局"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # ========== 标题 ==========
        title = QtWidgets.QLabel("CutMod — 基于骨骼权重的模型切分工具")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title_font = title.font()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title.setFont(title_font)
        main_layout.addWidget(title)

        # ========== 1. 输入设置 ==========
        input_group = QtWidgets.QGroupBox("输入设置")
        input_layout = QtWidgets.QVBoxLayout(input_group)

        # 网格选择
        mesh_row = QtWidgets.QHBoxLayout()
        mesh_row.addWidget(QtWidgets.QLabel("目标网格："))
        self.mesh_field = QtWidgets.QLineEdit()
        self.mesh_field.setPlaceholderText("选择带蒙皮的网格对象...")
        self.mesh_field.setReadOnly(True)
        mesh_row.addWidget(self.mesh_field)
        self.load_sel_btn = QtWidgets.QPushButton("<<")
        self.load_sel_btn.setFixedWidth(32)
        self.load_sel_btn.setToolTip("从场景选择中加载")
        mesh_row.addWidget(self.load_sel_btn)
        input_layout.addLayout(mesh_row)

        # 绑定模式
        mode_row = QtWidgets.QHBoxLayout()
        mode_row.addWidget(QtWidgets.QLabel("绑定模式："))
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems([
            "矩阵绑定 (Matrix) — 推荐",
            "约束绑定 (Constraint) — 兼容"
        ])
        mode_row.addWidget(self.mode_combo)
        input_layout.addLayout(mode_row)

        # 面部排除骨骼
        exclude_row = QtWidgets.QHBoxLayout()
        exclude_row.addWidget(QtWidgets.QLabel("面部排除："))
        self.exclude_field = QtWidgets.QLineEdit()
        self.exclude_field.setText("Head_M")
        self.exclude_field.setToolTip(
            "该骨骼下所有子层级骨骼的面合并为一体，\n"
            "保留 skinCluster 蒙皮（保持表情变形）。\n"
            "留空则不排除任何区域。")
        exclude_row.addWidget(self.exclude_field)
        input_layout.addLayout(exclude_row)

        # 权重阈值
        threshold_row = QtWidgets.QHBoxLayout()
        threshold_row.addWidget(QtWidgets.QLabel("权重阈值："))
        self.threshold_spin = QtWidgets.QDoubleSpinBox()
        self.threshold_spin.setRange(0.0, 0.5)
        self.threshold_spin.setSingleStep(0.001)
        self.threshold_spin.setDecimals(4)
        self.threshold_spin.setValue(0.001)
        self.threshold_spin.setToolTip(
            "低于此值的骨骼影响将被忽略（默认 0.001）")
        threshold_row.addWidget(self.threshold_spin)
        threshold_row.addStretch()
        input_layout.addLayout(threshold_row)

        # 平滑参数行
        smooth_row = QtWidgets.QHBoxLayout()
        smooth_row.addWidget(QtWidgets.QLabel("边界平滑："))
        self.smooth_iter_spin = QtWidgets.QSpinBox()
        self.smooth_iter_spin.setRange(0, 20)
        self.smooth_iter_spin.setValue(3)
        self.smooth_iter_spin.setToolTip("平滑迭代次数（0=关闭）")
        smooth_row.addWidget(self.smooth_iter_spin)
        smooth_row.addWidget(QtWidgets.QLabel("容差："))
        self.smooth_tol_spin = QtWidgets.QDoubleSpinBox()
        self.smooth_tol_spin.setRange(0.0, 0.5)
        self.smooth_tol_spin.setSingleStep(0.01)
        self.smooth_tol_spin.setDecimals(2)
        self.smooth_tol_spin.setValue(0.15)
        self.smooth_tol_spin.setToolTip(
            "权重差低于此值时允许平滑翻转（默认 0.15）")
        smooth_row.addWidget(self.smooth_tol_spin)
        smooth_row.addStretch()
        input_layout.addLayout(smooth_row)

        # 复选框行
        cb_row = QtWidgets.QHBoxLayout()
        self.keep_original_cb = QtWidgets.QCheckBox("保留原始网格")
        self.keep_original_cb.setChecked(True)
        cb_row.addWidget(self.keep_original_cb)
        self.enable_cap_cb = QtWidgets.QCheckBox("自动封口")
        self.enable_cap_cb.setChecked(True)
        self.enable_cap_cb.setToolTip(
            "切分后自动封闭开放边缘，封口面分配 lambert1")
        cb_row.addWidget(self.enable_cap_cb)
        cb_row.addStretch()
        input_layout.addLayout(cb_row)

        main_layout.addWidget(input_group)

        # ========== 2. 分析预览 ==========
        preview_group = QtWidgets.QGroupBox("分析预览")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)

        self.analyze_btn = QtWidgets.QPushButton("分析权重")
        self.analyze_btn.setToolTip("分析所选网格的蒙皮权重分布")
        preview_layout.addWidget(self.analyze_btn)

        # 预览表格
        self.preview_table = QtWidgets.QTableWidget()
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(
            ["骨骼", "面数", "占比", "绑定"])
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        self.preview_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectRows)
        self.preview_table.setEditTriggers(
            QtWidgets.QAbstractItemView.NoEditTriggers)
        self.preview_table.setMinimumHeight(150)
        preview_layout.addWidget(self.preview_table)

        # 信息标签
        self.info_label = QtWidgets.QLabel("")
        self.info_label.setWordWrap(True)
        preview_layout.addWidget(self.info_label)

        main_layout.addWidget(preview_group)

        # ========== 3. 操作按钮 ==========
        action_group = QtWidgets.QGroupBox("操作")
        action_layout = QtWidgets.QVBoxLayout(action_group)

        btn_row1 = QtWidgets.QHBoxLayout()
        self.execute_btn = QtWidgets.QPushButton("执行切分")
        self.execute_btn.setEnabled(False)
        self.execute_btn.setMinimumHeight(36)
        self.execute_btn.setToolTip(
            "根据分析结果执行模型切分和绑定")
        execute_font = self.execute_btn.font()
        execute_font.setBold(True)
        self.execute_btn.setFont(execute_font)
        btn_row1.addWidget(self.execute_btn)
        action_layout.addLayout(btn_row1)

        btn_row2 = QtWidgets.QHBoxLayout()
        self.delete_btn = QtWidgets.QPushButton("删除 CutMod")
        self.delete_btn.setToolTip(
            "删除所有 CutMod 产生的节点，恢复原始状态")
        btn_row2.addWidget(self.delete_btn)

        self.undo_btn = QtWidgets.QPushButton("撤销")
        self.undo_btn.setToolTip("Maya 撤销（Ctrl+Z）")
        btn_row2.addWidget(self.undo_btn)
        action_layout.addLayout(btn_row2)

        main_layout.addWidget(action_group)

        # ========== 4. 日志 ==========
        log_group = QtWidgets.QGroupBox("日志")
        log_layout = QtWidgets.QVBoxLayout(log_group)
        self.log_text = QtWidgets.QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        log_layout.addWidget(self.log_text)
        main_layout.addWidget(log_group)

    def _connect_signals(self):
        """连接信号"""
        self.load_sel_btn.clicked.connect(self._on_load_selection)
        self.analyze_btn.clicked.connect(self._on_analyze)
        self.execute_btn.clicked.connect(self._on_execute)
        self.delete_btn.clicked.connect(self._on_delete)
        self.undo_btn.clicked.connect(self._on_undo)

    def _log(self, msg, level="info"):
        """写入日志面板"""
        color = {
            "info": "#CCCCCC",
            "warning": "#FFD700",
            "error": "#FF6B6B",
            "success": "#66FF66",
        }.get(level, "#CCCCCC")
        self.log_text.append(
            '<span style="color:{};">{}</span>'.format(color, msg))

    # ---- 事件处理 ----

    def _on_load_selection(self):
        """从场景选择加载网格（支持多选）"""
        sel = cmds.ls(sl=True, type="transform") or []
        if not sel:
            self._log("请先在场景中选择带蒙皮的网格", "warning")
            return

        from CutModTools.source.utils.maya_helpers import get_skin_cluster
        valid_meshes = []
        for mesh in sel:
            sc = get_skin_cluster(mesh)
            if sc:
                valid_meshes.append(mesh)
            else:
                self._log("'{}' 无 skinCluster，已跳过".format(mesh), "warning")

        if not valid_meshes:
            self._log("所选对象均无 skinCluster", "error")
            return

        self._meshes = valid_meshes
        self.mesh_field.setText(", ".join(valid_meshes))
        self._mesh_face_maps = {}
        self._all_cut_results = None
        self.execute_btn.setEnabled(False)
        self.preview_table.setRowCount(0)
        self._log("已加载 {} 个网格: {}".format(
            len(valid_meshes), ", ".join(valid_meshes)), "success")

    def _on_analyze(self):
        """执行权重分析（多网格）"""
        if not self._meshes:
            self._log("请先加载目标网格", "warning")
            return

        threshold = self.threshold_spin.value()
        exclude_root = self.exclude_field.text().strip() or None
        smooth_iters = self.smooth_iter_spin.value()
        smooth_tol = self.smooth_tol_spin.value()

        try:
            # 汇总所有网格的分析结果
            self._mesh_face_maps = {}
            merged_summary = {}  # {骨骼名: {face_count, is_sc}}

            for mesh in self._meshes:
                if not cmds.objExists(mesh):
                    self._log("网格 '{}' 不存在，跳过".format(mesh), "warning")
                    continue

                analyzer = WeightAnalyzer(
                    mesh, threshold=threshold,
                    exclude_hierarchy=exclude_root,
                    smooth_iterations=smooth_iters,
                    smooth_tolerance=smooth_tol)
                face_map = analyzer.analyze()
                self._mesh_face_maps[mesh] = face_map

                # 合并摘要
                for item in analyzer.get_summary():
                    jname = item["joint"]
                    if jname not in merged_summary:
                        merged_summary[jname] = {
                            "face_count": 0,
                            "is_skincluster": item.get("is_skincluster", False)
                        }
                    merged_summary[jname]["face_count"] += item["face_count"]

                self._log("  '{}' 分析完成 ({} 骨骼)".format(
                    mesh, len(face_map)))

            # 更新预览表格
            total_faces = sum(v["face_count"] for v in merged_summary.values())
            sorted_items = sorted(merged_summary.items(),
                                  key=lambda x: -x[1]["face_count"])

            self.preview_table.setRowCount(len(sorted_items))
            for i, (jname, data) in enumerate(sorted_items):
                self.preview_table.setItem(
                    i, 0, QtWidgets.QTableWidgetItem(jname))
                self.preview_table.setItem(
                    i, 1, QtWidgets.QTableWidgetItem(str(data["face_count"])))
                pct = (data["face_count"] / float(total_faces) * 100
                       ) if total_faces else 0
                self.preview_table.setItem(
                    i, 2, QtWidgets.QTableWidgetItem("{:.1f}%".format(pct)))

                bind_mode = "skinCluster" if data["is_skincluster"] else "矩阵/约束"
                self.preview_table.setItem(
                    i, 3, QtWidgets.QTableWidgetItem(bind_mode))

                if data["is_skincluster"]:
                    highlight = QtGui.QColor(80, 120, 180)
                    for col in range(4):
                        self.preview_table.item(i, col).setBackground(highlight)

            sc_count = sum(1 for v in merged_summary.values()
                          if v["is_skincluster"])
            info_text = "{} 个网格 — 共 {} 个面分配到 {} 个骨骼组".format(
                len(self._mesh_face_maps), total_faces, len(merged_summary))
            if sc_count:
                info_text += "（{} 个 skinCluster）".format(sc_count)
            self.info_label.setText(info_text)

            self.execute_btn.setEnabled(bool(self._mesh_face_maps))
            self._log("权重分析完成 — {} 个网格".format(
                len(self._mesh_face_maps)), "success")

        except Exception as e:
            self._log("分析失败: {}".format(e), "error")
            import traceback
            traceback.print_exc()

    def _on_execute(self):
        """执行切分和绑定（多网格）"""
        if not self._mesh_face_maps:
            self._log("请先执行权重分析", "warning")
            return

        total_bones = set()
        for fm in self._mesh_face_maps.values():
            total_bones.update(fm.keys())

        reply = QtWidgets.QMessageBox.question(
            self, "确认执行",
            "即将切分 {} 个网格 → {} 个骨骼组。\n"
            "同一骨骼的子网格将合并到同一 transform 组。\n"
            "此操作支持 Maya 撤销（Ctrl+Z）。\n\n"
            "是否继续？".format(
                len(self._mesh_face_maps), len(total_bones)),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.Yes)

        if reply != QtWidgets.QMessageBox.Yes:
            return

        mode = "matrix" if self.mode_combo.currentIndex() == 0 else "constraint"
        keep_original = self.keep_original_cb.isChecked()
        enable_cap = self.enable_cap_cb.isChecked()
        exclude_root = self.exclude_field.text().strip() or None

        cmds.undoInfo(openChunk=True, chunkName="CutMod_Execute")
        try:
            # 1. 拍快照
            self._log("正在保存属性快照...")
            self._snapshot_mgr = SnapshotManager()
            self._snapshot_mgr.capture_scene_state()

            # 2. 逐网格切分，收集所有 cut_results
            all_cut_results = []
            for mesh, face_map in self._mesh_face_maps.items():
                self._log("正在切分 '{}'...".format(mesh))
                cutter = MeshCutter(
                    mesh, face_map,
                    keep_original=keep_original,
                    enable_cap=enable_cap,
                    skincluster_joint=exclude_root)
                cut_results = cutter.execute()
                all_cut_results.extend(cut_results)

            self._all_cut_results = all_cut_results

            # 3. 统一绑定（所有网格的子网格按骨骼分组）
            self._log("正在分组绑定 ({} 模式)...".format(mode))
            binder = Binder(
                all_cut_results, mode=mode,
                source_meshes=list(self._mesh_face_maps.keys()))
            bind_results = binder.execute()

            # 4. 恢复快照
            self._log("正在检查属性保护...")
            change_log = self._snapshot_mgr.restore_protected_attrs()
            if change_log:
                for entry in change_log:
                    self._log("  已恢复: {}".format(entry), "warning")

            sc_count = sum(
                1 for r in bind_results if r.get("mode") == "skincluster")
            grp_count = len(bind_results) - sc_count
            self._log(
                "切分完成！ {} 个骨骼组 ({} 矩阵 + {} skinCluster)，"
                "共 {} 个子网格".format(
                    len(bind_results), grp_count, sc_count,
                    len(all_cut_results)),
                "success")

        except Exception as e:
            self._log("执行失败: {}".format(e), "error")
            import traceback
            traceback.print_exc()
        finally:
            cmds.undoInfo(closeChunk=True)

    def _on_delete(self):
        """删除所有 CutMod 数据"""
        reply = QtWidgets.QMessageBox.question(
            self, "确认删除",
            "将删除所有 CutMod 产生的子网格和节点。\n"
            "是否继续？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)

        if reply != QtWidgets.QMessageBox.Yes:
            return

        cmds.undoInfo(openChunk=True, chunkName="CutMod_Delete")
        try:
            delete_cutmod()
            self._cut_results = None
            self._log("CutMod 数据已清除", "success")
        except Exception as e:
            self._log("删除失败: {}".format(e), "error")
        finally:
            cmds.undoInfo(closeChunk=True)

    def _on_undo(self):
        """Maya 撤销"""
        cmds.undo()
        self._log("已执行撤销")
