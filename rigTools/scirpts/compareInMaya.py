#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: compareInMaya.py
@date: 2025/07/14 13:29 (modified 2025)
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om2

try:
    from maya.api.OpenMayaUI import MQtUtil
except ImportError:
    from maya.OpenMayaUI import MQtUtil

try:
    from PySide2 import QtWidgets, QtCore, QtGui
    import shiboken2 as shiboken
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui
    import shiboken6 as shiboken


class MDColors(object):
    PRIMARY = "#64D2B9"
    PRIMARY_DARK = "#55B69F"
    PRIMARY_LIGHT = "#3C577A"
    SECONDARY = "#EB886B"
    SURFACE = "#4A4A4A"
    BACKGROUND = "#3C3C3C"
    BACKGROUND_DARK = "#323232"
    ERROR = "#E88B8B"
    ERROR_LIGHT = "#5C3B3B"
    WARNING = "#FFC400"
    SUCCESS = "#69F0AE"
    SUCCESS_LIGHT = "#425A46"
    TEXT_PRIMARY = "#F5F5F5"
    TEXT_SECONDARY = "#BDBDBD"
    TEXT_HINT = "#9E9E9E"
    DIVIDER = "#6E6E6E"


# ------------------------- Utility functions -------------------------

def get_name_without_namespace(name):
    return name.split(":")[-1]


def get_transform_from_shape(shape):
    parents = cmds.listRelatives(shape, parent=True, fullPath=False) or []
    return parents[0] if parents else shape


def get_shape_node(node):
    shapes = cmds.listRelatives(node, children=True, shapes=True, ni=1, fullPath=True) or []
    return shapes[0] if shapes else None


def compare_vertex_positions(s1, s2):
    sel = om2.MSelectionList()
    sel.add(s1)
    sel.add(s2)
    path1, path2 = sel.getDagPath(0), sel.getDagPath(1)
    m1, m2 = om2.MFnMesh(path1), om2.MFnMesh(path2)
    pts1, pts2 = m1.getPoints(om2.MSpace.kWorld), m2.getPoints(om2.MSpace.kWorld)

    if len(pts1) != len(pts2):
        return None, len(pts1), len(pts2)

    threshold = 1e-4
    diffs = [p1.distanceTo(p2) for p1, p2 in zip(pts1, pts2) if p1.distanceTo(p2) > threshold]

    rate = float(len(diffs)) / len(pts1) if pts1 else 0.0

    if diffs:
        min_diff = min(diffs)
        max_diff = max(diffs)
        return rate, min_diff, max_diff

    return rate, 0.0, 0.0


def match_hierarchy_recursive(ref, tgt, lookup, out):
    refs = cmds.listRelatives(ref, children=True, type="transform") or []
    tgts = cmds.listRelatives(tgt, children=True, type="transform") or []
    matched = set()

    for r in refs:
        key = get_name_without_namespace(r)
        if key in lookup:
            t = lookup[key]
            matched.add(t)
            try:
                cmds.reorder(t, b=1)
            except Exception:
                pass
            rs, ts = get_shape_node(r), get_shape_node(t)
            if rs and ts:
                if ts.split('|')[-1] in rs.split('|')[-1]:
                    matched.add(ts)
                    orig = ts + "Orig"
                    if cmds.objExists(orig):
                        diff = compare_vertex_positions(rs, orig)
                        if diff and (diff[0] is None or diff[0] > 0):
                            out["Diff"].append((rs, orig, diff))
                else:
                    out["Ref"].append(rs.split('|')[-1])
                    out["Tgt"].append(ts.split('|')[-1])
            match_hierarchy_recursive(r, t, lookup, out)
        else:
            out["Ref"].append(r)

    for t in tgts:
        if t not in matched:
            out["Tgt"].append(t)


def match_hierarchy(ref_grp, tgt_grp):
    all_tgts = cmds.listRelatives(tgt_grp, allDescendents=True, type="transform") or []
    lookup = {get_name_without_namespace(n): n for n in all_tgts}
    out = {"Ref": [], "Tgt": [], "Diff": []}
    match_hierarchy_recursive(ref_grp, tgt_grp, lookup, out)
    return out


