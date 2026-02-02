# -*- coding: utf-8 -*-
from __future__ import print_function, division

import os
import json
import re

import maya.cmds as cmds
import maya.mel as mel

# -------- Qt 兼容 --------
try:
    from PySide2 import QtWidgets, QtCore
    import shiboken2 as shiboken
    import maya.OpenMayaUI as omui
except ImportError:
    from PySide6 import QtWidgets, QtCore
    import shiboken6 as shiboken
    import maya.OpenMayaUI as omui

# -------- PyMEL（用于自动查找头部材质球）--------
try:
    import pymel.core as pm
except Exception:
    pm = None

# Python2/3 兼容
try:
    basestring
except NameError:
    basestring = str


# ======================================================================
# 全局配置
# ======================================================================

# 眨眼 JSON 根目录（按镜头号生成 camXXX.json）
JSON_ROOT = r'U:\ywm\wk\eyeblinkTrans'


# ======================================================================
# 通用工具 & Undo 封装
# ======================================================================

def _flatten_value(v):
    """把 getAttr / JSON 的 [x] / [[x]] 压成标量。"""
    if isinstance(v, (list, tuple)) and len(v) == 1:
        return v[0]
    return v


def _ensure_dir(path):
    folder = os.path.dirname(path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)


def _load_json(file_path):
    if not os.path.isfile(file_path):
        raise RuntimeError(u"[JSON] 文件不存在: %s" % file_path)

    try:
        import io
        with io.open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        with open(file_path, "r") as f:
            data = json.load(f)
    return data


def _sanitize_name_component(text):
    base = os.path.splitext(os.path.basename(text))[0]
    base = re.sub(r'[^A-Za-z0-9_]+', '_', base)
    if not base:
        base = "animCurve"
    return base


class UndoChunk(object):
    """把整套操作包进一次 Undo。"""

    def __init__(self, name=u"LayerTexToolOp"):
        self.name = name

    def __enter__(self):
        try:
            cmds.undoInfo(openChunk=True, chunkName=self.name)
        except Exception:
            pass

    def __exit__(self, exc_type, exc, tb):
        try:
            cmds.undoInfo(closeChunk=True)
        except Exception:
            pass


# ======================================================================
# 1. JSON 导出 / 导入（保留完整功能）
# ======================================================================

def _get_selected_channelbox_attrs():
    """
    获取 Channel Box 中当前选中的属性名列表。
    兼容不同 Maya 版本。
    """
    ch = mel.eval('$tmp=$gChannelBoxName;')

    attrs = []
    for flag in ("sma", "ssa", "sha"):
        a = cmds.channelBox(ch, q=True, **{flag: True}) or []
        attrs.extend(a)

    # sna 在低版本可能没有
    try:
        a = cmds.channelBox(ch, q=True, sna=True) or []
        attrs.extend(a)
    except TypeError:
        pass

    seen = set()
    result = []
    for a in attrs:
        if a not in seen:
            seen.add(a)
            result.append(a)
    return result


def export_selected_channels_to_json(file_path):
    """
    导出当前【选择物体】+【Channel Box 选中的属性】到 JSON。
    JSON 结构：
    {
      "__meta__": {"start":101,"end":168,"step":1},
      "nodeFullPath": {
        "attrName": [
          [frame, value],
          ...
        ]
      }
    }
    """
    sel = cmds.ls(sl=True, long=True) or []
    if not sel:
        raise RuntimeError(u"[export] 没有选择任何物体。")

    attrs = _get_selected_channelbox_attrs()
    if not attrs:
        raise RuntimeError(u"[export] Channel Box 中没有选中任何属性。")

    start = int(cmds.playbackOptions(q=True, min=True))
    end   = int(cmds.playbackOptions(q=True, max=True))
    if end < start:
        raise RuntimeError(u"[export] 时间轴范围非法: start=%s, end=%s" % (start, end))

    frames = list(range(start, end + 1))

    data = {
        "__meta__": {
            "start": start,
            "end": end,
            "step": 1
        }
    }

    for node in sel:
        node_dict = data.setdefault(node, {})
        for attr in attrs:
            plug = "%s.%s" % (node, attr)
            if not cmds.objExists(plug):
                cmds.warning(u"[export] 属性不存在，跳过: %s" % plug)
                continue

            samples = []
            for t in frames:
                val = cmds.getAttr(plug, time=t)
                val = _flatten_value(val)
                samples.append([int(t), val])

            node_dict[attr] = samples

    _ensure_dir(file_path)

    try:
        import io
        with io.open(file_path, "w", encoding="utf-8") as f:
            txt = json.dumps(data, ensure_ascii=False, indent=2)
            f.write(txt)
    except Exception:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    channel_count = 0
    for k, v in data.items():
        if k == "__meta__":
            continue
        if isinstance(v, dict):
            channel_count += len(v)

    print(u"[export] 完成，导出通道数量: %d -> %s" % (channel_count, file_path))


