import re
import os

FILE_PATH = r"Y:\GGbommer\scripts\plane_tool\rigTools\scirpts\matrixRibbonSystem\builder.py"

with open(FILE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# Split the file into Header and the RigBuilder class
header_match = re.search(r"(.*?)class RigBuilder:", content, re.DOTALL)
header = header_match.group(1)

rigbuilder_content = content[header_match.end():]

# Find all methods
method_pattern = re.compile(r"(\n    def \w+\(self.*?(?=\n    def |\Z))", re.DOTALL)
methods = method_pattern.findall("\n" + rigbuilder_content)

GEO_METHODS = ["create_preview_mesh", "_bake_uv_data", "_setup_uv_pin", "_get_stored_uvs", "_setup_follow_mesh"]
MATH_METHODS = ["_preserve_ik_offsets", "_build_fk_component", "_clean_fk_component", "_build_ik_component", "_clean_ik_component", "_connect_opm", "_connect_opm_with_scale", "_connect_opm_relative"]
HIERARCHY_METHODS = ["_ensure_group", "_ensure_control", "_cleanup_scale_connections", "_connect_scale_driver", "_setup_parent_scale", "_organize_hierarchy", "_parent_joints_safely", "_migrate_metadata", "_organize_sets"]
PROXY_METHODS = ["create_standalone_proxy"]

geo_class = "\n\nclass GeometryNodeBuilder:\n    \"\"\"Geometric creation and topological querying (UV, Ribbon Mesh).\"\"\""
math_class = "\n\nclass MathNetworkBuilder:\n    \"\"\"Directed Acyclic Graph (DAG) construction for Matrix blending and OPM.\"\"\""
hier_class = "\n\nclass HierarchyNodeBuilder:\n    \"\"\"Outliner hierarchy, control shapes, and DG/DAG housekeeping.\"\"\""
proxy_class = "\n\nclass ProxyNodeBuilder:\n    \"\"\"Standalone weighted proxy mechanics.\"\"\""
orchestrator_class = "\n\nclass RigBuilder(GeometryNodeBuilder, MathNetworkBuilder, HierarchyNodeBuilder, ProxyNodeBuilder):\n    \"\"\"God Class Facade (Safely decoupled via SRP-focused mixins for maintenance).\"\"\""

for m in methods:
    method_name = re.match(r"\n    def (\w+)\(", m).group(1)
    
    if method_name in GEO_METHODS:
        geo_class += m
    elif method_name in MATH_METHODS:
        math_class += m
    elif method_name in HIERARCHY_METHODS:
        hier_class += m
    elif method_name in PROXY_METHODS:
        proxy_class += m
    else:
        # e.g. build_rig_structure, finalize_bind, _resolve_bind_inputs
        orchestrator_class += m

new_content = header + geo_class + math_class + hier_class + proxy_class + orchestrator_class

with open(FILE_PATH, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Builder class successfully decoupled into semantic SRP mixins.")
