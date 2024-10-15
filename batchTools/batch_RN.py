#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: batch_RN.py
@date: 2024/9/14 16:19
@desc:
"""

import os
import sys
import maya.standalone
import maya.cmds as cmds

# 初始化 Maya 独立模式
maya.standalone.initialize(name='python')

# 指定要处理的 Maya 根目录路径
root_folder = r'X:\Project\tbx\pub\asset_lib\chr\cttvcamerist\rig\task_master'  # 请修改为您的实际路径

# 结果列表
results = []

# 用于存储已处理的 .ma 文件路径，避免重复处理
processed_files = set()

# 遍历根目录下的所有文件和文件夹，递归查找 .ma 文件
for dirpath, dirnames, filenames in os.walk(root_folder):
    for filename in filenames:
        if filename.endswith('.ma'):
            maya_file_path = os.path.join(dirpath, filename)
            # 避免重复处理同一个文件
            if maya_file_path in processed_files:
                continue
            processed_files.add(maya_file_path)
            try:
                print(u'正在处理文件：{}'.format(maya_file_path))

                # 打开 Maya 文件
                cmds.file(maya_file_path, open=True, force=True)

                # 查找所有 DAG 节点（场景中的所有物体）
                all_objects = cmds.ls(dag=True, long=True)

                for obj in all_objects:
                    # 检查物体名称中是否包含 'vitreous'（不区分大小写）
                    if 'vitreous' in obj.lower():
                        # 获取物体的形状节点
                        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True)
                        if shapes:
                            for shape in shapes:
                                # 获取形状的着色组（Shading Engine）
                                shading_engines = cmds.listConnections(shape, type='shadingEngine')
                                if shading_engines:
                                    for sg in shading_engines:
                                        # 获取连接到着色组的材质球
                                        materials = cmds.ls(cmds.listConnections(sg + '.surfaceShader'), materials=True)
                                        if materials:
                                            for material in materials:
                                                # 获取材质球的类型
                                                material_type = cmds.nodeType(material)
                                                # 记录结果，创建变量的副本
                                                results.append({
                                                    '文件': str(maya_file_path),
                                                    '物体': str(obj),
                                                    '材质球': str(material),
                                                    '材质类型': str(material_type)
                                                })
                # 关闭当前文件，避免影响下一个文件的处理
                cmds.file(new=True, force=True)
            except Exception as e:
                print(u'处理文件 {} 时出错：{}'.format(maya_file_path, e))
                continue

# 生成可读的总结文本信息
summary = u''
if results:
    summary += u'检测结果：\n'
    for item in results:
        summary += u"文件：{}\n物体：{}\n材质球：{}\n材质类型：{}\n\n".format(
            item['文件'], item['物体'], item['材质球'], item['材质类型'])
    summary += u'总共找到 {} 个名称中包含 "vitreous" 的物体。\n'.format(len(results))
else:
    summary = u'未找到名称中包含 "vitreous" 的物体。\n'

# 输出总结信息到控制台
print(summary)

# 将总结信息保存到文本文件
with open(r'C:\Users\yuweiming\Desktop\tmp\summary.txt', 'w') as f:
    f.write(summary.encode('utf-8'))

# 关闭 Maya 独立模式
maya.standalone.uninitialize()