def import_channels_from_json(file_path,
                              clear_existing=True,
                              set_timeline=True):
    """
    从 JSON 恢复所有通道：按原节点+属性名逐帧 setKeyframe。
    保留为通用导入工具。
    """
    data = _load_json(file_path)

    meta = data.get("__meta__", {})
    start = meta.get("start", None)
    end   = meta.get("end", None)

    if set_timeline and start is not None and end is not None:
        cmds.playbackOptions(min=start, max=end)

    imported_channels = 0

    for node_name, node_data in data.items():
        if node_name.startswith("__"):
            continue
        if not isinstance(node_data, dict):
            cmds.warning(u"[import] 节点数据不是字典，跳过: %s" % node_name)
            continue

        for attr_name, samples in node_data.items():
            plug = "%s.%s" % (node_name, attr_name)
            if not cmds.objExists(plug):
                cmds.warning(u"[import] 场景中找不到属性，跳过: %s" % plug)
                continue

            if not isinstance(samples, (list, tuple)):
                cmds.warning(u"[import] 通道数据不是列表，跳过: %s" % plug)
                continue

            valid_pairs = []
            for item in samples:
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    frame, value = item
                    try:
                        frame = int(frame)
                        valid_pairs.append([frame, value])
                    except Exception:
                        cmds.warning(u"[import] 非法帧号，跳过: %s in %s" % (item, plug))
                else:
                    cmds.warning(u"[import] 通道 %s 数据项不是 [frame, value]，跳过: %s" %
                                 (plug, item))

            if not valid_pairs:
                continue

            valid_pairs.sort(key=lambda x: x[0])

            if clear_existing:
                min_f = valid_pairs[0][0]
                max_f = valid_pairs[-1][0]
                cmds.cutKey(plug, t=(min_f, max_f), option="keys")

            for frame, value in valid_pairs:
                v = _flatten_value(value)
                try:
                    cmds.setKeyframe(plug, t=frame, v=v)
                except Exception as e:
                    cmds.warning(
                        u"[import] setKeyframe 失败: %s (frame=%s, value=%s) -> %s" %
                        (plug, frame, v, e)
                    )

            imported_channels += 1

    print(u"[import] 完成，从 JSON 导入通道数量: %d" % imported_channels)


def _pick_first_channel(data):
    """
    从 JSON 中挑选第一个有效通道:
    返回: (node_name, attr_name, samples_list)
    """
    for node_name, node_data in data.items():
        if node_name.startswith("__"):
            continue
        if not isinstance(node_data, dict):
            continue

        for attr_name, samples in node_data.items():
            return node_name, attr_name, samples

    raise RuntimeError(u"[import] JSON 中没有找到任何通道数据（除 __meta__ 之外为空）。")


def _parse_json_first_channel(file_path, verbose=True):
    data = _load_json(file_path)

    meta = data.get("__meta__", {})
    start = meta.get("start", None)
    end   = meta.get("end", None)
    step  = meta.get("step", None)

    src_node, src_attr, samples = _pick_first_channel(data)
    if not samples:
        raise RuntimeError(u"[import] 通道 %s.%s 在 JSON 中没有采样数据。" %
                           (src_node, src_attr))

    valid_pairs = []
    for item in samples:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            fr, val = item
            try:
                fr = int(fr)
                valid_pairs.append([fr, val])
            except Exception:
                if verbose:
                    print(u"[import] 跳过非法帧号: %s" % (item,))
        else:
            if verbose:
                print(u"[import] 跳过非 [frame, value] 结构: %s" % (item,))

    if not valid_pairs:
        raise RuntimeError(u"[import] 没有可用的 [frame, value] 数据。")

    valid_pairs.sort(key=lambda x: x[0])
    min_f, max_f = valid_pairs[0][0], valid_pairs[-1][0]

    if verbose:
        print(u"[import] JSON Meta: start=%s  end=%s  step=%s" % (start, end, step))
        print(u"[import] 源通道: %s.%s" % (src_node, src_attr))
        print(u"[import] 样本数量: %d, 帧范围: %s -> %s" %
              (len(valid_pairs), min_f, max_f))

    return valid_pairs, meta, (src_node, src_attr)


