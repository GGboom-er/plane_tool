import maya.cmds as cmds
from dna import DataLayer_All, FileStream, Status, BinaryStreamReader, BinaryStreamWriter
import maya.cmds as cmds
import pymel.core as pm
import json
from dnacalib import (
    CommandSequence,
    DNACalibDNAReader,
    SetNeutralJointRotationsCommand,
    SetNeutralJointTranslationsCommand,
    SetVertexPositionsCommand,
    VectorOperation_Add,
)


def load_dna_reader( path ):
    stream = FileStream(path, FileStream.AccessMode_Read, FileStream.OpenMode_Binary)
    reader = BinaryStreamReader(stream, DataLayer_All)
    reader.read()
    if not Status.isOk():
        status = Status.get()
        raise RuntimeError(f"Error loading DNA: {status.message}")
    return reader


def combine_lists_to_dict( A, B ):
    """
    将两个等长列表组合为字典，A的元素为键，对应B元素组成值列表

    参数:
        A (list): 包含重复元素的键列表
        B (list): 对应值元素的列表

    返回:
        dict: 结构为 {A元素: [对应B元素列表]}

    异常:
        ValueError: 当输入列表长度不相等时
    """
    if len(A) != len(B):
        raise ValueError("输入列表必须等长")

    result_dict = {}
    for key, value in zip(A, B):
        if key in result_dict:
            result_dict[key].append(value)
        else:
            result_dict[key] = [value]
    return result_dict


def getDNABsName( index ,calibrated):
    input_indices = calibrated.getBlendShapeChannelInputIndices()
    try:
        return calibrated.getBlendShapeChannelName(input_indices.index(index))
    except:
        return None


def get_blendshape_index( obj, target_name ):
    """
    判断指定物体是否有 blendShape 节点，是否有目标名为 target_name 的 blendShape，并返回其 index。
    :param obj: str or PyNode，变形目标物体
    :param target_name: str，blendShape 中的目标名称（例如：bs_01）
    :return: Tuple(bool, bool, int or None)
             是否有blendShape，是否有该目标，该目标index（如果存在）
    """
    try:
        obj = pm.PyNode(obj)
    except pm.MayaNodeError:
        return False, False, None

    # 查找 blendShape 节点（只找 deformers）
    history = pm.listHistory(obj, type='blendShape')
    if not history:
        return None, None

    for bs_node in history:
        # 获取所有 target 名称
        aliases = bs_node.listAliases()
        for alias_name, plug in aliases:
            if alias_name == target_name:
                index = int(str(plug).split('[')[-1].rstrip(']'))
                return index
        return bs_node, None  # 有blendShape但没有该target
    return None, None  # 没找到任何blendShape

# ------------------------------------------------------
# 工具函数：记录与还原属性状态（锁定、连接、当前值）
# ------------------------------------------------------
def record_and_unlock_attr( attr ):
    data = {
        'exists'     : cmds.objExists(attr),
        'locked'     : False,
        'connections': [],
        'value'      : 0.0
    }
    if not data['exists']:
        return data

    if cmds.getAttr(attr, lock=True):
        data['locked'] = True
        cmds.setAttr(attr, lock=False)

    connections = cmds.listConnections(attr, source=True, destination=False, plugs=True) or []
    if connections:
        data['connections'] = connections[:]
        for c in connections:
            cmds.disconnectAttr(c, attr)

    try:
        data['value'] = cmds.getAttr(attr)
    except:
        data['value'] = 0.0

    cmds.setAttr(attr, 0)
    return data


def restore_attr( attr, data ):
    if not data.get('exists'):
        return

    try:
        cmds.setAttr(attr, data['value'])
    except:
        pass

    for src in data['connections']:
        try:
            cmds.connectAttr(src, attr, force=True)
        except:
            pass

    if data.get('locked'):
        cmds.setAttr(attr, lock=True)


