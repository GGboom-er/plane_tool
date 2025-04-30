import re
from itertools import combinations
import maya.cmds as cmds
_WHITELIST = A

# ------------------------------------------------------------
# 1.  基本映射与工具
# ------------------------------------------------------------
_PREFIX = {
    'NS': 'nose', 'NK': 'neck', 'M': 'mouth', 'B': 'brow',
    'C' : 'cheek', 'E': 'eye', 'J': 'jaw', 'H': 'head',
}

_BRAISE_MAP = {
    'IN' : ('brow_raiseIn_', lambda s: s),  # L / R
    'OUT': ('brow_raiseOuter_', lambda s: 'left' if s == 'L' else 'right'),
}

# 需要生成局部倒序的组合对
_REVERSAL_PAIRS = {
    frozenset({'Mtowards', 'Mfunnel'}),
    frozenset({'NSwrinkle', 'McornerDepress'}),
    frozenset({'MlowerLipDepress', 'MupperLipRaise'}),  # ⇐ 新增
}

_JAW_FIXED = {
    'jaw_open', 'jaw_fwd', 'jaw_back', 'jaw_left', 'jaw_right',
    'jaw_clench_L', 'jaw_clench_R', 'jaw_chinCompress_L', 'jaw_chinCompress_R',
}


def _raw_suffix( name ):          return name.rsplit('_', 1)[-1] if '_' in name else ''


def _side_word_long( sfx ):       return 'left' if sfx[-1] in 'Ll' else 'right'


def _expand( seg ):
    """把驼峰段映射到官方 leaf 名"""
    if seg == 'Mpurse':            return 'mouth_lipsPurse'
    if seg == 'Mtowards':          return 'mouth_lipsTowards'
    if seg == 'Mfunnel':           return 'mouth_funnel'
    if seg == 'Mdimple':           return 'mouth_dimple'
    if seg == 'Mstretch':          return 'mouth_stretch'
    if seg == 'Mtighten':          return 'mouth_lipsTighten'
    if seg == 'MlowerLipDepress':  return 'mouth_lowerLipDepress'
    key = max((k for k in _PREFIX if seg.startswith(k)), key=len)
    return f"{_PREFIX[key]}_{seg[len(key):]}"


def _bubble_funnel( seq ):
    """把 Mfunnel 左移到 Mpurse/Mtowards 前（官方顺序）"""
    if 'Mpurse' in seq:  # 口袋优先，不动
        return list(seq)
    seq = list(seq)
    changed = True
    while changed:
        changed = False
        for i in range(1, len(seq)):
            if ('funnel' in seq[i].lower()
                    and 'funnel' not in seq[i - 1].lower()
                    and seq[i - 1] != 'McornerPull'):
                seq[i - 1], seq[i] = seq[i], seq[i - 1]
                changed = True
    return seq


def _add( out, item ):
    if item in _WHITELIST and item not in out:
        out.append(item)


def _add_side_variant( out, combo, raw_suffix ):
    """若后缀是 UL/UR/DL/DR → 再追加一个 _L/_R 简写 leaf"""
    if len(raw_suffix) == 2 and raw_suffix[-1] in 'LR':
        _add(out, f'{combo}_{raw_suffix[-1]}')