def transfer_json_channel_to_attr(file_path,
                                  target_plug,
                                  clear_existing=True,
                                  set_timeline=True,
                                  verbose=True):
    """
    兼容旧接口：把 JSON 中第一个通道迁移到某个属性上（逐帧 setKeyframe）。
    """
    if not isinstance(target_plug, basestring) or "." not in target_plug:
        raise RuntimeError(
            u"[import] target_plug 必须是 'node.attr' 形式，例如 'locator1.translateX'。当前: %s" %
            target_plug
        )

    if not cmds.objExists(target_plug):
        raise RuntimeError(u"[import] 目标属性不存在: %s" % target_plug)

    valid_pairs, meta, src_info = _parse_json_first_channel(file_path, verbose=verbose)
    start = meta.get("start", None)
    end   = meta.get("end", None)

    frames = [p[0] for p in valid_pairs]
    min_f, max_f = frames[0], frames[-1]

    if set_timeline:
        t_min = start if isinstance(start, int) else min_f
        t_max = end   if isinstance(end, int)   else max_f
        cmds.playbackOptions(min=t_min, max=t_max)

    if clear_existing:
        cmds.cutKey(target_plug, t=(min_f, max_f), option="keys")

    for fr, val in valid_pairs:
        v = _flatten_value(val)
        try:
            cmds.setKeyframe(target_plug, t=fr, v=v)
        except Exception as e:
            cmds.warning(
                u"[import] setKeyframe 失败: %s (frame=%s, value=%s) -> %s" %
                (target_plug, fr, v, e)
            )

    if verbose:
        print(u"[import] 完成：共写入关键帧数量 = %d  ->  %s" %
              (len(valid_pairs), target_plug))


# ======================================================================
# 2. animCurve 构建（单一动画曲线驱动多个属性）
# ======================================================================

def _get_animcurve_type_for_attr(attr_plug):
    """根据目标属性类型选择 animCurve 类型。"""
    if not cmds.objExists(attr_plug):
        return "animCurveTU"
    at = cmds.getAttr(attr_plug, type=True)
    if at in ("doubleLinear",):
        return "animCurveTL"
    elif at in ("doubleAngle",):
        return "animCurveTA"
    elif at in ("time",):
        return "animCurveTT"
    else:
        return "animCurveTU"


def _build_animcurve_from_pairs(anim, valid_pairs, verbose=True):
    """
    优先使用 maya.OpenMayaAnim.MFnAnimCurve 批量写 key，
    不可用时回退到 cmds.setKeyframe 循环。
    """
    if not valid_pairs:
        return

    # API 方案
    try:
        import maya.OpenMaya as om
        import maya.OpenMayaAnim as oma
    except Exception:
        om = None
        oma = None

    if om is not None and oma is not None:
        try:
            sel = om.MSelectionList()
            sel.add(anim)
            node = om.MObject()
            sel.getDependNode(0, node)

            fn_dep = om.MFnDependencyNode(node)
            out_plug = fn_dep.findPlug("output", True)

            fn_curve = oma.MFnAnimCurve(out_plug)

            num_keys = fn_curve.numKeys()
            if num_keys:
                fn_curve.remove(0, num_keys - 1)

            time_unit = om.MTime.uiUnit()

            for fr, val in valid_pairs:
                v = float(_flatten_value(val))
                t = om.MTime(float(fr), time_unit)
                fn_curve.addKey(
                    t, v,
                    oma.MFnAnimCurve.kTangentGlobal,
                    oma.MFnAnimCurve.kTangentGlobal
                )

            if verbose:
                print(u"[anim] 使用 OpenMayaAnim 写入 animCurve 关键帧: %s, 数量=%d" %
                      (anim, len(valid_pairs)))
            return
        except Exception as e:
            if verbose:
                print(u"[anim] OpenMayaAnim 写关键帧失败，回退 cmds.setKeyframe: %s" % e)

    # 回退：cmds.setKeyframe
    for fr, val in valid_pairs:
        v = _flatten_value(val)
        cmds.setKeyframe(anim, t=fr, v=v)

    if verbose:
        print(u"[anim] 使用 cmds.setKeyframe 循环写入 animCurve 关键帧: %s, 数量=%d" %
              (anim, len(valid_pairs)))


