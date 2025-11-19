#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: clearBlendShapeAttr.py
@date: 2025/10/9 16:48
@desc: 
"""
# -*- coding: utf-8 -*-
from __future__ import print_function
import re
import math
import maya.cmds as cmds

# ---- 兼容 PySide2 / PySide6（Maya 2025） ----
try:
    from PySide2 import QtWidgets, QtCore
    import shiboken2 as shiboken
    import maya.OpenMayaUI as omui
except ImportError:
    from PySide6 import QtWidgets, QtCore
    import shiboken6 as shiboken
    import maya.OpenMayaUI as omui

# OpenMaya API2 for fast mesh queries
try:
    import maya.api.OpenMaya as om
    OM_AVAILABLE = True
except Exception:
    OM_AVAILABLE = False

# Python2/3 兼容
try:
    basestring
except NameError:
    basestring = str


# ---------------- Helper: OpenMaya / Mesh utilities (新增) ----------------
def _get_mesh_shape(node):
    """
    返回 mesh shape（shape 节点），接受 transform 或 shape 名称。
    """
    if not node:
        return None
    # if it's a transform, find mesh child
    if cmds.objectType(node, isType='transform'):
        shapes = cmds.listRelatives(node, s=True, ni=True, fullPath=True) or []
        for s in shapes:
            if cmds.nodeType(s) == 'mesh':
                return s
        return None
    # if it's already a shape
    if cmds.nodeType(node) == 'mesh':
        return node
    # last attempt: try children shapes
    shapes = cmds.listRelatives(node, s=True, ni=True, fullPath=True) or []
    for s in shapes:
        if cmds.nodeType(s) == 'mesh':
            return s
    return None


def _get_mesh_points(shape):
    """
    使用 API2 高效返回顶点列表 [(x,y,z), ...]。
    如果 OpenMaya 不可用，则退回到慢速 cmds.getAttr(mesh.vtx[*])
    """
    if not shape:
        return None
    # ensure shape is a mesh shape
    shape_node = _get_mesh_shape(shape)
    if not shape_node:
        return None

    if OM_AVAILABLE:
        try:
            sel = om.MSelectionList()
            sel.add(shape_node)
            dag = sel.getDagPath(0)
            fn = om.MFnMesh(dag)
            pts = fn.getPoints(space=om.MSpace.kWorld)
            # convert to simple tuple list
            return [(p.x, p.y, p.z) for p in pts]
        except Exception:
            # fallthrough to cmds fallback
            pass

    # fallback (much slower): use cmds.xform on each vertex
    try:
        vtx_count = cmds.polyEvaluate(shape_node, vertex=True)
        pts = []
        # use getAttr on entire vtx array is not consistent cross-versions; use xform
        for i in range(vtx_count):
            pt = cmds.xform("{}.vtx[{}]".format(shape_node, i), q=True, ws=True, t=True)
            pts.append((pt[0], pt[1], pt[2]))
        return pts
    except Exception:
        return None


def _meshes_different(meshA, meshB, tol=1e-6):
    """
    比较两个 mesh（shape 名或 transform）是否有顶点差异。
    返回 True 表示不同（即存在 delta）。
    """
    a = _get_mesh_points(meshA)
    b = _get_mesh_points(meshB)
    if a is None or b is None:
        # 无法获取点数据 -> 返回 None 等价于“不确定”，此处保守地认为不同
        return True
    if len(a) != len(b):
        return True
    tol2 = tol * tol
    for pa, pb in zip(a, b):
        dx = pa[0] - pb[0]
        dy = pa[1] - pb[1]
        dz = pa[2] - pb[2]
        if (dx*dx + dy*dy + dz*dz) > tol2:
            return True
    return False


# ---------------- Core: Data Query ----------------
def _safe_get_attr(attr):
    try:
        return True, cmds.getAttr(attr)
    except:
        return False, None


def _list_multi_indices(attr):
    try:
        return cmds.getAttr(attr, multiIndices=True) or []
    except:
        return []


def _collect_alias_map(bs):
    """
    构建 {index -> alias} & 明细列表
    - 优先 aliasAttr
    - 同步补齐 weight[*] 上存在但无别名的通道
    """
    idx2alias = {}
    records = []

    pairs = cmds.aliasAttr(bs, q=True) or []
    for i in range(0, len(pairs), 2):
        alias = pairs[i]
        weight_plug = pairs[i + 1]  # 'weight[3]'
        m = re.match(r"weight\[(\d+)\]", weight_plug)
        if not m:
            continue
        idx = int(m.group(1))
        idx2alias[idx] = alias

    # 扫描实际存在的 weight 元素索引，补齐无别名者
    exist_idxs = _list_multi_indices(bs + ".weight")
    for idx in exist_idxs:
        alias = idx2alias.get(idx, None)
        records.append({
            "index": idx,
            "alias": alias,
            "plug_alias": ("%s.%s" % (bs, alias)) if alias else None,
            "plug_weight": "%s.weight[%d]" % (bs, idx),
        })
    return records


def _is_unconnected(plug):
    """
    无任意上游连接（包含动画曲线与任意驱动网络）视为 Unconnected。
    若 plug 为 None（无别名），将使用 weight plug。
    """
    if not plug:
        return True
    src = cmds.listConnections(plug, s=True, d=False) or []
    return len(src) == 0


# ---------------- 新增：基于 inputGeomTarget 的更准确检测 ----------------
def _get_base_shapes_for_geo_index(bs, geo_index):
    """
    寻找 blendShape 在该 geometryIndex 下对应的 base shape（可能为 transform 或 shape）。
    尝试多种方式，尽量稳健。
    """
    # 1) 直接检查 outputGeometry[geo_index] 的下游连接（输出到被驱动的 mesh）
    plug = "{}.outputGeometry[{}]".format(bs, geo_index)
    try:
        shapes = cmds.listConnections(plug, d=True, s=False) or []
        if shapes:
            return shapes
    except Exception:
        pass

    # 2) 使用 blendShape query geometry（可能返回对应几何列表）
    try:
        geo_list = cmds.blendShape(bs, q=True, geometry=True) or []
        geo_indices = cmds.blendShape(bs, q=True, geometryIndices=True) or []
        if geo_list and geo_indices:
            # geo_list 与 geo_indices 对应索引位置
            for i, idx in enumerate(geo_indices):
                if int(idx) == int(geo_index):
                    return [geo_list[i]]
        elif geo_list:
            return geo_list
    except Exception:
        pass

    # 3) 最后：遍历所有 mesh，查看哪些 mesh 的 history 包含该 blendShape
    res = []
    all_meshes = cmds.ls(type='mesh', long=True) or []
    for mesh in all_meshes:
        # listConnections(mesh+'.inMesh') 中可能包含 blendShape 输出
        cons = cmds.listConnections(mesh + ".inMesh", s=True, d=False) or []
        if bs in cons:
            res.append(mesh)
    return res


def _target_has_delta_on_geo(bs, geo_index, tgt_index, tol=1e-6):
    """
    判定单个 geometryIndex 上该 targetIndex 是否存在 delta（修改）：
      - 优先检查 inputPointsTarget / inputComponentsTarget（内部存储的 delta）
      - 如果没有内部 delta，但存在 inputGeomTarget 连接（外部目标网格），则
        将目标网格与 base 网格逐点比较；若任一目标网格不同则判定有 delta。
      - 只有在所有途径均无差异时返回 False（无变化）
    """
    base = "%s.inputTarget[%d].inputTargetGroup[%d]" % (bs, geo_index, tgt_index)

    items = _list_multi_indices(base + ".inputTargetItem")
    if not items:
        return False

    # 找到 base shapes（可能是 transform 或 shape）
    base_shapes = _get_base_shapes_for_geo_index(bs, geo_index) or []

    for it in items:
        pts_attr = "%s.inputTargetItem[%d].inputPointsTarget" % (base, it)
        cmp_attr = "%s.inputTargetItem[%d].inputComponentsTarget" % (base, it)
        geo_attr = "%s.inputTargetItem[%d].inputGeomTarget" % (base, it)

        ok_pts, v_pts = _safe_get_attr(pts_attr)
        if ok_pts and v_pts not in (None, [], ()):
            # 内部显式存储的点 delta（inputPointsTarget）存在 -> 有 delta
            return True

        ok_cmp, v_cmp = _safe_get_attr(cmp_attr)
        if ok_cmp and v_cmp not in (None, [], ()):
            # 内部 component delta（inputComponentsTarget）存在 -> 有 delta
            return True

        # 如果存在外部 target 几何连接，则要做顶点比较（新增逻辑）
        conns = cmds.listConnections(geo_attr, s=True, d=False) or []
        if conns:
            # 对每一个连接的目标 shape，与 base shape 做比较
            for target_shape in conns:
                # 如果找不到 base shape，退回为“有 delta”的保守判断（避免误删）
                if not base_shapes:
                    # 无法定位 base -> 保守认为有 delta
                    return True
                # 比较 target_shape 与任一 base_shape；只要有任一不同即判为有 delta
                different = False
                for base_shape in base_shapes:
                    try:
                        if _meshes_different(base_shape, target_shape, tol=tol):
                            different = True
                            break
                    except Exception:
                        # 若比较失败，则保守认为有 delta
                        different = True
                        break
                if different:
                    return True
            # 所有连接的目标与 base 都相同 -> 继续检查下一个 inputTargetItem（可能有 in-between）
            continue

    # 所有子项均无有效数据或外部目标均与 base 相同 -> 无变化
    return False


def _is_no_delta_across_all_geos(bs, tgt_index):
    """
    仅当“所有 geometryIndices 上都无 delta”才视为 No-delta。
    """
    geos = cmds.blendShape(bs, q=True, geometryIndices=True) or [0]
    for gi in geos:
        if _target_has_delta_on_geo(bs, gi, tgt_index):
            return False
    return True


# ---------------- Core: Deletion ----------------
def _remove_target_everywhere(bs, tgt_index):
    """
    在所有 geometryIndices 上移除 inputTargetGroup[tgt_index]；
    同时移除 weight[tgt_index] 和别名，保证干净一致。
    """
    geos = cmds.blendShape(bs, q=True, geometryIndices=True) or [0]
    # 1) 删除每个几何上的数据组
    for gi in geos:
        grp = "%s.inputTarget[%d].inputTargetGroup[%d]" % (bs, gi, tgt_index)
        if cmds.objExists(grp):
            try:
                cmds.removeMultiInstance(grp, b=True)  # break 连接并移除
            except:
                pass

    # 2) 删除权重数组元素
    wplug = "%s.weight[%d]" % (bs, tgt_index)
    if cmds.objExists(wplug):
        try:
            cmds.removeMultiInstance(wplug, b=True)
        except:
            pass

    # 3) 删除别名（若存在）
    pairs = cmds.aliasAttr(bs, q=True) or []
    for i in range(0, len(pairs), 2):
        alias = pairs[i]
        w = pairs[i + 1]
        m = re.match(r"weight\[(\d+)\]", w)
        if m and int(m.group(1)) == tgt_index:
            try:
                cmds.aliasAttr("%s.%s" % (bs, alias), remove=True)
            except:
                pass
            break


# ---------------- Public Ops ----------------
def prune_unconnected(bs=None, dry_run=True, include_locked=False, skip_names=None):
    """
    删除“未被连接（Unconnected）”的 BS 权重。
    """
    if skip_names is None:
        skip_names = set()

    bs = _ensure_bs_selected(bs)
    items = _collect_alias_map(bs)

    to_del = []
    for it in items:
        idx = it["index"]
        alias = it["alias"] or "weight[%d]" % idx
        plug = it["plug_alias"] if it["plug_alias"] else it["plug_weight"]

        # 锁定检查
        locked = False
        try:
            locked = cmds.getAttr(plug, l=True)
        except:
            locked = False
        if locked and not include_locked:
            continue

        if alias in skip_names:
            continue

        if _is_unconnected(plug):
            to_del.append((idx, alias))

    if dry_run:
        _print_preview(bs, "Unconnected", to_del)
        return to_del

    cmds.undoInfo(openChunk=True, cn="prune_unconnected")
    try:
        for idx, alias in to_del:
            _remove_target_everywhere(bs, idx)
    finally:
        cmds.undoInfo(closeChunk=True)
    _print_done(bs, "Unconnected", to_del)
    return to_del


def prune_no_delta(bs=None, dry_run=True, include_locked=False, skip_names=None, tol=1e-6):
    """
    删除“无变化（No-delta）”的 BS 权重：开启后对模型无任何形变。
    —— 仅当所有几何上都不存在 delta 才删除。
    """
    if skip_names is None:
        skip_names = set()

    bs = _ensure_bs_selected(bs)
    items = _collect_alias_map(bs)

    to_del = []
    for it in items:
        idx = it["index"]
        alias = it["alias"] or "weight[%d]" % idx
        plug = it["plug_alias"] if it["plug_alias"] else it["plug_weight"]

        # 锁定检查
        locked = False
        try:
            locked = cmds.getAttr(plug, l=True)
        except:
            locked = False
        if locked and not include_locked:
            continue

        if alias in skip_names:
            continue

        if _is_no_delta_across_all_geos(bs, idx):
            to_del.append((idx, alias))

    if dry_run:
        _print_preview(bs, "No-Delta", to_del)
        return to_del

    cmds.undoInfo(openChunk=True, cn="prune_no_delta")
    try:
        for idx, alias in to_del:
            _remove_target_everywhere(bs, idx)
    finally:
        cmds.undoInfo(closeChunk=True)
    _print_done(bs, "No-Delta", to_del)
    return to_del


def _ensure_bs_selected(bs):
    if bs and cmds.objExists(bs) and cmds.nodeType(bs) == "blendShape":
        return bs
    sel = cmds.ls(sl=True) or []
    if not sel or cmds.nodeType(sel[0]) != "blendShape":
        raise RuntimeError("请先选中一个 BlendShape 节点（blendShape node）。")
    return sel[0]


def _print_preview(bs, tag, pairs):
    print("===== Dry-Run 预览：%s @ %s  待删 %d =====" % (tag, bs, len(pairs)))
    for idx, alias in pairs:
        print("  - [%3d] %s" % (idx, alias))


def _print_done(bs, tag, pairs):
    print("===== 已删除：%s @ %s  数量 %d =====" % (tag, bs, len(pairs)))
    for idx, alias in pairs:
        print("  - [%3d] %s" % (idx, alias))


# ---------------- Minimal UI（新增 Pick Selected 按钮） ----------------
def _get_maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    return shiboken.wrapInstance(int(ptr), QtWidgets.QWidget)


class BSPruneDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(BSPruneDialog, self).__init__(parent or _get_maya_main_window())
        self.setWindowTitle(u"BlendShape 清理工具（Unconnected / No-Delta）")
        self.setMinimumWidth(520)
        self._build_ui()

    def _build_ui(self):
        lay = QtWidgets.QVBoxLayout(self)

        hl_top = QtWidgets.QHBoxLayout()
        self.bs_line = QtWidgets.QLineEdit()
        self.bs_line.setPlaceholderText(u"留空=使用当前选中的 blendShape 节点")
        hl_top.addWidget(QtWidgets.QLabel(u"目标 BlendShape 节点（blendShape node）"))
        lay.addLayout(hl_top)

        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(self.bs_line)

        # 新增：拾取选中按钮（Pick Selected）
        self.btn_pick = QtWidgets.QPushButton(u"拾取选中")
        self.btn_pick.setToolTip(u"将当前选中的 blendShape 或包含 blendShape 的 shape 的第一个 blendShape 填入")
        hl.addWidget(self.btn_pick)
        lay.addLayout(hl)

        self.cb_dry = QtWidgets.QCheckBox(u"预览（Dry-Run，不真正删除）")
        self.cb_dry.setChecked(True)
        lay.addWidget(self.cb_dry)

        hl2 = QtWidgets.QHBoxLayout()
        self.btn_no_delta = QtWidgets.QPushButton(u"删除无变化（No-Delta）")
        self.btn_unconnected = QtWidgets.QPushButton(u"删除未被连接（Unconnected）")
        hl2.addWidget(self.btn_no_delta)
        hl2.addWidget(self.btn_unconnected)
        lay.addLayout(hl2)

        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        lay.addWidget(self.log)

        self.btn_no_delta.clicked.connect(self._on_no_delta)
        self.btn_unconnected.clicked.connect(self._on_unconnected)
        self.btn_pick.clicked.connect(self._on_pick_selected)

    def _resolve_bs(self):
        name = self.bs_line.text().strip()
        return name if name else None

    def _append_log(self, text):
        self.log.append(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _on_no_delta(self):
        bs = self._resolve_bs()
        try:
            res = prune_no_delta(bs=bs, dry_run=self.cb_dry.isChecked())
            self._append_log(u"[No-Delta] 完成：%d 个条目（预览=%s）" %
                             (len(res), "是" if self.cb_dry.isChecked() else "否"))
        except Exception as e:
            self._append_log(u"[No-Delta] 错误：%s" % e)

    def _on_unconnected(self):
        bs = self._resolve_bs()
        try:
            res = prune_unconnected(bs=bs, dry_run=self.cb_dry.isChecked())
            self._append_log(u"[Unconnected] 完成：%d 个条目（预览=%s）" %
                             (len(res), "是" if self.cb_dry.isChecked() else "否"))
        except Exception as e:
            self._append_log(u"[Unconnected] 错误：%s" % e)

    def _on_pick_selected(self):
        sel = cmds.ls(sl=True) or []
        if not sel:
            self._append_log(u"[Pick] 未检测到选中项。")
            return
        node = sel[0]
        # 若选中的是 blendShape 节点
        if cmds.nodeType(node) == "blendShape":
            self.bs_line.setText(node)
            self._append_log(u"[Pick] 填入 blendShape 节点：%s" % node)
            return
        # 否则尝试从 shape 的历史中寻找 blendShape
        shapes = cmds.listRelatives(node, s=True, ni=True, fullPath=True) or []
        found = None
        for s in shapes:
            hist_bs = cmds.ls(cmds.listHistory(s) or [], type='blendShape') or []
            if hist_bs:
                found = hist_bs[0]
                break
        if found:
            self.bs_line.setText(found)
            self._append_log(u"[Pick] 从选中对象历史找到 blendShape：%s" % found)
        else:
            # 进一步尝试：如果直接选择的 node 可能是 shape 名称而非 transform
            hist_bs = cmds.ls(cmds.listHistory(node) or [], type='blendShape') or []
            if hist_bs:
                found = hist_bs[0]
                self.bs_line.setText(found)
                self._append_log(u"[Pick] 从选中 shape 历史找到 blendShape：%s" % found)
                return
            self._append_log(u"[Pick] 未找到对应的 blendShape（请直接选中 blendShape 节点或带有 blendShape 的 shape/transform）。")


# 入口
_dialog_ref = None
def show_bs_cleaner_ui():
    global _dialog_ref
    if _dialog_ref is None or not _dialog_ref.isVisible():
        _dialog_ref = BSPruneDialog()
    _dialog_ref.show()
    _dialog_ref.raise_()
    _dialog_ref.activateWindow()
    return _dialog_ref
