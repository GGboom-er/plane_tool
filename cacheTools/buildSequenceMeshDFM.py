import bpy


def add_mesh_sequence_cache_to_selected( cache_path ):
    selected_objects = bpy.context.selected_objects

    if not selected_objects:
        print("没有选择任何模型。")
        return

    # 确保缓存文件已经存在于项目中
    cache_file = None
    for cf in bpy.data.cache_files:
        if cf.filepath == cache_path:
            cache_file = cf
            break

    if cache_file is None:
        # 创建缓存文件
        bpy.ops.cachefile.open(filepath=cache_path)
        cache_file = bpy.context.blend_data.cache_files[-1]

    for obj in selected_objects:
        if obj.type != 'MESH':
            print(f"对象 {obj.name} 不是Mesh类型，跳过...")
            continue

        # 添加Mesh Sequence Cache Modifier
        modifier = obj.modifiers.new(name="MeshSequenceCache", type='MESH_SEQUENCE_CACHE')

        # 设置Cache File
        modifier.cache_file = cache_file

        # 设置File Path
        modifier.cache_file.filepath = cache_path

        # 替换名称中的 . 为 _
        obj_name = obj.name.replace('.', '_')
        shape_name = obj.data.name.replace('.', '_')

        # 设置Object Path，格式为 /group10/当前物体名/当前物体shape名
        object_path = f"/group10/{obj_name}/{shape_name}"
        modifier.object_path = object_path

        print(
            f"为模型 {obj.name} 添加了Mesh Sequence Cache变形器，并设置了缓存路径为 {cache_path} 和对象路径为 {object_path}")


# 使用函数
cache_path = r"U:\ywm\ssx\cache\jodInCircle.abc"  # 缓存文件路径
add_mesh_sequence_cache_to_selected(cache_path)
