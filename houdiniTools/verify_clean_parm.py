import sys
import os
import hou

# Manually add package path to ensure we are testing the right file
pkg_path = r"Y:\GGbommer\scripts\plane_tool\houdiniTools\GG_SmartReduce_Tool\python"
if pkg_path not in sys.path:
    sys.path.insert(0, pkg_path)

import PolyReduce

print(f"--- PARM VERIFICATION TEST ---")
print(f"Module File: {PolyReduce.__file__}")

# Create a dummy container
obj = hou.node("/obj")
geo = obj.createNode("geo", "verify_test")
clean_node = geo.createNode("clean", "clean_test")

# Manually call the parameter setting logic
# We simulate what build_smart_reduce_chain does
print(f"Setting 'consoldist' to 0.0001 ...")
PolyReduce.safe_set_parm(clean_node, "consoldist", 0.0001)

# Read it back
val = clean_node.parm("consoldist").eval()
print(f"Read Back Value: {val}")
print(f"Is it 0.0001? {abs(val - 0.0001) < 0.0000001}")

print("--- END TEST ---")
