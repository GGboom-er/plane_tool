#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: rebuildBoneHierarchy.py
@date: 2024/12/14 18:28
@desc:
"""
#!/usr/bin/env python
# _*_ coding: cp936 _*_

"""
骨骼层级导出和恢复工具，支持 Python 2 和 Python 3，包含旋转和 jointOrient 属性
"""
# !/usr/bin/env python
# _*_ coding: cp936 _*_

"""
骨骼层级导出和恢复工具，支持 Python 2 和 Python 3，包含旋转和 jointOrient 属性，并新增 DNA 节点功能
"""
import maya.cmds as cmds
import json
import os
import tempfile

try:
    import maya.api.OpenMaya as om
except ImportError:
    import maya.OpenMaya as om


def get_all_bone_hierarchy_with_attributes( root_joint ):
    def traverse_hierarchy( joint, parent_path ):
        bone_name = joint.split(":")[-1]
        current_path = "{}/{}".format(parent_path, bone_name)
        rotation = cmds.getAttr("{}.rotate".format(joint))[0]
        joint_orient = cmds.getAttr("{}.jointOrient".format(joint))[0]
        hierarchy_data.append({
            "path"       : current_path,
            "name"       : bone_name,
            "rotation"   : rotation,
            "jointOrient": joint_orient
        })
        children = cmds.listRelatives(joint, children=True, type="joint") or []
        for child in children:
            traverse_hierarchy(child, current_path)

    hierarchy_data = []
    traverse_hierarchy(root_joint, "")
    return hierarchy_data


def export_bone_hierarchy_to_json():
    selected = cmds.ls(selection=True, type="joint")
    if not selected:
        om.MGlobal.displayError(u"请选择一个根骨骼")
        return

    root_joint = selected[0]
    hierarchy = get_all_bone_hierarchy_with_attributes(root_joint)
    temp_dir = tempfile.gettempdir()
    json_path = os.path.join(temp_dir, "___bone_hierarchy.json")

    try:
        with open(json_path, "w") as json_file:
            json.dump(hierarchy, json_file, indent=4)
    except Exception as e:
        om.MGlobal.displayError(u"写入 JSON 文件失败: {}".format(e))
        return

    om.MGlobal.displayInfo(u"骨骼层级路径及属性已导出到: {}".format(json_path))


def parse_json_hierarchy( json_path ):
    if not os.path.exists(json_path):
        cmds.error(u"JSON 文件不存在: {}".format(json_path))
        return None

    try:
        with open(json_path, "r") as json_file:
            hierarchy = json.load(json_file)
    except Exception as e:
        cmds.error(u"加载 JSON 文件失败: {}".format(e))
        return None

    bone_relationships = {}
    bone_attributes = {}
    for item in hierarchy:
        path = item["path"]
        name = item["name"]
        parent_path = "/".join(path.split("/")[:-1])
        parent_name = parent_path.split("/")[-1] if parent_path else None
        bone_relationships[name] = parent_name
        bone_attributes[name] = {
            "rotation"   : item["rotation"],
            "jointOrient": item["jointOrient"]
        }
    return bone_relationships, bone_attributes


def match_bones_with_namespace( bone_relationships ):
    scene_bones = cmds.ls(type="joint")
    matched_bones = {}
    missing_bones = []

    for bone_name in bone_relationships:
        matches = [bone for bone in scene_bones if bone.split(":")[-1] == bone_name]
        if matches:
            matched_bones[bone_name] = matches[0]
        else:
            missing_bones.append(bone_name)

    return matched_bones, missing_bones


def restore_bone_hierarchy_with_attributes():
    json_path = os.path.join(tempfile.gettempdir(), "___bone_hierarchy.json")
    bone_relationships, bone_attributes = parse_json_hierarchy(json_path)

    if not bone_relationships:
        return

    matched_bones, missing_bones = match_bones_with_namespace(bone_relationships)

    if not matched_bones:
        cmds.error(u"没有找到匹配的骨骼，无法恢复层级和属性")
        return

    if missing_bones:
        om.MGlobal.displayWarning(
            u"以下骨骼在场景中不存在: {}".format(", ".join(missing_bones))
        )

    selected_bones = cmds.ls(selection=True, type="joint")
    if not selected_bones:
        cmds.error(u"请选中需要恢复的骨骼")
        return

    selected_names = {bone.split(":")[-1] for bone in selected_bones}

    for bone_name, parent_name in bone_relationships.items():
        if bone_name in selected_names and bone_name in matched_bones:
            current_bone = matched_bones[bone_name]
            if parent_name and parent_name in matched_bones:
                parent_bone = matched_bones[parent_name]
                try:
                    cmds.parent(current_bone, parent_bone)
                except RuntimeError:
                    om.MGlobal.displayWarning(
                        "无法设置骨骼 {} 的父级为 {}".format(current_bone, parent_bone)
                    )

            rotation = bone_attributes[bone_name]["rotation"]
            joint_orient = bone_attributes[bone_name]["jointOrient"]
            try:
                cmds.setAttr("{}.rotate".format(current_bone), *rotation)
                cmds.setAttr("{}.jointOrient".format(current_bone), *joint_orient)
            except RuntimeError:
                om.MGlobal.displayWarning(
                    "无法恢复骨骼 {} 的属性".format(current_bone)
                )

    om.MGlobal.displayInfo(u"选中骨骼的层级和属性已恢复")


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


def create_ui():
    window_name = "BoneHierarchyUI"
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    window = cmds.window(window_name, title=u"骨骼层级工具", widthHeight=(400, 350))
    layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=10)
    cmds.button(label=u"导出骨骼层级及属性到 JSON", height=40, command=lambda _: export_bone_hierarchy_to_json())
    cmds.button(label=u"删除DNA节点", height=40, command=lambda _: delete_dna_node())
    cmds.button(label=u"恢复选中骨骼层级及属性", height=40, command=lambda _: restore_bone_hierarchy_with_attributes())
    dna_text_field = cmds.textField(placeholderText="输入DNA节点内容")
    initialize_dna_line_text(dna_text_field)

    cmds.button(label=u"加载DNA节点", height=40,
                command=lambda _: load_dna_node(cmds.textField(dna_text_field, query=True, text=True)))

    cmds.showWindow(window)


if __name__ == "__main__":
    create_ui()