def apply_json_to_attrs_via_animCurve(file_path,
                                      target_plugs,
                                      animcurve_name=None,
                                      clear_target_keys=True,
                                      set_timeline=True,
                                      reuse_animcurve=True,
                                      verbose=True):
    """
    核心方案：从 JSON 读取第一个通道，生成一条 animCurve，
    再把 animCurve.output 连接到多个属性上。
    """
    if not target_plugs:
        raise RuntimeError(u"[anim] 未提供任何目标属性。")

    valid_targets = []
    for p in target_plugs:
        if not isinstance(p, basestring) or "." not in p:
            cmds.warning(u"[anim] 非法 plug 名称，跳过: %s" % p)
            continue
        if not cmds.objExists(p):
            cmds.warning(u"[anim] 场景中不存在 plug，跳过: %s" % p)
            continue
        valid_targets.append(p)

    if not valid_targets:
        raise RuntimeError(u"[anim] 没有可用的目标属性。")

    valid_pairs, meta, src_info = _parse_json_first_channel(file_path, verbose=verbose)
    frames = [p[0] for p in valid_pairs]
    min_f, max_f = frames[0], frames[-1]
    start = meta.get("start", None)
    end   = meta.get("end", None)

    if set_timeline:
        t_min = start if isinstance(start, int) else min_f
        t_max = end   if isinstance(end, int)   else max_f
        cmds.playbackOptions(min=t_min, max=t_max)

    if not animcurve_name:
        comp = _sanitize_name_component(file_path)
        animcurve_name = "jsonAnimCurve_%s" % comp

    was_suspended = False
    try:
        was_suspended = cmds.refresh(q=True, su=True)
    except Exception:
        was_suspended = False

    try:
        if not was_suspended:
            try:
                cmds.refresh(suspend=True)
            except Exception:
                pass

        # 创建 / 复用 animCurve
        if reuse_animcurve and cmds.objExists(animcurve_name):
            anim = animcurve_name
            if verbose:
                print(u"[anim] 复用已有 animCurve: %s（不重新写关键帧）" % anim)
        else:
            first_target = valid_targets[0]
            curve_type = _get_animcurve_type_for_attr(first_target)
            anim = cmds.createNode(curve_type, name=animcurve_name)
            _build_animcurve_from_pairs(anim, valid_pairs, verbose=verbose)

        # 连接到目标属性
        for plug in valid_targets:
            if clear_target_keys:
                cmds.cutKey(plug, t=(min_f, max_f), option="keys")

            srcs = cmds.listConnections(plug, s=True, d=False, p=True) or []
            for s in srcs:
                try:
                    cmds.disconnectAttr(s, plug)
                except Exception:
                    pass

            try:
                cmds.connectAttr(anim + ".output", plug, f=True)
            except Exception as e:
                cmds.warning(u"[anim] 连接 %s.output -> %s 失败: %s" %
                             (anim, plug, e))

        if verbose:
            print(u"[anim] 完成：animCurve=%s 已连接到 %d 个属性。" %
                  (anim, len(valid_targets)))

        return anim

    finally:
        if not was_suspended:
            try:
                cmds.refresh(suspend=False)
                cmds.refresh()
            except Exception:
                pass


# ======================================================================
# 3. LayeredTexture / File 构建
# ======================================================================

def _is_file_like_node(node):
    """
    判断节点是否为“贴图节点 File-like node”：
    - Maya file
    - Arnold aiImage
    - 或任何包含 fileTextureName / filename 属性的节点
    """
    if not cmds.objExists(node):
        return False
    ntype = cmds.nodeType(node)
    if ntype in ("file", "aiImage", "image"):
        return True
    if cmds.attributeQuery("fileTextureName", n=node, exists=True):
        return True
    if cmds.attributeQuery("filename", n=node, exists=True):
        return True
    return False


def _get_shaders_from_selection():
    """
    旧方案：从当前选择模型里根据 shadingEngine 找 Shader。
    仍然保留此功能。
    """
    sel = cmds.ls(sl=True, long=True) or []
    if not sel:
        raise RuntimeError(u"[shader] 请先选择至少一个模型(Transform/Shape)。")

    shapes = cmds.ls(sel, dag=True, s=True, ni=True, long=True) or []
    if not shapes:
        raise RuntimeError(u"[shader] 选择的物体中没有有效 Shape。")

    shaders = []
    for shp in shapes:
        sgs = cmds.listConnections(shp, type="shadingEngine") or []
        for sg in sgs:
            surf = cmds.listConnections(sg + ".surfaceShader", s=True, d=False) or []
            for sh in surf:
                if sh not in shaders:
                    shaders.append(sh)

    if not shaders:
        raise RuntimeError(u"[shader] 在所选模型上没有找到任何 Shader 节点。")

    return shaders


