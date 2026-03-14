import sys
import os
import importlib
import traceback

# Setup Path
plugin_root = r"Y:\\GGbommer\\scripts\\plane_tool\\houdiniTools\\GG_SmartReduce_Tool"
python_dir = os.path.join(plugin_root, "python")
if python_dir not in sys.path:
    sys.path.insert(0, python_dir)

print("=== FINAL CODE AUDIT ===")

# 1. Syntax & Import Test
print("\n[TEST 1] Syntax & Import Check")
try:
    import PolyReduce
    print("  [PASS] PolyReduce imported.")
except Exception as e:
    print(f"  [FAIL] PolyReduce import error: {e}")
    traceback.print_exc()

try:
    import PolyReduce_UI
    print("  [PASS] PolyReduce_UI imported.")
except Exception as e:
    # It's expected to fail on hou.ui usage in __init__ if instantiated, 
    # but import itself should be clean.
    print(f"  [FAIL] PolyReduce_UI import error: {e}")
    traceback.print_exc()

# 2. Logic Simulation
print("\n[TEST 2] Core Logic Simulation")
import hou
try:
    # Setup
    test_obj = r"Y:\\GGbommer\\scripts\\plane_tool\\houdiniTools\\test.obj"
    out_dir = os.path.dirname(test_obj) + "/output_optimized"
    if not os.path.exists(out_dir): os.makedirs(out_dir)
    
    # Mock Params
    parms = {
        'percentage': 10,
        'mask_weight': 50,
        'hard_threshold': 1.5,
        'tolerance': 0.0001,
        'blur_iter': 8
    }
    
    # Create Container
    geo = hou.node("/obj").createNode("geo", "AUDIT_GEO")
    
    # Run Process
    print(f"  Running process_file on {test_obj}...")
    nodes = PolyReduce.process_file(test_obj, out_dir, geo, parms)
    
    # Verify Nodes
    print("  Verifying node creation...")
    required_nodes = ['reduce', 'wrangle', 'blur', 'pre_clean', 'final_clean']
    missing = [n for n in required_nodes if n not in nodes]
    
    if missing:
        print(f"  [FAIL] Missing nodes in return dict: {missing}")
    else:
        print("  [PASS] All core nodes created and tracked.")
        
    # Verify Clean Tolerance
    tol_val = nodes['pre_clean'].parm('fusedist').eval()
    if abs(tol_val - 0.0001) < 0.000001:
        print(f"  [PASS] Clean Tolerance set correctly to {tol_val}")
    else:
        print(f"  [FAIL] Clean Tolerance mismatch. Expected 0.0001, got {tol_val}")
        
    # Verify Blur Iteration
    blur_val = nodes['blur'].parm('iterations').eval()
    if blur_val == 8:
        print(f"  [PASS] Blur Iterations set correctly to {blur_val}")
    else:
        print(f"  [FAIL] Blur mismatch. Expected 8, got {blur_val}")

except Exception as e:
    print(f"  [FAIL] Logic execution error: {e}")
    traceback.print_exc()

print("\n=== AUDIT COMPLETE ===")
