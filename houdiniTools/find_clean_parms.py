import sys
import os
import hou

obj = hou.node("/obj")
geo = obj.createNode("geo", "verify_test")
clean_node = geo.createNode("clean", "clean_test")

print(f"--- CLEAN NODE PARMS ---")
for p in clean_node.parms():
    if "tol" in p.name().lower() or "dist" in p.name().lower():
        print(f"Name: {p.name()} | Label: {p.description()} | Value: {p.eval()}")
