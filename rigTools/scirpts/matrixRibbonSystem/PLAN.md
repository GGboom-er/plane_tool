# Matrix Ribbon System (MRS) - 重构与开发计划

## 1. 目标 (Objectives)
构建一个**专业级、模块化、易于维护**的 Maya 矩阵丝带工具。代码应清晰分离“数据/核心逻辑”、“Rig 构建逻辑”和“用户界面”。

## 2. 架构规划 (Architecture)

### A. 核心插件层 (`py_matrix_ribbon.py`)
*   **职责**: 仅负责高性能网格生成。
*   **现状**: 功能基本完备 (V2)，但需检查属性命名是否规范，计算逻辑是否可进一步优化。
*   **计划**: 
    *   保留现有核心逻辑。
    *   确保输入/输出属性具有清晰的短名和长名。
    *   添加版本号和节点 ID 管理。

### B. 核心逻辑层 (`matrix_ribbon_system.py`)
*   **职责**: 处理 Maya 场景操作、节点连接、数学计算。
*   **重构方向**: 将当前的单一大类 `RibbonRigSystem` 拆分或整理为更清晰的职责块。
    *   **Manager Class**: 管理场景中的 Rig 实例（查找、列出、删除）。
    *   **Builder Class**: 负责构建的具体步骤（Preview -> Bind）。
    *   **Utils**: 独立的静态方法集（如 `_connect_via_opm`, `metrics_calculation`），减少类内部的杂乱。

### C. 用户界面层 (`mrs_tool.py`)
*   **职责**: 展示状态，接收用户指令。
*   **重构方向**:
    *   UI 代码应尽量少包含逻辑，只调用核心层的方法。
    *   增加错误捕获和用户提示。
    *   确保 `reload` 机制顺畅，方便开发。

## 3. 开发路线图 (Roadmap)

### 阶段 1: 清理与标准化 (Cleanup & Standardization)
- [x] 删除废弃文件 (`verify_mrs.py`).
- [ ] **Review Plugin**: 检查 `py_matrix_ribbon.py` 代码规范。
- [ ] **Utils提取**: 将通用数学/Maya操作提取出来。

### 阶段 2: 核心重写 (Core Refactor)
- [ ] **RigBuilder**: 重写 `bind` 逻辑，确保每一步（创建节点、UV Pin、控制器、OPM）都清晰、可调试。
- [ ] **PreviewManager**: 优化预览模式的体验，确保切换到 Bind 模式时无缝衔接。

### 阶段 3: UI 优化 (UI Polish)
- [ ] 刷新 UI 布局。
- [ ] 增加更详细的 Rig 列表管理功能。

### 阶段 4: 测试 (Testing)
- [ ] 编写新的 `tests/test_core.py`，使用 `unittest` 或简单的脚本确保 API 稳定。

## 4. 冗余代码清理清单 (Redundancy Check)
- 移除 `verify_mrs.py` (已完成)。
- 检查 `matrix_ribbon_system.py` 中是否有未使用的旧方法。
- 检查是否有重复的导入或路径设置代码。
