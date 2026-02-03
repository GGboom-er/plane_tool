"""
Matrix Ribbon System (MRS) - NUCLEAR RELOADER
Version: 15.0.2
"""
import maya.cmds as cmds
import maya.mel as mel
import sys
import os
import importlib
import gc

def run():
    print("\n" + "#"*60)
    print("MRS ULTIMATE RELOAD (New Scene Mode)")
    print("#"*60)

    # 1. Force New Scene (Releases ALL plugin and file locks)
    cmds.file(new=True, f=True)
    
    # 2. Close UI
    if cmds.window("MatrixRibbonToolUI", exists=True):
        cmds.deleteUI("MatrixRibbonToolUI")

    # 3. Flush Undo and GC
    cmds.flushUndo()
    gc.collect()

    # 4. Unload Plugin
    plugin_name = "py_matrix_ribbon.py"
    if cmds.pluginInfo("matrixRibbonMesh", q=True, loaded=True):
        try:
            # Force unload via MEL
            mel.eval(f'unloadPlugin -force "{plugin_name}"')
            print(f"[Reloader] Unloaded {plugin_name}")
        except Exception as e:
            print(f"[Reloader Error] Failed to unload: {e}")

    # 5. Clear sys.modules
    to_del = [m for m in sys.modules if m.startswith("matrix_ribbon") or m in ["builder", "manager", "utils", "mrs_tool", "py_matrix_ribbon"]]
    for m in to_del:
        if m in sys.modules: del sys.modules[m]

    # 6. Re-launch
    try:
        import mrs_tool
        mrs_tool.show()
        print("[Reloader] MRS System Rebooted.")
    except Exception as e:
        print(f"[Launch Error] {e}")

if __name__ == "__main__":
    run()
