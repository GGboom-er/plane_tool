"""
Matrix Ribbon System (MRS) - Tool UI
Version: 19.0.0
"""
import maya.cmds as cmds
import sys
import os
import importlib
import traceback
from contextlib import contextmanager

try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    try:
        from PySide6 import QtWidgets, QtCore
    except ImportError:
        raise ImportError("MRS requires PySide2 or PySide6 (included with Maya).")

CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path: sys.path.append(CURRENT_DIR)

import utils
import builder
import manager
import matrix_ribbon_system

# Global reference to prevent Garbage Collection from destroying the UI
_mrs_window_instance = None

def _reload_all():
    """Reload all MRS modules in dependency order."""
    for mod in [utils, builder, manager, matrix_ribbon_system]:
        importlib.reload(mod)


def get_maya_window():
    app = QtWidgets.QApplication.instance()
    for widget in app.topLevelWidgets():
        if widget.objectName() == "MayaWindow": return widget
    return None

def show_error(msg, detail=""):
    box = QtWidgets.QMessageBox()
    box.setIcon(QtWidgets.QMessageBox.Critical)
    box.setText(msg)
    box.setDetailedText(detail)
    box.setWindowTitle("MRS Error")
    box.exec_()


@contextmanager
def _undo_chunk(name):
    """Context manager for Maya undo chunks with automatic error display."""
    cmds.undoInfo(openChunk=True, chunkName=name)
    try:
        yield
    except Exception as e:
        traceback.print_exc()
        show_error(f"{name} Error", str(e))
    finally:
        cmds.undoInfo(closeChunk=True)

def force_reload_plugin():
    PLUGIN = "py_matrix_ribbon.py"
    PATH = os.path.join(CURRENT_DIR, PLUGIN)
    
    if cmds.pluginInfo(PLUGIN, q=True, loaded=True):
        try: cmds.unloadPlugin(PLUGIN)
        except Exception as e: 
            print(f"[MRS] Plugin Unload Warning: {e}")
            return

    if os.path.exists(PATH):
        try: cmds.loadPlugin(PATH)
        except Exception as e: print(f"[MRS] Plugin Load Error: {e}")

