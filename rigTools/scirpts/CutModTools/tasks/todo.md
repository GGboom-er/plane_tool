# CutMod 任务清单

## v1.0.0 ✅
- [x] 权重分析器
- [x] 几何切分器
- [x] 绑定器（矩阵/约束）
- [x] 属性快照保护
- [x] UI 主窗口
- [x] Maya 2025 验证

## v1.1.0 ✅
- [x] 边界拓扑平滑（形态学 + 连通性修复）
- [x] 父骨骼优先策略
- [x] 面部区域排除（Head_M 子层级合并 + skinCluster 保留）
- [x] 封口（polyCloseBorder + lambert1）
- [x] UI 更新（排除骨骼/平滑参数/封口开关/预览表标记）
- [x] Maya 2025 全流程测试通过
- [x] 修复 MItMeshPolygon 替代 MFnMesh.getPolygonEdges

## v1.2.0 ✅
- [x] 多网格支持与统一按骨骼组绑定（大幅减少矩阵节点）
- [x] 修复 ensure_group 引起的同名层级冲突（避免改动原始骨骼层级）
- [x] 修复基于边界点的智能封口（跳过片状模型的原始开放边界）
- [x] 提交到 GitHub 仓库
