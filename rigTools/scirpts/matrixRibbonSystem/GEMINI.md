# Matrix Ribbon System (MRS) - 核心指南

## 1. 项目概述
MRS 是一个专为 Autodesk Maya 设计的高级绑定工具，利用矩阵数学 (`matrixNodes` 插件) 代替传统的 NURBS 来生成高保真的 **丝带绑定 (Ribbon Rigs)**。

**核心特性：**
*   **自定义插件节点 (`matrixRibbonMesh`)**：根据骨骼链位置实时生成丝带几何体。
*   **混合 FK/IK (Hybrid FK/IK)**：支持同时生成 FK 和 IK 控制器，并提供可见性切换。
*   **纯 IK 模式 (Pure IK)**：经过优化的“直接驱动”模式，性能极佳。
*   **蒙皮代理生成 (Proxy Generation)**：生成独立的、权重完美的代理网格，用于蒙皮传递。
*   **健壮架构**：采用“驱动即真理 (Driver is Truth)”逻辑，确保骨骼始终吸附于控制器，防止在模式切换时发生位移。

## 2. 核心模块与架构

### A. `matrix_ribbon_system.py` (外观/入口)
*   **角色**：主要的 API 调用入口。
*   **核心类**：`RibbonRigSystem`。
*   **用法示例**：
    ```python
    import matrix_ribbon_system
    mrs = matrix_ribbon_system.RibbonRigSystem()
    # 1. 创建预览
    preview_mesh, node, w, h = mrs.create_preview_mesh(chains, base_name="Ribbon")
    # 2. 执行绑定
    mrs.bind_from_preview(preview_mesh, chains, enable_fk=True, enable_ik=True)
    ```

### B. `mrs_tool.py` (UI 界面)
*   **角色**：基于 PySide2/PySide6 的用户界面。
*   **功能**：
    *   **Build 标签页**：创建预览、绑定 Rig、生成 Proxy。
    *   **Manage 标签页**：列表显示和移除 Rigs。
    *   **智能选择**：优先响应视口 (Viewport) 选择，而非 UI 列表，删除操作更符合直觉。

### C. `builder.py` (构建逻辑)
*   **角色**：负责构建节点图和层级结构。
*   **核心方法**：`finalize_bind`。
*   **逻辑特点**：
    *   **直接 OPM 连接**：所有驱动均使用 `offsetParentMatrix`。
    *   **驱动即真理**：强制骨骼吸附到控制器（Identity Offset），防止历史残留导致的漂移。
    *   **干净重建**：在创建新连接前，强制删除旧的 OPM 节点。

### D. `manager.py` (生命周期管理)
*   **角色**：负责安全地查找和删除 Rigs。
*   **核心方法**：`remove_rig`。
*   **安全性**：在删除 Rig 结构之前，先将骨骼“解绑”并恢复到世界空间，防止误删骨骼。

### E. `utils.py` (工具库)
*   **角色**：常量定义和共享算法。
*   **核心类**：`MrsNaming` (常量表), `RigUtils`.
*   **关键算法**：
    *   `get_rig_from_selection`：使用正则 `^(.*)_([A-Za-z0-9]+)(?:_(\d+))?$` 精准识别 Rig。
    *   `connect_via_opm`：处理矩阵连接（判断是否为 Identity 或需要 Offset）。
    *   `get_reverse_state`：智能检测 Ribbon 是否反转（优先级：插件节点 > 实时连接 > 烘焙属性）。

### F. `py_matrix_ribbon.py` (插件)
*   **角色**：Maya API 2.0 自定义节点 (`matrixRibbonMesh`, ID: 0x8700D)。
*   **功能**：根据输入的矩阵数组计算网格几何体。

## 3. 开发规范
*   **命名规范**：严格遵循 `[BaseName]_[GroupID]_[Index]_[Suffix]` 格式。
*   **属性管理**：所有自定义属性名均在 `MrsNaming` 中统一定义。
*   **安全性**：访问节点前必须检查 `cmds.objExists`。UI 操作必须包裹在 `cmds.undoInfo` 中。
*   **拓扑结构**：Ribbon 网格为每根骨骼段生成特定的 3 排顶点（左、中、右）。

## 4. 构建与运行
*   **启动 UI**：在 Maya 脚本编辑器中运行以下 Python 代码：
    ```python
    import sys
    import os
    import importlib
    
    # 将脚本路径添加到系统路径
    path = r"MRS_工具文件夹路径"
    if path not in sys.path: sys.path.append(path)
    
    import mrs_tool
    importlib.reload(mrs_tool)
    mrs_tool.show()
    ```