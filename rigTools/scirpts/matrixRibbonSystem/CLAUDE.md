# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Matrix Ribbon System (MRS) — Maya 飘带绑定工具，使用矩阵数学（`offsetParentMatrix`、`multMatrix`、`uvPin`）替代传统 NURBS 曲面生成飘带绑定。包含自定义 Maya 插件节点（`matrixRibbonMesh`, ID: `0x8700D`），从骨骼链世界矩阵程序化生成飘带几何体。

运行环境：Autodesk Maya（Python 2/3, `maya.cmds`, `maya.api.OpenMaya`）。UI：PySide2 (Maya ≤2024) / PySide6 (Maya 2025+)。

## Commands

**启动 UI（Maya Script Editor）：**
```python
import sys, importlib
path = r"Y:\GGbommer\scripts\plane_tool\rigTools\scirpts\matrixRibbonSystem"
if path not in sys.path: sys.path.append(path)
import mrs_tool
importlib.reload(mrs_tool)
mrs_tool.show()
```

**运行测试：** 测试文件按需创建，通过 mayapy 独立模式运行：
```bash
"C:\Program Files\Autodesk\Maya2025\bin\mayapy.exe" <test_file>.py
```
测试依赖 `matrixRibbonMesh` 插件（`py_matrix_ribbon.py`）和 Maya 内置 `matrixNodes` 插件。

## Architecture

**Facade + Builder + Manager** 模式：

```
py_matrix_ribbon.py      (Maya API 2.0 插件节点，完全独立)
ctrl_shapes.py           (FK/IK 控制器形状定义，用户可替换)

utils.py                 (底层：MrsNaming 命名常量 + RigUtils 共享算法)
  ├── builder.py         (RigBuilder：构建逻辑，finalize_bind 为主入口)
  ├── manager.py         (RigManager：发现 + 安全删除)
  └── matrix_ribbon_system.py  (Facade：RibbonRigSystem，统一对外 API)
       └── mrs_tool.py   (PySide UI，调用 RibbonRigSystem)
```

- **`ctrl_shapes.py`** — FK/IK 控制器形状定义。`create_fk_shape(name, size)` 返回圆环 + 颜色，`create_ik_shape(name, size)` 返回方块 + 颜色。用户可直接修改此文件替换控制器外观，无需改动其他代码。
- **`utils.py`** — `MrsNaming`（所有命名常量/后缀/属性名的单一真相源）和 `RigUtils`（共享算法：`connect_via_opm`、`get_rig_from_selection`、`apply_perfect_ribbon_weights`、`delete_opm_nodes`）。`_resolve_transform(node)` 辅助函数解析 shape→transform。`create_control_shape` 委托 `ctrl_shapes` 创建形状。
- **`builder.py`** — `RigBuilder` + `BindConfig`（dataclass）。`BindConfig` 打包 `enable_fk/enable_ik/enable_follow/parent_object/update_mode` 等配置参数。`finalize_bind(preview_mesh, chains, config)` 为主入口，支持新绑定和更新模式两条路径。使用 `_BuildContext`（`__slots__`）传递每骨骼构建状态。`create_standalone_proxy()` 生成独立加权代理 mesh。
- **`manager.py`** — `RigManager`。`remove_rig()` 安全解绑骨骼（保留世界空间姿态）后删除绑定结构。`get_all_rigs()` 通过 `*_Rig_Set` objectSet 发现绑定。
- **`matrix_ribbon_system.py`** — `RibbonRigSystem` 门面。所有外部 API 通过此类。`bind_from_preview` 将关键字参数打包为 `BindConfig` 后委托 Builder。
- **`py_matrix_ribbon.py`** — Maya API 2.0 `MPxNode`（`MatrixRibbonNode`）。接收链矩阵作为复合数组输入，输出带 UV 的 mesh。支持 6 种轴模式、loop/stitch、flip、reverse。使用预分配 list 做 flat-array point lookup 优化几何计算。
- **`mrs_tool.py`** — PySide UI。Build 区（preview/bind/proxy）和 Manage 区（list/remove）。初始化时强制重载插件。视口选择优先于 UI 列表用于删除。使用 `_undo_chunk` 上下文管理器确保一致的撤销处理。

### Data Flow（生命周期）

