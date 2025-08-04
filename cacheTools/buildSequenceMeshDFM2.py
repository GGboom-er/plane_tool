import bpy
import os


def get_object_hierarchy_path(obj):
    """
    获取选中物体在大纲中的绝对路径
    :param obj: 目标物体
    :return: 物体的绝对路径字符串
    """
    path = obj.name
    parent = obj.parent
    while parent:
        path = parent.name + "/" + path
        parent = parent.parent
    return path


def add_mesh_sequence_cache_to_selected(cache_path):
    """
    为选中的物体添加Mesh Sequence Cache变形器，并设置计算优先级为最高
    :param cache_path: 缓存文件路径
    """
    selected_objects = bpy.context.selected_objects

    if not selected_objects:
        print("没有选择任何模型。")
        return

    # 规范化路径
    cache_path = os.path.normpath(cache_path)

    # 确保缓存文件已经存在于项目中
    cache_file = None
    for cf in bpy.data.cache_files:
        if cf.filepath == cache_path:
            cache_file = cf
            break

    if cache_file is None:
        try:
            # 创建缓存文件（只需加载一次）
            bpy.ops.cachefile.open(filepath=cache_path)
            cache_file = bpy.context.blend_data.cache_files[-1]
        except Exception as e:
            print(f"加载缓存文件失败: {e}")
            return

    for obj in selected_objects:
        if obj.type != 'MESH':
            print(f"对象 {obj.name} 不是Mesh类型，跳过...")
            continue

        # 检查是否已经有Mesh Sequence Cache Modifier
        existing_mod = next((mod for mod in obj.modifiers if mod.type == 'MESH_SEQUENCE_CACHE'), None)
        if existing_mod:
            print(f"对象 {obj.name} 已有Mesh Sequence Cache变形器，跳过...")
            continue

        # 添加Mesh Sequence Cache Modifier
        modifier = obj.modifiers.new(name="MeshSequenceCache", type='MESH_SEQUENCE_CACHE')
        modifier.read_data = {'VERT'}

        # 设置Cache File
        modifier.cache_file = cache_file

        # 替换名称中的 . 为 _
        obj_name = obj.name.replace('.', '_')
        shape_name = obj.data.name.replace('.', '_')

        # 设置Object Path，格式为 /group10/当前物体名/当前物体shape名
        object_path = get_object_hierarchy_path(obj)

        # 根据需求替换路径层次
        if 'Group/cache/' in object_path:
            object_path = object_path.replace('Group/cache/', '/Group/Geometry/cache/')

        modifier.object_path = object_path

        # 将修改器移到堆栈顶部（直接移动到索引0）
        obj.modifiers.move(len(obj.modifiers) - 1, 0)

        print(
            f"为模型 {obj.name} 添加了Mesh Sequence Cache变形器，缓存路径: {cache_path}，对象路径: {object_path}")


# 使用函数
cache_path = r"U:\ywm\cache\ssx\ssx_chr_sunshangxiang_rig_master_v003_LGTcache.usd"  # 缓存文件路径
add_mesh_sequence_cache_to_selected(cache_path)
