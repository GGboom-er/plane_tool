#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: appendFile.py
@date: 2024/12/5 16:59
@desc: 
"""
import bpy
def append_mesh_and_materials( file_paths ):
    """
    从多个 Blender 文件中加载 Mesh 和 Materials 并追加到当前场景中。

    :param file_paths: list[str]，包含 .blend 文件路径的列表
    """
    for file_path in file_paths:
        try:
            print(f"开始加载文件: {file_path}")

            # 加载 Mesh 数据
            with bpy.data.libraries.load(file_path, link=False) as (data_from, data_to):
                # 筛选 Mesh 数据
                data_to.meshes = [name for name in data_from.meshes]
                data_to.materials = [name for name in data_from.materials]

            # 将加载的 Mesh 链接到当前场景
            for mesh_name in data_to.meshes:
                if mesh_name:
                    mesh = bpy.data.meshes.get(mesh_name)
                    if mesh:
                        # 创建一个对象并附加 Mesh
                        obj = bpy.data.objects.new(mesh_name, mesh)
                        bpy.context.scene.collection.objects.link(obj)
                        print(f"成功追加 Mesh 对象: {mesh_name}")

            # 打印加载的材料信息
            for mat_name in data_to.materials:
                if mat_name:
                    material = bpy.data.materials.get(mat_name)
                    if material:
                        print(f"成功加载材质: {mat_name}")

        except Exception as e:
            print(f"加载文件 {file_path} 时出错: {e}")


# 示例用法
file_paths = [
    r"x:\Project\tbx\asset\chr\componenta\tex\task_master\tbx_chr_componenta_tex_master_v006.blend"
]

append_mesh_and_materials(file_paths)

import bpy


def sanitize_name( name ):
    """
    移除名称中的数字后缀，例如 `****abc_AAABBBCC_EEShape.001` -> `****abc_AAABBBCC_EEShape`
    """
    if '.' in name and name.split('.')[-1].isdigit():
        return ".".join(name.split('.')[:-1])  # 去掉最后的数字后缀
    return name  # 如果没有数字后缀，直接返回原名称


def get_all_shape_names():
    """
    获取当前场景中所有 Shape (Mesh Data) 节点的名称，兼容是否以 Shape 结尾的情况。
    """
    shape_names = [obj.data.name for obj in bpy.data.objects if obj.type == 'MESH' and obj.data]
    print("当前场景中的 Shape 节点名称:")
    for name in shape_names:
        print(f" - {name}")
    return shape_names


def match_and_apply_materials():
    """
    匹配当前场景 Shape 与导入场景 Shape 的名称，忽略尾缀，并将导入 Shape 的材质赋予当前 Shape。
    """
    # 获取当前场景中的 Shape 节点
    current_shape_names = get_all_shape_names()

    # 获取导入场景的 Shape 节点
    imported_shape_names = [mesh.name for mesh in bpy.data.meshes if mesh.users == 0]
    print("\n导入场景中的 Shape 节点:")
    for name in imported_shape_names:
        print(f" - {name}")

    # 匹配 Shape 节点并赋予材质
    for current_name in current_shape_names:
        # 移除尾缀
        sanitized_current_name = sanitize_name(current_name)
        # 提取尾部名称（支持 Shape 结尾与非 Shape 结尾）
        tail_name = "_".join(sanitized_current_name.split("_")[-3:]).rstrip("Shape")
        print(f"当前 Shape: {current_name}, 提取的尾部名称: {tail_name}")

        # 在导入 Shape 中查找匹配
        matched_name = next(
            (name for name in imported_shape_names if name.rstrip("Shape").endswith(tail_name)),
            None
        )

        if matched_name:
            print(f"匹配成功: {current_name} -> {matched_name}")
            # 获取当前和导入 Shape 的材质
            current_shape = bpy.data.meshes[current_name]
            matched_shape = bpy.data.meshes[matched_name]

            if matched_shape.materials:
                current_shape.materials.clear()  # 清空当前材质
                for material in matched_shape.materials:
                    current_shape.materials.append(material)  # 赋予导入材质
                print(f"材质已赋予给 Shape: {current_name}")
            else:
                print(f"导入 Shape {matched_name} 没有材质")
        else:
            print(f"未找到匹配: {current_name}")


# 调用主函数
match_and_apply_materials()











