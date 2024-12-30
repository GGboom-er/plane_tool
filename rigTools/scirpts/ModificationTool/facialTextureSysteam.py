#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: facialTextureSysteam.py
@date: 2024/5/30 15:36
@desc: 
"""
import maya.cmds as cmds
import os
import shutil
def addDirveAttr():
    soft_limits = [0.01, 3.0]
    ctrlAttrDict = {'EyeBrowInner':['Squeeze_Facial_Drive_Value','squeeze_Value','BrowMin_Facial_Driva_Value','BrowMax_Facial_Driva_Value'],
                    'EyeBrowRegion':['BrowMax_Facial_Driva_Value'],
                    'NoseSide':['Wrinkle_Facial_Drive_Value'],
                    'NoseRegion_M':{'Side_NoseRegion_Shadow':['Hide','Left','Right'],'Under_NoseRegion_Shadow':['Hide','Under']},
                    'LipRegion_M':{'LipRegion_Shadow':['Hide','Lip_Under']}
                    }
    for controller,attributes in ctrlAttrDict.items():
        if controller.endswith('_M'):
            if cmds.objExists(controller):
                for attr, enum_values in attributes.items():
                    full_attr = '{}.{}'.format(controller, attr)
                    # 如果属性不存在，创建 enum 类型的属性
                    if not cmds.attributeQuery(attr, node=controller, exists=True):
                        if attr == 'Side_NoseRegion_Shadow':
                            value = 2
                        else:
                            value =1
                        cmds.addAttr(controller, longName=attr, attributeType='enum', enumName=':'.join(enum_values),
                                     keyable=False,dv =value)

                    # 设置属性为可见但不可键帧
                    cmds.setAttr(full_attr, keyable=False, channelBox=True)
        else:
            for i in ['_L','_R']:
                controllerSide = controller+i

                if not cmds.objExists(controllerSide):
                    print("控制器 {} 不存在".format(controllerSide))
                    return
                soft_min, soft_max = soft_limits
                # 设置每个属性的可见性和软限制
                for attr in attributes:
                    full_attr = '{}.{}'.format(controllerSide, attr)
                    # 如果属性不存在，创建它
                    if not cmds.attributeQuery(attr, node=controllerSide, exists=True):
                        cmds.addAttr(controllerSide, longName=attr, attributeType='double', softMinValue=soft_min,
                                     softMaxValue=soft_max, keyable=False,dv =1)
                    # 设置属性为可见但不可键帧
                    cmds.setAttr(full_attr, keyable=False, channelBox=True)
                    # 更新软限制
                    cmds.addAttr(full_attr, edit=True, softMinValue=soft_min, softMaxValue=soft_max)

def create_and_connect_file_node( texture_path, nodeName ):
    # 创建 file 节点
    if not cmds.objExists(nodeName):
        nodeName = cmds.shadingNode('file', n=nodeName, asShader=True, isColorManaged=True)
    else:
        nodeName = nodeName  # 使用现有的节点名

    cmds.setAttr(nodeName + '.fileTextureName', texture_path, type='string')

    # 创建 place2dTexture 节点
    place2d_texture_node = 'place2dTexture_' + nodeName
    if not cmds.objExists(place2d_texture_node):
        place2d_texture_node = cmds.shadingNode('place2dTexture', n=place2d_texture_node, asUtility=True)

    # 连接 place2dTexture 和 file 节点的属性
    connections = {
        '.coverage'       : '.coverage',
        '.translateFrame' : '.translateFrame',
        '.rotateFrame'    : '.rotateFrame',
        '.mirrorU'        : '.mirrorU',
        '.mirrorV'        : '.mirrorV',
        '.stagger'        : '.stagger',
        '.wrapU'          : '.wrapU',
        '.wrapV'          : '.wrapV',
        '.repeatUV'       : '.repeatUV',
        '.offset'         : '.offset',
        '.rotateUV'       : '.rotateUV',
        '.noiseUV'        : '.noiseUV',
        '.vertexUvOne'    : '.vertexUvOne',
        '.vertexUvTwo'    : '.vertexUvTwo',
        '.vertexUvThree'  : '.vertexUvThree',
        '.vertexCameraOne': '.vertexCameraOne',
        '.outUV'          : '.uvCoord',
        '.outUvFilterSize': '.uvFilterSize',
    }

    for place2d_attr, file_attr in connections.items():
        if not cmds.isConnected(place2d_texture_node + place2d_attr, nodeName + file_attr):
            cmds.connectAttr(place2d_texture_node + place2d_attr, nodeName + file_attr, force=True)

    return nodeName
def EyeLidDirveFn(textureNode = [],EyeLid = '',EyeBrowRegion = ''):
    EyeLidValueFM = EyeLid + '__EyeLidDirveFM__'
    EyeLidValueCDI = EyeLid + '__EyeLidDirveCDI__'
    if not cmds.objExists(EyeLidValueFM):
        cmds.createNode('floatMath', n=EyeLidValueFM)
    if not cmds.objExists(EyeLidValueCDI):
        cmds.createNode('condition', n=EyeLidValueCDI)
    if EyeLid:
        cmds.setAttr(EyeLidValueFM + '.operation', 2)
        cmds.setAttr(EyeLidValueFM + '.floatB', 0.5)
        cmds.setAttr(EyeLidValueCDI + '.operation', 5)
        cmds.setAttr(EyeLidValueCDI + '.colorIfTrueR', 1)
        cmds.setAttr(EyeLidValueCDI + '.colorIfFalseR', 0)
        cmds.connectAttr(EyeLidValueFM + '.outFloat', EyeLidValueCDI + '.secondTerm', f=1)
        cmds.connectAttr(EyeLid + '.translateY', EyeLidValueCDI + '.firstTerm', f=1)
        cmds.connectAttr(EyeLid + '.BrowMin_Facial_Driva_Value', EyeLidValueFM + '.floatA', f=1)
        cmds.connectAttr(EyeLidValueCDI + '.outColorR', textureNode[0] + '.colorGain.colorGainR', f=1)
    if EyeBrowRegion:
        EyeLidconnectCDI = EyeBrowRegion + '__EyeLidDirveFir_CDI__'
        EyeBrowRegionValueFM = EyeBrowRegion + '__EyeLidDirveFM__'
        EyeLidCDI_A = EyeBrowRegion + '__EyeLidDirveCDI__A__'
        EyeLidCDI_B = EyeBrowRegion + '__EyeLidDirveCDI__B__'
        if not cmds.objExists(EyeLidconnectCDI):
            cmds.createNode('condition', n=EyeLidconnectCDI)
        if not cmds.objExists(EyeBrowRegionValueFM):
            cmds.createNode('floatMath', n=EyeBrowRegionValueFM)
        if not cmds.objExists(EyeLidCDI_A):
            cmds.createNode('condition', n=EyeLidCDI_A)
        if not cmds.objExists(EyeLidCDI_B):
            cmds.createNode('condition', n=EyeLidCDI_B)
        cmds.setAttr(EyeBrowRegionValueFM + '.operation', 2)
        cmds.setAttr(EyeBrowRegionValueFM + '.floatB', -0.150)
        cmds.connectAttr(EyeBrowRegion + '.BrowMax_Facial_Driva_Value', EyeBrowRegionValueFM + '.floatA', f=1)
        cmds.setAttr(EyeLidconnectCDI + '.operation', 3)
        cmds.setAttr(EyeLidconnectCDI + '.colorIfFalseR', 1)

        cmds.connectAttr(EyeBrowRegion + '.translateY', EyeLidconnectCDI + '.firstTerm', f=1)
        cmds.connectAttr(EyeBrowRegionValueFM + '.outFloat', EyeLidconnectCDI + '.secondTerm', f=1)
        cmds.setAttr(EyeLidCDI_A + '.operation', 5)
        cmds.setAttr(EyeLidCDI_A + '.colorIfFalseR', 1)
        cmds.connectAttr(EyeBrowRegion + '.translateY', EyeLidCDI_A + '.colorIfTrueR', f=1)
        cmds.connectAttr(EyeBrowRegion + '.translateY', EyeLidCDI_A + '.firstTerm', f=1)

        cmds.setAttr(EyeLidCDI_B + '.operation', 5)
        cmds.setAttr(EyeLidCDI_B + '.colorIfTrueR', 1)
        cmds.setAttr(EyeLidCDI_B + '.colorIfFalseR', 0)
        cmds.connectAttr(EyeLidCDI_A + '.outColor.outColorR', EyeLidCDI_B + '.firstTerm', f=1)
        cmds.connectAttr(EyeBrowRegionValueFM + '.outFloat', EyeLidCDI_B + '.secondTerm', f=1)
        cmds.connectAttr(EyeLidCDI_B + '.outColorR', textureNode[1]+ '.colorGain.colorGainR', f=1)
        try:
            cmds.connectAttr(EyeLid + '.translateY', EyeLidconnectCDI + '.colorIfTrue.colorIfTrueR', f=1)
            cmds.connectAttr(EyeLidconnectCDI + '.outColorR', EyeLidValueCDI + '.firstTerm', f=1)
            cmds.connectAttr(EyeLidValueFM + '.outFloat', EyeLidCDI_A + '.secondTerm', f=1)
        except:
            pass
def WrinkleDirveFn(ctrlName = '',textureNode = ''):
    WrinkleValueFM = ctrlName + '__WrinkleFM__'
    WrinkleValueCDI = ctrlName + '__WrinkleCDI__'
    if not cmds.objExists(WrinkleValueFM):
        cmds.createNode('floatMath', n=WrinkleValueFM)
    if not cmds.objExists(WrinkleValueCDI):
        cmds.createNode('condition', n=WrinkleValueCDI)
    cmds.setAttr(WrinkleValueFM + '.operation', 2)
    cmds.setAttr(WrinkleValueFM + '.floatB', 0.15)
    cmds.setAttr(WrinkleValueCDI + '.operation', 2)
    cmds.setAttr(WrinkleValueCDI + '.colorIfTrueR', 1)
    cmds.setAttr(WrinkleValueCDI + '.colorIfFalseR', 0)

    cmds.connectAttr(ctrlName+'.Wrinkle_Facial_Drive_Value',WrinkleValueFM+'.floatA',f =1)

    cmds.connectAttr(ctrlName + '.translateY', WrinkleValueCDI + '.firstTerm', f=1)

    cmds.connectAttr(WrinkleValueFM + '.outFloat', WrinkleValueCDI + '.secondTerm', f=1)

    cmds.connectAttr(WrinkleValueCDI + '.outColorR', textureNode + '.colorGainR', f=1)

def NoseDirveFn(ctrlName = '',textureNode = '',type = ''):
    NoseValueCDI = ctrlName + '__NoseCDI__'+type

    if not cmds.objExists(NoseValueCDI):
        cmds.createNode('condition', n=NoseValueCDI)

    cmds.setAttr(NoseValueCDI + '.operation', 0)
    cmds.setAttr(NoseValueCDI + '.colorIfTrueR', 1)
    cmds.setAttr(NoseValueCDI + '.colorIfFalseR', 0)
    if type == 'R_Nose':
        cmds.setAttr(NoseValueCDI+'.secondTerm',2)
        cmds.connectAttr(ctrlName+'.Side_NoseRegion_Shadow',NoseValueCDI+'.firstTerm',f =1)

    if type == 'L_Nose':
        cmds.setAttr(NoseValueCDI+'.secondTerm',1)
        cmds.connectAttr(ctrlName+'.Side_NoseRegion_Shadow',NoseValueCDI+'.firstTerm',f =1)

    if type == 'M_Nose_B':
        cmds.setAttr(NoseValueCDI+'.secondTerm',1)
        cmds.connectAttr(ctrlName+'.Under_NoseRegion_Shadow',NoseValueCDI+'.firstTerm',f =1)

    cmds.connectAttr(NoseValueCDI+'.outColorR',textureNode+'.colorGainR',f =1)

def LipsDirveFn(ctrlName = '',textureNode = ''):
    cmds.connectAttr(ctrlName+'.LipRegion_Shadow',textureNode + '.colorGainR', f=1)
def BrowLnnerDirveFn(ctrlName = '',textureNode = ''):
    BrowLnnerValueFM = ctrlName + '__BrowLnnerFM__'
    BrowLnnerValueCDI = ctrlName + '__BrowLnnerCDI__'
    if not cmds.objExists(BrowLnnerValueFM):
        cmds.createNode('floatMath', n=BrowLnnerValueFM)
    if not cmds.objExists(BrowLnnerValueCDI):
        cmds.createNode('condition', n=BrowLnnerValueCDI)
    cmds.setAttr(BrowLnnerValueFM + '.operation', 2)
    cmds.setAttr(BrowLnnerValueFM + '.floatB', 10.0)
    cmds.setAttr(BrowLnnerValueCDI + '.operation', 3)
    cmds.setAttr(BrowLnnerValueCDI + '.colorIfTrueR', 1)
    cmds.setAttr(BrowLnnerValueCDI + '.colorIfFalseR', 0)

    cmds.connectAttr(ctrlName+'.Squeeze_Facial_Drive_Value',BrowLnnerValueFM+'.floatA',f =1)
    cmds.connectAttr(ctrlName + '.squeeze', BrowLnnerValueCDI + '.firstTerm', f=1)
    cmds.connectAttr(BrowLnnerValueFM + '.outFloat', BrowLnnerValueCDI + '.secondTerm', f=1)
    cmds.connectAttr(BrowLnnerValueCDI + '.outColorR', textureNode + '.colorGainR', f=1)

def copy_and_rename_file(src_path, dst_path_with_name):
    # 提取目标目录和目标文件名

    dst_dir = os.path.dirname(dst_path_with_name)
    dst_file_name = os.path.basename(dst_path_with_name)

    # 确保目标目录存在，不存在则创建
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

    # 目标文件路径
    dst_file_path = os.path.join(dst_dir, dst_file_name)

    # 如果目标文件存在，则覆盖
    if os.path.exists(dst_file_path):
        os.remove(dst_file_path)

    # 复制文件到目标路径
    shutil.copy2(src_path, dst_file_path)

    # 打开目标文件夹
    os.startfile(dst_dir)

def check_layered_texture_usage(layered_textures):
    unused_layers = []
    layers = cmds.getAttr(layered_textures + '.inputs', multiIndices=True)
    for layer in layers:
        connected_nodes = cmds.listConnections(layered_textures + '.inputs[' + str(layer) + '].color', source=True, destination=False)
        if not connected_nodes:
            unused_layers.append((layered_textures, layer))
    return unused_layers

def remove_unused_layers(unused_layers):
    for texture, layer in unused_layers:
        cmds.removeMultiInstance(texture + '.inputs[' + str(layer) + ']', b=True)

def remove_unused_layered_textures(layered_textures):
    if not cmds.listConnections(layered_textures, source=False, destination=True):
        cmds.delete(layered_textures)

def clean_layered_textures(layered_textures):

    unused_layers = check_layered_texture_usage(layered_textures)
    remove_unused_layers(unused_layers)
    remove_unused_layered_textures(layered_textures)

def insert_files_to_layered_texture(layered_texture, file_nodes):
    # 获取当前Layer Texture节点中的所有层
    layers = cmds.getAttr(layered_texture + '.inputs', multiIndices=True) or []
    layer_data = {}

    # 存储当前连接信息
    for layer in layers:
        color_attr = '{}.inputs[{}].color'.format(layered_texture, layer)
        alpha_attr = '{}.inputs[{}].alpha'.format(layered_texture, layer)
        color_conn = cmds.listConnections(color_attr, source=True, plugs=True)
        alpha_conn = cmds.listConnections(alpha_attr, source=True, plugs=True)
        if color_conn:
            layer_data[color_conn[0].split('.')[0]] = (color_conn[0], alpha_conn[0] if alpha_conn else None)

    # 断开所有现有连接并移除属性槽
    for layer in layers:
        cmds.removeMultiInstance('{}.inputs[{}]'.format(layered_texture, layer), b=True)

    # 将新的节点插入到最小的插槽，并重新连接所有节点
    new_layers = file_nodes + [node for node in layer_data if node not in file_nodes]
    connected_nodes = set()  # 用于跟踪已经连接的文件节点

    for i, file_node in enumerate(new_layers):
        color_attr = '{}.inputs[{}].color'.format(layered_texture, i)
        alpha_attr = '{}.inputs[{}].alpha'.format(layered_texture, i)

        if file_node not in connected_nodes:
            # 如果节点之前已经连接，按照之前的连接属性进行重新连接
            if file_node in layer_data:
                cmds.connectAttr(layer_data[file_node][0], color_attr, force=True)
                if layer_data[file_node][1]:
                    cmds.connectAttr(layer_data[file_node][1], alpha_attr, force=True)
            else:
                # 对于新的文件节点，连接color和colorR属性到alpha
                cmds.connectAttr(file_node + '.outColor', color_attr, force=True)
                cmds.connectAttr(file_node + '.outColorR', alpha_attr, force=True)

            connected_nodes.add(file_node)

#创建完驱动后需要输出给cache，传递给lgt
import maya.cmds as cmds

def buildFacialInfo(textureNode, dirveName='cache', direction='node_to_cache'):
    """
    为指定的节点在cache组上添加一个自定义float属性，并根据方向参数决定连接方向。

    :param textureNode: 需要连接的节点名称
    :param dirveName: 需要添加属性的cache组名称
    :param direction: 控制连接方向，默认值为 'node_to_cache'。
                      可选值:
                      - 'node_to_cache'：节点的cgr属性控制cache的属性（默认）。
                      - 'cache_to_node'：cache的属性控制节点的cgr属性。
    """
    # 检查节点是否存在
    if not cmds.objExists(textureNode):
        cmds.error("节点 '{}' 不存在。".format(textureNode))
        return

    # 检查cache组是否存在
    if not cmds.objExists(dirveName):
        cmds.error("Cache组 '{}' 不存在。".format(dirveName))
        return

    # 使用传递的 textureNode 名称作为属性名称
    attr_name = textureNode

    # 为 cache 组添加一个 float 类型的自定义属性
    if not cmds.attributeQuery(attr_name, node=dirveName, exists=True):
        cmds.addAttr(dirveName, longName=attr_name, attributeType='float', keyable=True)

    # 获取节点的 cgr 属性
    cgr_attr = "{}.cgr".format(textureNode)
    if not cmds.objExists(cgr_attr):
        cmds.error("{} 上不存在 'cgr' 属性。".format(textureNode))
        return

    # 根据 direction 参数决定连接方向
    if direction == 'node_to_cache':
        # 节点的 cgr 属性控制 cache 组的属性
        cmds.connectAttr(cgr_attr, "{}.{}".format(dirveName, attr_name), force=True)
        print("成功连接：'{}.{}' 由 '{}' 控制".format(dirveName, attr_name, cgr_attr))

    elif direction == 'cache_to_node':
        # cache 组的属性控制节点的 cgr 属性
        cmds.connectAttr("{}.{}".format(dirveName, attr_name), cgr_attr, force=True)
        cmds.setAttr(dirveName+'.'+attr_name,1.0)
        print("成功连接：'{}' 由 '{}.{}' 控制".format(cgr_attr, dirveName, attr_name))

    else:
        cmds.error("无效的 direction 参数。请使用 'node_to_cache' 或 'cache_to_node'。")


def split_layered_texture( node_name, layer_limit=7 ):
    # 检查节点是否是 layeredTexture
    if not cmds.nodeType(node_name) == "layeredTexture":
        raise ValueError("指定的节点不是一个 layeredTexture 节点")

    # 获取图层数量
    layers = cmds.getAttr("{}.inputs".format(node_name), multiIndices=True)

    if len(layers) <= layer_limit:
        print("图层数量在限制范围内，无需拆分")
        return node_name  # 如果没有超出限制，返回原始节点

    # 保留前 7 层连接
    layers_to_keep = layers[:layer_limit]
    remaining_layers = layers[layer_limit:]

    # 创建新的 layeredTexture 节点来存储多余的层
    new_layered_node = cmds.shadingNode("layeredTexture", asShader=True)

    # 移动多余的层到新节点，并保留节点连接
    for i, layer_index in enumerate(remaining_layers):
        source_attr_prefix = "{}.inputs[{}]".format(node_name, layer_index)

        # 查询需要移动的属性
        connected_attributes = ["color", "alpha", "blendMode"]  # 常见属性
        for attr in connected_attributes:
            source_attr = "{}.{}".format(source_attr_prefix, attr)
            connections = cmds.listConnections(source_attr, plugs=True, destination=False)
            if connections:
                dest_attr = "{}.inputs[{}].{}".format(new_layered_node, i, attr)
                cmds.connectAttr(connections[0], dest_attr, force=True)
            else:
                # 如果没有连接，但需要复制静态值
                if cmds.objExists(source_attr):
                    value = cmds.getAttr(source_attr)
                    if attr == "color":
                        cmds.setAttr("{}.inputs[{}].{}".format(new_layered_node, i, attr), value[0][0], value[0][1],
                                     value[0][2], type="double3")
                    else:
                        cmds.setAttr("{}.inputs[{}].{}".format(new_layered_node, i, attr), value)

    # 删除旧的连接
    for layer_index in remaining_layers:
        cmds.removeMultiInstance("{}.inputs[{}]".format(node_name, layer_index), b=True)
    # 查找原始节点的第 8 层
    existing_layers = cmds.getAttr("{}.inputs".format(node_name), multiIndices=True)
    new_layer_index = max(existing_layers) + 1 if existing_layers else 0
    # 将新的 layeredTexture 节点作为第 8 层连接回原始节点
    cmds.setAttr("{}.inputs[{}].blendMode".format(node_name, new_layer_index), 0)  # 默认设置为混合模式
    cmds.connectAttr("{}.outColor".format(new_layered_node), "{}.inputs[{}].color".format(node_name, new_layer_index),
                     force=True)
    print("已完成拆分，新的 layeredTexture 节点为：{}".format(new_layered_node))
    return new_layered_node