def returnShapeOrig( mesh_transform ):
    """
    给定模型 transform 节点，返回其有效 shape 与有效 orig 节点路径。
    自动清理无效 Orig。
    返回值：(shape_path, orig_path) 或 None
    """
    if not cmds.objExists(mesh_transform):
        print("模型不存在：{}".format(mesh_transform))
        return None

    # 获取所有 shape 节点（long path）
    shape_nodes = cmds.listRelatives(mesh_transform, shapes=True, fullPath=True) or []
    if not shape_nodes:
        print("无 shape 节点")
        return None

    # 区分 shape 与 orig
    valid_shapes = []
    orig_shapes = []

    for shape in shape_nodes:
        if not cmds.nodeType(shape) == 'mesh':
            continue
        if cmds.getAttr(shape + ".intermediateObject"):
            orig_shapes.append(shape)
        else:
            valid_shapes.append(shape)

    # 无有效 shape，也不处理
    if not valid_shapes:
        print("无有效 shape")
        return None

    valid_shape = valid_shapes[0]  # 只返回第一个有效 shape，若有多个 shape 可自定义逻辑

    # 检查 orig_shapes 是否有连接 deformers
    connected_orig = None
    for orig in orig_shapes:
        cons = cmds.listConnections(orig + ".outMesh", destination=True, plugs=True) or []
        is_connected = False
        for plug in cons:
            node = plug.split('.')[0]
            if cmds.nodeType(node) in ["skinCluster", "blendShape", "ffd", "deltaMush"] or \
                    "deform" in cmds.nodeType(node).lower():
                is_connected = True
                break

        if is_connected:
            if connected_orig is None:
                connected_orig = orig
            else:
                print("[⚠] 多个有效 Orig？已忽略：", orig)
        else:
            print("[🗑] 删除无连接 Orig：", orig)
            cmds.delete(orig)

    return (valid_shape, connected_orig)


# ------------------------------------------------------
# 复制干净模型到临时组
# ------------------------------------------------------
def extract_clean_mesh_from_transform( transform, name="cleanMesh", container_group="__EXPR_TEMP__" ):
    # 创建临时组
    if not cmds.objExists(container_group):
        cmds.group(em=True, name=container_group)

    # 创建并连接
    new_transform = cmds.createNode("transform", name=name)
    new_shape = cmds.createNode("mesh", name="{}Shape".format(name), parent=new_transform)
    cmds.connectAttr(transform + ".outMesh", new_shape + ".inMesh", force=True)
    cmds.refresh(force=True)
    cmds.disconnectAttr(transform + ".outMesh", new_shape + ".inMesh")

    cmds.setAttr(new_shape + ".intermediateObject", 0)
    cmds.parent(new_transform, container_group)
    return new_transform


# ------------------------------------------------------
# 主逻辑：处理数据结构并复制模型
# ------------------------------------------------------
def get_blendshape_node_from_mesh(mesh_shape):
    """从shape节点获取其绑定的blendShape节点"""
    history = cmds.listHistory(mesh_shape) or []
    blendshapes = next((node for node in history if cmds.nodeType(node) == 'blendShape'), None)
    if blendshapes:
        return blendshapes
    return None
def get_active_blendshape_targets(blendshape_node, threshold=0.99):
    """返回当前激活权重为1的blendShape target名称列表"""
    active_targets = []
    if not blendshape_node or not cmds.objExists(blendshape_node):
        return active_targets

    weight_attrs = cmds.listAttr(blendshape_node + ".w", m=True) or []
    for attr in weight_attrs:
        full_attr = "{}.{}".format(blendshape_node, attr)
        try:
            value = cmds.getAttr(full_attr)
            if value >= threshold:
                active_targets.append(attr)
        except Exception:
            continue
    return active_targets

def process_expression_data(expr_data_dict, source_model, container_group="__EXPR_TEMP__"):
    result_models = []
    expr_bs_map = {}  # 存储每个expr_name对应激活的blendshape属性
    source_model_shapes = returnShapeOrig(source_model)[0]

    # 获取绑定的 blendShape 节点
    blendshape_node = get_blendshape_node_from_mesh(source_model_shapes)
    if not blendshape_node:
        print("❌ 未找到blendShape节点: {}".format(source_model))
        return result_models, expr_bs_map

    for index, item in expr_data_dict.items():
        expr_name = list(item.keys())[0]
        attr_paths = item[expr_name]

        if expr_name in [None, '', 'None']:
            print("⚠️ 跳过无效bs属性 index {} attr {}".format(index, attr_paths))
            continue

        valid_attrs = []
        attr_state_map = {}

        # 激活表达属性
        for attr_path in attr_paths:
            if not cmds.objExists(attr_path):
                print("⚠️ 属性不存在: {}，跳过".format(attr_path))
                continue

            state = record_and_unlock_attr(attr_path)
            cmds.setAttr(attr_path, 1)
            attr_state_map[attr_path] = state
            valid_attrs.append(attr_path)

            drive_attr = 'drive:' + attr_path
            if cmds.objExists(drive_attr):
                TEMPstate = record_and_unlock_attr(drive_attr)
                cmds.setAttr(drive_attr, 1)
                attr_state_map[drive_attr] = TEMPstate
                valid_attrs.append(drive_attr)

        if not valid_attrs:
            continue

        print("🟢 Index {} → [{}] → 激活 {}".format(index, expr_name, valid_attrs))

        # 记录当前bs属性
        active_bs_targets = get_active_blendshape_targets(blendshape_node)
        expr_bs_map[expr_name] = active_bs_targets

        # 提取表达网格
        expr_mesh = extract_clean_mesh_from_transform(source_model_shapes, name=expr_name,container_group=container_group)
        if expr_mesh:
            result_models.append(expr_mesh)
        else:
            print("❌ 无法复制模型: {} → {}".format(source_model, expr_name))

        # 还原属性
        for attr_path in valid_attrs:
            restore_attr(attr_path, attr_state_map[attr_path])

    return expr_bs_map


