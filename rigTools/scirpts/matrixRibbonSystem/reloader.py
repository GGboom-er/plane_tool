"""
Matrix Ribbon System (MRS) - Smart Reloader
Reloads code and plugin without forcing a new scene.
"""
import maya.cmds as cmds
import sys
import os
import importlib

def run():
    print("\n--- MRS RELOAD START ---")

    # 1. Close UI
    if cmds.window("MatrixRibbonToolUI", exists=True):
        cmds.deleteUI("MatrixRibbonToolUI")

    # 2. Try Unload Plugin (Requires scene to be clean of MRS nodes)
    nodes = cmds.ls(type="matrixRibbonMesh")
    if nodes:
        print(f"[Warning] Scene contains {len(nodes)} matrixRibbonMesh nodes. Plugin cannot be unloaded.")
        print(" -> Please delete these nodes and flush undo to reload the plugin binary.")
    else:
        cmds.flushUndo() # Essential
        if cmds.pluginInfo("matrixRibbonMesh", q=True, loaded=True):
            try:
                cmds.unloadPlugin("matrixRibbonMesh")
                print("[Success] Plugin binary unloaded.")
            except Exception as e:
                print(f"[Error] Plugin unload failed: {e}")

    # 3. Reload Python Modules
    modules = ["utils", "builder", "manager", "matrix_ribbon_system", "mrs_tool", "py_matrix_ribbon"]
    for m in modules:
        if m in sys.modules:
            importlib.reload(sys.modules[m])
            print(f"[Success] Module reloaded: {m}")

    # 4. Re-Launch
    import mrs_tool
    mrs_tool.show()
    print("--- MRS RELOAD COMPLETE ---\n")

if __name__ == "__main__":
    run()