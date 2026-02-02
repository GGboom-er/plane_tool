# Matrix Ribbon System (MRS) V2.2

## 项目概述 (Project Overview)

**Matrix Ribbon System (MRS)** 是专为 Autodesk Maya 设计的高级绑定工具，利用矩阵数学创建高保真的丝带绑定 (Ribbon Rig)。与传统的基于 NURBS 的丝带不同，MRS 使用自定义的 Maya API 2.0 插件 (`matrixRibbonMesh`) 根据骨骼位置动态生成丝带几何体，从而确保极其稳定的变形，并彻底解决翻转 (Flipping) 问题。

**关键特性:** 
*   **自定义插件节点 (`matrixRibbonMesh`):** 根据输入矩阵实时生成拓扑结构。
*   **混合驱动系统:** 支持 FK 和 IK (Tweak/微调) 控制层级。
*   **矩阵递归 (Matrix Recursion):** 利用 `offsetParentMatrix` 和 `uvPin` 节点构建局部稳定的坐标系。
*   **直接驱动工作流 (Direct Drive):** 提供“预览 (Preview)”模式，网格可随骨骼实时移动，所见即所得。
*   **安全解绑 (Safe Unbind):** 能够撤销绑定更改并将骨骼恢复到原始状态，无数据丢失风险。

## 文件结构 (File Structure) 

*   `mrs_tool.py`: 程序入口。包含 PySide (Qt) 用户界面代码。
*   `matrix_ribbon_system.py`: 核心绑定逻辑和控制器类 `RibbonRigSystem`。处理绑定的构建过程。
*   `py_matrix_ribbon.py`: `matrixRibbonMesh` 节点的 Maya API 2.0 插件定义。
*   `verify_mrs.py`: 验证/测试脚本 (注意：可能引用了过时的 API 方法，如 `bind` 或 `swap_attachment`，需更新)。

## 安装与开发调用 (Installation & Usage)

### 开发/运行代码
请在 Maya 的脚本编辑器 (Script Editor) 中运行以下 Python 代码以启动 UI 并进行开发调试：

```python
import sys
import os
import importlib

# 设置工具路径
path = r"Y:\\GGbommer\\scripts\\plane_tool\\rigTools\\scirpts\\matrixRibbonSystem"
if path not in sys.path:
    sys.path.append(path)

import mrs_tool
# 强制重载以应用代码更改
importlib.reload(mrs_tool)
mrs_tool.show()
```

### 操作流程 (Workflow)
1.  **加载根骨骼 (Load Root Bone):** 在 "Create" 标签页中，选择骨骼链的根关节 (Root Joint)，点击 **Load Root Bone**。
2.  **生成预览 (Preview):** 点击 **1. Preview Mesh** 生成实时丝带网格。
    *   系统会自动计算最佳的 `Width` (宽度) 和 `Hold Length` (簇长度) 启发式数值。
    *   *提示：如果需要，可以在 `preview_ribbon_node` 节点上调整 `width` 和 `holdLength` 属性。*
3.  **绑定 (Bind):** 点击 **2. BIND RIG** 完成绑定。此步骤将：
    *   对网格进行快照 (Snapshot)。
    *   创建 `uvPin` 节点。
    *   构建 FK/IK 控制结构。
    *   使用偏移父矩阵 (Offset Parent Matrix, OPM) 将绑定连接回原始骨骼。

### 管理绑定 (Managing Rigs)
**Manage** 标签页允许您查看场景中现有的绑定，并使用 **Remove Selected Rig** 按钮安全地移除它们（同时将骨骼恢复到原始层级结构）。

## 技术细节 (Technical Details)

### 插件: `matrixRibbonMesh` (ID: `0x8700C`)
*   **输入 (Inputs):** `driveMatrices` (矩阵数组), `width` (浮点), `holdLength` (浮点)。
*   **输出 (Output):** `outMesh` (网格)。
*   **算法:** 生成多边形带。对于每个输入矩阵，它创建一个顶点“簇”(前、中、后)，以确保平滑插值和体积保持。

### 绑定架构 (Rig Architecture)
*   **UVPin:** 用于将控制器吸附在丝带表面。
*   **Offset Parent Matrix (OPM):** 广泛用于驱动原始关节，避免复杂的约束网络，并保持变换通道 (Transform Channels) 相对整洁。
*   **矩阵递归:** 计算每个控制器相对于其父级 Pin 的局部空间，确保控制器正确跟随丝带表面变形。

## 开发与测试 (Development & Testing)

*   **环境要求:** Autodesk Maya (建议 2020+), `maya.api.OpenMaya`。
*   **已知问题:** `verify_mrs.py` 测试套件似乎引用了当前 `matrix_ribbon_system.py` 中不存在的方法 (`mrs.bind`, `mrs.swap_attachment`)。该测试脚本需要更新以匹配 V2.2 API (`bind_from_preview`)。