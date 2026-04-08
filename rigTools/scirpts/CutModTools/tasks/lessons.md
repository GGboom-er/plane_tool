# CutMod 工具专属经验沉淀

## 经验记录

### 2026-04-08 — 初始版本开发

- [触发条件] AdvancedSkeleton CutUp 在 OPM 模式下使用
- [根因] `asParentConstraint` 在 OPM 模式下无条件重置目标通道值且不保护 `inheritsTransform`
- [正确方案] 使用 SnapshotManager 在操作前后保护既有节点状态
- [避坑规则] 任何涉及 OPM 连接的操作都必须先快照再恢复

### 2026-04-08 — MFnSkinCluster 导入

- [触发条件] `maya.api.OpenMaya` 中找不到 `MFnSkinCluster`
- [根因] Maya OpenMaya 2.0 将动画类放在 `maya.api.OpenMayaAnim`
- [正确方案] `import maya.api.OpenMayaAnim as oma2` → `oma2.MFnSkinCluster`
- [避坑规则] 蒙皮/动画/关键帧相关函数集都在 OpenMayaAnim 中

### 2026-04-08 — MFnMesh 无 getPolygonEdges

- [触发条件] `MFnMesh.getPolygonEdges(faceId)` 报 AttributeError
- [根因] OpenMaya 2.0 MFnMesh 不提供该方法
- [正确方案] 使用 `MItMeshPolygon` 迭代器的 `getEdges()`
- [避坑规则] 面级操作用 MItMeshPolygon

### 2026-04-08 — 多网格分组绑定架构

- [触发条件] 多个网格同一骨骼时产生大量冗余矩阵节点
- [根因] v1.0 对每个子网格单独创建 multMatrix 节点
- [正确方案] 按骨骼创建 transform 组，一个组一个 multMatrix
- [避坑规则] 先分组再绑定，不要逐网格绑定

### 2026-04-08 — ensure_group 命名冲突导致骨骼被移出层级

- [触发条件] 绑定系统已有同名组（如 AdvancedSkeleton 的 Head_M_grp）
- [根因] ensure_group 只检查 objExists，不检查父级是否正确，直接返回其他层级的同名节点
- [正确方案] 检查已有节点的 parent 是否在 CutModGeometry 下，不是则创建 CutMod_ 前缀新组
- [避坑规则] 绝不能假设同名节点就是我们的节点，必须验证层级归属

### 2026-04-08 — 片状模型被错误封口

- [触发条件] 片状/开放模型切分后被 polyCloseBorder 无差别封口
- [根因] 封口函数不区分"原始开放边"和"切割新产生的边"
- [正确方案] 切分前采集原始 border 顶点位置集合，封口时逐边匹配，只封新边界
- [避坑规则] 封口必须对比原始拓扑，切勿无脑 polyCloseBorder
