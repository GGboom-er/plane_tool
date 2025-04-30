#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: create_bs_connection_manager.py
@date: 2025/4/25 14:58
@desc: 
"""
import maya.cmds as cmds

# 全局变量存储连接信息（格式：{bs节点名: [连接信息列表]})
BS_CONNECTION_DATA = {}


def get_bs_connections( bs_node ):
    """
    获取blendshape节点所有输入连接
    返回格式：[{"source": 源属性, "destination": 目标属性}]
    """
    connections = []

    # 获取所有weight属性连接
    num_weights = cmds.getAttr(f"{bs_node}.weight", size=True)
    for i in range(num_weights):
        attr = f"{bs_node}.weight[{i}]"
        src = cmds.listConnections(attr, plugs=True, source=True, destination=False)
        if src:
            connections.append({
                "source"     : src[0],
                "destination": attr
            })

    # 获取envelope等可能存在的其他关键属性
    for attr in ["envelope"]:
        full_attr = f"{bs_node}.{attr}"
        src = cmds.listConnections(full_attr, plugs=True, source=True, destination=False)
        if src:
            connections.append({
                "source"     : src[0],
                "destination": full_attr
            })

    return connections


def disconnect_bs( bs_node ):
    """断开指定blendshape节点的所有输入连接"""
    global BS_CONNECTION_DATA
    BS_CONNECTION_DATA[bs_node] = get_bs_connections(bs_node)

    for conn in BS_CONNECTION_DATA[bs_node]:
        try:
            cmds.disconnectAttr(conn["source"], conn["destination"])
        except:
            cmds.warning(f"断开连接失败: {conn['source']} -> {conn['destination']}")


def restore_bs( bs_node ):
    """恢复指定blendshape节点的连接"""
    global BS_CONNECTION_DATA

    if bs_node not in BS_CONNECTION_DATA:
        cmds.warning(f"找不到该节点的连接记录: {bs_node}")
        return

    for conn in BS_CONNECTION_DATA.get(bs_node, []):
        try:
            if not cmds.isConnected(conn["source"], conn["destination"]):
                cmds.connectAttr(conn["source"], conn["destination"], force=True)
        except:
            cmds.warning(f"恢复连接失败: {conn['source']} -> {conn['destination']}")


# ================= UI =================
def create_bs_connection_manager():
    """创建连接管理界面"""
    win_name = "bsConnectionManager"
    if cmds.window(win_name, exists=True):
        cmds.deleteUI(win_name)

    cmds.window(win_name, title="BlendShape 连接管理器", width=300)

    main_layout = cmds.columnLayout(adjustableColumn=True)

    # 输入框
    cmds.text(label="输入BlendShape节点名称:")
    bs_field = cmds.textField("bsNameField")

    # 自动填充按钮
    cmds.button(label="获取选中节点", command=lambda _: update_from_selection(bs_field))

    # 操作按钮
    btn_layout = cmds.rowLayout(numberOfColumns=2, columnWidth2=(150, 150))
    cmds.button(label="断开所有连接", command=lambda _: process_disconnect(bs_field))
    cmds.button(label="恢复所有连接", command=lambda _: process_restore(bs_field))

    cmds.window(win_name, e=True, width=300, height=100)
    cmds.showWindow(win_name)


def update_from_selection( field ):
    """从选择自动填充输入框"""
    sel = cmds.ls(selection=True, type="blendShape")
    if sel:
        cmds.textField(field, e=True, text=sel[0])
    else:
        cmds.warning("请先选择一个blendShape节点")


def process_disconnect( field ):
    """处理断开连接操作"""
    bs_node = cmds.textField(field, q=True, text=True)

    if not bs_node or not cmds.objExists(bs_node):
        cmds.warning("无效的blendShape节点")
        return

    if cmds.nodeType(bs_node) != "blendShape":
        cmds.warning("选择的节点不是blendShape类型")
        return

    disconnect_bs(bs_node)
    cmds.inViewMessage(amg=f"已断开 <hl>{bs_node}</hl> 的所有输入连接", pos="midCenter", fade=True)


def process_restore( field ):
    """处理恢复连接操作"""
    bs_node = cmds.textField(field, q=True, text=True)

    if not bs_node or not cmds.objExists(bs_node):
        cmds.warning("无效的blendShape节点")
        return

    restore_bs(bs_node)
    cmds.inViewMessage(amg=f"已恢复 <hl>{bs_node}</hl> 的连接", pos="midCenter", fade=True)


# ================= 使用方式 =================
# 在Maya中运行以下命令打开界面：
create_bs_connection_manager()