# ------------------------- UI widgets -------------------------


class MDClickableLabel(QtWidgets.QLabel):
    doubleClicked = QtCore.Signal(str)

    def __init__(self, text, target, label_type="primary", parent=None):
        super(MDClickableLabel, self).__init__(text, parent)
        self.target = target
        self.label_type = label_type
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self._setup_style()

    def set_text_and_target(self, text, target):
        self.setText(text)
        self.target = target

    def _setup_style(self):
        color_map = {
            "primary": (MDColors.PRIMARY, MDColors.PRIMARY_LIGHT),
            "error": (MDColors.ERROR, MDColors.ERROR_LIGHT),
            "success": (MDColors.SUCCESS, MDColors.SUCCESS_LIGHT),
        }
        color, bg = color_map.get(self.label_type, (MDColors.TEXT_PRIMARY, MDColors.SURFACE))
        style = (
            "QLabel {{ color:{0}; background-color:{1}; border:1px solid {0}; "
            "border-radius:14px; padding:4px 12px; font-size:10pt; font-weight:500; }} "
            "QLabel:hover {{ background-color:{0}; color:{2}; }}".format(
                color, bg, MDColors.BACKGROUND_DARK
            )
        )
        self.setStyleSheet(style)

    def mouseDoubleClickEvent(self, ev):
        self.doubleClicked.emit(self.target)
        super(MDClickableLabel, self).mouseDoubleClickEvent(ev)


class MDDataCard(QtWidgets.QFrame):
    def __init__(self, title, value, subtitle=None, color_type="primary", parent=None):
        super(MDDataCard, self).__init__(parent)
        self._setup_ui(title, value, subtitle, color_type)

    def _setup_ui(self, title, value, subtitle, color_type):
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 8, 12, 8)

        title_lbl = QtWidgets.QLabel(title)
        title_lbl.setStyleSheet("color:{0}; font-size:10pt; font-weight:500;".format(MDColors.TEXT_SECONDARY))
        layout.addWidget(title_lbl)

        v_color = {
            "error": MDColors.ERROR,
            "warning": MDColors.WARNING,
            "success": MDColors.SUCCESS,
        }.get(color_type, MDColors.PRIMARY)
        value_lbl = QtWidgets.QLabel(str(value))
        value_lbl.setStyleSheet("color:{0}; font-size:14pt; font-weight:600;".format(v_color))
        layout.addWidget(value_lbl)

        if subtitle:
            sub_lbl = QtWidgets.QLabel(subtitle)
            sub_lbl.setStyleSheet("color:{0}; font-size:9pt;".format(MDColors.TEXT_HINT))
            layout.addWidget(sub_lbl)

        self.setStyleSheet(
            "QFrame {{ background-color:{0}; border:1px solid {1}; border-radius:8px; }}".format(
                MDColors.BACKGROUND, MDColors.DIVIDER
            )
        )


# ------------------------- Main dialog -------------------------


