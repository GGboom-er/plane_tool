#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: textCheckMa.py
@date: 2024/12/4 11:33
@desc: 
"""
import os
import re
'''
"C:\Program Files\Autodesk\Maya2018\bin\mayapy.exe" Y:\GGbommer\scripts\plane_tool\batchTools\textCheckMa.py
'''
# 指定要处理的 Maya 根目录路径
root_folder = r'X:\Project\tbx\pub\asset_lib\prp'  # 请修改为您的实际路径
# 指定目标字符串
target_string = "3d66Models"  # 替换为您要查找的目标字符串

# 存储包含最高版本文件的路径
highest_version_files = {}

# 版本号提取的正则表达式
version_pattern = re.compile(r'_v(\d+)\.ma$')

# 遍历根目录下的所有文件和文件夹，递归查找 .ma 文件
for dirpath, dirnames, filenames in os.walk(root_folder):
    ma_files = [f for f in filenames if f.endswith('.ma')]
    file_versions = {}

    # 按文件名解析版本号并分类
    for filename in ma_files:
        version_match = version_pattern.search(filename)
        if version_match:
            version_number = int(version_match.group(1))
            base_name = re.sub(r'_v\d+\.ma$', '', filename)
            if base_name not in file_versions:
                file_versions[base_name] = {'version': version_number, 'path': os.path.join(dirpath, filename)}
            else:
                # 更新为更高版本
                if version_number > file_versions[base_name]['version']:
                    file_versions[base_name] = {'version': version_number, 'path': os.path.join(dirpath, filename)}

    # 保存最高版本文件路径
    for base_name, info in file_versions.items():
        highest_version_files[info['path']] = info['version']

# 对筛选后的最高版本文件执行目标字符串查找
matching_files = []

for file_path in highest_version_files.keys():
    try:
        with open(file_path, 'r') as f:
            for line in f:
                if target_string in line:
                    matching_files.append(file_path)
                    # 一旦找到目标字符串，就跳过剩余行，加速处理
                    break
    except Exception as e:
        print(u'处理文件 {} 时出错：{}'.format(file_path, e))
        continue

# 输出包含目标字符串的文件路径
if matching_files:
    print(u'找到包含目标字符串的文件：')
    for file_path in matching_files:
        print(file_path)
else:
    print(u'未找到包含目标字符串的文件。')

# 将结果保存到文本文件
output_file = r'C:\Users\yuweiming\Desktop\tmp\matching_files.txt'  # 修改为您的实际输出路径
try:
    with open(output_file, 'w') as f:  # 移除编码关键字参数
        if matching_files:
            f.write("找到以下包含目标字符串的文件：\n")
            for file_path in matching_files:
                f.write(file_path + '\n')
        else:
            f.write("未找到包含目标字符串的文件。\n")
except Exception as e:
    print(u'保存结果到文件时出错：{}'.format(e))