# ------------------------------------------------------------
# 2.  主函数
# ------------------------------------------------------------
def decompose_alias( alias: str ):
    """
    将 MetaHuman blendShape alias 拆成若干候选并与白名单求交。
    返回唯一、保持生成顺序的列表。
    """
    # ---- 0. Braise_*_(IN|OUT)(L/R) --------------------------
    m = re.match(r'^Braise_([A-Z]\w+)_(IN|OUT)([LR])$', alias)
    if m:
        eye_seg, io, side = m.groups()
        out = []
        _add(out, alias)
        _add(out, f'{_expand(eye_seg)}_{side}')
        _add(out, f"{_BRAISE_MAP[io][0]}{_BRAISE_MAP[io][1](side)}")
        return out

    # ---- 0-bis. mouth_sharpCornerPull_[LR] ------------------
    m = re.match(r'^mouth_sharpCornerPull_([LR])$', alias)
    if m:
        side = m.group(1)
        out = []
        for x in (alias, f'MsharpCornerPull_Jopen_{side}', 'jaw_open'):
            _add(out, x)
        return out

    # ---- 0-ter. brow_raiseIn/Outer_* 仅返回自身 -------------
    if re.match(r'^brow_raise(In|Outer)_(left|right|[LR])$', alias):
        return [alias] if alias in _WHITELIST else []

    # ---------- A. 蛇形 / jaw 固定 ---------------------------
    if alias in _JAW_FIXED or alias[0].islower():
        return [a for a in _simple_rules(alias) if a in _WHITELIST]

    # ---------- B. 驼峰主体 ---------------------------------
    body, raw = alias.rsplit('_', 1)
    core, ext = body.split('__', 1) if '__' in body else (body, '')
    parts = core.split('_')

    out, seen = [], set()

    def add( x ):
        _add(out, x)

    # B-1. leaf -------------
    for seg in parts:
        if seg.lower() in ('jopen', 'jopenextreme'):
            continue
        base = _expand(seg)
        add(f'{base}_{raw}')
        if raw[-1] in 'LR':
            add(f'{base}_{_side_word_long(raw)}')
        if base.startswith('jaw_'):  # jaw_left / right
            add(base)
        if raw == 'cor':
            add(base)

    # helper — 组合 + 左右 variant + 局部倒序
    def emit( segs, suffix ):
        combo = '_'.join(segs)
        add(f'{combo}{suffix}')
        if suffix.startswith('_') and '__' not in suffix:
            _add_side_variant(out, combo, suffix[1:])
        # 局部倒序
        for rp in _REVERSAL_PAIRS:
            if rp.issubset(segs):
                a, b = tuple(rp)
                if segs.index(a) < segs.index(b):
                    sw = [b if s == a else a if s == b else s for s in segs]
                    combo_sw = '_'.join(sw)
                    add(f'{combo_sw}{suffix}')
                    if suffix.startswith('_') and '__' not in suffix:
                        _add_side_variant(out, combo_sw, suffix[1:])

    # B-2. 普通 / tag 组合 ----
    n = len(parts)
    for L in range(2, n + 1):
        for idxs in combinations(range(n), L):
            segs = [parts[i] for i in idxs]
            if any(s.lower() in ('jopen', 'jopenextreme') for s in segs):
                continue
            purse = 'Mpurse' in segs
            towd = 'Mtowards' in segs
            funnel = 'Mfunnel' in segs
            tighten = 'Mtighten' in segs
            dimple = 'Mdimple' in segs
            stretch = 'Mstretch' in segs
            # both original order & bubble-funnel order
            for order in (segs, _bubble_funnel(segs)):
                emit(order, f'_{raw}')
                if purse and towd:
                    if tighten:
                        t = 'puckerTighten' if not funnel else 'ohTighten'
                    elif dimple:
                        t = 'dimplePucker' if not funnel else 'dimpleOh'
                    elif stretch:
                        t = 'mouthStretchPucker' if not funnel else 'mouthStretchOh'
                    else:
                        t = 'pucker' if not funnel else 'oh'
                    if 'McornerPull' in order:
                        t = 'cornerPull' + t[0].upper() + t[1:]
                    emit(order, f'__{t}_{raw}')
                if funnel and {'MupperLipRaise', 'MlowerLipDepress'}.issubset(order):
                    emit(order, f'__funnelWide_{raw}')

    # ---------- C. Jopen / JopenExtreme ---------------------
    def handle( kind, open_alias ):
        k_lower = kind.lower()
        if k_lower not in core.lower() and not ext.lower().endswith(k_lower):
            return
        base = [p for p in parts if p.lower() != k_lower]
        m = len(base)
        for L in range(1, m + 1):
            for idxs in combinations(range(m), L):
                segs = [base[i] for i in idxs]
                purse = 'Mpurse' in segs
                towd = 'Mtowards' in segs
                funnel = 'Mfunnel' in segs
                tighten = 'Mtighten' in segs
                dimple = 'Mdimple' in segs
                stretch = 'Mstretch' in segs
                emit(segs, f'_{kind}_{raw}')
                if kind == 'Jopen' and purse and towd:
                    if tighten:
                        t = 'puckerTighten' if not funnel else 'ohTighten'
                    elif dimple:
                        t = 'dimplePucker' if not funnel else 'dimpleOh'
                    elif stretch:
                        t = 'mouthStretchPucker' if not funnel else 'mouthStretchOh'
                    else:
                        t = 'pucker' if not funnel else 'oh'
                    emit(segs, f'_{kind}__{t}JawOpen_{raw}')
        add(open_alias)
        # Jleft/Jright 派生
        if any(p.startswith('Jleft') for p in parts):  add('Jleft_Jopen_cor')
        if any(p.startswith('Jright') for p in parts):  add('Jright_Jopen_cor')

    handle('Jopen', 'jaw_open')
    handle('JopenExtreme', 'jaw_openExtreme_cor')

    # ---------- D. 原 alias ---------------------------------
    add(alias)
    return out


# ------------------------------------------------------------
# 3.  蛇形规则（全部小写 / *_cor / *Full）
# ------------------------------------------------------------
def _simple_rules( name: str ):
    res = [name]
    raw = _raw_suffix(name)
    if name.startswith('jaw_open') and name != 'jaw_open':
        res.append('jaw_open')
    if 'Full' in name:
        base = name.replace('Full', '')
        res.append(base.replace('_' + raw, f'_{_side_word_long(raw)}'))
    if name.endswith('_cor'):
        stem = name[:-4]
        res = [f'{stem}_left', f'{stem}_right', name]
    return res

