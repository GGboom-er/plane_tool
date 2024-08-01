import bpy


def add_mesh_sequence_cache_to_selected( cache_path ):
    selected_objects = bpy.context.selected_objects

    if not selected_objects:
        print("û��ѡ���κ�ģ�͡�")
        return

    # ȷ�������ļ��Ѿ���������Ŀ��
    cache_file = None
    for cf in bpy.data.cache_files:
        if cf.filepath == cache_path:
            cache_file = cf
            break

    if cache_file is None:
        # ���������ļ�
        bpy.ops.cachefile.open(filepath=cache_path)
        cache_file = bpy.context.blend_data.cache_files[-1]

    for obj in selected_objects:
        if obj.type != 'MESH':
            print(f"���� {obj.name} ����Mesh���ͣ�����...")
            continue

        # ���Mesh Sequence Cache Modifier
        modifier = obj.modifiers.new(name="MeshSequenceCache", type='MESH_SEQUENCE_CACHE')

        # ����Cache File
        modifier.cache_file = cache_file

        # ����File Path
        modifier.cache_file.filepath = cache_path

        # �滻�����е� . Ϊ _
        obj_name = obj.name.replace('.', '_')
        shape_name = obj.data.name.replace('.', '_')

        # ����Object Path����ʽΪ /group10/��ǰ������/��ǰ����shape��
        object_path = f"/group10/{obj_name}/{shape_name}"
        modifier.object_path = object_path

        print(
            f"Ϊģ�� {obj.name} �����Mesh Sequence Cache���������������˻���·��Ϊ {cache_path} �Ͷ���·��Ϊ {object_path}")


# ʹ�ú���
cache_path = r"U:\ywm\ssx\cache\jodInCircle.abc"  # �����ļ�·��
add_mesh_sequence_cache_to_selected(cache_path)
