"""
Matrix Ribbon System (MRS) - Tool UI
Version: 7.2.0
Fix: Removed obsolete Loop/Loft checkboxes.
"""

import maya.cmds as cmds
import maya.api.OpenMaya as om
import sys
import os
import importlib
import traceback

try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    try:
        from PySide6 import QtWidgets, QtCore, QtGui
    except ImportError:
        cmds.error("Could not import PySide2 or PySide6.")

CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

import utils
import builder
import manager
import matrix_ribbon_system

# Force Reload for Dev Iteration
importlib.reload(utils)
importlib.reload(builder)
importlib.reload(manager)
importlib.reload(matrix_ribbon_system)

def get_maya_window():
    try:
        app = QtWidgets.QApplication.instance()
        for widget in app.topLevelWidgets():
            if widget.objectName() == "MayaWindow":
                return widget
    except: pass
    return None

def show_error_dialog(message, details=""):
    msg_box = QtWidgets.QMessageBox()
    msg_box.setIcon(QtWidgets.QMessageBox.Critical)
    msg_box.setText(message)
    if details:
        msg_box.setDetailedText(details)
    msg_box.setWindowTitle("MRS Error")
    msg_box.exec_()

def force_reload_plugin():
    PLUGIN_NAME = "py_matrix_ribbon.py"
    PLUGIN_PATH = os.path.join(CURRENT_DIR, PLUGIN_NAME)
    if cmds.pluginInfo("matrixRibbonMesh", query=True, loaded=True):
        try:
            print(f"[MRS] Attempting to unload plugin: {PLUGIN_NAME}")
            cmds.unloadPlugin("matrixRibbonMesh")
        except Exception as e:
            print(f"[MRS] Warning: Could not unload plugin (Nodes in use?): {e}")
            return
    try:
        if os.path.exists(PLUGIN_PATH):
            cmds.loadPlugin(PLUGIN_PATH)
            print(f"[MRS] Plugin reloaded from: {PLUGIN_PATH}")
        else:
            print(f"[MRS] Error: Plugin file not found: {PLUGIN_PATH}")
    except Exception as e:
        print(f"[MRS] Error loading plugin: {e}")

