#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: renameParent.py
@date: 2025/4/15 14:31
@desc: 
"""
import pymel.core as pm


def rename_parent_hierarchy_batch( suffixes ):
    """
    对选中的多个物体的上层父级按顺序进行重命名。

    工作原理：
      - 首先获取当前选中的所有物体，若未选中物体，则报错终止。
      - 对于每个选中的物体，记录其原始名称作为命名前缀。
      - 从当前物体开始，逐级向上查找父级：
          1. 获取当前物体的直接父级。
          2. 如果父级存在，则按“前缀_后缀”（例如 'obj_a'）格式重命名该父级。
          3. 更新当前对象为刚刚重命名的父级，然后继续处理下一级父级。
      - 若在迭代过程中发现父级不足，则发出警告并终止对该物体后续层级的处理。

    参数:
      suffixes (list[str]): 后缀列表，其长度决定了沿着父级链重命名的层级数量。

    使用示例：
      假设选中 'A', 'B' 两个物体，且传入参数 ['a','b']：
        - 'A' 的父节点依次重命名为 'A_a'、'A_b'
        - 'B' 的父节点依次重命名为 'B_a'、'B_b'
    """
    # 获取所有选中的物体
    selected_objs = pm.ls(sl=True)
    if not selected_objs:
        pm.error("请先选中至少一个物体！")
        return

    # 对每个选中的物体都进行处理
    for base_obj in selected_objs:
        base_name = base_obj.nodeName()  # 记录原始名称作为前缀
        current_obj = base_obj  # 从选中物体开始
        for suffix in suffixes:
            parent_obj = current_obj.getParent()
            if not parent_obj:
                pm.warning("物体 '{}' 的父级不足，无法继续重命名。".format(current_obj))
                break
            # 拼接新名称，格式为 "原始名称_后缀"
            new_name = "{}_{}".format(base_name, suffix)
            parent_obj.rename(new_name)
            # 将当前对象更新为刚刚重命名的父级，继续处理更高层级
            current_obj = parent_obj


# 使用方法示例：
# 1. 在 Maya 中同时选中多个目标物体（例如名称为 'A' 和 'B'）。
# 2. 在 Script Editor 中执行以下代码：
#    rename_parent_hierarchy_batch(['a', 'b'])
#
# 运行结果：
# 对 'A' 及 'B' 分别执行：
# - 直接父级重命名为 "A_a" 和 "B_a"
# - 上一级父级重命名为 "A_b" 和 "B_b"
rename_parent_hierarchy_batch(['Offset', 'OffsetPnt'])