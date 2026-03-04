# 任务清单 (Tasks)

- [x] 解决控制器尺寸不随骨骼距离自适应的问题
  - 原因定位：`RigUtils.create_control_shape` 内部参数硬编码
  - 修复：恢复基于距离算出的动态 `size` 参数传递
- [x] 沉淀尺寸计算异常原因至 lessons.md