class MatrixRibbonTool(QtWidgets.QWidget):
    WINDOW_NAME = "MatrixRibbonToolUI"
    
    def __init__(self, parent=None):
        super(MatrixRibbonTool, self).__init__(parent)
        force_reload_plugin()
        self.mrs = matrix_ribbon_system.RibbonRigSystem()
        self.build_ui()
        self.refresh_list()
        
    def build_ui(self):
        self.setWindowTitle("Ribbon System Tools")
        self.resize(300, 450)
        self.setWindowFlags(QtCore.Qt.Window)

        main_lay = QtWidgets.QVBoxLayout(self)
        main_lay.addWidget(self._build_section())
        main_lay.addWidget(self._manage_section())
        main_lay.addStretch()

    def _build_section(self):
        grp = QtWidgets.QGroupBox("1. Build")
        lay = QtWidgets.QVBoxLayout(grp)

        # Opts row 1: FK / IK / Follow (Mesh)
        h_opts = QtWidgets.QHBoxLayout()
        self.chk_fk = QtWidgets.QCheckBox("FK")
        self.chk_fk.setChecked(True)
        self.chk_ik = QtWidgets.QCheckBox("IK")
        self.chk_ik.setChecked(True)
        self.chk_follow = QtWidgets.QCheckBox("Follow")
        self.chk_follow.setChecked(False)
        self.chk_follow.setToolTip("Add Follow_Mesh toggle to FK controls (requires Parent Object)")
        
        h_opts.addWidget(self.chk_fk)
        h_opts.addWidget(self.chk_ik)
        h_opts.addWidget(self.chk_follow)
        h_opts.addStretch()
        lay.addLayout(h_opts)


        # Parent Object
        h_parent = QtWidgets.QHBoxLayout()
        lbl_parent = QtWidgets.QLabel("Parent:")
        self.txt_parent = QtWidgets.QLineEdit()
        self.txt_parent.setReadOnly(True)
        self.txt_parent.setPlaceholderText("None (Auto-detect from bone parent)")
        btn_pick = QtWidgets.QPushButton("<<")
        btn_pick.setFixedWidth(30)
        btn_pick.setToolTip("Pick parent object from selection")
        btn_pick.clicked.connect(self.on_pick_parent)
        h_parent.addWidget(lbl_parent)
        h_parent.addWidget(self.txt_parent)
        h_parent.addWidget(btn_pick)
        lay.addLayout(h_parent)

        # Buttons
        btn_prev = QtWidgets.QPushButton("A. Preview from Selection")
        btn_prev.clicked.connect(self.on_preview)
        lay.addWidget(btn_prev)

        btn_bind = QtWidgets.QPushButton("B. BIND RIG")
        btn_bind.setStyleSheet("background-color: #5D99C6; color: white; font-weight: bold; padding: 6px;")
        btn_bind.clicked.connect(self.on_bind)
        lay.addWidget(btn_bind)

        btn_proxy = QtWidgets.QPushButton("C. Create Weighted Proxy Only")
        btn_proxy.clicked.connect(self.on_proxy)
        lay.addWidget(btn_proxy)

        return grp

    def _manage_section(self):
        grp = QtWidgets.QGroupBox("2. Manage")
        lay = QtWidgets.QVBoxLayout(grp)

        self.list_rigs = QtWidgets.QListWidget()
        self.list_rigs.setFixedHeight(120)
        lay.addWidget(self.list_rigs)

        h_man = QtWidgets.QHBoxLayout()
        btn_ref = QtWidgets.QPushButton("Refresh")
        btn_ref.clicked.connect(self.refresh_list)
        self.chk_res = QtWidgets.QCheckBox("Restore Pose")
        
        h_man.addWidget(btn_ref)
        h_man.addWidget(self.chk_res)
        lay.addLayout(h_man)

        btn_rem = QtWidgets.QPushButton("Remove Selected Rig")
        btn_rem.setStyleSheet("background-color: #C65D5D; color: white;")
        btn_rem.clicked.connect(self.on_remove)
        lay.addWidget(btn_rem)

        return grp

    def on_pick_parent(self):
        sel = cmds.ls(sl=True)
        if sel:
            self.txt_parent.setText(sel[0])
        else:
            self.txt_parent.clear()

    def on_preview(self):
        base_text = "Ribbon"
        while True:
            text, ok = QtWidgets.QInputDialog.getText(self, "Name", "Base Name:", text=base_text)
            if not ok or not text: return
            base = text.strip()
            
            with _undo_chunk("MRS Preview"):
                try:
                    parent_obj = self.mrs.process_preview_generation(base)
                    if parent_obj:
                        self.txt_parent.setText(parent_obj)
                    print(f"[MRS] Preview Generated: {base}")
                    break
                except Exception as e:
                    if "already exists" in str(e).lower():
                        # 直接静默复用重命名输入窗口，不再弹出错误提示
                        base_text = base
                    else:
                        show_error("Preview Error", str(e))
                        break

    def on_bind(self):
        try:
            ctx = self.mrs.get_bind_context()
        except Exception as e:
            return show_error("Bind Error", str(e))

        parent_obj = self.txt_parent.text().strip() or None

        if ctx["mode"] == "UPDATE":
            base = ctx["base_name"]
            msg = f"Update '{base}'?\nFK: {self.chk_fk.isChecked()}\nIK: {self.chk_ik.isChecked()}\nFollow: {self.chk_follow.isChecked()}"
            if QtWidgets.QMessageBox.question(self, "Update", msg) != QtWidgets.QMessageBox.Yes: return

            with _undo_chunk("MRS Update"):
                try:
                    self.mrs.process_update_rig(
                        base_name=base,
                        enable_fk=self.chk_fk.isChecked(),
                        enable_ik=self.chk_ik.isChecked(),
                        enable_follow=self.chk_follow.isChecked(),
                        parent_obj=parent_obj
                    )
                    self.refresh_list()
                except Exception as e:
                    show_error("Update Error", str(e))
        else:
            with _undo_chunk("MRS Bind"):
                try:
                    self.mrs.bind_from_preview(
                        preview_mesh=ctx["t_node"],
                        chains=ctx["chains"],
                        enable_fk=self.chk_fk.isChecked(),
                        enable_ik=self.chk_ik.isChecked(),
                        parent_object=parent_obj,
                        enable_follow=self.chk_follow.isChecked()
                    )
                    self.refresh_list()
                except Exception as e:
                    show_error("Bind Error", str(e))

    def on_proxy(self):
        is_pure_ik = self.chk_ik.isChecked() and not self.chk_fk.isChecked()
        with _undo_chunk("MRS Proxy"):
            try:
                self.mrs.process_proxy_generation(is_pure_ik)
                print("[MRS] Proxy Created.")
            except Exception as e:
                show_error("Proxy Error", str(e))

    def on_remove(self):
        # Priority 1: Scene Selection
        scene_sel = cmds.ls(sl=True)
        set_name = utils.RigUtils.get_rig_from_selection(scene_sel)
        
        # Priority 2: UI List Selection
        if not set_name:
            item = self.list_rigs.currentItem()
            if item: set_name = item.text()
        
        if not set_name: return cmds.warning("Select Rig (in Viewport or List).")
        
        if QtWidgets.QMessageBox.question(self, "Remove", f"Delete {set_name}?") != QtWidgets.QMessageBox.Yes: return
        
        with _undo_chunk("MRS Remove"):
            self.mrs.remove_rig(set_name, self.chk_res.isChecked())
            self.refresh_list()

    def refresh_list(self):
        self.list_rigs.clear()
        for s in self.mrs.get_all_rigs():
            self.list_rigs.addItem(s)

def show():
    global _mrs_window_instance
    _reload_all()

    win = get_maya_window()
    if not win: return

    # Close existing
    for w in QtWidgets.QApplication.instance().topLevelWidgets():
        if w.objectName() == MatrixRibbonTool.WINDOW_NAME: w.close()

    _mrs_window_instance = MatrixRibbonTool(parent=win)
    _mrs_window_instance.setObjectName(MatrixRibbonTool.WINDOW_NAME)
    _mrs_window_instance.show()

if __name__ == "__main__":
    show()