#获取 blendshape 节点目标属性的权重索引
def get_blendshape_weight_index( bs_node, target_name ):
    """
    获取 blendshape 节点目标属性的权重索引
    :param bs_node: blendshape 节点名称 (如: 'blendShape1')
    :param target_name: 目标属性名称 (如: 'A') 或权重属性全名 (如: 'weight[0]')
    :return: 权重索引 (找不到返回 -1)
    """
    # 验证节点有效性
    if not cmds.objExists(bs_node):
        cmds.warning(f"节点 {bs_node} 不存在")
        return -1

    # 获取所有目标别名和权重属性
    alias_list = cmds.aliasAttr(bs_node, q=True) or []

    # 将别名列表转换为字典 {权重属性: 别名}
    alias_dict = {}
    for i in range(0, len(alias_list), 2):
        weight_attr = alias_list[i + 1]  # 如: "weight[0]"
        alias_name = alias_list[i]  # 如: "A"
        alias_dict[weight_attr] = alias_name

    # 处理直接输入权重属性的情况 (如: "weight[2]")
    if target_name.startswith("weight["):
        return int(target_name.split("[")[1].split("]")[0])

    # 查找匹配的权重属性
    for weight_attr, alias in alias_dict.items():
        if alias == target_name:
            return int(weight_attr.split("[")[1].split("]")[0])

    # 额外检查输入是否为未被别名的原始属性
    all_weights = cmds.listAttr(bs_node, multi=True) or []
    for attr in all_weights:
        if attr.startswith("weight[") and attr == target_name:
            return int(attr.split("[")[1].split("]")[0])

    cmds.warning(f"未找到目标属性: {target_name} in {bs_node}")
    return -1
#获取bs激活状态的bs属性
def get_bs_named_attributes_with_value_one( bs_node=None ):
    """
    获取blendShape节点中值为1的命名属性列表（如 "eyeClose"，而非 "weight[0]"）
    参数：
        bs_node (str/None): 指定的blendShape节点，若为None则检查所有节点
    返回：
        list: 包含属性名称的列表（如 ["smile", "blink"]）
    """

    def _get_alias_attributes( node ):
        # 获取节点所有别名属性（别名与实际属性的映射）
        aliases = cmds.aliasAttr(node, q=True) or []
        attr_map = {}
        for i in range(0, len(aliases), 2):
            alias = aliases[i]
            attr = aliases[i + 1]
            attr_map[attr] = alias
        return attr_map

    # 获取目标blendShape节点列表
    target_nodes = []
    if bs_node:
        if cmds.objExists(bs_node) and cmds.nodeType(bs_node) == "blendShape":
            target_nodes = [bs_node]
        else:
            cmds.warning(f"无效的blendShape节点: {bs_node}")
            return []
    else:
        target_nodes = cmds.ls(type="blendShape") or []

    result = []
    for node in target_nodes:
        # 获取属性别名映射
        attr_alias_map = _get_alias_attributes(node)
        if not attr_alias_map:
            continue

        # 检查每个属性值
        for attr, alias in attr_alias_map.items():
            try:
                value = cmds.getAttr(f"{node}.{attr}")
                if abs(value - 1.0) < 1e-5:  # 浮点容差
                    result.append(alias)
            except:
                continue

    return result
if __name__ == '__main__':
    expressionsList = (cmds.listAttr('CTRL_expressions', userDefined=True))
    filtered = [x for x in _WHITELIST if not (x and x[0].isupper())]

    attrDict = dict()
    for i in expressionsList:
        cmds.setAttr('CTRL_expressions.' + i, 1)
        value = get_bs_named_attributes_with_value_one(selected_bs[0])

        cmds.setAttr('CTRL_expressions.' + i, 0)
        if value == []:
            continue
        elif value in filtered:
            continue
        attrDict[value[0]] = i

    meshName = ['head_lod0_mesh']
    bsNode = 'head_lod0_mesh_blendShapes'
    for bsName in attrDict.keys():
        splitBSNameList = decompose_alias(bsName)
        sdkList = [attrDict[splitBSName] for splitBSName in splitBSNameList]
        [cmds.setAttr('CTRL_expressions.' + i, 0) for i in expressionsList]
        [cmds.setAttr('CTRL_expressions.' + i, 1) for i in sdkList]
        temp = cmds.duplicate(meshName, n=bsName, f=1, rc=1)
        tempShape = cmds.listRelatives(temp[0], s=1, ni=1)
        index = get_blendshape_weight_index(bsNode, bsName)
        cmds.connectAttr(tempShape + '.outMesh',
                         bsNode + '.inputTarget[0].inputTargetGroup[' + index + '].inputTargetItem[6000].inputGeomTarget')
        cmds.delete(temp)









