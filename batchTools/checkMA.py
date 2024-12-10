# -*- coding: utf-8 -*-
import os
import re
'''
"C:\Program Files\Autodesk\Maya2018\bin\mayapy.exe" Y:\GGbommer\scripts\plane_tool\batchTools\checkMA.py
'''
# 指定要处理的 Maya 根目录路径
root_folder = r'X:\Project\tbx\pub\asset_lib\chr\ctboy\rig\task_master'  # 请修改为您的实际路径

# 结果列表
results = []

# 用于存储已处理的 .ma 文件路径，避免重复处理
processed_files = set()

# 正则表达式模式（更新）
create_node_pattern = re.compile(r'^createNode\s+(\w+)(?:\s+-[^;]+)*\s+-n\s+"([^"]+)"')
connect_attr_pattern = re.compile(r'^connectAttr\s+"([^"]+)\.([^"]+)"\s+"([^"]+)\.([^"]+)";?')

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

                # 存储节点信息的字典
                nodes = {}
                # 存储连接信息的列表
                connections = []

                # 逐行读取文件，解析所需信息
                with open(maya_file_path, 'r', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        # 匹配 createNode
                        create_node_match = create_node_pattern.match(line)
                        if create_node_match:
                            node_type, node_name = create_node_match.groups()
                            nodes[node_name] = {
                                'type': node_type,
                                'attributes': {},
                                'connections': []
                            }
                            # 调试信息
                            # print(u'找到节点：{}，类型：{}'.format(node_name, node_type))
                            continue

                        # 匹配 connectAttr
                        connect_attr_match = connect_attr_pattern.match(line)
                        if connect_attr_match:
                            src_node, src_attr, dest_node, dest_attr = connect_attr_match.groups()
                            connections.append({
                                'source': (src_node, src_attr),
                                'destination': (dest_node, dest_attr)
                            })
                            # 调试信息
                            # print(u'找到连接：{}.{}, {}.{}'.format(src_node, src_attr, dest_node, dest_attr))
                            # 将连接信息添加到节点中
                            if dest_node in nodes:
                                nodes[dest_node]['connections'].append({
                                    'source': (src_node, src_attr),
                                    'destination': (dest_node, dest_attr)
                                })
                            continue

                # 查找名称中包含 'vitreous' 的物体
                for node_name, node_info in nodes.items():
                    if 'vitreous' in node_name.lower():
                        # 检查节点类型是否为变换或形状节点
                        if node_info['type'] in ['transform', 'mesh', 'nurbsSurface', 'nurbsCurve']:
                            # 查找与该节点相关的材质球
                            # 首先找到该形状节点连接的 shadingEngine
                            shading_engines = []
                            for conn in connections:
                                if conn['source'][0] == node_name and conn['source'][1] == 'instObjGroups':
                                    shading_engine = conn['destination'][0]
                                    shading_engines.append(shading_engine)
                            # 然后找到 shadingEngine 连接的材质球
                            for sg in shading_engines:
                                for conn in connections:
                                    if conn['destination'][0] == sg and conn['destination'][1] == 'surfaceShader':
                                        material = conn['source'][0]
                                        # 获取材质类型
                                        material_type = nodes.get(material, {}).get('type', '未知类型')
                                        # 记录结果
                                        results.append({
                                            '文件': maya_file_path,
                                            '物体': node_name,
                                            '材质球': material,
                                            '材质类型': material_type
                                        })
                # 完成当前文件的处理
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