class CompareUI(QtWidgets.QDialog):
    def __init__(self, parent=None):
        if parent is None:
            ptr = MQtUtil.mainWindow()
            parent = shiboken.wrapInstance(int(ptr), QtWidgets.QWidget)

        super(CompareUI, self).__init__(parent)
        self.ref_grp = None
        self.tgt_grp = None
        self.setWindowTitle(u"资产信息对比工具")
        # 初始大小，但用户可自由调整窗口大小
        self.resize(1200, 800)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("QDialog {{ background-color:{0}; color:{1}; }}".format(MDColors.BACKGROUND_DARK, MDColors.TEXT_PRIMARY))

        top_widget = self._create_top_bar()
        self.list_ref = self._create_list_widget()
        self.list_tgt = self._create_list_widget()
        self.list_diff = self._create_list_widget()

        # 使列表支持水平/垂直自适应伸缩
        for lw in (self.list_ref, self.list_tgt, self.list_diff):
            lw.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            lw.setWordWrap(True)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet(
            "QSplitter::handle {{ background-color:{0}; border-radius:4px; margin:2px; }} QSplitter::handle:hover {{ background-color:{1}; }}".format(
                MDColors.DIVIDER, MDColors.PRIMARY
            )
        )

        # 使用 groupbox 标题仅中文
        splitter.addWidget(self._create_group_box(u"参考未匹配", self.list_ref, MDColors.ERROR))
        splitter.addWidget(self._create_group_box(u"绑定未匹配", self.list_tgt, MDColors.PRIMARY))
        splitter.addWidget(self._create_group_box(u"差异分析", self.list_diff, MDColors.WARNING))

        # 赋予 splitter 强制伸缩因子，确保差异分析窗格占更多空间并随窗口拉伸
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 2)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.addWidget(top_widget)
        main_layout.addWidget(splitter, 1)
        self._populate_empty_state()

    def _create_top_bar(self):
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        analyze_button = QtWidgets.QPushButton(u"分析所选")
        try:
            analyze_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_CommandLink))
        except Exception:
            pass
        analyze_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        analyze_button.setStyleSheet(
            "QPushButton {{ background-color:{0}; color:white; border:none; border-radius:8px; padding:8px 16px; font-size:11pt; font-weight:600; }} QPushButton:hover {{ background-color:{1}; }}".format(
                MDColors.PRIMARY, MDColors.PRIMARY_DARK
            )
        )
        analyze_button.clicked.connect(self.analyze_selection)

        refresh_button = QtWidgets.QPushButton(u"刷新")
        try:
            refresh_button.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_BrowserReload))
        except Exception:
            pass
        refresh_button.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        refresh_button.setStyleSheet(
            "QPushButton {{ background-color:{0}; color:{1}; border:none; border-radius:8px; padding:8px 16px; font-size:11pt; font-weight:600; }} QPushButton:hover {{ background-color:{2}; }}".format(
                MDColors.SURFACE, MDColors.TEXT_PRIMARY, MDColors.PRIMARY_LIGHT
            )
        )
        refresh_button.clicked.connect(self.refresh)

        self.ref_label = MDClickableLabel(u"参考: 未选择", None, "error")
        self.tgt_label = MDClickableLabel(u"目标: 未选择", None, "success")
        self.ref_label.doubleClicked.connect(self.select_node)
        self.tgt_label.doubleClicked.connect(self.select_node)

        # 将 top bar 的控件加入布局
        for w in (analyze_button, refresh_button, self.ref_label, self.tgt_label):
            layout.addWidget(w, 0, QtCore.Qt.AlignVCenter)

        layout.addStretch(1)
        return widget

    def _create_list_widget(self):
        lw = QtWidgets.QListWidget()
        lw.setStyleSheet(
            "QListWidget {{ background-color:{0}; border:none; border-radius:8px; padding:2px; }} QListWidget::item {{ border:none; padding:0px; margin:0px 0; }} QListWidget::item:selected {{ background-color:transparent; }}".format(
                MDColors.BACKGROUND
            )
        )
        lw.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        lw.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        return lw

    def _create_group_box(self, title, widget, accent):
        gb = QtWidgets.QGroupBox(title)
        gb.setStyleSheet(
            "QGroupBox {{ background-color:{0}; border:2px solid {1}; border-radius:12px; font-size:14pt; font-weight:600; color:{1}; padding-top:20px; }} QGroupBox::title {{ subcontrol-origin:margin; subcontrol-position:top left; left:16px; top:8px; padding:4px 8px; background-color:{1}; color:{2}; border-radius:4px; }}".format(
                MDColors.SURFACE, accent, MDColors.BACKGROUND_DARK
            )
        )
        layout = QtWidgets.QVBoxLayout(gb)
        layout.setContentsMargins(12, 24, 12, 12)
        layout.addWidget(widget)
        return gb

    # --- Business logic ----------------------------------------------------

    def analyze_selection(self):
        selection = cmds.ls(sl=True, type="transform")
        if len(selection) != 2:
            cmds.warning(u"请选择两个组进行对比：一个带命名空间（参考），一个不带（目标）。")
            return

        ref = [s for s in selection if ":" in s]
        tgt = [s for s in selection if ":" not in s]
        if not ref or not tgt:
            cmds.warning(u"选择不符合要求。必须一个带命名空间，一个不带。")
            return

        self.ref_grp, self.tgt_grp = ref[0], tgt[0]
        self.ref_label.set_text_and_target(u"参考: {0}".format(self.ref_grp), self.ref_grp)
        self.tgt_label.set_text_and_target(u"目标: {0}".format(self.tgt_grp), self.tgt_grp)
        self.refresh()

    def highlight(self, nodes, mode):
        idx = 13 if mode == "Ref" else 6
        for n in nodes:
            if cmds.objExists(n):
                s = get_shape_node(n)
                if s and cmds.attributeQuery("overrideEnabled", node=s, exists=True):
                    try:
                        cmds.setAttr("{0}.overrideEnabled".format(s), 1)
                        cmds.setAttr("{0}.overrideColor".format(s), idx)
                    except Exception:
                        pass

    def refresh(self):
        if not (self.ref_grp and self.tgt_grp):
            cmds.warning(u"请先选择参考组和目标组进行分析。")
            self._populate_empty_state()
            return

        if not (cmds.objExists(self.ref_grp) and cmds.objExists(self.tgt_grp)):
            cmds.warning(u"参考组或目标组在场景中不存在。")
            return

        data = match_hierarchy(self.ref_grp, self.tgt_grp)

        for lw in (self.list_ref, self.list_tgt, self.list_diff):
            lw.clear()

        self._populate_list(self.list_ref, data["Ref"], "Ref", u"无未匹配项")
        self._populate_list(self.list_tgt, data["Tgt"], "Tgt", u"无未匹配项")

        count_mismatch_items = [d for d in data["Diff"] if d[2][0] is None]
        pos_diff_items = [d for d in data["Diff"] if d[2][0] is not None and d[2][0] > 0.0001]

        pos_diff_items.sort(key=lambda x: x[2][0], reverse=True)

        all_diff_items = count_mismatch_items + pos_diff_items

        if all_diff_items:
            for item_data in all_diff_items:
                s, o, diff_tuple = item_data

                if diff_tuple[0] is None:
                    _, ref_count, tgt_count = diff_tuple
                    widget = self._create_count_mismatch_widget(s, o, ref_count, tgt_count)
                else:
                    rate, min_diff, max_diff = diff_tuple
                    try:
                        print(s, o, "rate:", "{:.4%}".format(float(rate)), "min:", "{:.6f}".format(float(min_diff)), "max:", "{:.6f}".format(float(max_diff)))
                    except Exception:
                        print(s, o, "rate:", rate, "min:", min_diff, "max:", max_diff)
                    widget = self._create_diff_widget(s, o, rate, min_diff, max_diff)

                item = QtWidgets.QListWidgetItem()
                item.setSizeHint(widget.sizeHint())
                self.list_diff.addItem(item)
                self.list_diff.setItemWidget(item, widget)
        else:
            self._add_empty_message(self.list_diff, u"无明显差异项或点数不匹配")

    # --- Helpers -----------------------------------------------------------

    def _populate_empty_state(self):
        for lw in (self.list_ref, self.list_tgt, self.list_diff):
            lw.clear()
            self._add_empty_message(lw, u"请先进行分析")

    def _add_empty_message(self, lw, msg):
        item = QtWidgets.QListWidgetItem(msg)
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = item.font()
        font.setItalic(True)
        item.setFont(font)
        item.setForeground(QtGui.QColor(MDColors.TEXT_HINT))
        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
        lw.addItem(item)

    def _populate_list(self, lw, nodes, mode, empty_msg):
        if nodes:
            for n in sorted(nodes):
                widget = self._create_unmatched_widget(n, mode)
                item = QtWidgets.QListWidgetItem()
                item.setSizeHint(widget.sizeHint())
                lw.addItem(item)
                lw.setItemWidget(item, widget)
            self.highlight(nodes, mode)
        else:
            self._add_empty_message(lw, empty_msg)

    def _create_unmatched_widget(self, node_name, mode):
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("background-color:transparent;")
        layout = QtWidgets.QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        label_type = "error" if mode == "Ref" else "primary"
        label = MDClickableLabel(get_name_without_namespace(node_name), node_name, label_type)
        label.doubleClicked.connect(self.select_node)
        layout.addWidget(label)
        return frame

    def _create_count_mismatch_widget(self, s, o, ref_count, tgt_count):
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("QFrame {{ background-color:{0}; border:2px solid {1}; border-radius:8px; padding:8px; }}".format(MDColors.ERROR_LIGHT, MDColors.ERROR))
        v_layout = QtWidgets.QVBoxLayout(frame)
        v_layout.setSpacing(12)
        v_layout.setContentsMargins(12, 12, 12, 12)

        name_s = get_transform_from_shape(s)
        name_o = get_transform_from_shape(o.replace("Orig", ""))

        lbl1 = MDClickableLabel(u"参考: {0}".format(get_name_without_namespace(name_s)), name_s, "error")
        lbl2 = MDClickableLabel(u"绑定: {0}".format(get_name_without_namespace(name_o)), name_o, "success")
        lbl1.doubleClicked.connect(self.select_node)
        lbl2.doubleClicked.connect(self.select_node)

        for l in (lbl1, lbl2):
            v_layout.addWidget(l)

        cards = QtWidgets.QHBoxLayout()
        cards.setSpacing(8)
        cards.addWidget(MDDataCard(u"参考点数", ref_count, color_type="error"))
        cards.addWidget(MDDataCard(u"绑定点数", tgt_count, color_type="error"))
        v_layout.addLayout(cards)
        return frame

    def _create_diff_widget(self, s, o, rate, min_diff, max_diff):
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("QFrame {{ background-color:{0}; border:1px solid {1}; border-radius:8px; padding:8px; }}".format(MDColors.SURFACE, MDColors.DIVIDER))
        v_layout = QtWidgets.QVBoxLayout(frame)
        v_layout.setSpacing(12)
        v_layout.setContentsMargins(12, 12, 12, 12)

        name_s = get_transform_from_shape(s)
        name_o = get_transform_from_shape(o.replace("Orig", ""))

        lbl1 = MDClickableLabel(u"参考: {0}".format(get_name_without_namespace(name_s)), name_s, "error")
        lbl2 = MDClickableLabel(u"绑定: {0}".format(get_name_without_namespace(name_o)), name_o, "success")
        lbl1.doubleClicked.connect(self.select_node)
        lbl2.doubleClicked.connect(self.select_node)

        for l in (lbl1, lbl2):
            v_layout.addWidget(l)

        cards = QtWidgets.QHBoxLayout()
        cards.setSpacing(8)

        try:
            rate_text = "{:.4%}".format(float(rate))
        except Exception:
            rate_text = str(rate)

        try:
            min_text = "{:.4f}".format(float(min_diff))
        except Exception:
            min_text = str(min_diff)

        try:
            max_text = "{:.4f}".format(float(max_diff))
        except Exception:
            max_text = str(max_diff)

        cards.addWidget(MDDataCard(u"差异率", rate_text, color_type="warning"))
        cards.addWidget(MDDataCard(u"最小差异", min_text))
        cards.addWidget(MDDataCard(u"最大差异", max_text))
        v_layout.addLayout(cards)
        return frame

    def select_node(self, name):
        if name and cmds.objExists(name):
            cmds.select(name, r=True)
            try:
                cmds.setFocus("viewPanes")
            except Exception:
                pass


# ------------------------- Launcher ---------------------------------------


def launch_compare_ui():
    global _compare_ui_window
    try:
        if _compare_ui_window and isinstance(_compare_ui_window, QtWidgets.QDialog):
            _compare_ui_window.close()
            _compare_ui_window.deleteLater()
    except (NameError, RuntimeError):
        pass

    _compare_ui_window = CompareUI()
    _compare_ui_window.show()


if __name__ == "__main__":
    launch_compare_ui()
