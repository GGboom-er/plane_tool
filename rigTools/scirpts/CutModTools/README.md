# CutMod — 基于骨骼权重的模型切分工具

## 功能说明

CutMod 是一个 Maya 2025 工具，用于将带有 skinCluster 蒙皮的完整角色模型，按骨骼权重自动切分为多个独立子网格，并用**矩阵约束**或 **parentConstraint** 绑定到对应骨骼。

### 使用场景

当你需要将 skinCluster 绑定模式转换为纯约束/矩阵驱动的切模绑定（Cut-Up Binding）时：
- 提高绑定运算效率（消除 skinCluster 的逐顶点权重计算开销）
- 适用于半刚性角色（机甲、盔甲、硬表面角色等）
- 替代 AdvancedSkeleton 的 CutUp 功能（解决其在矩阵绑定模式下的属性破坏问题）

## 安装

确保 `CutModTools` 文件夹所在目录在 Maya 的 Python 路径中：

```python
import sys
sys.path.append(r"Y:\GGbommer\scripts\plane_tool\rigTools\scirpts")
```

## 使用方式

### UI 模式
```python
import CutModTools
CutModTools.show()
```

### 脚本模式
```python
import CutModTools

# 切分当前选择的网格（矩阵绑定模式）
CutModTools.run()

# 指定参数
CutModTools.run(
    meshes=["body_geo"],      # 目标网格
    mode="matrix",            # "matrix" 或 "constraint"
    threshold=0.001           # 权重忽略阈值
)
```

## 绑定模式对比

| 特性 | 矩阵绑定 (Matrix) | 约束绑定 (Constraint) |
|------|-------------------|----------------------|
| 性能 | ★★★ 最优 | ★★ 良好 |
| 节点数 | 每个子网格 1 个 multMatrix | 每个子网格 2 个约束节点 |
| 并行求值 | 完全支持 | 支持 |
| 兼容性 | Maya 2020+ | 所有版本 |
| 推荐场景 | 默认推荐 | 需要约束查询的下游流程 |

## 技术架构

```
CutModTools/
├── __init__.py              # 入口（show / run）
├── source/
│   ├── core/
│   │   ├── weight_analyzer.py   # 权重分析器（OpenMaya 2.0）
│   │   ├── mesh_cutter.py       # 几何切分器
│   │   ├── binding.py           # 绑定器（矩阵/约束）
│   │   └── snapshot.py          # 属性快照保护系统
│   ├── ui/
│   │   └── main_window.py       # PySide2 UI
│   └── utils/
│       └── maya_helpers.py      # Maya 辅助函数
├── config/
│   └── defaults.json
└── tasks/
    ├── todo.md
    └── lessons.md
```

## 核心特性

### 属性快照保护（Snapshot Protection）

这是本工具相比 AdvancedSkeleton CutUp 的核心改进。在执行切分操作前，SnapshotManager 会自动捕获场景中所有可能受影响节点的关键属性（如 `inheritsTransform`、通道值、`offsetParentMatrix` 连接等），操作完成后自动对比并恢复被意外修改的属性。

这解决了 AS CutUp 在 OPM 矩阵绑定模式下会破坏 `FKOffsetSpine1_M` 等节点的 `inheritsTransform` 和通道值的问题。
