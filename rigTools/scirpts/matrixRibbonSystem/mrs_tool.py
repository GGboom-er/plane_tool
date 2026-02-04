"""
Matrix Ribbon System (MRS) - Tool UI
Version: 8.0.0
Optimized: Decoupled UI logic, lean architecture.
"""
import maya.cmds as cmds
import sys
import os
import importlib
import traceback

try:
    from PySide2 import QtWidgets, QtCore
except ImportError:
    try:
        from PySide6 import QtWidgets, QtCore
    except ImportError:
        pass

CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path: sys.path.append(CURRENT_DIR)

import utils
import builder
import manager
import matrix_ribbon_system
from utils import MrsNaming

# Force Reload
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
    box.setText(msg); box.setDetailedText(detail)
    box.setWindowTitle("MRS Error")
    box.exec_()

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
        self.setWindowTitle("MRS V8.0 - Matrix Ribbon")
        self.resize(300, 450)
        self.setWindowFlags(QtCore.Qt.Window)
        
        main_lay = QtWidgets.QVBoxLayout(self)
        
        # Header
        lbl = QtWidgets.QLabel("MRS V8.0 - Optimized")
        lbl.setAlignment(QtCore.Qt.AlignCenter)
        lbl.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px; color: #DDD;")
        main_lay.addWidget(lbl)
        
        # Build Group
        grp_build = QtWidgets.QGroupBox("1. Build")
        lay_build = QtWidgets.QVBoxLayout(grp_build)
        
        # Opts
        h_opts = QtWidgets.QHBoxLayout()
        self.chk_fk = QtWidgets.QCheckBox("FK"); self.chk_fk.setChecked(True)
        self.chk_ik = QtWidgets.QCheckBox("IK"); self.chk_ik.setChecked(True)
        h_opts.addWidget(self.chk_fk); h_opts.addWidget(self.chk_ik); h_opts.addStretch()
        lay_build.addLayout(h_opts)
        
        # Buttons
        btn_prev = QtWidgets.QPushButton("A. Preview from Selection")
        btn_prev.clicked.connect(self.on_preview)
        lay_build.addWidget(btn_prev)
        
        btn_bind = QtWidgets.QPushButton("B. BIND RIG")
        btn_bind.setStyleSheet("background-color: #5D99C6; color: white; font-weight: bold; padding: 6px;")
        btn_bind.clicked.connect(self.on_bind)
        lay_build.addWidget(btn_bind)
        
        # Proxy Section
        btn_proxy = QtWidgets.QPushButton("C. Create Weighted Proxy Only")
        btn_proxy.clicked.connect(self.on_proxy)
        lay_build.addWidget(btn_proxy)
        
        main_lay.addWidget(grp_build)
        
        # Manage Group
        grp_man = QtWidgets.QGroupBox("2. Manage")
        lay_man = QtWidgets.QVBoxLayout(grp_man)
        
        self.list_rigs = QtWidgets.QListWidget()
        self.list_rigs.setFixedHeight(120)
        lay_man.addWidget(self.list_rigs)
        
        h_man = QtWidgets.QHBoxLayout()
        btn_ref = QtWidgets.QPushButton("Refresh")
        btn_ref.clicked.connect(self.refresh_list)
        self.chk_res = QtWidgets.QCheckBox("Restore Pose")
        h_man.addWidget(btn_ref); h_man.addWidget(self.chk_res)
        lay_man.addLayout(h_man)
        
        btn_rem = QtWidgets.QPushButton("Remove Selected Rig")
        btn_rem.setStyleSheet("background-color: #C65D5D; color: white;")
        btn_rem.clicked.connect(self.on_remove)
        lay_man.addWidget(btn_rem)
        
        main_lay.addWidget(grp_man)
        main_lay.addStretch()

    def on_preview(self):
        sel = cmds.ls(sl=True, type="transform")
        if not sel: return cmds.warning("Select Root Joints.")
        
        chains = utils.RigUtils.get_chains_from_selection(sel)
        if not chains: return cmds.warning("No chains found.")
        
        text, ok = QtWidgets.QInputDialog.getText(self, "Name", "Base Name:", text="Ribbon")
        if not ok or not text: return
        base = text.strip()
        
        # Check Conflict
        if cmds.objExists(f"{base}{MrsNaming.RIG_SET}"):
            return QtWidgets.QMessageBox.warning(self, "Conflict", "Rig exists.")
            
        # Clean Old Preview
        p_mesh = f"{base}{MrsNaming.MESH_PREVIEW}"
        p_node = f"{base}{MrsNaming.NODE_PREVIEW}"
        if cmds.objExists(p_mesh): cmds.delete(p_mesh)
        if cmds.objExists(p_node): cmds.delete(p_node)
        
        cmds.undoInfo(openChunk=True, chunkName="MRS Preview")
        try:
            mesh, _, _, _ = self.mrs.create_preview_mesh(chains, base_name=base)
            cmds.select(mesh)
            print(f"[MRS] Preview: {base}")
        except Exception as e:
            traceback.print_exc()
            show_error("Preview Error", str(e))
        finally: cmds.undoInfo(closeChunk=True)

    def on_bind(self):
        sel = cmds.ls(sl=True)
        if not sel: return show_error("Select Preview or Rig.")
        
        # Path A: Update Existing
        rig_set = utils.RigUtils.get_rig_from_selection(sel)
        if rig_set:
            self._update_rig(rig_set)
            return

        # Path B: New Bind (from Preview)
        raw_sel = sel[0]
        t_node = None
        s_node = None
        
        if cmds.nodeType(raw_sel) == "transform":
            t_node = raw_sel
            shapes = cmds.listRelatives(raw_sel, s=True)
            if shapes: s_node = shapes[0]
        elif cmds.nodeType(raw_sel) == "mesh":
            s_node = raw_sel
            parents = cmds.listRelatives(raw_sel, p=True)
            if parents: t_node = parents[0]
            
        if not s_node or not t_node:
             return show_error("Invalid Selection (Mesh/Transform required).")
            
        # Extract Node from Shape History
        node = None
        hist = cmds.listHistory(s_node) or []
        for h in hist:
            if cmds.nodeType(h) == "matrixRibbonMesh":
                node = h; break
        
        if not node: return show_error("Invalid Selection (No Driver Node).")
        
        chains = utils.RigUtils.get_chains_from_ribbon_node(node)
        if not chains: return show_error("Chain Data Missing.")
        
        # Get Base Name from Transform
        base = "Ribbon"
        if cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=t_node, exists=True):
            base = cmds.getAttr(f"{t_node}.{MrsNaming.ATTR_BASE_NAME}")
        
        cmds.undoInfo(openChunk=True, chunkName="MRS Bind")
        try:
            self.mrs.bind_from_preview(t_node, chains, 
                                     self.chk_fk.isChecked(), 
                                     self.chk_ik.isChecked())
            self.refresh_list()
        except Exception as e:
            traceback.print_exc()
            show_error("Bind Error", str(e))
        finally: cmds.undoInfo(closeChunk=True)

    def _update_rig(self, rig_set):
        base = rig_set.replace(MrsNaming.RIG_SET, "")
        
        # Confirm
        msg = f"Update '{base}'?\nFK: {self.chk_fk.isChecked()}\nIK: {self.chk_ik.isChecked()}"
        if QtWidgets.QMessageBox.question(self, "Update", msg) != QtWidgets.QMessageBox.Yes: return
        
        # Find Components
        follow_mod = f"{base}{MrsNaming.MESH_FOLLOW}"
        if not cmds.objExists(follow_mod):
            # Search Geo Set
            geo_set = f"{base}{MrsNaming.GEO_SET}"
            if cmds.objExists(geo_set):
                for m in (cmds.sets(geo_set, q=True) or []):
                    if MrsNaming.MESH_FOLLOW in m: follow_mod = m; break
        
        if not cmds.objExists(follow_mod): return show_error("Substrate Mesh Missing.")
        
        # Get Chains via Driver
        chains = []
        if cmds.attributeQuery(MrsNaming.ATTR_DRIVER_CONN, node=follow_mod, exists=True):
            drv = cmds.listConnections(f"{follow_mod}.{MrsNaming.ATTR_DRIVER_CONN}")
            if drv: chains = utils.RigUtils.get_chains_from_ribbon_node(drv[0])
            
        if not chains: return show_error("Chain Data Lost.")
        
        cmds.undoInfo(openChunk=True, chunkName="MRS Update")
        try:
            self.mrs.bind_from_preview(
                preview_mesh=None,
                chains=chains,
                enable_fk=self.chk_fk.isChecked(),
                enable_ik=self.chk_ik.isChecked(),
                update_mode=True,
                existing_follow_mesh=follow_mod,
                existing_base_name=base
            )
            self.refresh_list()
        except Exception as e:
            traceback.print_exc()
            show_error("Update Error", str(e))
        finally: cmds.undoInfo(closeChunk=True)

    def on_proxy(self):
        sel = cmds.ls(sl=True)
        if not sel: return show_error("Select Mesh or Rig Part.")
        
        target = None
        # 1. Check Rig Context
        rig_set = utils.RigUtils.get_rig_from_selection(sel)
        if rig_set:
            base = rig_set.replace(MrsNaming.RIG_SET, "")
            # Try finding FollowMod
            cand = f"{base}{MrsNaming.MESH_FOLLOW}"
            if cmds.objExists(cand): target = cand
            else:
                # Search Geo Set
                geo_set = f"{base}{MrsNaming.GEO_SET}"
                if cmds.objExists(geo_set):
                    for m in (cmds.sets(geo_set, q=True) or []):
                        if MrsNaming.MESH_FOLLOW in m: target = m; break
        
        # 2. Direct Selection
        if not target: target = sel[0]
        
        # Validate & Find Driver
        node = None
        shape = target
        if cmds.nodeType(target) == "transform":
            s = cmds.listRelatives(target, s=True)
            if s: shape = s[0]
            
        # Try history (Preview)
        hist = cmds.listHistory(shape) or []
        for h in hist:
            if cmds.nodeType(h) == "matrixRibbonMesh": node = h; break
            
        # Try Connection (FollowMod)
        if not node and cmds.attributeQuery(MrsNaming.ATTR_DRIVER_CONN, node=target, exists=True):
            c = cmds.listConnections(f"{target}.{MrsNaming.ATTR_DRIVER_CONN}")
            if c: node = c[0]
            
        if not node: return show_error("No Driver Found.")
        
        chains = utils.RigUtils.get_chains_from_ribbon_node(node)
        
        # Determine Weighting Mode
        # Pure IK = IK is ON and FK is OFF
        is_pure_ik = self.chk_ik.isChecked() and not self.chk_fk.isChecked()
        
        cmds.undoInfo(openChunk=True, chunkName="MRS Proxy")
        try:
            self.mrs.create_proxy_from_preview(target, chains, pure_ik=is_pure_ik)
            print("[MRS] Proxy Created.")
        except Exception as e: show_error("Proxy Error", str(e))
        finally: cmds.undoInfo(closeChunk=True)

    def on_remove(self):
        item = self.list_rigs.currentItem()
        set_name = item.text() if item else utils.RigUtils.get_rig_from_selection(cmds.ls(sl=True))
        
        if not set_name: return cmds.warning("Select Rig.")
        if QtWidgets.QMessageBox.question(self, "Remove", f"Delete {set_name}?") != QtWidgets.QMessageBox.Yes: return
        
        cmds.undoInfo(openChunk=True, chunkName="MRS Remove")
        try:
            self.mrs.remove_rig(set_name, self.chk_res.isChecked())
            self.refresh_list()
        except: traceback.print_exc()
        finally: cmds.undoInfo(closeChunk=True)

    def refresh_list(self):
        self.list_rigs.clear()
        for s in self.mrs.get_all_rigs():
            self.list_rigs.addItem(s)

def show():
    win = get_maya_window()
    if not win: return
    
    # Close existing
    for w in QtWidgets.QApplication.instance().topLevelWidgets():
        if w.objectName() == MatrixRibbonTool.WINDOW_NAME: w.close()
        
    ui = MatrixRibbonTool(parent=win)
    ui.setObjectName(MatrixRibbonTool.WINDOW_NAME)
    ui.show()

if __name__ == "__main__":
    show()