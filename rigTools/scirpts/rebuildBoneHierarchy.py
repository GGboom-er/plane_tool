#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: rebuildBoneHierarchy.py
@date: 2024/12/14 18:28
@desc:
骨骼层级导出和恢复工具，支持 Python 2 和 Python 3，包含旋转和 jointOrient 属性
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import os
import json
import tempfile
import maya.cmds as cmds

try:
    import maya.api.OpenMaya as om
except ImportError:
    import maya.OpenMaya as om


def get_all_bone_hierarchy_with_attributes( root_joint, attrValue=True ):
    """递归获取骨骼层级及其属性

    参数：
    root_joint (str): 根关节的名称
    attrValue (bool): 是否获取 `rotate` 和 `jointOrient` 属性

    返回：
    list: 包含骨骼层级信息的字典列表
    """

    def traverse_hierarchy( joint, parent_path ):
        bone_name = joint.split(":")[-1]
        current_path = "{}/{}".format(parent_path, bone_name)
        bone_data = {"path": current_path, "name": bone_name}

        if attrValue:
            bone_data["rotation"] = cmds.getAttr("{}.rotate".format(joint))[0]
            bone_data["jointOrient"] = cmds.getAttr("{}.jointOrient".format(joint))[0]

        hierarchy_data.append(bone_data)

        children = cmds.listRelatives(joint, children=True, type="joint") or []
        for child in children:
            traverse_hierarchy(child, current_path)

    hierarchy_data = []
    traverse_hierarchy(root_joint, "")
    return hierarchy_data


def export_bone_hierarchy_to_json(attrValue=True):
    """导出骨骼层级和属性到 JSON 文件"""
    selected = cmds.ls(selection=True, type="joint")
    if not selected:
        om.MGlobal.displayError("请选择一个根骨骼")
        return

    root_joint = selected[0]
    hierarchy = get_all_bone_hierarchy_with_attributes(root_joint,attrValue)
    if attrValue:
        temp_dir = tempfile.gettempdir()
        json_path = os.path.join(temp_dir, "___bone_attrValue.json")

        try:
            with open(json_path, "w") as json_file:
                json.dump(hierarchy, json_file, indent=4)
        except (IOError, OSError) as e:
            om.MGlobal.displayError("写入 JSON 文件失败: {}".format(e))
            return

        om.MGlobal.displayInfo("骨骼层级路径及属性已导出到: {}".format(json_path))
    else:
        temp_dir = tempfile.gettempdir()
        json_path = os.path.join(temp_dir, "___bone_hierarchy.json")

        try:
            with open(json_path, "w") as json_file:
                json.dump(hierarchy, json_file, indent=4)
        except (IOError, OSError) as e:
            om.MGlobal.displayError("写入 JSON 文件失败: {}".format(e))
            return

        om.MGlobal.displayInfo("骨骼属性已导出到: {}".format(json_path))


def parse_json_hierarchy( json_path, attrValue=True ):
    """从 JSON 文件解析骨骼层级关系和属性

    参数：
    json_path (str): JSON 文件路径
    attrValue (bool): 是否解析 `rotation` 和 `jointOrient` 属性

    返回：
    tuple: (bone_relationships, bone_attributes, child_order)
    """
    if not os.path.exists(json_path):
        cmds.error("JSON 文件不存在: {}".format(json_path))
        return None

    try:
        with open(json_path, "r") as json_file:
            hierarchy = json.load(json_file)
    except (IOError, OSError, ValueError) as e:
        cmds.error("加载 JSON 文件失败: {}".format(e))
        return None

    bone_relationships = {}
    bone_attributes = {}
    child_order = {}
    for item in hierarchy:
        path = item["path"]
        name = item["name"]
        parent_path = "/".join(path.split("/")[:-1])
        parent_name = parent_path.split("/")[-1] if parent_path else None
        bone_relationships[name] = parent_name

        if attrValue:
            bone_attributes[name] = {
                "rotation"   : item.get("rotation"),
                "jointOrient": item.get("jointOrient")
            }

        if parent_name not in child_order:
            child_order[parent_name] = []
        child_order[parent_name].append(name)

    return bone_relationships, bone_attributes if attrValue else None, child_order


def match_bones_with_namespace(bone_relationships):
    """根据命名空间匹配场景中的骨骼"""
    scene_bones = cmds.ls(type="joint")
    scene_index = {bone.split(":")[-1]: bone for bone in scene_bones}

    matched_bones = {}
    missing_bones = []

    for bone_name in bone_relationships:
        if bone_name in scene_index:
            matched_bones[bone_name] = scene_index[bone_name]
        else:
            missing_bones.append(bone_name)

    return matched_bones, missing_bones


