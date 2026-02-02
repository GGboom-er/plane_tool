#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: renameShape.py
@date: 2024/8/5 17:40
@desc: 
"""
import bpy

def batch_rename_shape_nodes():
    """
    功能：将选中对象的数据块(Data/Shape)重命名为 '对象名 + Shape'。
    适用版本：Blender 3.x, 4.x, 5.x
    """
    # 1. 获取当前所有选中的对象
    selected_objs = bpy.context.selected_objects

    if not selected_objs:
        print(">>> 错误：未选中任何对象 (No Selection)。")
        return

    # 计数器
    success_count = 0
    skipped_count = 0

    print(f"{'-' * 30}\n开始执行批量 Shape 重命名...\n{'-' * 30}")

    # 2. 迭代遍历所有选中对象
    for obj in selected_objs:
        # 3. 验证对象是否存在 Data Block (过滤掉 Empty 等无 Shape 的物体)
        if obj.data:
            old_data_name = obj.data.name
            target_name = f"{obj.name}Shape"

            # 4. 执行重命名
            # 注意：如果多个物体共享同一个 Mesh Data (Instance)，重命名会影响所有实例
            obj.data.name = target_name

            print(f"[成功] 对象: {obj.name} | 原Shape: {old_data_name} -> 新Shape: {obj.data.name}")
            success_count += 1
        else:
            print(f"[跳过] 对象: {obj.name} (无数据块/Shape)")
            skipped_count += 1

    # 5. 总结输出
    print(f"{'-' * 30}")
    print(f"处理完成。成功: {success_count} | 跳过: {skipped_count}")
    print(f"{'-' * 30}")


# 执行主函数
if __name__ == "__main__":
    batch_rename_shape_nodes()
