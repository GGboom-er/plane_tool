# Plane Tool Project (平面工具项目)

**一个为CGI/DCC工作流设计的综合性工具集，旨在提升动画、绑定、建模、缓存以及与Unreal Engine交互的效率和质量。**
(A comprehensive toolset designed for CGI/DCC workflows, aimed at enhancing efficiency and quality in animation, rigging, modeling, caching, and Unreal Engine interaction.)

## 核心功能模块 (Core Functional Modules)

### 1. 动画工具 (Animation Tools) - `aniTools/`
*   **引用管理 (Reference Management)**: 提供批处理引用、修改引用路径和修复引用名称的功能，确保大型场景中引用资产的稳定性和可管理性。
*   **关键帧优化 (Keyframe Optimization)**: 包含关键帧减面（`keyframeReduction`）和动画曲线平滑（`smoothAnimCurve`）工具，用于精简动画数据，提高播放性能和编辑效率。
*   **动画重定向 (Animation Retargeting)**: 支持动画在不同骨骼结构间的重定向，提高动画资产的复用性。

### 2. 绑定工具 (Rigging Tools) - `rigTools/`
*   **高级角色绑定系统 (Advanced Character Rigging System)**: `MHC/` 模块专注于DNA数据处理、BlendShape驱动、LOD管理和网格匹配，支持复杂角色绑定，实现高精度形变。
*   **蒙皮与权重管理 (Skinning & Weight Management)**: 提供快速蒙皮（`Quick_skin.py`）和蒙皮权重复制（`copySkinWeight/`）等功能，简化蒙皮流程，确保权重分配的准确性。
*   **骨骼与约束操作 (Joint & Constraint Operations)**: 包含重建骨骼层级、重建约束、关节转换等基础骨骼操作，以及属性集函数、通道盒颜色等辅助功能。
*   **BlendShape与SDK (BlendShape & SDK)**: 支持构建BlendShape、创建BlendShape驱动文件、管理BlendShape连接以及动画到Set Driven Key (SDK) 的转换，用于高级表情和形变控制。
*   **自定义高级骨骼 (Custom Advanced Skeleton)**: `customADV/` 模块可能包含对Advanced Skeleton等现有绑定框架的定制和扩展。

### 3. 建模工具 (Modeling Tools) - `modTools/`
*   **拓扑与UV处理 (Topology & UV Processing)**: 提供修复UV集、传输UV、四边形修补（`quadPatcher`）等功能，确保模型拓扑和UV的正确性和优化。
*   **肌肉与纹理绑定 (Muscle & Texture Rigging)**: 包含肌肉工具（`muscleTool`）和纹理绑定（`textureRig`）相关功能，用于创建更真实的形变和视觉效果。

### 4. 批处理工具 (Batch Processing Tools) - `batchTools/`
*   专注于自动化重复性任务，例如批处理引用节点（`batch_RN.py`）和Maya文件检查（`checkMA.py`），大幅提升工作效率。

### 5. Blender 工具 (Blender Tools) - `blenderTools/`
*   提供Blender内部的各种操作，如添加驱动、导入导出曲线到Maya、优化Blender场景等，促进Blender在CGI管线中的应用。

### 6. Unreal Engine 工具 (Unreal Engine Tools) - `ueTools/`
*   包含FBX导入到材质（`inputFBXToMat.py`）和Maya到UE的FBX导出（`mayaToUeFbx.py`）功能，支持资产在Maya和Unreal Engine之间的顺畅流通，优化游戏开发流程。

### 7. 通用辅助工具 (General Utilities) - `ourthTools/`
*   包含图像转换和MP4压缩等通用工具，为日常工作提供便利。

## 配置说明 (Configuration Details)

### `dcc_port_map.json`
此文件用于管理DCC应用程序（如Maya, Blender）的远程命令端口映射。`GGbommer/winUI.py` 等工具通过Socket连接这些端口以发送命令。

**格式示例 (Example Format):**
```json
{
    "1234": 7002,
    "2345": 7003
}
```
其中，键为进程ID (PID)，值为对应的 `commandPort` 端口号。

**使用说明 (Usage Notes):**
由于DCC软件通常不默认开启远程命令端口，建议在启动脚本中显式开启 `commandPort` 并将进程ID和端口号写入此JSON文件。工具界面启动后会读取此文件以确定每个进程的可用端口。若未找到端口映射，相关功能将提示“Port is unknown”并不会尝试发送命令。

## 安装 (Installation)
(待补充：此处将提供详细的安装步骤，包括环境配置、依赖安装和工具路径设置等。)
(To be completed: This section will provide detailed installation steps, including environment configuration, dependency installation, and tool path setup.)

## 使用 (Usage)
(待补充：此处将提供工具的通用使用指南和常见工作流示例。)
(To be completed: This section will provide general usage guidelines and common workflow examples for the tools.)

## 贡献 (Contributing)
(待补充：欢迎社区贡献，此处将提供贡献指南。)
(To be completed: Community contributions are welcome. This section will provide contribution guidelines.)

## 许可证 (License)
(待补充：此处将说明项目的许可证信息。)
(To be completed: This section will state the project's license information.)