def _find_file_chains_from_plug(start_plug, max_depth=50, verbose=False):
    """
    从 Shader 属性 plug 出发递归向上查找 file-like 节点。
    返回列表：
    {
        "file_node": file 节点,
        "file_out_plug": file 输出 plug,
        "downstream_plug": file 直接连到的下游 plug
    }
    """
    if not cmds.objExists(start_plug):
        if verbose:
            print(u"[trace] 属性不存在: %s" % start_plug)
        return []

    results = []
    visited_plugs = set()
    queue = [start_plug]

    while queue:
        dst_plug = queue.pop(0)
        if dst_plug in visited_plugs:
            continue
        visited_plugs.add(dst_plug)

        pair_list = cmds.listConnections(dst_plug, s=True, d=False, p=True, c=True) or []
        for i in range(0, len(pair_list), 2):
            p1 = pair_list[i]
            p2 = pair_list[i + 1]

            if p1 == dst_plug:
                src_plug = p2
                real_dst = p1
            elif p2 == dst_plug:
                src_plug = p1
                real_dst = p2
            else:
                continue

            src_node = src_plug.split('.', 1)[0]

            if _is_file_like_node(src_node):
                results.append({
                    "file_node": src_node,
                    "file_out_plug": src_plug,
                    "downstream_plug": real_dst,
                })
                if verbose:
                    print(u"[trace] 找到 file 节点: %s (%s -> %s)" %
                          (src_node, src_plug, real_dst))
                continue

            node_pairs = cmds.listConnections(src_node, s=True, d=False, p=True, c=True) or []
            for j in range(0, len(node_pairs), 2):
                q1 = node_pairs[j]
                q2 = node_pairs[j + 1]

                if q1.split('.', 1)[0] == src_node:
                    up_dst = q1
                elif q2.split('.', 1)[0] == src_node:
                    up_dst = q2
                else:
                    continue

                if up_dst not in visited_plugs and len(visited_plugs) < max_depth:
                    queue.append(up_dst)

    return results


def _insert_layered_texture_for_file_output(file_plug, old_layer_index=1, verbose=True):
    """
    在 file 输出之后插入 layeredTexture：
      原 file -> inputs[old_layer_index].color
      layeredTexture.outColor -> 原所有下游
    """
    if not cmds.objExists(file_plug):
        if verbose:
            print(u"[insert] file 输出属性不存在: %s" % file_plug)
        return None

    file_node = file_plug.split('.', 1)[0]

    pair_list = cmds.listConnections(file_plug, s=False, d=True, p=True, c=True) or []
    if not pair_list:
        if verbose:
            print(u"[insert] %s 没有任何下游连接，跳过。" % file_plug)
        return None

    dest_plugs = []
    for i in range(0, len(pair_list), 2):
        p1 = pair_list[i]
        p2 = pair_list[i + 1]

        if p1 == file_plug:
            dst = p2
        elif p2 == file_plug:
            dst = p1
        else:
            continue
        dest_plugs.append(dst)

    if not dest_plugs:
        if verbose:
            print(u"[insert] %s 未找到有效下游 plug，跳过。" % file_plug)
        return None

    first_dst = dest_plugs[0]
    first_node = first_dst.split('.', 1)[0]
    first_attr = first_dst.split('.', 1)[1]
    if cmds.nodeType(first_node) == "layeredTexture" and "inputs[" in first_attr:
        if verbose:
            print(u"[insert] %s 已连接到现有 layeredTexture: %s，直接复用。" %
                  (file_plug, first_node))
        return first_node

    lt_name = file_node + "_LT"
    lt_node = cmds.shadingNode("layeredTexture", asTexture=True, name=lt_name)

    valid_attr = "%s.inputs[%d].isValid" % (lt_node, old_layer_index)
    if cmds.objExists(valid_attr):
        try:
            cmds.setAttr(valid_attr, 1)
        except Exception:
            pass

    try:
        cmds.connectAttr(file_plug,
                         "%s.inputs[%d].color" % (lt_node, old_layer_index),
                         f=True)
    except Exception as e:
        cmds.warning(u"[insert] 连接 %s -> %s.inputs[%d].color 失败: %s" %
                     (file_plug, lt_node, old_layer_index, e))
        return None

    for dst in dest_plugs:
        try:
            cmds.disconnectAttr(file_plug, dst)
        except Exception:
            pass
        try:
            cmds.connectAttr(lt_node + ".outColor", dst, f=True)
        except Exception as e:
            cmds.warning(u"[insert] 连接 %s.outColor -> %s 失败: %s" %
                         (lt_node, dst, e))

    if verbose:
        print(u"[insert] 已在 %s 与其所有下游之间插入 layeredTexture: %s" %
              (file_plug, lt_node))
    return lt_node