class MatrixRibbonTool(QtWidgets.QWidget):
    WINDOW_NAME = "MatrixRibbonToolUI"
    TITLE = "Matrix Ribbon System V7.2"
    
    def __init__(self, parent=None):
        super(MatrixRibbonTool, self).__init__(parent)
        
        force_reload_plugin()
        
        try:
            self.mrs = matrix_ribbon_system.RibbonRigSystem()
        except Exception as e:
            cmds.warning(f"MRS System Init Warning: {e}")
            
        self.preview_mesh = None
        self.build_ui()
        self.refresh_rig_list()
        
    def build_ui(self):
        self.setWindowTitle(self.TITLE)
        self.resize(350, 550)
        self.setWindowFlags(QtCore.Qt.Window)
        
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        
        header = QtWidgets.QLabel("MRS V7.2 - Optimized Matrix")
        header.setAlignment(QtCore.Qt.AlignCenter)
        header.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 5px; color: #DDD;")
        layout.addWidget(header)
        
        tabs = QtWidgets.QTabWidget()
        layout.addWidget(tabs)
        
        # --- Tab 1: Create ---
        tab_create = QtWidgets.QWidget()
        layout_create = QtWidgets.QVBoxLayout(tab_create)
        tabs.addTab(tab_create, "Create")
        
        grp_sel = QtWidgets.QGroupBox("1. Chains")
        lay_sel = QtWidgets.QVBoxLayout(grp_sel)
        
        self.list_bones = QtWidgets.QListWidget()
        self.list_bones.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.list_bones.setFixedHeight(80)
        lay_sel.addWidget(self.list_bones)
        
        hbox_sel_btns = QtWidgets.QHBoxLayout()
        btn_add = QtWidgets.QPushButton("Add Root")
        btn_add.clicked.connect(self.add_selection)
        btn_clear_sel = QtWidgets.QPushButton("Clear List")
        btn_clear_sel.clicked.connect(self.list_bones.clear)
        hbox_sel_btns.addWidget(btn_add)
        hbox_sel_btns.addWidget(btn_clear_sel)
        lay_sel.addLayout(hbox_sel_btns)
        
        hbox_move = QtWidgets.QHBoxLayout()
        btn_up = QtWidgets.QPushButton("Move Up")
        btn_up.clicked.connect(self.move_item_up)
        btn_down = QtWidgets.QPushButton("Move Down")
        btn_down.clicked.connect(self.move_item_down)
        hbox_move.addWidget(btn_up)
        hbox_move.addWidget(btn_down)
        lay_sel.addLayout(hbox_move)
        
        layout_create.addWidget(grp_sel)
        
        grp_opt = QtWidgets.QGroupBox("2. Options")
        lay_opt = QtWidgets.QVBoxLayout(grp_opt)
        
        hbox_flags = QtWidgets.QHBoxLayout()
        self.chk_fk = QtWidgets.QCheckBox("FK Control")
        self.chk_fk.setChecked(True)
        self.chk_ik = QtWidgets.QCheckBox("IK (Tweak)")
        self.chk_ik.setChecked(True)
        hbox_flags.addWidget(self.chk_fk)
        hbox_flags.addWidget(self.chk_ik)
        lay_opt.addLayout(hbox_flags)
        
        # REMOVED LOFT/LOOP Checkboxes as requested
        
        layout_create.addWidget(grp_opt)
        
        grp_act = QtWidgets.QGroupBox("3. Build")
        lay_act = QtWidgets.QVBoxLayout(grp_act)
        
        self.btn_preview = QtWidgets.QPushButton("1. Preview Mesh")
        self.btn_preview.clicked.connect(self.generate_preview)
        lay_act.addWidget(self.btn_preview)
        
        self.btn_bind = QtWidgets.QPushButton("2. BIND RIG")
        self.btn_bind.setStyleSheet("background-color: #5D99C6; color: white; font-weight: bold; padding: 5px;")
        self.btn_bind.clicked.connect(self.generate_bind)
        lay_act.addWidget(self.btn_bind)
        
        layout_create.addWidget(grp_act)
        layout_create.addStretch()

        # --- Tab 2: Manage ---
        tab_manage = QtWidgets.QWidget()
        layout_manage = QtWidgets.QVBoxLayout(tab_manage)
        tabs.addTab(tab_manage, "Manage")
        
        layout_manage.addWidget(QtWidgets.QLabel("Existing Rigs (Sets):"))
        self.list_rigs = QtWidgets.QListWidget()
        layout_manage.addWidget(self.list_rigs)
        
        btn_refresh = QtWidgets.QPushButton("Refresh List")
        btn_refresh.clicked.connect(self.refresh_rig_list)
        layout_manage.addWidget(btn_refresh)
        
        self.chk_restore = QtWidgets.QCheckBox("Restore Bind Pose on Remove")
        self.chk_restore.setToolTip("Reverts bones to original bind pose on removal.")
        layout_manage.addWidget(self.chk_restore)
        
        btn_remove = QtWidgets.QPushButton("Remove Selected Rig (Safe Unbind)")
        btn_remove.setStyleSheet("background-color: #C65D5D; color: white; font-weight: bold; padding: 5px;")
        btn_remove.clicked.connect(self.remove_rig_from_list)
        layout_manage.addWidget(btn_remove)
        
        layout_manage.addStretch()

    def move_item_up(self):
        row = self.list_bones.currentRow()
        if row > 0:
            item = self.list_bones.takeItem(row)
            self.list_bones.insertItem(row - 1, item)
            self.list_bones.setCurrentRow(row - 1)

    def move_item_down(self):
        row = self.list_bones.currentRow()
        if row < self.list_bones.count() - 1:
            item = self.list_bones.takeItem(row)
            self.list_bones.insertItem(row + 1, item)
            self.list_bones.setCurrentRow(row + 1)

    def get_chains(self):
        chains = []
        for i in range(self.list_bones.count()):
            root = self.list_bones.item(i).text()
            if not cmds.objExists(root): continue
            chain = [root]
            curr = root
            while True:
                children = cmds.listRelatives(curr, children=True, type="joint") or []
                if not children: break
                curr = children[0]
                chain.append(curr)
            chains.append(chain)
        return chains

    def add_selection(self):
        sel = cmds.ls(selection=True, type="joint")
        if not sel:
            cmds.warning("Select Root Joint(s).")
            return
        existing = [self.list_bones.item(i).text() for i in range(self.list_bones.count())]
        for s in sel:
            if s not in existing:
                self.list_bones.addItem(s)

    def generate_preview(self):
        chains = self.get_chains()
        if not chains: 
            cmds.warning("No bones loaded.")
            return
        
        cmds.undoInfo(openChunk=True, chunkName="MRS Preview")
        try:
            if self.preview_mesh and cmds.objExists(self.preview_mesh):
                cmds.delete(self.preview_mesh)
            
            # Loop is now default False, controlled by Attribute Editor later if needed
            mesh, node, w, h = self.mrs.builder.create_preview_mesh(
                chains, 
                width=None, 
                hold_length=None, 
                loop=False 
            )
            self.preview_mesh = mesh
            cmds.select(mesh)
            print(f"[MRS] Preview Generated (Chains:{len(chains)})")
        except Exception as e:
            traceback.print_exc()
            show_error_dialog("Preview Failed", str(e))
        finally:
            cmds.undoInfo(closeChunk=True)

    def generate_bind(self):
        chains = self.get_chains()
        if not chains: return
        if not self.preview_mesh or not cmds.objExists(self.preview_mesh):
            show_error_dialog("Preview Missing", "Please generate a preview mesh first.")
            return
            
        cmds.undoInfo(openChunk=True, chunkName="MRS Bind")
        try:
            # Pass FK/IK flags
            rig_grp = self.mrs.builder.finalize_bind(
                preview_mesh=self.preview_mesh,
                chains=chains,
                enable_fk=self.chk_fk.isChecked(),
                enable_ik=self.chk_ik.isChecked()
            )
            self.preview_mesh = None 
            self.refresh_rig_list()
            self.list_bones.clear()
            cmds.select(rig_grp)
            print(f"[MRS] Bind Complete: {rig_grp}")
        except Exception as e:
            traceback.print_exc()
            show_error_dialog("Bind Failed", str(e))
        finally:
            cmds.undoInfo(closeChunk=True)

    def refresh_rig_list(self):
        self.list_rigs.clear()
        try:
            sets = self.mrs.get_all_rigs()
            for s in sets:
                self.list_rigs.addItem(s)
        except Exception as e:
             print(f"List Refresh Error: {e}")

    def remove_rig_from_list(self):
        item = self.list_rigs.currentItem()
        if not item: return
        set_name = item.text()
        
        confirm = QtWidgets.QMessageBox.question(
            self, 
            "Confirm Remove", 
            f"Remove '{set_name}'?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if confirm != QtWidgets.QMessageBox.Yes:
            return

        cmds.undoInfo(openChunk=True, chunkName="MRS Remove")
        try:
            restore = self.chk_restore.isChecked()
            self.mrs.remove_rig(set_name, restore_pose=restore)
            self.refresh_rig_list()
            print("[MRS] Safe Removal Complete.")
        except Exception as e:
            traceback.print_exc()
            show_error_dialog("Remove Failed", str(e))
        finally:
            cmds.undoInfo(closeChunk=True)

_mrs_window_instance = None

def show():
    global _mrs_window_instance
    maya_win = get_maya_window()
    app = QtWidgets.QApplication.instance()
    for widget in app.topLevelWidgets():
        if widget.objectName() == MatrixRibbonTool.WINDOW_NAME:
            widget.close()
    _mrs_window_instance = MatrixRibbonTool(parent=maya_win)
    _mrs_window_instance.setObjectName(MatrixRibbonTool.WINDOW_NAME)
    _mrs_window_instance.show()

if __name__ == "__main__":
    show()
