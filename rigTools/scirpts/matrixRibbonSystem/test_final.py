import maya.standalone
maya.standalone.initialize(name='python')

import maya.cmds as cmds
import maya.api.OpenMaya as om
import sys
import os
import math

# Setup
CURRENT_DIR = "Y:\\GGbommer\\scripts\\plane_tool\\rigTools\\scirpts\\matrixRibbonSystem"
if CURRENT_DIR not in sys.path: sys.path.append(CURRENT_DIR)

PLUGIN_PATH = os.path.join(CURRENT_DIR, "py_matrix_ribbon.py")
try:
    if not cmds.pluginInfo("matrixRibbonMesh", q=True, loaded=True): cmds.loadPlugin(PLUGIN_PATH)
    if not cmds.pluginInfo("matrixNodes", q=True, loaded=True):
        try: cmds.loadPlugin("matrixNodes")
        except: pass
except: pass

import matrix_ribbon_system
from utils import MrsNaming

def get_vec(node, axis):
    m = om.MMatrix(cmds.xform(node, q=True, ws=True, m=True))
    return om.MVector(m[axis*4], m[axis*4+1], m[axis*4+2])

def run():
    print(">>> STARTING FINAL VERIFICATION >>>")
    mrs = matrix_ribbon_system.RibbonRigSystem()
    cmds.file(new=True, force=True)
    
    # 1. Setup
    parent = cmds.polyCube(n="Parent_Obj")[0]
    j1 = cmds.joint(p=(0,0,0)); j2 = cmds.joint(p=(0,0,10)); j3 = cmds.joint(p=(0,0,20)) # Z-Aim
    chains = [[j1, j2, j3]]
    
    # 2. Preview (Axis 4: Z-Aim, X-Width)
    print("[TEST] Preview Mesh (Z-Aim)...")
    mrs.create_preview_mesh(chains, base_name="FinalTest", axis=4)
    
    # 3. Bind
    print("[TEST] Bind Rig...")
    mrs.bind_from_preview(
        f"FinalTest{MrsNaming.MESH_PREVIEW}", chains, 
        enable_fk=True, enable_ik=False, 
        parent_object=parent
    )
    
    # 4. Verify FK Hierarchy (Child follows Parent rotation)
    print("[TEST] Verifying FK Hierarchy...")
    fk_root = f"FinalTest_A_0{MrsNaming.FK_CTRL}"
    fk_child = f"FinalTest_A_1{MrsNaming.FK_CTRL}"
    
    start_pos = cmds.xform(fk_child, q=True, ws=True, t=True)
    cmds.setAttr(f"{fk_root}.rotateY", 45) # Rotate Root
    end_pos = cmds.xform(fk_child, q=True, ws=True, t=True)
    
    dist = math.sqrt(sum([(a-b)**2 for a, b in zip(start_pos, end_pos)]))
    print(f"  > Child Movement Dist: {dist:.4f}")
    
    if dist < 0.1:
        raise Exception("CRITICAL FAILURE: Child FK did not move! FK hierarchy broken.")
    print("  > FK Hierarchy OK.")
    
    # 5. Verify Global Scale
    print("[TEST] Verifying Global Scale...")
    # Reset rotation first to isolate scale test
    cmds.setAttr(f"{fk_root}.rotateY", 0)

    # Record unscaled position
    unscaled_pos = cmds.xform(fk_child, q=True, ws=True, t=True)
    unscaled_dist = math.sqrt(sum([v**2 for v in unscaled_pos]))

    cmds.setAttr(f"{parent}.scale", 2, 2, 2)

    scaled_pos = cmds.xform(fk_child, q=True, ws=True, t=True)
    scaled_dist = math.sqrt(sum([v**2 for v in scaled_pos]))

    expected_dist = unscaled_dist * 2.0
    print(f"  > Unscaled Dist: {unscaled_dist:.2f}, Scaled Dist: {scaled_dist:.2f} (Expected ~{expected_dist:.2f})")

    if abs(scaled_dist - expected_dist) > 1.0:
        raise Exception(f"FAILURE: Global Scale not propagating. Scaled dist {scaled_dist:.2f}, expected {expected_dist:.2f}")
        
    print("  > Global Scale OK.")
    
    print(">>> VERIFICATION COMPLETE >>>")

if __name__ == "__main__":
    try: run()
    except Exception as e: 
        print(f"\nFAIL: {e}")
        import traceback
        traceback.print_exc()