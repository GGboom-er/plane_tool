#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: optimizBlender.py
@date: 2024/12/6 13:14
@desc: 
"""
import bpy

def optimize_scene():
    """
    优化当前场景：
    1. 清理未使用的数据块（Data-Blocks）。
    2. 删除所有 Libraries（外部链接资源）。
    """
    print("开始优化场景...")

    # 删除所有 Libraries
    def delete_all_libraries():
        print("\n>>> 开始删除所有 Libraries...")
        library_count = len(bpy.data.libraries)
        if library_count == 0:
            print("当前场景中没有 Libraries，无需删除。")
        else:
            for library in list(bpy.data.libraries):  # 使用 list() 防止迭代时修改集合
                print(f"删除库: {library.filepath}")
                bpy.data.libraries.remove(library)
            print(f"已删除 {library_count} 个 Libraries。")

    # 清理未使用的数据块
    def clean_up_data_blocks():
        print("\n>>> 开始清理未使用的数据块...")
        # 执行各种清理操作
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=False)
        print("已清理未使用的本地数据块。")
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
        print("已递归清理未使用的本地数据块。")
        bpy.ops.outliner.orphans_purge(do_local_ids=False, do_linked_ids=True, do_recursive=False)
        print("已清理未使用的链接数据块。")
        bpy.ops.outliner.orphans_purge(do_local_ids=False, do_linked_ids=True, do_recursive=True)
        print("已递归清理未使用的链接数据块。")
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
        print("已递归清理所有未使用的数据块。")

    # 调用子功能
    delete_all_libraries()
    clean_up_data_blocks()

    print("\n场景优化完成！")


# 调用优化场景函数
optimize_scene()
