#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: appendCache.py
@date: 2024/11/20 11:49
@desc: 
"""
import bpy
import os


def append_collection_to_cache( blender_file_path, collection_name ):
    # 检查文件是否存在
    if not os.path.isfile(blender_file_path):
        raise FileNotFoundError("指定的 Blender 文件不存在: {}".format(blender_file_path))

    # 定义 Collection 路径
    collection_path = os.path.join(blender_file_path, "Collection", collection_name)

    # 确保目标 Collection 存在于外部文件
    with bpy.data.libraries.load(blender_file_path) as (data_from, data_to):
        if collection_name not in data_from.collections:
            raise ValueError("外部文件中不存在 Collection: {}".format(collection_name))

    # Append Collection
    bpy.ops.wm.append(filepath=collection_path, directory=os.path.join(blender_file_path, "Collection"),
                      filename=collection_name)

    # 获取导入的 Collection
    imported_collection = bpy.data.collections.get(collection_name)
    if not imported_collection:
        raise RuntimeError("导入 Collection 失败: {}".format(collection_name))

    # 找到当前文件中的 cache 组
    cache_group = bpy.data.collections.get("cache")
    if not cache_group:
        raise ValueError("当前场景中未找到 'cache' 组")

    # 将导入的 Collection 移动到 cache 组中
    cache_group.children.link(imported_collection)

    # 从顶级场景移除导入的 Collection
    bpy.context.scene.collection.children.unlink(imported_collection)

    print("成功将 Collection '{}' 导入到 'cache' 组中".format(collection_name))


# 示例：文件路径和 Collection 名称
blender_file_path = r"C:\Users\yuweiming\Desktop\tmp\tbx_chr_componenta_tex_master_v006.blend"
collection_name = "Collection"

# 执行导入并移动到 cache
append_collection_to_cache(blender_file_path, collection_name)
