#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: createBSDriveFile.py
@date: 2025/6/11 14:49
@desc: 
"""

import pymel.core as pm
import hashlib

class BlendShapeFileDriverTool:
    def __init__(self):
        self.window = 'bsFileDriverWin'
        self.bs_node = None

        if pm.window(self.window, exists=True):
            pm.deleteUI(self.window)

        with pm.window(self.window, title="BlendShape File Driver Tool", widthHeight=(600, 400)):
            with pm.columnLayout(adj=True):
                with pm.rowLayout(nc=3, adj=2):
                    pm.text(label='BlendShape节点:')
                    self.bs_field = pm.textField()
                    pm.button(label='加载选中', c=self.load_bs_node)

                pm.separator(h=10, style='in')

                with pm.rowLayout(nc=2, adjustableColumn=2):
                    with pm.columnLayout(adj=True, width=200):  # 左侧宽度固定
                        pm.text(label='当前值为 1 的属性')
                        self.active_list = pm.textScrollList(
                            allowMultiSelection=True,
                            height=200,
                            dcc=self.filter_created_list_by_attr  # 添加双击事件
                        )

                    with pm.columnLayout(adj=True):
                        pm.text(label='已创建的驱动')
                        self.created_list = pm.textScrollList(allowMultiSelection=True, height=200, dcc=self.select_file_node)

                with pm.rowLayout(nc=3):
                    pm.button(label='刷新属性', c=self.refresh_all)
                    pm.button(label='创建驱动', c=self.create_driver)
                    pm.button(label='删除驱动', c=self.delete_driver)

        pm.showWindow(self.window)

    def load_bs_node(self, *args):
        sel = pm.ls(selection=True, type='transform')
        if not sel:
            pm.warning("请先选择一个包含 blendShape 节点的模型")
            return

        history = pm.listHistory(sel[0])
        bs_nodes = [n for n in history if isinstance(n, pm.nodetypes.BlendShape)]
        if not bs_nodes:
            pm.warning("未在模型历史中找到 blendShape 节点")
            return

        self.bs_node = bs_nodes[0]
        pm.textField(self.bs_field, edit=True, text=self.bs_node.name())
        self.refresh_all()

    def refresh_all(self, *args):
        self.refresh_active_weights()
        self.refresh_created_list()

    def refresh_active_weights(self, *args):
        self.active_list.removeAll()
        if not self.bs_node:
            return
        for alias, plug in self.bs_node.listAliases():
            try:
                if pm.getAttr(plug) == 1.0:
                    self.active_list.append(alias)
            except:
                continue

    def refresh_created_list(self, *args):
        self.created_list.removeAll()
        self.all_driver_items = []  # 存储所有驱动信息，便于筛选使用
        files = pm.ls("bsDriverFile_*", type="file")
        for f in files:
            if f.hasAttr("bsDriver_info"):
                info = f.attr("bsDriver_info").get()
                if ":" in info:
                    _, attrs = info.split(":", 1)
                    item = f"{attrs} -> {f.name()}"
                    self.all_driver_items.append(item)
                    self.created_list.append(item)

    def filter_created_list_by_attr(self, *args):
        selected_attr = self.active_list.getSelectItem()
        if not selected_attr:
            return
        # 支持多选筛选，显示包含任一属性的驱动
        match_items = []
        for item in self.all_driver_items:
            attr_str = item.split('->')[0].strip()
            attrs = [a.strip() for a in attr_str.split(',')]
            if any(attr in attrs for attr in selected_attr):
                match_items.append(item)

        self.created_list.removeAll()
        for item in match_items:
            self.created_list.append(item)

    def create_driver(self, *args):
        if not self.bs_node:
            pm.warning("请先加载 blendShape 节点")
            return

        selected_attrs = self.active_list.getSelectItem()
        if not selected_attrs:
            pm.warning("请选择至少一个属性")
            return

        new_attr_set = set(selected_attrs)

        # 检查是否重复
        existing_files = pm.ls("bsDriverFile_*", type="file")
        for f in existing_files:
            if f.hasAttr("bsDriver_info"):
                info = f.attr("bsDriver_info").get()
                if ":" not in info:
                    continue
                _, existing_attrs_str = info.split(":", 1)
                existing_attr_list = existing_attrs_str.split(',')
                existing_attr_set = set(existing_attr_list)

                if new_attr_set == existing_attr_set:
                    pm.warning("已经存在完全相同属性组合的驱动，无法重复创建。")
                    return

        attr_key = ",".join(sorted(selected_attrs))
        attr_paths = [self.bs_node.attr(a) for a in selected_attrs]
        hash_id = hashlib.md5(attr_key.encode()).hexdigest()[:8]

        file_node = pm.shadingNode("file", asTexture=True, name=f"bsDriverFile_{hash_id}")
        file_node.addAttr("bsDriver_info", dt="string")
        file_node.attr("bsDriver_info").set(f"{self.bs_node}:{attr_key}")

        if len(attr_paths) == 1:
            pm.connectAttr(attr_paths[0], file_node.alphaGain, force=True)
        else:
            mult_node = pm.createNode("multiply", name=f"bsDriverMult_{hash_id}")
            for i in range(len(attr_paths)):
                pm.setAttr(f"{mult_node}.input[{i}]", 1.0)
                pm.connectAttr(attr_paths[i], f"{mult_node}.input[{i}]", force=True)
            pm.connectAttr(mult_node.output, file_node.alphaGain, force=True)

        self.refresh_created_list()

    def delete_driver(self, *args):
        selected = self.created_list.getSelectItem()
        if not selected:
            pm.warning("请选择要删除的驱动")
            return

        for item in selected:
            if '->' not in item:
                continue
            file_name = item.split('->')[-1].strip()
            if not pm.objExists(file_name):
                continue

            conns = pm.listConnections(f"{file_name}.alphaGain", plugs=True, source=True)
            if conns:
                src_attr = conns[0]
                src_node = src_attr.split('.')[0]
                pm.disconnectAttr(src_attr, f"{file_name}.alphaGain")
                if pm.objExists(src_node) and (src_node.startswith("bsDriverMult_") or pm.nodeType(src_node) == "multiply"):
                    pm.delete(src_node)

            pm.delete(file_name)

        self.refresh_created_list()

    def select_file_node(self, *args):
        selected = self.created_list.getSelectItem()
        if not selected:
            return
        for item in selected:
            if '->' not in item:
                continue
            file_name = item.split('->')[-1].strip()
            if pm.objExists(file_name):
                pm.select(file_name, r=True)

# 使用方式
BlendShapeFileDriverTool()

