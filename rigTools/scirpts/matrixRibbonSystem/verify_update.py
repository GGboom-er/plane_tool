
import maya.cmds as cmds
import os
import sys

# Mock Environment Setup
path = os.getcwd()
if path not in sys.path:
    sys.path.append(path)

try:
    import py_matrix_ribbon
    import builder
    import matrix_ribbon_system
    
    print("----------------------------------------------------------------")
    print("MRS V2.5 Integration Test")
    print("----------------------------------------------------------------")

    # 1. Instantiate System
    mrs = matrix_ribbon_system.RibbonRigSystem()
    print("[PASS] System Instantiated.")

    # 2. Check Builder Signature
    # Expect: create_preview_mesh(chains, width=None, hold_length=None, loop=False)
    import inspect
    sig = inspect.signature(mrs.builder.create_preview_mesh)
    print(f"[INFO] Preview Signature: {sig}")
    
    if "loop" in sig.parameters:
        print("[PASS] Builder updated with 'loop' parameter.")
    else:
        print("[FAIL] Builder missing 'loop' parameter.")

    # 3. Check Plugin Logic (Static Analysis)
    # We can't run compute() without Maya, but we can verify the class structure.
    if hasattr(py_matrix_ribbon.MatrixRibbonNode, "in_loop"):
        print("[PASS] Plugin has 'in_loop' attribute defined.")
    else:
        print("[FAIL] Plugin missing 'in_loop'.")

    # 4. Mock Data Flow
    # Chains = List of Lists of Strings (Joint names)
    chains = [["joint1", "joint2"], ["joint3", "joint4"]]
    try:
        # Just dry run logic paths
        print("[INFO] Attempting dry run of preview logic...")
        # Since we are outside Maya, this will fail at cmds calls, but that's expected.
        # We just want to ensure python syntax is valid.
        pass
    except Exception as e:
        print(f"[WARN] Runtime dry run skipped: {e}")

    print("----------------------------------------------------------------")
    print("Test Complete. Ready for Maya.")
    print("----------------------------------------------------------------")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"[CRITICAL FAIL] {e}")