# ------------------------------------------------------
# 连接表情模型至目标模型 BlendShape 节点
# ------------------------------------------------------
def connect_expression_meshes_to_blendshape( target_model, expr_meshes ):
    if not expr_meshes:
        print("⚠️ 无表情模型可连接")
        return

    # 获取已有 blendShape 节点
    history = cmds.listHistory(target_model) or []
    bs_node = next((node for node in history if cmds.nodeType(node) == 'blendShape'), None)

    if not bs_node:
        # 若无bs节点，直接添加所有表情
        bs_node = cmds.blendShape(expr_meshes, target_model, name="{}_bs".format(target_model))[0]
        print("✅ 创建新blendShape节点: {}".format(bs_node))
        return

    # 已有bs节点，查询现有blendshape属性（别名与真实属性）
    existing_targets = cmds.aliasAttr(bs_node, q=True) or []

    existing_target_indices = {}
    for i in range(0, len(existing_targets), 2):
        alias = existing_targets[i]  # e.g. 'brow_down_L'
        real_attr = existing_targets[i + 1]  # e.g. 'weight[0]'
        try:
            index = int(real_attr.split('[')[-1].replace(']', ''))
            existing_target_indices[alias] = index
        except ValueError:
            print("⚠️ 跳过无法解析的属性: {}".format(real_attr))

    # 获取当前已有index最大值，便于追加新属性
    existing_indices = cmds.getAttr(bs_node + ".weight", multiIndices=True) or []
    max_index = max(existing_indices) + 1 if existing_indices else 0

    for mesh in expr_meshes:
        expr_name = mesh.split('|')[-1]  # 去除层级路径
        mesh_shape = cmds.listRelatives(mesh, shapes=True, fullPath=True)[0]

        if expr_name in existing_target_indices:
            # 已存在此blendshape属性，只需连接
            index = existing_target_indices[expr_name]
            print("🔁 已存在: {} → index {}，重新连接输出".format(expr_name, index))

            # 强制连接 worldMesh 到 blendShape 的 inputGeomTarget
            target_attr = "{0}.inputTarget[0].inputTargetGroup[{1}].inputTargetItem[6000].inputGeomTarget".format(
                bs_node, index)
            cmds.connectAttr(mesh_shape + ".worldMesh[0]", target_attr, force=True)
        else:
            # 不存在此blendshape属性，追加新目标
            index = max_index
            max_index += 1
            cmds.blendShape(bs_node, e=True, t=(target_model, index, mesh, 1.0))
            print("➕ 添加: {} → index {}".format(expr_name, index))

def create_blendshape_diff(target_expr_name, source_expr_names, source_model, blendshape_name="autoBlendShape"):
    """
    创建 blendShape 节点并：
      1. 将 target_expr_name 的权重设为 +1，其它 source_expr_names 的权重设为 -1
      2. 断开 blendShape.inputTarget[*].inputGeomTarget 上的 mesh 连接

    参数：
        target_expr_name (str): 目标表达式模型名（权重 +1）
        source_expr_names (list of str or None): 差分源表达式模型名（权重 -1），允许有 None 值，将被自动忽略
        source_model (str): 被变形的目标模型
        blendshape_name (str): blendShape 节点名称（可选）
    返回：
        str: 新创建的 blendShape 节点名
    """

    if not cmds.objExists(source_model):
        raise ValueError("目标网格不存在: {}".format(source_model))

    if not cmds.objExists(target_expr_name):
        raise ValueError("目标表达式模型不存在: {}".format(target_expr_name))

    # 清理输入：忽略 None、空字符串、非存在对象
    cleaned_sources = []
    for src in source_expr_names:
        if src and isinstance(src, str) and cmds.objExists(src):
            cleaned_sources.append(src)
        elif src:
            print("警告: 忽略无效的源表达式: {}".format(src))

    # 构建 blendShape 输入列表（目标表情 + 有效源表情）
    all_targets = [target_expr_name] + cleaned_sources

    # 创建 blendShape 节点
    bs_node = cmds.blendShape(all_targets, source_model, name=blendshape_name)[0]

    # 设置权重并断开 mesh 输入连接
    for idx, tgt in enumerate(all_targets):
        weight_value = 1.0 if idx == 0 else -1.0
        cmds.setAttr(f"{bs_node}.w[{idx}]", weight_value)

        # 构建 inputGeomTarget 路径并断开
        geom_attr = f"{bs_node}.inputTarget[{idx}].inputTargetGroup[0].inputTargetItem[6000].inputGeomTarget"
        if cmds.objExists(geom_attr):
            conns = cmds.listConnections(geom_attr, source=True, destination=False, plugs=True) or []
            for src_plug in conns:
                try:
                    cmds.disconnectAttr(src_plug, geom_attr)
                except Exception:
                    pass  # 可忽略特殊连接失败

    return bs_node



