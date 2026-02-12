# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Matrix Ribbon System (MRS) — a Maya rigging tool that generates ribbon rigs using matrix math (`offsetParentMatrix`, `multMatrix`, `uvPin`) instead of traditional NURBS surfaces. Includes a custom Maya plugin node (`matrixRibbonMesh`, ID: `0x8700D`) that procedurally generates ribbon geometry from joint chain world matrices.

Runtime: Autodesk Maya (Python 2/3, `maya.cmds`, `maya.api.OpenMaya`). UI: PySide2 (Maya ≤2024) / PySide6 (Maya 2025+).

## Commands

**Launch UI (Maya Script Editor):**
```python
import sys, importlib
path = r"Y:\GGbommer\scripts\plane_tool\rigTools\scirpts\matrixRibbonSystem"
if path not in sys.path: sys.path.append(path)
import mrs_tool
importlib.reload(mrs_tool)
mrs_tool.show()
```

**Run tests (standalone via mayapy):**
```
mayapy test_mrs.py      # Comprehensive: preview, bind, update, proxy, removal
mayapy test_final.py    # Focused: deformation verification + global scale
```
Both tests require `matrixRibbonMesh` plugin (`py_matrix_ribbon.py`) and Maya's `matrixNodes` plugin.

## Architecture

**Facade + Builder + Manager** pattern:

```
matrix_ribbon_system.py  (Facade: RibbonRigSystem)
    ├── builder.py       (RigBuilder: construction, finalize_bind is main entry)
    ├── manager.py       (RigManager: discovery + safe deletion)
    └── utils.py         (MrsNaming constants + RigUtils shared algorithms)

py_matrix_ribbon.py      (Maya API 2.0 plugin node, standalone)
mrs_tool.py              (PySide UI, calls RibbonRigSystem)
```

- **`matrix_ribbon_system.py`** — `RibbonRigSystem` facade. All external API goes through here. Delegates to Builder and Manager.
- **`builder.py`** — `RigBuilder`. Core build logic. `finalize_bind()` is the main entry supporting both new-bind and update-mode paths. Creates preview meshes via plugin node, builds FK/IK hierarchies, sets up `uvPin` sampling, organizes Maya sets. `create_standalone_proxy()` generates weighted proxy meshes (independent from rig binding).
- **`manager.py`** — `RigManager`. `remove_rig()` safely unbinds joints (preserving world-space pose) before deleting rig structure. `get_all_rigs()` discovers rigs by `*_Rig_Set` objectSets.
- **`utils.py`** — `MrsNaming` (single source of truth for all naming constants/suffixes/attribute names) and `RigUtils` (shared algorithms: `connect_via_opm`, `get_rig_from_selection`, `apply_perfect_ribbon_weights`, `delete_opm_nodes`).
- **`py_matrix_ribbon.py`** — Maya API 2.0 `MPxNode` (`MatrixRibbonNode`). Takes chain matrices as compound array input, outputs mesh with UVs. Supports 6 axis modes, loop/stitch, flip, reverse.
- **`mrs_tool.py`** — PySide UI. Build section (preview/bind/proxy) and Manage section (list/remove). Forces plugin reload on init. Viewport selection takes priority over UI list for removal.

### Data Flow (Lifecycle)

1. **Preview**: Joint chains → `matrixRibbonMesh` plugin node → live preview mesh (transform + shape connected to `outMesh`)
2. **Bind**: Preview mesh duplicated as "FollowMod" (static, no skinCluster) → `uvPin` samples FollowMod surface → FK/IK controls driven by uvPin outputs via `offsetParentMatrix` → bones driven by controls via `connect_via_opm(maintain_offset=False)` → preview mesh + plugin node deleted
3. **Update**: Existing FollowMod mesh reused, controls rebuilt with new FK/IK config
4. **Proxy** (independent): Mesh duplicated from preview or FollowMod → skinned via `apply_perfect_ribbon_weights` → used as weight reference for clothing/accessories
5. **Remove**: Joints unbound (world-space pose preserved via `safe_unbind_batch`) → rig nodes/groups/sets deleted → joints survive

### Key Design Principles

- **"Driver is Truth"**: Bones snap to controllers with identity offset (`maintain_offset=False`), preventing drift from historical transforms.
- **All driving via `offsetParentMatrix`**: No parent constraints. `multMatrix` + `inverseMatrix` nodes compute relative transforms. FK chain uses relative OPM (`_connect_opm_relative`), IK uses direct pin output.
- **FollowMod is static**: The FollowMod mesh has no skinCluster — it is a clean static surface for `uvPin` sampling. Skinning is only used in the independent Proxy feature (`create_standalone_proxy`).
- **Deterministic proxy skinning**: `apply_perfect_ribbon_weights` assigns weights by vertex topology position — 3 columns (L/C/R) × 3 rows per bone segment = 9 vertices per bone. Pre-row vertices follow parent bone in FK mode.
- **Scale propagation**: FK mode connects parent scale to chain root only (children inherit). Pure IK mode connects to ALL IK offsets (no hierarchy inheritance).
- **Rig tracking via Maya objectSets**: `_Rig_Set`, `_Geo_Set`, `_Group_Set`, `_Control_Set`, `_Node_Set`, `_Jnt_Set`.

## Naming Convention

Pattern: `[BaseName]_[GroupID]_[Index][Suffix]`
- GroupID: alphabetic via `RigUtils.get_alpha_index()` — A, B, ... Z, A1, B1...
- All suffixes defined in `MrsNaming` (e.g., `_FK_Ctrl`, `_IK_Offset`, `_Grp`, `_FollowMod`)
- Colons in base names (Maya namespaces) replaced with underscores

## Critical Rules

- **`MrsNaming` is the single source of truth** for all attribute names and suffixes — never hardcode these strings elsewhere.
- **Always `cmds.objExists()` before accessing any node.**
- **UI operations must wrap in `cmds.undoInfo(openChunk=True)` / `closeChunk=True`.**
- **Plugin node ID `0x8700D` is fixed** — do not change without re-registering across all scenes.
- **Mesh topology is deterministic**: 9 vertices per bone per chain (3 columns × 3 sub-rows). Skinning logic depends on this exact layout.
- **Axis mode** (0–5) maps aim/width axes for the plugin node AND must be baked to the mesh transform for `uvPin` tangent/normal axis setup in `builder._setup_uv_pin()`.
