# MRS 两个核心 Bug 修复计划

## 问题分析

### 问题1：uvPin 轴向映射错误

**根因**：`builder.py:_setup_uv_pin()` 中的 `axis_map` 映射表完全搞反了。

**Maya uvPin 节点的实际行为**（已通过 mayapy 测试验证）：
- `tangentAxis` = UV 空间的 **U 方向切线** 映射到输出矩阵的哪个轴
- `normalAxis` = **表面法线** 映射到输出矩阵的哪个轴
- 第三个轴自动成为 **binormal（V 方向）**

**MRS mesh 的 UV 布局**（由 `py_matrix_ribbon.py` 生成）：
- **U 方向 = width 方向**（跨链方向）
- **V 方向 = aim 方向**（沿链方向）

**正确映射推导**：

以 axis_mode=0 (X-Aim, Z-Width) 为例：
- tangent(U方向) = width = Z → `tangentAxis = 2`
- normal = 剩余轴 = Y → `normalAxis = 1`
- binormal(V方向) = aim = X → 自动推导 ✓

当前错误代码：`axis_map[0] = (0, 1)` → tangentAxis=0(X)，把 width 方向错误映射到了 X。

**完整正确映射表**：

| Mode | Aim | Width | Normal | tangentAxis(=Width) | normalAxis(=Normal) |
|------|-----|-------|--------|---------------------|---------------------|
| 0 | X | Z | Y | 2 | 1 |
| 1 | X | Y | Z | 1 | 2 |
| 2 | Y | Z | X | 2 | 0 |
| 3 | Y | X | Z | 0 | 2 |
| 4 | Z | X | Y | 0 | 1 |
| 5 | Z | Y | X | 1 | 0 |

### 问题2：followMod 不应被骨骼蒙皮

**正确架构**：
```
followMod (静态mesh，由外部身体驱动，不受绑定系统内任何控制)
    → uvPin 采样 followMod 表面
        → 输出矩阵驱动控制器 Offset 组
            → 控制器通过 OPM 驱动骨骼
                → 骨骼蒙皮衣服/配饰
```

**当前错误**：`finalize_bind()` 中对 followMod 调用了 `apply_perfect_ribbon_weights()`，给它绑了 skinCluster 到骨骼上。这形成了循环依赖：骨骼→蒙皮followMod→uvPin→控制器→骨骼。

**正确行为**：followMod 应该是一个**干净的静态 mesh**（无 skinCluster），等待用户后续从身体拷贝权重或其他外部驱动。

**Proxy（蒙皮代理）是完全独立的功能**：
- 利用 mesh 拓扑 + `apply_perfect_ribbon_weights` 生成预设权重的代理模型
- 方便用户绘制衣服/配饰权重
- 可以在 Preview 阶段直接生成（从 preview mesh），也可以在 Bind 之后生成（从 followMod）
- 与绑定系统无关

---

## 修改方案

### Fix1：修正 uvPin 轴向映射（builder.py）

**文件**：`builder.py:_setup_uv_pin()`

将 `axis_map` 从：
```python
axis_map = {
    0: (0, 1),  # 错误
    1: (0, 2),  # 错误
    2: (1, 0),  # 错误
    3: (1, 2),  # 错误
    4: (2, 1),  # 错误
    5: (2, 0)   # 错误
}
```

改为：
```python
# tangentAxis = Width 轴, normalAxis = Normal 轴 (binormal 自动 = Aim 轴)
axis_map = {
    0: (2, 1),  # X-Aim, Z-Width -> tangent=Z(2), normal=Y(1)
    1: (1, 2),  # X-Aim, Y-Width -> tangent=Y(1), normal=Z(2)
    2: (2, 0),  # Y-Aim, Z-Width -> tangent=Z(2), normal=X(0)
    3: (0, 2),  # Y-Aim, X-Width -> tangent=X(0), normal=Z(2)
    4: (0, 1),  # Z-Aim, X-Width -> tangent=X(0), normal=Y(1)
    5: (1, 0),  # Z-Aim, Y-Width -> tangent=Y(1), normal=X(0)
}
```

### Fix2：followMod 不再蒙皮（builder.py）

**文件**：`builder.py:finalize_bind()`

删除 `finalize_bind` 中对 followMod 的 `apply_perfect_ribbon_weights` 调用。followMod 保持为干净的静态 mesh。

具体删除行 419-429 中的：
```python
if not update_mode:
    follow_mesh = self._setup_follow_mesh(...)
    is_reversed = ...
    RigUtils.apply_perfect_ribbon_weights(...)  # ← 删除这部分
```

改为：
```python
if not update_mode:
    follow_mesh = self._setup_follow_mesh(...)
    # followMod 保持为静态 mesh，不蒙皮
```

### Fix3：Proxy 功能保持不变

`create_standalone_proxy` 中的 `apply_perfect_ribbon_weights` 调用**保留不变**——这是独立的蒙皮代理功能，与绑定系统无关。

### Fix4：更新测试

更新 `test_mrs.py` 和 `test_final.py`：
- 移除对 followMod 有 skinCluster 的断言
- 添加对 followMod 无 skinCluster 的验证
- 添加 uvPin 轴向正确性验证

---

## 修改文件清单

| 文件 | 修改 |
|------|------|
| `builder.py` | Fix1: 修正 axis_map; Fix2: 删除 followMod 蒙皮 |
| `test_mrs.py` | Fix4: 更新测试断言 |
| `test_final.py` | Fix4: 更新测试断言 |

---

## 验证方案

1. `mayapy test_mrs.py` — 完整生命周期
2. `mayapy test_final.py` — 变形 + 全局缩放
3. 新增 uvPin 轴向验证测试：创建已知轴向的骨骼链 → Preview → Bind → 验证控制器轴向与骨骼一致
