#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: moveOutline.py
@date: 2024/9/27 15:40
@desc: 
"""
import bpy

# 获取红框中的集合
source_collection = bpy.data.collections['Collection.001'].children.get('cache.001')

# 如果找到该集合，则遍历其中的对象并取消链接
if source_collection:
    for obj in source_collection.objects:
        source_collection.objects.unlink(obj)
    print("物体已从集合 'cache.001' 中移除")
else:
    print("未找到集合 'cache.001'")
