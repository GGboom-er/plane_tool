import bpy
import os


def get_object_hierarchy_path( obj ):
    """
    获取选中物体在大纲中的绝对路径 (DAG Path)
    :param obj: 目标物体
    :return: 物体的绝对路径字符串
    """
    path = obj.name
    parent = obj.parent
    while parent:
        path = parent.name + "/" + path
        parent = parent.parent
    return path


def move_modifier_to_top( obj, modifier_name ):
    """
    [Atomic Operation] 将指定名称的修改器移动到堆栈顶层
    :param obj: 目标物体对象
    :param modifier_name: 修改器名称
    """
    # 获取修改器集合
    modifiers = obj.modifiers

    # 1. 验证修改器是否存在
    mod_index = modifiers.find(modifier_name)
    if mod_index == -1:
        print(f"Error: Modifier '{modifier_name}' not found on {obj.name}.")
        return

    # 2. 如果已经是在索引 0 (最顶层)，则无需操作
    if mod_index == 0:
        return

    # 3. 执行移动操作: move(from_index, to_index)
    try:
        modifiers.move(mod_index, 0)
        # 再次验证 (Double Check)
        if modifiers[0].name != modifier_name:
            print(f"Warning: Failed to force modifier '{modifier_name}' to top on {obj.name}. Stack might be locked.")
    except Exception as e:
        print(f"Critical Error moving modifier: {e}")


def add_mesh_sequence_cache_to_selected( cache_path ):
    """
    为选中的物体添加Mesh Sequence Cache变形器，并强制设置优先级为最高 (Stack Top)
    """
    # 1. 环境感知与输入验证
    selected_objects = bpy.context.selected_objects
    if not selected_objects:
        print("Warning: No objects selected.")
        return

    cache_path = os.path.normpath(cache_path)

    # 2. 缓存文件处理 (Cache File Handling)
    # 查找现有缓存或创建新缓存
    cache_file = next((cf for cf in bpy.data.cache_files if cf.filepath == cache_path), None)

    if cache_file is None:
        try:
            bpy.ops.cachefile.open(filepath=cache_path)
            # 使用 filepath 再次确认获取，而非依赖 [-1]，防止并发索引偏移
            cache_file = next((cf for cf in bpy.data.cache_files if cf.filepath == cache_path), None)
            if not cache_file:
                # 极端情况 fallback
                cache_file = bpy.context.blend_data.cache_files[-1]
        except Exception as e:
            print(f"Fatal: Failed to load cache file: {e}")
            return

    # 3. 遍历对象执行 (Execution Loop)
    for obj in selected_objects:
        if obj.type != 'MESH':
            continue

        # 检查是否已存在 (避免重复添加)
        existing_mod = next((mod for mod in obj.modifiers if mod.type == 'MESH_SEQUENCE_CACHE'), None)

        target_mod = None

        if existing_mod:
            print(f"Info: Object {obj.name} already has Mesh Sequence Cache. Updating logic...")
            target_mod = existing_mod
        else:
            # 创建新修改器 (默认在堆栈底部)
            target_mod = obj.modifiers.new(name="MeshSequenceCache", type='MESH_SEQUENCE_CACHE')

        # 配置属性
        target_mod.cache_file = cache_file
        target_mod.read_data = {'VERT'}  # 根据需要开启 'POLY', 'UV' 等

        # 路径逻辑处理
        object_path = get_object_hierarchy_path(obj)
        # 你的特定路径替换逻辑
        if 'Group/cache/' in object_path:
            object_path = object_path.replace('Group/cache/', '/Group/Geometry/cache/')

        target_mod.object_path = object_path

        # 4. 关键步骤：强制重排 (Reorder)
        # 使用专用函数移动到 Index 0
        move_modifier_to_top(obj, target_mod.name)

        print(f"Success: {obj.name} -> Cache Path Set -> Modifier Moved to Top.")

# 使用函数
# cache_path = r"U:\ywm\cache\ysj\cache_hair.usd"
# add_mesh_sequence_cache_to_selected(cache_path)