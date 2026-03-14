#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: copySkin.py
@date: 2026/3/12 14:29
@desc: 
"""
import maya.cmds as cmds
from PySide6 import QtWidgets, QtCore
from maya.app.general.mayaMixin import MayaQWidgetDockableMixin


class SmartTianGridWeightTool(MayaQWidgetDockableMixin, QtWidgets.QWidget):
    def __init__( self, parent=None ):
        super(SmartTianGridWeightTool, self).__init__(parent)
        self.setWindowTitle("权重拷贝映射器 (Smart Stride V5)")
        self.setWindowFlags(QtCore.Qt.Window)

        self.weight_clipboard = {}
        self.build_ui()

    def build_ui( self ):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # --- 拓扑解析设置区 ---
        group_box = QtWidgets.QGroupBox("拓扑解析规则 (选边时生效)")
        grid_layout = QtWidgets.QGridLayout(group_box)

        self.spin_stride = QtWidgets.QSpinBox()
        self.spin_stride.setRange(1, 10)
        self.spin_stride.setValue(3)  # 默认 21点/7田 = 步长3

        self.spin_offset = QtWidgets.QSpinBox()
        self.spin_offset.setRange(0, 10)
        self.spin_offset.setValue(1)  # 默认取中间点 (索引1)

        grid_layout.addWidget(QtWidgets.QLabel("步长 (Stride):"), 0, 0)
        grid_layout.addWidget(self.spin_stride, 0, 1)
        grid_layout.addWidget(QtWidgets.QLabel("偏移 (Offset):"), 1, 0)
        grid_layout.addWidget(self.spin_offset, 1, 1)
        layout.addWidget(group_box)

        # --- 核心操作区 ---
        self.btn_copy = QtWidgets.QPushButton("1. 提取真实中心点并拷贝 (Copy & Select)")
        self.btn_copy.setMinimumHeight(40)
        self.btn_copy.setStyleSheet("background-color: #3b4c5a; font-weight: bold; font-size: 13px;")
        self.btn_copy.clicked.connect(self.execute_copy)

        self.btn_paste = QtWidgets.QPushButton("2. 强制映射给田字8点 (Paste to 8 Neighbors)")
        self.btn_paste.setMinimumHeight(40)
        self.btn_paste.setStyleSheet("background-color: #5a3b3b; font-weight: bold; font-size: 13px;")
        self.btn_paste.clicked.connect(self.execute_paste)

        layout.addWidget(self.btn_copy)
        layout.addWidget(self.btn_paste)

    def get_skin_cluster( self, shape_node ):
        history = cmds.listHistory(shape_node, pruneDagObjects=True, interestLevel=1)
        if not history: return None
        skin_clusters = cmds.ls(history, type="skinCluster")
        return skin_clusters[0] if skin_clusters else None

    def execute_copy( self ):
        sel = cmds.ls(selection=True)
        if not sel:
            cmds.warning("请选择模型上的循环线 (Edges) 或直接选择中心顶点 (Vertices)。")
            return

        self.weight_clipboard.clear()
        centers = []

        # 判断用户选的是边还是点
        if ".e[" in sel[0]:
            # 选边逻辑：自动按步长解析
            raw_verts = cmds.polyListComponentConversion(sel, toVertex=True)
            verts = cmds.filterExpand(raw_verts, selectionMask=31)
            if not verts: return

            # 按世界坐标 Y 轴从上到下绝对排序
            sorted_verts = sorted(
                verts,
                key=lambda v: cmds.xform(v, query=True, translation=True, worldSpace=True)[1],
                reverse=True
            )

            stride = self.spin_stride.value()
            offset = self.spin_offset.value()

            # 数学抽样：提取真正的中心点
            centers = [v for i, v in enumerate(sorted_verts) if i % stride == offset]

            # [强制视觉复核] 将算出的中心点在视口中选中，让用户肉眼确认
            cmds.select(centers, replace=True)
            print(f"[Info] 依据步长 {stride} 解析，已自动在视口中选中 {len(centers)} 个中心点。")

        elif ".vtx[" in sel[0]:
            # 选点逻辑：完全信任用户的选择
            centers = cmds.filterExpand(sel, selectionMask=31)
        else:
            cmds.warning("不支持的组件类型。")
            return

        mesh_transform = centers[0].split('.')[0]
        skin_cluster = self.get_skin_cluster(mesh_transform)
        if not skin_cluster:
            cmds.warning(f"网格缺少蒙皮簇 (SkinCluster)。")
            return

        # 缓存权重
        for vtx in centers:
            influences = cmds.skinPercent(skin_cluster, vtx, query=True, transform=None)
            weights = cmds.skinPercent(skin_cluster, vtx, query=True, value=True)
            self.weight_clipboard[vtx] = [(inf, w) for inf, w in zip(influences, weights) if w > 0.0001]

        print(f"[Success] 成功提取并缓存了 {len(self.weight_clipboard)} 个中心点的权重。请检查视口中的点是否准确！")

    def execute_paste( self ):
        if not self.weight_clipboard:
            cmds.warning("无缓存数据，请先执行提取操作。")
            return

        cmds.undoInfo(openChunk=True, chunkName="PasteSmartTianGrid")
        try:
            mesh_transform = list(self.weight_clipboard.keys())[0].split('.')[0]
            skin_cluster = self.get_skin_cluster(mesh_transform)
            paste_count = 0

            for src_vtx, weight_data in self.weight_clipboard.items():
                # 田字 9点扩选
                adj_faces = cmds.polyListComponentConversion(src_vtx, fromVertex=True, toFace=True)
                adj_verts_raw = cmds.polyListComponentConversion(adj_faces, fromFace=True, toVertex=True)
                adj_verts = set(cmds.filterExpand(adj_verts_raw, selectionMask=31))

                # 剔除中心点自身 -> 剩下精准的 8个点
                target_verts = adj_verts - {src_vtx}

                # 强行覆盖权重
                for tgt_vtx in target_verts:
                    cmds.skinPercent(skin_cluster, tgt_vtx, transformValue=weight_data, normalize=True)
                    paste_count += 1

            print(
                f"[Success] 映射完毕！基于 {len(self.weight_clipboard)} 个中心，强制同步了周围 {paste_count} 个顶点的权重。")

        except Exception as e:
            cmds.warning(f"执行异常: {str(e)}")
        finally:
            cmds.undoInfo(closeChunk=True)


if __name__ == "__main__":
    if cmds.workspaceControl('SmartTianGridWeightToolWorkspaceControl', exists=True):
        cmds.deleteUI('SmartTianGridWeightToolWorkspaceControl', control=True)
    ui = SmartTianGridWeightTool()
    ui.show(dockable=True, floating=True, area='right', allowedArea='all')