def restore_bone_hierarchy_with_attributes(hierarchyOrattrValue = True ):
    """恢复骨骼层级和属性"""
    bone_relationships, _, _ = parse_json_hierarchy(os.path.join(tempfile.gettempdir(), "___bone_hierarchy.json"),0)
    _, bone_attributes, _ = parse_json_hierarchy(os.path.join(tempfile.gettempdir(), "___bone_attrValue.json"), 1)
    if not bone_relationships and not bone_attributes:
        return

    matched_bones, missing_bones = match_bones_with_namespace(bone_relationships)

    if not matched_bones:
        cmds.error("没有找到匹配的骨骼，无法恢复层级和属性")
        return

    if missing_bones:
        om.MGlobal.displayWarning(
            "以下骨骼在场景中不存在: {}".format(", ".join(missing_bones))
        )

    # 获取选中的骨骼
    selected_bones = cmds.ls(selection=True, type="joint")
    selected_names = {bone.split(":")[-1] for bone in selected_bones} if selected_bones else set()

    for bone_name, parent_name in bone_relationships.items():
        # 仅处理选中的骨骼或其子骨骼
        if not selected_names or bone_name in selected_names:
            if bone_name in matched_bones:
                current_bone = matched_bones[bone_name]
                if parent_name and parent_name in matched_bones:
                    parent_bone = matched_bones[parent_name]
                    try:
                        cmds.parent(current_bone, parent_bone)
                    except RuntimeError:
                        om.MGlobal.displayWarning(
                            "无法设置骨骼 {} 的父级为 {}".format(current_bone, parent_bone)
                        )
                if hierarchyOrattrValue:
                    rotation = bone_attributes[bone_name]["rotation"]
                    joint_orient = bone_attributes[bone_name]["jointOrient"]
                    try:
                        cmds.setAttr("{}.rotate".format(current_bone), *rotation)
                        cmds.setAttr("{}.jointOrient".format(current_bone), *joint_orient)
                    except RuntimeError:
                        om.MGlobal.displayWarning("无法恢复骨骼 {} 的属性".format(current_bone))

    restore_bone_order(selected_names)
    if hierarchyOrattrValue:
        om.MGlobal.displayInfo("选中骨骼的层级和属性已恢复")
    else:
        om.MGlobal.displayInfo("选中骨骼的层级已恢复")

def delete_dna_node():
    embedded_nodes = cmds.ls(type="embeddedNodeRL4")
    if embedded_nodes:
        for node in embedded_nodes:
            try:
                cmds.delete(node)
                om.MGlobal.displayInfo(u"已删除节点: {}".format(node))
            except RuntimeError:
                om.MGlobal.displayWarning(u"无法删除节点: {}".format(node))
    else:
        om.MGlobal.displayInfo(u"未找到 embeddedNodeRL4 类型节点")


def initialize_dna_line_text( dna_text_field ):
    embedded_nodes = cmds.ls(type="embeddedNodeRL4")
    for node in embedded_nodes:
        source_connections = cmds.listConnections(node, source=True, destination=False)
        destination_connections = cmds.listConnections(node, source=False, destination=True)
        if source_connections and destination_connections:
            try:
                dna_file_path = cmds.getAttr("{}.dnaFilePath".format(node))
                cmds.textField(dna_text_field, edit=True, text=dna_file_path)
                break
            except RuntimeError:
                om.MGlobal.displayWarning("无法读取 {} 的 dnaFilePath 属性".format(node))


def load_dna_node( dna_text ):
    cmds.createEmbeddedNodeRL4(
        n="rigLogicNode",
        dfp=dna_text.replace("\\", "/"),
        jn="DHIhead:<objName>.<attrName>",
        amn="FRM_WMmultipliers.<objName>_<attrName>",
        bsn="<objName>_blendShapes.<objName>__<attrName>",
        cn="<objName>.<attrName>"
    )

def restore_bone_order(selected_names=None):
    """恢复骨骼的上下顺序"""
    json_path = os.path.join(tempfile.gettempdir(), "___bone_hierarchy.json")
    _, _, child_order = parse_json_hierarchy(json_path)

    if not child_order:
        om.MGlobal.displayWarning("未能从 JSON 文件中解析骨骼层级顺序")
        return

    scene_bones = cmds.ls(type="joint")
    scene_index = {bone.split(":")[-1]: bone for bone in scene_bones}

    for parent_name, children in child_order.items():
        if parent_name in scene_index:
            parent_bone = scene_index[parent_name]
            for index, child_name in enumerate(children):
                if child_name in scene_index:
                    target_child = scene_index[child_name]
                    # 如果启用部分骨骼选中，跳过非选中骨骼
                    if selected_names and child_name not in selected_names:
                        continue
                    try:
                        cmds.reorder(target_child, b=index + 1)
                    except RuntimeError:
                        om.MGlobal.displayWarning("无法调整骨骼 {} 的顺序".format(target_child))

    om.MGlobal.displayInfo("骨骼顺序已恢复")

def create_ui():
    window_name = "BoneHierarchyUI"
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    window = cmds.window(window_name, title=u"骨骼层级工具", widthHeight=(400, 350))
    layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=10)

    cmds.button(label=u"导出——————骨骼层级 JSON", height=40,
                command=lambda _: export_bone_hierarchy_to_json(attrValue =0))
    cmds.button(label=u"导出——————骨骼旋转数值 JSON", height=40,
                command=lambda _: export_bone_hierarchy_to_json(attrValue =1))
    cmds.button(label=u"删除DNA节点", height=40, command=lambda _: delete_dna_node())

    export_checkbox = cmds.checkBox(label=u"导入骨骼数值", value=True)

    cmds.button(label=u"恢复选中骨骼层级以及旋转数值", height=40,
                command=lambda _: restore_bone_hierarchy_with_attributes(cmds.checkBox(export_checkbox, query=True, value=True)))
    dna_text_field = cmds.textField(placeholderText="输入DNA节点内容")
    initialize_dna_line_text(dna_text_field)

    cmds.button(label=u"加载DNA节点", height=40,
                command=lambda _: load_dna_node(cmds.textField(dna_text_field, query=True, text=True)))

    cmds.showWindow(window)


if __name__ == "__main__":
    create_ui()

