#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: transferUV.py
@date: 2025/1/3 19:15
@desc: 
"""
#!/usr/bin/env python
# _*_ coding: utf-8 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: transferUV.py
@date: 2025/1/3 19:15
@desc: 使用代理模型和 maya.cmds.transferAttributes 进行 UV 数据传递，兼容 Python 2 和 3
"""

from __future__ import print_function  # 兼容 Python 2 的打印
import maya.cmds as cmds
import maya.api.OpenMaya as om
import sys

# 检查 Python 版本
is_py2 = sys.version_info[0] == 2
is_py3 = sys.version_info[0] == 3


def get_mobject(node_name):
    """
    获取 Maya 节点的 MObject。
    :param node_name: 节点名称
    :return: MObject
    """
    sel_list = om.MSelectionList()
    sel_list.add(node_name)
    return sel_list.getDependNode(0)


def get_orig_node(mesh_shape):
    """
    获取指定网格的 orig 节点。
    :param mesh_shape: 网格的 shape 名称
    :return: orig 节点名称或 None
    """
    try:
        tweak_connection = cmds.listConnections(
            "{}.tweakLocation".format(mesh_shape), source=True, destination=False
        )
        if tweak_connection:
            group_parts_node = cmds.listConnections(
                "{}.input[0].inputGeometry".format(tweak_connection[0]),
                source=True,
                destination=False,
            )
            if group_parts_node:
                input_connections = cmds.listConnections(
                    "{}.inputGeometry".format(group_parts_node[0]),
                    source=True,
                    destination=False,
                    plugs=True,
                )
                return input_connections[0].split(".")[0] if input_connections else None
    except Exception:
        pass
    return None


def create_proxy_mesh(proxy_transform_name="__temp_transferUV", proxy_shape_name="__temp_transferUVShape"):
    """
    创建代理模型（transform 和 mesh）。
    :param proxy_transform_name: 代理模型 transform 名称
    :param proxy_shape_name: 代理模型 shape 名称
    :return: shape 节点名称
    """
    if cmds.objExists(proxy_transform_name):
        cmds.delete(proxy_transform_name)

    proxy_transform = cmds.createNode("transform", name=proxy_transform_name)
    proxy_shape = cmds.createNode("mesh", name=proxy_shape_name, parent=proxy_transform)
    return proxy_shape


def transfer_uv_via_proxy(source_shape, target_shape):
    """
    使用代理模型和 transferAttributes 传递 UV 数据，并更新目标模型的 orig 节点。
    :param source_shape: 源模型的 shape 名称
    :param target_shape: 目标模型的 shape 名称
    """
    proxy_transform_name = "__temp_transferUV"
    proxy_shape_name = "__temp_transferUVShape"

    try:
        # 获取目标模型的 orig 节点
        orig_node = get_orig_node(target_shape)
        if not orig_node:
            raise RuntimeError("无法找到目标模型 {} 的 orig 节点。".format(target_shape))

        # 创建代理模型
        proxy_shape = create_proxy_mesh(proxy_transform_name, proxy_shape_name)

        # 初始化代理模型拓扑
        cmds.connectAttr("{}.outMesh".format(orig_node), "{}.inMesh".format(proxy_shape))
        cmds.refresh()
        cmds.disconnectAttr("{}.outMesh".format(orig_node), "{}.inMesh".format(proxy_shape))

        # 使用 transferAttributes 传递 UV 数据
        cmds.transferAttributes(
            source_shape,  # 源模型
            proxy_shape,   # 代理模型
            transferPositions=False,  # 不传递顶点位置
            transferNormals=False,    # 不传递法线
            transferUVs=True,         # 只传递 UV 数据
            transferColors=False,     # 不传递颜色
            sampleSpace=4,            # 使用世界空间
            searchMethod=3,           # 最近点匹配
            flipUVs=False,            # 不翻转 UV
            colorBorders=True         # 包括 UV 边界
        )

        # 更新目标模型的 UV 数据
        cmds.connectAttr("{}.outMesh".format(proxy_shape), "{}.inMesh".format(orig_node), force=True)
        cmds.refresh()
        cmds.disconnectAttr("{}.outMesh".format(proxy_shape), "{}.inMesh".format(orig_node))

        print("UV 数据已成功从 {} 传递到 {}。".format(source_shape, target_shape))

    except Exception as e:
        cmds.warning("UV 数据传递失败：{}".format(e))
    finally:
        if cmds.objExists(proxy_transform_name):
            cmds.delete(proxy_transform_name)


def transfer_uv_from_selection():
    """
    从选择的两个模型中传递 UV 数据。
    """
    try:
        selection = cmds.ls(selection=True, long=True)
        if len(selection) != 2:
            raise RuntimeError("请选中两个模型，依次为：源模型和目标模型。")

        source_shape = cmds.listRelatives(selection[0], shapes=True, noIntermediate=True, fullPath=True)
        target_shape = cmds.listRelatives(selection[1], shapes=True, noIntermediate=True, fullPath=True)

        if not source_shape or not target_shape:
            raise RuntimeError("选择的对象必须是有效的网格 (mesh)。")

        transfer_uv_via_proxy(source_shape[0], target_shape[0])

    except Exception as e:
        cmds.warning("UV 传递失败：{}".format(e))


# 脚本执行入口
if __name__ == "__main__":
    transfer_uv_from_selection()