def _copy_inputs_from_old_file_to_new(old_file, new_file):
    """把 old_file 的所有输入连接复制到 new_file。"""
    pair_list = cmds.listConnections(old_file, s=True, d=False, p=True, c=True) or []
    for i in range(0, len(pair_list), 2):
        p1 = pair_list[i]
        p2 = pair_list[i + 1]

        if p1.split('.', 1)[0] == old_file:
            dst_plug = p1
            src_plug = p2
        elif p2.split('.', 1)[0] == old_file:
            dst_plug = p2
            src_plug = p1
        else:
            continue

        attr = dst_plug.split('.', 1)[1]
        new_dst = "%s.%s" % (new_file, attr)
        if cmds.objExists(new_dst):
            try:
                cmds.connectAttr(src_plug, new_dst, f=True)
            except Exception as e:
                cmds.warning(u"[copy] 连接 %s -> %s 失败: %s" %
                             (src_plug, new_dst, e))


def _set_file_texture_path(file_node, texture_path, verbose=True):
    """根据节点类型设置贴图路径。"""
    if not texture_path:
        return
    try:
        if cmds.attributeQuery("fileTextureName", n=file_node, exists=True):
            cmds.setAttr(file_node + ".fileTextureName",
                         texture_path, type="string")
        elif cmds.attributeQuery("filename", n=file_node, exists=True):
            cmds.setAttr(file_node + ".filename",
                         texture_path, type="string")
        else:
            if verbose:
                cmds.warning(u"[path] 节点 %s 不存在 fileTextureName/filename 属性。" %
                             file_node)
    except Exception as e:
        cmds.warning(u"[path] 设置 %s 贴图路径失败: %s" % (file_node, e))


def _add_new_file_to_layered_texture(old_file_node,
                                     lt_node,
                                     file_out_attr="outColor",
                                     texture_path=None,
                                     verbose=True):
    """
    在 layeredTexture 上新增一层：
      - new_file（与 old_file_node 同类型）
      - 复制输入
      - 设置贴图
      - new_file.<file_out_attr> -> lt.inputs[0].color
    """
    if not cmds.objExists(lt_node):
        raise RuntimeError(u"[add] layeredTexture 节点不存在: %s" % lt_node)

    ntype = cmds.nodeType(old_file_node)
    new_file = cmds.shadingNode(ntype, asTexture=True,
                                name=old_file_node + "_extra")

    _copy_inputs_from_old_file_to_new(old_file_node, new_file)
    _set_file_texture_path(new_file, texture_path, verbose=verbose)

    valid0 = "%s.inputs[0].isValid" % lt_node
    if cmds.objExists(valid0):
        try:
            cmds.setAttr(valid0, 1)
        except Exception:
            pass

    color_attr = "%s.inputs[0].color" % lt_node
    file_out_plug = "%s.%s" % (new_file, file_out_attr)
    if not cmds.objExists(file_out_plug):
        outs = cmds.listAttr(new_file, k=True, s=True) or []
        if outs:
            file_out_plug = "%s.%s" % (new_file, outs[0])

    try:
        cmds.connectAttr(file_out_plug, color_attr, f=True)
    except Exception as e:
        cmds.warning(u"[add] 连接新 file %s -> %s 失败: %s" %
                     (file_out_plug, color_attr, e))

    if verbose:
        print(u"[add] 已创建新贴图节点 %s 并连接到 %s.inputs[0].color" %
              (new_file, lt_node))

    return new_file


