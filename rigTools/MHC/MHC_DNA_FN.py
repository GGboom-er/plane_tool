#!/usr/bin/env python
# _*_ coding:cp936 _*_
"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: MHC_DNA_FN.py
@date: 2024/8/29 15:26
@desc: 
"""
from os import makedirs
from os import path as ospath
from shutil import copyfile
from maya import cmds, mel
from dna import DataLayer_All, FileStream, Status, BinaryStreamReader, BinaryStreamWriter
import maya.cmds as cmds
import pymel.core as pm
import json
from dna_viewer import DNA, RigConfig, build_rig, build_meshes
from dnacalib import (
    CommandSequence,
    DNACalibDNAReader,
    SetNeutralJointRotationsCommand,
    SetNeutralJointTranslationsCommand,
    SetVertexPositionsCommand,
    VectorOperation_Add,
)
#构建绑定
def dna_build_rig(path,DATA_DIR):
    '''
    path = r'U:\ywm\MHC\Downloaded\DHI\5jd1XPwC_asset\2k\asset_source\MetaHumans\yy\SourceAssets\yy.dna'
    DATA_DIR = r'Y:\GGbommer\scripts\MetaHumanDNACalibration\data'
    :return:
    '''
    ANALOG_GUI = f"{DATA_DIR}/analog_gui.ma"
    GUI = f"{DATA_DIR}/mh4/gui.ma"
    ADDITIONAL_ASSEMBLE_SCRIPT = f"{DATA_DIR}/mh4/additional_assemble_script.py"
    dna = DNA(path)
    config = RigConfig(
        gui_path=GUI,
        analog_gui_path=ANALOG_GUI,
        aas_path=ADDITIONAL_ASSEMBLE_SCRIPT,
    )
    # Creates the rig
    build_rig(dna=dna, config=config)
#加载DNa驱动
def load_dna(path):
    cmds.createEmbeddedNodeRL4(
    n="rigLogicNode",
    dfp=path.replace("\\", "/"),
    jn="<objName>.<attrName>",
    amn="FRM_WMmultipliers.<objName>_<attrName>",
    bsn="<objName>_blendShapes.<attrName>",
    cn="<objName>.<attrName>"
    )
#读取DNA文件信息
def load_dna_reader(path):
    stream = FileStream(path, FileStream.AccessMode_Read, FileStream.OpenMode_Binary)
    reader = BinaryStreamReader(stream, DataLayer_All)
    reader.read()
    if not Status.isOk():
        status = Status.get()
        raise RuntimeError(f"Error loading DNA: {status.message}")
    return reader
#保存DNA修改
def save_dna(reader,path):
    stream = FileStream(path, FileStream.AccessMode_Write, FileStream.OpenMode_Binary)
    writer = BinaryStreamWriter(stream)
    writer.setFrom(reader)
    writer.write()

    if not Status.isOk():
        status = Status.get()
        raise RuntimeError(f"Error saving DNA: {status.message}")



#读取骨骼位置并写入修改
def run_joints_command(reader, calibrated):
    # Making arrays for joints' transformations and their corresponding mapping arrays
    joint_translations = []
    joint_rotations = []

    for i in range(reader.getJointCount()):
        joint_name = reader.getJointName(i)

        translation = cmds.xform(joint_name, query=True, translation=True)
        joint_translations.append(translation)

        rotation = cmds.joint(joint_name, query=True, orientation=True)
        joint_rotations.append(rotation)

    # This is step 5 sub-step a
    set_new_joints_translations = SetNeutralJointTranslationsCommand(joint_translations)
    # This is step 5 sub-step b
    set_new_joints_rotations = SetNeutralJointRotationsCommand(joint_rotations)

    # Abstraction to collect all commands into a sequence, and run them with only one invocation
    commands = CommandSequence()
    # Add vertex position deltas (NOT ABSOLUTE VALUES) onto existing vertex positions
    commands.add(set_new_joints_translations)
    commands.add(set_new_joints_rotations)

    commands.run(calibrated)
    # Verify that everything went fine
    if not Status.isOk():
        status = Status.get()
        raise RuntimeError(f"Error run_joints_command: {status.message}")
#修改骨骼位置DNA示例
reader = load_dna_reader(CHARACTER_DNA)
calibrated = DNACalibDNAReader(reader)
run_joints_command(reader, calibrated)
save_dna(calibrated)


def rename_blendshape_attributes():
    '''
    # 示例调用
    rename_blendshape_attributes()
    :return:
    '''
    # 获取当前选中的物体
    selected_objects = cmds.ls(selection=True)

    if not selected_objects:
        cmds.warning("请选择一个物体。")
        return

    # 处理每个选中的物体
    for obj in selected_objects:
        # 获取物体下的所有变形节点
        history = cmds.listHistory(obj)
        bs_nodes = cmds.ls(history, type='blendShape')

        if not bs_nodes:
            cmds.warning(f"物体 {obj} 没有找到 BlendShape 节点。")
            continue

        # 获取物体名称，作为新属性名的前缀
        object_name = obj.split('|')[-1]

        for bs_node in bs_nodes:
            # 获取 BlendShape 节点的所有关键属性（target 属性）
            attrs = cmds.listAttr(bs_node + '.w', m=True)

            if not attrs:
                cmds.warning(f"BlendShape 节点 {bs_node} 没有找到可修改的权重属性。")
                continue

            for attr in attrs:
                # 完整属性名称
                full_attr_name = f"{bs_node}.{attr}"
                # 新的属性名称
                new_attr_name = f"{object_name}__{attr}"

                # 修改属性名称
                try:
                    cmds.aliasAttr(new_attr_name, full_attr_name)
                except Exception as e:
                    cmds.warning(f"无法重命名属性 {full_attr_name}：{e}")

        cmds.select(clear=True)
        cmds.select(obj)
        cmds.select(bs_nodes, add=True)
        cmds.select(obj, add=True)
        print(f"物体 {obj} 下的 BlendShape 节点 {bs_node} 的属性名已更新。")


def reset_orient_for_selected_and_children():
    # 获取当前选择的骨骼
    selection = cmds.ls(selection=True, type='joint',dag =1)

    if not selection:
        cmds.warning("请先选择至少一个骨骼!")
        return

    # 遍历所有选择的骨骼
    for bone in selection:
        # 获取该骨骼以及所有子骨骼
        joints = cmds.listRelatives(bone, allDescendents=True, type="joint")

        # 将自身也添加到处理列表
        if joints:
            joints.append(bone)
        else:
            joints = [bone]

        # 遍历所有骨骼并归零 orient 属性
        for joint in joints:
            cmds.setAttr("{}.jointOrient".format(joint), 0, 0, 0)
            print("骨骼 {} 的 orient 已归零".format(joint))


#镜像骨骼
# 使用方式
# selected_joints = pm.ls(selection=True, type='joint')
# for joint in selected_joints:
#     mirror_joint_hierarchy_recursive(joint, across='YZ', behaviour=True)
def is_attr_connected( joint, attribute ):
    """检查属性是否有连接"""
    return pm.listConnections(f"{joint}.{attribute}", source=True, destination=False) is not None
def xformMirror( transforms=[], across='YZ', behaviour=True ):
    """ Mirrors transform across hyperplane.

    transforms -- list of Transform or string.
    across -- plane which to mirror across.
    behaviour -- bool

    """
    # No specified transforms, so will get selection
    if not transforms:
        transforms = pm.selected(type='transform')

    # Check to see all provided objects is an instance of pymel transform node,
    elif not all(map(lambda x: isinstance(x, pm.nt.Transform), transforms)):
        raise ValueError("Passed node which wasn't of type: Transform")

    # Validate plane which to mirror across,
    if not across in ('XY', 'YZ', 'XZ'):
        raise ValueError("Keyword Argument: 'across' not of accepted value ('XY', 'YZ', 'XZ').")

    for transform in transforms:
        # 找到与当前骨骼对应的镜像骨骼
        mirrored_joint = transform.name().replace('_l_',
                                                  '_r_') if '_l_' in transform.name() else transform.name().replace(
            '_r_', '_l_')

        if not pm.objExists(mirrored_joint):
            pm.warning(f"Mirrored joint {mirrored_joint} does not exist.")
            continue

        # Get the worldspace matrix, as a list of 16 float values
        mtx = pm.xform(transform, q=True, ws=True, m=True)

        # Invert rotation columns
        rx = [n * -1 for n in mtx[0:9:4]]
        ry = [n * -1 for n in mtx[1:10:4]]
        rz = [n * -1 for n in mtx[2:11:4]]

        # Invert translation row
        t = [n * -1 for n in mtx[12:15]]

        # Set matrix based on given plane, and whether to include behaviour or not
        if across == 'XY':
            mtx[14] = t[2]  # set inverse of the Z translation
            if behaviour:
                mtx[0:9:4] = rx
                mtx[1:10:4] = ry

        elif across == 'YZ':
            mtx[12] = t[0]  # set inverse of the X translation
            if behaviour:
                mtx[1:10:4] = ry
                mtx[2:11:4] = rz
        else:
            mtx[13] = t[1]  # set inverse of the Y translation
            if behaviour:
                mtx[0:9:4] = rx
                mtx[2:11:4] = rz

        # 设置镜像骨骼的矩阵，跳过已连接的属性
        if is_attr_connected(mirrored_joint, 'translate'):
            pm.xform(mirrored_joint, ws=True, m=mtx)
def mirror_joint_hierarchy_recursive( source_joint, across='YZ', behaviour=True ):
    """递归处理骨骼层级，从父节点开始"""
    '''
    # 使用方式
    selected_joints = pm.ls(selection=True, type='joint')
    for joint in selected_joints:
    mirror_joint_hierarchy_recursive(joint, across='YZ', behaviour=True)
    '''
    # 找到与当前骨骼对应的镜像骨骼
    mirrored_joint = source_joint.replace('_l_', '_r_') if '_l_' in source_joint else source_joint.replace('_r_', '_l_')

    if not pm.objExists(mirrored_joint):
        pm.warning(f"Mirrored joint {mirrored_joint} does not exist.")
        return

    # 镜像当前骨骼
    xformMirror([source_joint], across=across, behaviour=behaviour)

    # 获取当前骨骼的子骨骼
    source_children = pm.listRelatives(source_joint, children=True, type="joint")
    target_children = pm.listRelatives(mirrored_joint, children=True, type="joint")

    # 递归处理每一个子骨骼
    if source_children and target_children:
        for s_child, t_child in zip(source_children, target_children):
            mirror_joint_hierarchy_recursive(s_child, across, behaviour)




#添加后缀
# 示例调用
# add_suffix_to_children("_drv")
def add_suffix_to_children( suffix ):
    # 获取当前选中的物体
    selected_objects = cmds.ls(selection=True)

    if not selected_objects:
        cmds.warning("请选择至少一个物体。")
        return

    # 遍历选中的每个物体
    for obj in selected_objects:
        # 获取该物体的所有子物体
        children = cmds.listRelatives(obj, allDescendents=True, type="transform", fullPath=True)

        if children:
            for child in children:
                # 获取子物体的当前名称
                current_name = child.split('|')[-1]
                # 添加后缀
                new_name = current_name + suffix
                # 重命名子物体
                cmds.rename(child, new_name)
        else:
            cmds.warning(f"物体 {obj} 没有子物体。")


#传递骨骼数据
# file_path = r'U:\ywm\MHC\sxx\aaa.json'
def save_bone_transform_data( file_path ):
    """
    将所选骨骼及其所有子层级的位移、旋转、缩放和方向信息保存到文件。

    参数：
        file_path (str): 保存数据的文件路径。
    """
    selection = cmds.ls(selection=True, type='joint')
    if not selection:
        cmds.warning("请先选择一个或多个骨骼节点。")
        return

    bone_data = {}

    def traverse_hierarchy( node ):
        if cmds.nodeType(node) != 'joint':
            return

        # 获取变换属性
        transform_attrs = {}
        for attr in ['translate', 'rotate', 'scale', 'jointOrient']:
            values = cmds.getAttr(f"{node}.{attr}")[0]
            transform_attrs[attr] = values

        bone_data[node] = transform_attrs

        # 遍历子节点
        children = cmds.listRelatives(node, children=True, type='joint') or []
        for child in children:
            traverse_hierarchy(child)

    for root_node in selection:
        traverse_hierarchy(root_node)

    # 将数据保存到文件
    with open(file_path, 'w') as f:
        json.dump(bone_data, f, indent=4)

    print(f"骨骼变换数据已保存到 {file_path}")
def load_bone_transform_data( file_path ):
    """
    从文件中读取骨骼变换数据，并在当前场景中设置对应骨骼的属性。

    参数：
        file_path (str): 读取数据的文件路径。
    """
    try:
        with open(file_path, 'r') as f:
            bone_data = json.load(f)
    except IOError:
        cmds.error(f"无法打开文件：{file_path}")
        return
    except json.JSONDecodeError:
        cmds.error("文件内容不是有效的JSON格式。")
        return

    for bone, attrs in bone_data.items():
        if not cmds.objExists(bone):
            cmds.warning(f"场景中不存在骨骼：{bone}")
            continue

        for attr, values in attrs.items():
            try:
                cmds.setAttr(f"{bone}.{attr}", *values)
            except Exception as e:
                cmds.warning(f"无法设置 {bone}.{attr}：{e}")

    print("骨骼变换数据已加载并应用到当前场景。")






