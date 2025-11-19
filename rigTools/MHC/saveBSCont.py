#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: saveBSCont.py
@date: 2025/10/10 16:21
@desc: 
"""
# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals
import maya.cmds as cmds

"""
简化版 BlendShape 连接管理器
- 界面只有四个按钮：
  1) 选中模型获取 blendShape 节点 (Get BS from selection)
  2) 保存当前 bs 节点连接 (Save connections)
  3) 断开连接 (Disconnect)
  4) 恢复连接 (Restore)
- 关键保证：第一次断开前会保存原始快照（original snapshot），后续断开不会覆盖该快照，
  因此多次断开后仍可恢复到最初的连接状态。
术语：blendShape 节点 (blendShape node), 连接 connections, 断开 disconnect, 恢复 restore
"""

# 全局缓存
ORIGINAL_BS_CONNECTIONS = {}   # { bs_node: [ { "source":..., "destination":... }, ... ] }  — 原始快照（首次断开前保存）
MANUAL_BS_CONNECTIONS = {}     # { bs_node: [ ... ] }  — 用户手动保存（覆盖原始快照的可选记录）

# ---------------- 辅助函数 ----------------
def find_first_blendshape_for_selection():
    """
    从当前选择中查找第一个 blendShape 节点（支持选 transform/shape 或直接选 blendShape 节点）
    返回：blendShape 节点名 或 None
    """
    sel = cmds.ls(selection=True, long=True) or []
    if not sel:
        return None

    for item in sel:
        # 若直接选中了 blendShape 节点
        try:
            if cmds.objExists(item) and cmds.nodeType(item) == "blendShape":
                return item
        except Exception:
            pass

        # 检查 item 的 shape，并在历史中查找 blendShape
        shapes = cmds.listRelatives(item, shapes=True, fullPath=True) or []
        targets = shapes if shapes else [item]
        for t in targets:
            hist = cmds.listHistory(t) or []
            found = cmds.ls(hist, type='blendShape') or []
            if found:
                return found[0]
    return None


def get_bs_connections(bs_node):
    """
    获取 blendShape 节点的所有输入连接（weight array 与 envelope）
    返回：list of { "source": plug, "destination": plug }
    """
    conns = []
    if not bs_node or not cmds.objExists(bs_node):
        return conns

    # 获取 weight array 大小
    try:
        size = cmds.getAttr("{0}.weight".format(bs_node), size=True)
    except Exception:
        size = 0

    for i in range(size):
        dst = "{0}.weight[{1}]".format(bs_node, i)
        srcs = cmds.listConnections(dst, plugs=True, source=True, destination=False) or []
        if srcs:
            conns.append({"source": srcs[0], "destination": dst})

    # 常见其他属性
    for attr in ("envelope",):
        full = "{0}.{1}".format(bs_node, attr)
        srcs = cmds.listConnections(full, plugs=True, source=True, destination=False) or []
        if srcs:
            conns.append({"source": srcs[0], "destination": full})

    return conns


# ---------------- 操作函数 ----------------
def save_current_connections(bs_node, store_as_original=False):
    """
    保存当前连接到 MANUAL_BS_CONNECTIONS；
    如果 store_as_original=True，则仅在 ORIGINAL_BS_CONNECTIONS 不存在该节点时保存（不覆盖）。
    返回保存的连接列表
    """
    if not bs_node or not cmds.objExists(bs_node) or cmds.nodeType(bs_node) != "blendShape":
        cmds.warning("无效的 blendShape 节点: {0}".format(bs_node))
        return []

    conns = get_bs_connections(bs_node)
    # 保存到手动缓存
    MANUAL_BS_CONNECTIONS[bs_node] = conns

    # 如果要求并且原始快照还不存在，则保存原始快照（首次断开前使用）
    if store_as_original and bs_node not in ORIGINAL_BS_CONNECTIONS:
        ORIGINAL_BS_CONNECTIONS[bs_node] = list(conns)  # 复制一份
    return conns


def disconnect_bs(bs_node):
    """
    断开连接：逻辑：
    - 如果 ORIGINAL_BS_CONNECTIONS 中尚无该节点的快照，则先保存原始快照（保证可恢复）
    - 断开时不覆盖 ORIGINAL_BS_CONNECTIONS（保证多次断开后依然可恢复到最初状态）
    - 同时更新 MANUAL_BS_CONNECTIONS 为当前断开前的快照（便于可选恢复）
    """
    if not bs_node or not cmds.objExists(bs_node) or cmds.nodeType(bs_node) != "blendShape":
        cmds.warning("无效的 blendShape 节点: {0}".format(bs_node))
        return

    # 在断开前保存快照：original（若不存在）和 manual（总是更新）
    current = get_bs_connections(bs_node)
    MANUAL_BS_CONNECTIONS[bs_node] = current
    if bs_node not in ORIGINAL_BS_CONNECTIONS:
        ORIGINAL_BS_CONNECTIONS[bs_node] = list(current)

    if not current:
        cmds.inViewMessage(amg="未检测到输入连接，跳过断开: {0}".format(bs_node), pos="midCenter", fade=True)
        return

    cmds.undoInfo(openChunk=True)
    try:
        for c in current:
            src = c.get("source")
            dst = c.get("destination")
            try:
                if src and dst and cmds.isConnected(src, dst):
                    cmds.disconnectAttr(src, dst)
            except Exception as e:
                cmds.warning("断开失败: {0} -> {1} ({2})".format(src, dst, e))
    finally:
        cmds.undoInfo(closeChunk=True)

    cmds.inViewMessage(amg="已断开 {0} 的输入连接（已保存快照）".format(bs_node), pos="midCenter", fade=True)


def restore_bs(bs_node, prefer_original=True):
    """
    恢复连接：
    - 默认优先使用 ORIGINAL_BS_CONNECTIONS（原始快照），若不存在则使用 MANUAL_BS_CONNECTIONS。
    - 若两者都不存在，给出警告。
    """
    if not bs_node:
        cmds.warning("请输入要恢复的 blendShape 节点名称")
        return

    # 选择恢复源
    conns = None
    if prefer_original and bs_node in ORIGINAL_BS_CONNECTIONS:
        conns = ORIGINAL_BS_CONNECTIONS.get(bs_node, [])
    else:
        conns = MANUAL_BS_CONNECTIONS.get(bs_node, [])

    if not conns:
        cmds.warning("找不到可用的连接记录以恢复（original/manually saved 均为空）: {0}".format(bs_node))
        return

    cmds.undoInfo(openChunk=True)
    try:
        for c in conns:
            src = c.get("source")
            dst = c.get("destination")
            if not src or not dst:
                continue
            src_node = src.split(".")[0]
            dst_node = dst.split(".")[0]
            if not cmds.objExists(src_node):
                cmds.warning("源节点不存在，跳过: {0}".format(src))
                continue
            if not cmds.objExists(dst_node):
                cmds.warning("目标节点不存在，跳过: {0}".format(dst))
                continue
            try:
                if not cmds.isConnected(src, dst):
                    cmds.connectAttr(src, dst, force=True)
            except Exception as e:
                cmds.warning("恢复连接失败: {0} -> {1} ({2})".format(src, dst, e))
    finally:
        cmds.undoInfo(closeChunk=True)

    cmds.inViewMessage(amg="已尝试恢复 {0} 的连接（使用 {1} 快照）".format(bs_node, "original" if (prefer_original and bs_node in ORIGINAL_BS_CONNECTIONS) else "manual"), pos="midCenter", fade=True)


# ---------------- 简洁 UI ----------------
def create_simple_bs_manager():
    win = "simpleBSManager"
    if cmds.window(win, exists=True):
        cmds.deleteUI(win)

    cmds.window(win, title="简易 BlendShape 管理器", widthHeight=(420, 90))
    column = cmds.columnLayout(adjustableColumn=True, rowSpacing=6, columnAttach=('both', 6))

    cmds.text(label="BlendShape 节点 (显示):")
    bs_field = cmds.textField("bsNameField_simple", placeholderText="blendShape 节点名会显示在这里")

    # 四个按钮：获取 / 保存 / 断开 / 恢复
    cmds.rowLayout(numberOfColumns=4, columnWidth4=(100,100,100,120), adjustableColumn=4)
    cmds.button(label="选中获取 (Get BS)", command=lambda *a: on_get_bs(bs_field))
    cmds.button(label="保存连接 (Save)", command=lambda *a: on_save(bs_field))
    cmds.button(label="断开 (Disconnect)", command=lambda *a: on_disconnect(bs_field))
    cmds.button(label="恢复 (Restore)", command=lambda *a: on_restore(bs_field))
    cmds.setParent(column)

    cmds.showWindow(win)


# ---------------- UI 回调 ----------------
def on_get_bs(field_name):
    bs = find_first_blendshape_for_selection()
    if not bs:
        cmds.warning("未找到 blendShape 节点，请选中 transform/shape 或直接选中 blendShape 节点")
        return
    if cmds.textField(field_name, exists=True):
        cmds.textField(field_name, edit=True, text=bs)
    cmds.inViewMessage(amg="已获取 blendShape: <hl>{0}</hl>".format(bs), pos="midCenter", fade=True)


def on_save(field_name):
    bs_node = cmds.textField(field_name, q=True, text=True) if cmds.textField(field_name, exists=True) else None
    if not bs_node:
        cmds.warning("请先在输入框中填写或通过“选中获取”填充 blendShape 节点名")
        return
    conns = save_current_connections(bs_node, store_as_original=False)
    cmds.inViewMessage(amg="已保存 {0} 的连接（{1} 项，手动保存）".format(bs_node, len(conns)), pos="midCenter", fade=True)


def on_disconnect(field_name):
    bs_node = cmds.textField(field_name, q=True, text=True) if cmds.textField(field_name, exists=True) else None
    if not bs_node:
        cmds.warning("请先在输入框中填写或通过“选中获取”填充 blendShape 节点名")
        return
    disconnect_bs(bs_node)


def on_restore(field_name):
    bs_node = cmds.textField(field_name, q=True, text=True) if cmds.textField(field_name, exists=True) else None
    if not bs_node:
        cmds.warning("请先在输入框中填写或通过“选中获取”填充 blendShape 节点名")
        return
    # 优先恢复 original（生产安全）；若不存在 original，会尝试使用 manual
    restore_bs(bs_node, prefer_original=True)


# 运行入口
if __name__ == "__main__":
    create_simple_bs_manager()