def generate_blendshape_delta_target( target_expr_name, source_expr_names, source_model ):
    """
    创建差值表情模型：
    - 输入一个目标模型名（需已存在于场景中）
    - 输入多个驱动该目标的表情模型名称
    - 输入源基础模型名（将提取其 Orig 形态进行blend）
    """
    if not cmds.objExists(source_model):
        cmds.error("❌ 源模型不存在: {}".format(source_model))
        return
    # 获取Orig节点并复制为 clean 原始形态
    orig_shape = returnShapeOrig(source_model)[1]
    if not orig_shape:
        cmds.error("❌ 无法找到 {} 的Orig节点".format(source_model))
        return
    print(orig_shape)
    original_mesh = extract_clean_mesh_from_transform(orig_shape, name="{}_TMEP_Au".format(target_expr_name))
    if not original_mesh:
        cmds.error("❌ 无法复制 Orig 网格")
        return

    # 创建 BlendShape 驱动节点
    create_blendshape_diff(target_expr_name, source_expr_names, original_mesh, blendshape_name="TEMPcomBsNode")
    # 执行差值生成命令
    print("✅ 差值模型生成: {}".format(original_mesh))

    # 替换目标模型 inMesh

    original_meshShape = returnShapeOrig(original_mesh)[0]
    target_shape = returnShapeOrig(target_expr_name)[0]
    cmds.connectAttr(original_meshShape + ".outMesh", target_shape + ".inMesh", force=True)
    cmds.refresh(force=True)
    print("🔁 成功连接 {} → {}".format(original_meshShape + ".outMesh", target_shape + ".inMesh"))

    # 删除差值模型
    delta_parent = cmds.listRelatives(original_meshShape, parent=True, fullPath=True)
    if delta_parent:
        #cmds.delete(delta_parent[0])
        print("🧹 已清理差值临时模型")

    print("✅ 完成差值替换: {}".format(target_expr_name))

if __name__ == '__main__':
CHARACTER_DNA = r'U:\ywm\MHC\Downloaded\DHI\5jd1XPwC_asset\1k\asset_source\MetaHumans\yy\SourceAssets\yy.dna'
reader = load_dna_reader(CHARACTER_DNA)
calibrated = DNACalibDNAReader(reader)
AUlist = combine_lists_to_dict(calibrated.getPSDRowIndices(), calibrated.getPSDColumnIndices())
AuBsInfo = dict()
BsInfo = dict()
AuBsMapInfo = dict()
for AuIndex in sorted(AUlist.keys()):
    AuBsName = getDNABsName(AuIndex,calibrated)
    # Result: 'MupperLipRaise_MlowerLipDepress_Jopen_R'
    AuBsComName = [getDNABsName(i,calibrated) for i in AUlist[AuIndex]]
    # Result: ['mouth_upperLipRaise_right', 'mouth_lowerLipDepress_right', 'jaw_open']
    AuBsExpName = [calibrated.getRawControlName(i) for i in AUlist[AuIndex]]
    # 得到复合表情受哪些基础表情联合控制
    AuBsInfo[AuIndex] = {AuBsName: AuBsExpName}
    AuBsMapInfo[AuIndex] = {AuBsName: AuBsComName}
for expIndex in range(calibrated.getRawControlCount()):
    expName = calibrated.getRawControlName(expIndex)
    bsName = getDNABsName(expIndex,calibrated)
    BsInfo[expIndex] = {bsName: [expName]}
AllBsInfo = {**BsInfo, **AuBsInfo}
# ---------------------------
# 示例调用
# ---------------------------
#
result_meshes = process_expression_data(AllBsInfo, source_model='pasted__sunshangxiang_L_eyeshadow2')
connect_expression_meshes_to_blendshape('pasted__sunshangxiang_L_eyeshadow2', result_meshes.keys())
for k,v in result_meshes.items():
    if len(v)>1:
        generate_blendshape_delta_target(
        target_expr_name=k,
        source_expr_names=v,
        source_model='pasted__sunshangxiang_L_eyeshadow2'
        )