def _process_shaders_build_layerTex(shaders,
                                    target_attrs=("baseColor", "normalCamera"),
                                    verbose=True):
    """
    通用：给一组 shader 节点构建 LayeredTexture+新 File。
    返回 info 列表，每个 info:
    {
      "shader": shader,
      "shader_attr": attr,
      "file_node": file_node,
      "file_plug": file_plug,
      "layerTex": lt_node,
      "new_file": new_file,
      "control_plug": lt_node + ".inputs[0].alpha"
    }
    """
    TEXTURE_PATHS = {
        "baseColor":   r"X:\Project\wk\sourceimages\chr\wk\tex\master\wukong_B_Color.1001.png",
        "normalCamera": r"X:\Project\wk\sourceimages\chr\wk\tex\master\wukong_B_Norma.1001.png",
    }

    data_list = []

    for shader in shaders:
        for attr in target_attrs:
            shader_plug = "%s.%s" % (shader, attr)
            if not cmds.objExists(shader_plug):
                continue

            if verbose:
                print(u"\n[proc] 处理 Shader 属性: %s" % shader_plug)

            chains = _find_file_chains_from_plug(shader_plug, verbose=verbose)
            if not chains:
                if verbose:
                    print(u"[proc] 在 %s 的链路中没有找到任何 file-like 节点。" %
                          shader_plug)
                continue

            by_file_plug = {}
            for ch in chains:
                f_plug = ch["file_out_plug"]
                by_file_plug.setdefault(f_plug, []).append(ch["downstream_plug"])

            tex_path = TEXTURE_PATHS.get(attr)

            for file_plug, dst_list in by_file_plug.items():
                file_node = file_plug.split('.', 1)[0]
                if verbose:
                    print(u"[proc] file 节点: %s, 输出: %s, 下游连接数: %d" %
                          (file_node, file_plug, len(dst_list)))

                lt_node = _insert_layered_texture_for_file_output(
                    file_plug, old_layer_index=1, verbose=verbose
                )
                if not lt_node:
                    continue

                file_out_attr = file_plug.split('.', 1)[1]
                new_file = _add_new_file_to_layered_texture(
                    file_node,
                    lt_node,
                    file_out_attr=file_out_attr,
                    texture_path=tex_path,
                    verbose=verbose
                )

                info = {
                    "shader": shader,
                    "shader_attr": attr,
                    "file_node": file_node,
                    "file_plug": file_plug,
                    "layerTex": lt_node,
                    "new_file": new_file,
                    "control_plug": lt_node + ".inputs[0].alpha",
                }
                data_list.append(info)

    return data_list


def build_layerTex_for_selection(target_attrs=("baseColor", "normalCamera"),
                                 verbose=True):
    """
    保留的老接口：基于当前选择的模型构建 LayeredTexture。
    """
    shaders = _get_shaders_from_selection()
    return _process_shaders_build_layerTex(shaders, target_attrs, verbose=verbose)


def insert_layerTexture_and_new_file_on_selected(
        target_attrs=("baseColor", "normalCamera"),
        verbose=True):
    """
    老接口：返回 layeredTexture 节点名称列表。
    """
    data_list = build_layerTex_for_selection(target_attrs, verbose=verbose)
    lt_nodes = []
    for d in data_list:
        lt = d["layerTex"]
        if lt not in lt_nodes:
            lt_nodes.append(lt)

    if verbose:
        if lt_nodes:
            print(u"[result] 本次处理的 layeredTexture 节点: %s" %
                  ", ".join(lt_nodes))
        else:
            print(u"[result] 未创建或复用任何 layeredTexture 节点。")
    return lt_nodes


# ======================================================================
# 4. 自动查找头部材质球（pymel 正则）& 一键眨眼管线
# ======================================================================

def _get_head_shaders_by_regex():
    """
    使用 PyMEL 正则直接查找头部 aiStandardSurface：
        face_s = pm.ls(regex="*"+"pasted__pasted__wk_head"+"(\\w*|\\d*|_)",
                       type="aiStandardSurface")
    返回：shader 名称字符串列表。
    """
    if pm is None:
        raise RuntimeError(u"[head] 无法导入 pymel.core，请确认 PyMEL 可用。")

    pattern = "*" + "pasted__pasted__wk_head" + r"(\w*|\d*|_)"  # 按你给的写法
    nodes = pm.ls(regex=pattern, type="aiStandardSurface") or []
    shaders = [n.name() for n in nodes]

    if not shaders:
        raise RuntimeError(u"[head] 未通过名称规则找到任何 aiStandardSurface 头部材质。")

    print(u"[head] 发现头部 Shader: %s" % ", ".join(shaders))
    return shaders


def build_layerTex_for_head_shaders(target_attrs=("baseColor", "normalCamera"),
                                    verbose=True):
    """
    专用：基于“pasted__pasted__wk_head” 命名规则自动找到头部材质球，
    然后构建 LayeredTexture + 新 File。
    """
    shaders = _get_head_shaders_by_regex()
    return _process_shaders_build_layerTex(shaders, target_attrs, verbose=verbose)


def _get_current_shot_name_from_scene():
    """
    从当前场景路径推断镜头号：
    X:\Project\wk\publ\gt_comp\lgt_shot\cam008\cam008_chr_org.ma
    -> 取上一级目录名 cam008
    """
    scene = cmds.file(q=True, sn=True)
    if not scene:
        raise RuntimeError(u"[json] 当前场景尚未保存，无法推断镜头号。")
    shot = os.path.basename(os.path.dirname(scene))
    return shot