1. **Preview**：骨骼链 → `matrixRibbonMesh` 插件节点 → 实时预览 mesh（transform + shape 连接到 `outMesh`）
2. **Bind**：预览 mesh 复制为 "FollowMod"（静态，无 skinCluster）→ `uvPin` 采样 FollowMod 表面 → FK/IK 控制器通过 `offsetParentMatrix` 由 uvPin 输出驱动 → 骨骼通过 `connect_via_opm(maintain_offset=False)` 由控制器驱动 → 预览 mesh + 插件节点删除
3. **Update**：复用现有 FollowMod mesh，根据新 FK/IK 配置重建控制器。旧 scale/follow 节点在重建前清理。UI 复选框（FK/IK/Follow）决定新模式。
4. **Proxy**（独立）：从预览或 FollowMod 复制 mesh → 通过 `apply_perfect_ribbon_weights` 蒙皮 → 用作服装/配件的权重参考
5. **Remove**：骨骼解绑（通过 `safe_unbind_batch` 保留世界空间姿态）→ 绑定节点/组/Set 删除 → 骨骼保留

### Follow Toggle 机制

当 `enable_follow=True` 且存在 `parent_object` 时：
- 在每个 FK_Offset 的 OPM 输出处插入 `blendMatrix` 节点（`_FollowBlend`）
- FK_Ctrl 上的 `Follow_Mesh` 属性（0–1）控制 blend envelope
- **Follow=1**：透传实时 OPM（uvPin 驱动，跟随 mesh 行为）
- **Follow=0**：输出静态 OPM 快照（纯层级跟随）
- **链根节点（i==0）**：Follow=0 输出 `_FallbackMM` = offset × parent.worldMatrix（动态跟踪 parent_object）
- **子骨骼（i>=1）**：Follow=0 输出冻结的 OPM 快照（通过层级继承父级 FK_Ctrl 旋转）

### Scale Propagation 机制

当检测到/指定 `parent_object` 时：
- 共享 `_Parent_DCM`（decomposeMatrix）从 parent 的 worldMatrix 提取 scale
- **FK 模式**：Scale 通过 OPM 注入 — 共享 `_Scale_CM`（composeMatrix）前置到每个 FK_Offset 的 OPM 链。子级 FK_Offset 还获得 `_InvScale_CM` 用于相对 OPM 计算中的 scale 补偿。
- **纯 IK 模式**（IK 开，FK 关）：`DCM.outputScale` 直接连接到所有 IK_Offset 的 `.scale` 属性（IK 无层级继承）
- **FIK 模式**（两者都开）：FK 通过 OPM 注入处理 scale；IK 通过 FK 层级继承

### Key Design Principles

- **"Driver is Truth"**：骨骼以 identity offset 吸附到控制器（`maintain_offset=False`），防止历史变换导致的漂移。
- **全部通过 `offsetParentMatrix` 驱动**：无 parent constraint。`multMatrix` + `inverseMatrix` 节点计算相对变换。FK 链使用相对 OPM（`_connect_opm_relative`），IK 使用直接 pin 输出。
- **FollowMod 是静态的**：FollowMod mesh 无 skinCluster — 它是 `uvPin` 采样的干净静态表面。蒙皮仅用于独立 Proxy 功能（`create_standalone_proxy`）。
- **确定性代理蒙皮**：`apply_perfect_ribbon_weights` 按顶点拓扑位置分配权重 — 每骨骼段 3 列（L/C/R）× 3 行 = 9 顶点。前行顶点在 FK 模式下跟随父骨骼。
- **通过 Maya objectSet 跟踪绑定**：`_Rig_Set`、`_Ctrl_Set`（控制器 + Offset 组）、`_Geo_Set`、`_Node_Set`、`_Jnt_Set`。

## Naming Convention

模式：`[BaseName]_[GroupID]_[Index][Suffix]`
- GroupID：通过 `RigUtils.get_alpha_index()` 生成字母 — A, B, ... Z, A1, B1...
- 所有后缀定义在 `MrsNaming`（如 `_FK_Ctrl`、`_IK_Offset`、`_Grp`、`_FollowMod`）
- 基础名中的冒号（Maya 命名空间）替换为下划线

## Critical Rules

- **`MrsNaming` 是所有属性名和后缀的单一真相源** — 绝不在其他地方硬编码这些字符串。
- **访问任何节点前必须 `cmds.objExists()`。**
- **UI 操作必须包裹在 `cmds.undoInfo(openChunk=True)` / `closeChunk=True` 中。**
- **插件节点 ID `0x8700D` 是固定的** — 不要在未跨所有场景重新注册的情况下更改。
- **Mesh 拓扑是确定性的**：每骨骼每链 9 个顶点（3 列 × 3 子行）。蒙皮逻辑依赖此精确布局。
- **轴模式**（0–5）映射插件节点的 aim/width 轴，且必须烘焙到 mesh transform 以供 `builder._setup_uv_pin()` 中的 `uvPin` tangent/normal 轴设置使用。