def build_json_path_for_current_shot():
    """
    根据 JSON_ROOT 和当前场景推导：
    U:\ywm\wk\eyeblinkTrans\cam008.json
    """
    shot = _get_current_shot_name_from_scene()
    json_path = os.path.join(JSON_ROOT, "%s.json" % shot)
    return json_path, shot


def run_auto_eyeblink_pipeline(verbose=True):
    """
    一键流程（无选择，无输入）：
      1. 根据当前场景推导 JSON 路径。
      2. 用 PyMEL 找到头部 aiStandardSurface。
      3. 为 baseColor / normalCamera 构建 LayeredTexture + 新 File。
      4. 用 JSON 数据生成一条 animCurve，并把 output 连接到
         所有 layeredTexture.inputs[0].alpha 上。
    """
    json_path, shot = build_json_path_for_current_shot()

    if not os.path.isfile(json_path):
        raise RuntimeError(u"[auto] JSON 文件不存在: %s" % json_path)

    if verbose:
        print(u"[auto] 当前镜头: %s" % shot)
        print(u"[auto] 使用 JSON: %s" % json_path)

    with UndoChunk(u"EyeblinkAutoPipeline"):
        infos = build_layerTex_for_head_shaders(
            target_attrs=("baseColor", "normalCamera"),
            verbose=verbose
        )

        control_plugs = []
        for info in infos:
            plug = info.get("control_plug")
            if plug and cmds.objExists(plug):
                control_plugs.append(plug)

        if not control_plugs:
            raise RuntimeError(u"[auto] 没有获得任何可用的 layeredTexture.inputs[0].alpha 属性。")

        if verbose:
            print(u"[auto] 目标属性列表：")
            for p in control_plugs:
                print("    ", p)

        anim = apply_json_to_attrs_via_animCurve(
            json_path,
            control_plugs,
            animcurve_name=None,
            clear_target_keys=True,
            set_timeline=True,
            reuse_animcurve=True,
            verbose=verbose
        )

    if verbose:
        print(u"[auto] 整体完成：animCurve = %s ，驱动属性数量 = %d" %
              (anim, len(control_plugs)))

    return anim, control_plugs


# ======================================================================
# 5. 极简 UI：一个按钮
# ======================================================================

def _get_maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    if ptr is None:
        return None
    return shiboken.wrapInstance(int(ptr), QtWidgets.QWidget)


class EyeblinkOneButtonTool(QtWidgets.QDialog):

    def __init__(self, parent=None):
        super(EyeblinkOneButtonTool, self).__init__(parent)
        self.setObjectName("EyeblinkOneButtonToolDialog")
        self.setWindowTitle(u"Eyeblink 一键挂载工具")
        self.setMinimumWidth(420)
        self._build_ui()
        self._make_connections()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        label_root = QtWidgets.QLabel(
            u"JSON 根目录：%s\n"
            u"规则：根据当前场景路径上一级目录名生成 camXXX.json" % JSON_ROOT
        )
        label_root.setWordWrap(True)

        self.btn_run = QtWidgets.QPushButton(
            u"一键执行：读取 JSON → 创建 LayerTexture/File → 挂载动画曲线"
        )
        self.btn_run.setMinimumHeight(60)

        layout.addWidget(label_root)
        layout.addWidget(self.btn_run)
        layout.addStretch(1)

    def _make_connections(self):
        self.btn_run.clicked.connect(self._on_run_clicked)

    def _on_run_clicked(self):
        try:
            anim, plugs = run_auto_eyeblink_pipeline(verbose=True)
            QtWidgets.QMessageBox.information(
                self,
                u"完成",
                u"已完成眨眼挂载。\nanimCurve: %s\n驱动属性数量: %d"
                % (anim, len(plugs))
            )
        except Exception as e:
            cmds.warning(u"[UI] 一键眨眼失败: %s" % e)
            QtWidgets.QMessageBox.critical(
                self,
                u"错误",
                u"一键眨眼失败：\n%s" % e
            )


_tool_dialog = None


def show_eyeblink_one_button_tool():
    """入口：弹出只有一个按钮的 UI。"""
    global _tool_dialog

    try:
        if _tool_dialog is not None:
            _tool_dialog.close()
            _tool_dialog.deleteLater()
    except Exception:
        pass

    parent = _get_maya_main_window()
    _tool_dialog = EyeblinkOneButtonTool(parent)
    _tool_dialog.show()
    _tool_dialog.raise_()
    _tool_dialog.activateWindow()


# 在 Script Editor 中直接执行可打开 UI：
show_eyeblink_one_button_tool()
