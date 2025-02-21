import sys
sys.path.append(r'P:\pipeline\python39_python_lib')
sys.path.append(r'P:\pipeline\ppas')
from dayu_widgets.line_edit import MLineEdit
from dayu_widgets.qt import *

from dayu_widgets import dayu_theme, MItemViewFullSet, MPushButton, MMenu
from dayu_widgets.label import MLabel
from dayu_widgets.progress_bar import MProgressBar
from dayu_widgets.qt import *
import os
import unreal
import os
import re
import json

fbxPath = r'U:\ywm\crowds\FBX'
texturePath = "/Game/FBX_mat"
ueFbxPath = "/Game/FBX_asset"
class LightRenderWidget(QDialog):
    def __init__(self, parent=None):
        super(LightRenderWidget, self).__init__(parent=parent)

        # Layout for Output Path
        output_path_lay = QHBoxLayout()
        output_path_lay.addWidget(MLabel('Output Path: ').strong().secondary())
        self.output_path = MLineEdit()
        self.output_path.setText(fbxPath)
        output_path_lay.addWidget(self.output_path)

        # Table Widget for Folders
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(5)  # 5 columns per row
        self.table_widget.horizontalHeader().setStretchLastSection(True)
        self.table_widget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.verticalHeader().setDefaultSectionSize(50)  # Adjust row height
        self.table_widget.setSelectionMode(QAbstractItemView.NoSelection)
        self.table_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_widget.setShowGrid(False)

        # Set header style
        self.table_widget.horizontalHeader().setStyleSheet(
            "QHeaderView::section { background-color: black; color: white; font-weight: bold; }"
        )
        self.table_widget.verticalHeader().setStyleSheet(
            "QHeaderView::section { background-color: black; color: white; font-weight: bold; }"
        )

        # Progress Bar
        self.progress = MProgressBar()
        self.progress.setValue(0)

        # Import FBX Button
        self.run_all_btn = MPushButton('importFBX')
        self.run_all_btn.clicked.connect(self.import_fbx)
        btn_lay = QHBoxLayout()
        btn_lay.addWidget(self.run_all_btn)

        # Main Layout
        main_lay = QVBoxLayout()
        main_lay.addLayout(output_path_lay)
        main_lay.addWidget(self.table_widget)
        main_lay.addWidget(self.progress)
        main_lay.addLayout(btn_lay)
        self.setLayout(main_lay)
        self.resize(1288, 800)

        # Load folders into the table widget
        self.load_folders()

    def load_folders(self):
        """Load all folders from the specified path into the table widget."""
        folder_list = [folder for folder in os.listdir(fbxPath) if os.path.isdir(os.path.join(fbxPath, folder))]
        rows = (len(folder_list) + 4) // 5  # Calculate number of rows
        self.table_widget.setRowCount(rows)

        font = QFont()
        font.setPointSize(18)  # Larger font size
        font.setFamily("黑体")  # Set font to 黑体

        for index, folder_name in enumerate(folder_list):
            row, col = divmod(index, 5)
            checkbox = QCheckBox(folder_name)
            checkbox.setFont(font)
            checkbox.setStyleSheet(
                "QCheckBox::indicator { width: 30px; height: 30px; } "
                "QCheckBox::indicator:unchecked { background-color: white; border: 1px solid black; } "
                "QCheckBox::indicator:checked { background-color: red; border: 1px solid black; } "
                "QCheckBox { margin: 0px; text-align: center; font-weight: bold; }"
            )
            self.table_widget.setCellWidget(row, col, checkbox)

    def import_fbx( self ):
        """Handle the import FBX button click."""
        selected_folders = []
        for row in range(self.table_widget.rowCount()):
            for col in range(self.table_widget.columnCount()):
                widget = self.table_widget.cellWidget(row, col)
                if widget and isinstance(widget, QCheckBox) and widget.isChecked():
                    selected_folders.append(os.path.join(fbxPath, widget.text()))

        for folder in selected_folders:
            folder_name = os.path.basename(folder)  # 获取文件夹名
            fbx_file = os.path.join(folder, f"{folder_name}.fbx")  # 动态拼接 .fbx 文件名
            json_file = os.path.join(folder, f"{folder_name}_material_connections.json")  # 动态拼接 .json 文件名

            if os.path.exists(fbx_file) and os.path.exists(json_file):
                print (fbx_file, ueFbxPath+'/'+folder_name)
                fbx_in_uePath = import_fbx(fbx_file, ueFbxPath+'/'+folder_name)
                json_file_path = json_file
                process_textures_from_json(fbx_in_uePath,json_file_path)
            else:
                if not os.path.exists(fbx_file):
                    print(f"Missing file: {fbx_file}")
                if not os.path.exists(json_file):
                    print(f"Missing file: {json_file}")

# ------------------------------------------
# 全局后缀与属性映射
# ------------------------------------------
ALL_SUFFIXES = ["_c", "_sp", "_nor", "_rou"]

SUFFIX_MAP = {
    "_c":   unreal.MaterialProperty.MP_BASE_COLOR,
    "_sp":  unreal.MaterialProperty.MP_SPECULAR,
    "_nor": unreal.MaterialProperty.MP_NORMAL,
    "_rou": unreal.MaterialProperty.MP_ROUGHNESS
}
mat_edit_lib = unreal.MaterialEditingLibrary

def log(msg):
    unreal.log(msg)

def log_warn(msg):
    unreal.log_warning(msg)
# ------------------------------------------
# 从磁盘路径解析： (core_name, udim_num, file_ext)
# 带UDIM示例: componenta_c.1001.png -> (componenta_c, 1001, .png)
# 无UDIM示例: componenta_c.png     -> (componenta_c, None, .png)
# ------------------------------------------
def parse_texture_path(disk_path):
    base_name = os.path.basename(disk_path)       # e.g. "componenta_c.1001.png"
    core, file_ext = os.path.splitext(base_name)  # "componenta_c.1001", ".png"
    match = re.match(r"(.*)\.(\d{4})$", core)
    if match:
        return match.group(1), match.group(2), file_ext
    else:
        return core, None, file_ext
def does_asset_exist(asset_path):
    return unreal.EditorAssetLibrary.does_asset_exist(asset_path)


def find_asset_data(asset_path):
    """
    在UE中，“资产路径”通常是 /Game/Folder/AssetName
    但实际注册表里存的是“对象路径”(Object Path)，形如 /Game/Folder/AssetName.AssetName
    如果这里传的不是完整对象路径也可能查不到。
    """
    return unreal.EditorAssetLibrary.find_asset_data(asset_path)
def create_folder_if_not_exists(folder_path):
    if not unreal.EditorAssetLibrary.does_directory_exist(folder_path):
        unreal.EditorAssetLibrary.make_directory(folder_path)
# 从核心名称找到后缀 (_c/_sp/_nor/_rou)
def find_suffix_from_core_name(core_name):
    name_lower = core_name.lower()
    for sfx in ALL_SUFFIXES:
        if sfx in name_lower:
            return sfx
    return None
def get_material_property_from_suffix(sfx):
    return SUFFIX_MAP.get(sfx, None)

# ------------------------------------------
# 构建UE导入资产名称：
# 若有UDIM则 componenta_c_1001，否则 componenta_c
# ------------------------------------------
def build_asset_name(core_name, udim_num=None):
    if udim_num:
        return f"{core_name}_{udim_num}"
    else:
        return core_name
# ------------------------------------------
# 根据磁盘路径推断UE文件夹
# 例: D:/Project/Textures/chr/componenta/... -> /Game/FBX_mat/chr/componenta
# ------------------------------------------
def derive_unreal_folder_from_disk_path(disk_path, base_path="/Game/FBX_mat"):
    path_parts = disk_path.replace("\\", "/").split("/")
    category = "chr" if "chr" in [p.lower() for p in path_parts] else "prp"

    cat_index = 0
    for i, part in enumerate(path_parts):
        if part.lower() == category:
            cat_index = i
            break

    if cat_index + 1 < len(path_parts):
        sub_name = path_parts[cat_index + 1]
    else:
        sub_name = "unknown"

    folder_path = f"{base_path}/{category}/{sub_name}"
    return folder_path
# ------------------------------------------
# 导入贴图：如果asset已存在则返回其对象路径，否则执行导入并返回新对象路径
# ------------------------------------------
def import_texture_single(disk_path, core_name, udim_num, dest_folder):
    """
    返回值为在引擎中的“对象路径”，如 /Game/FBX_mat/chr/componenta/componenta_c_1001.componenta_c_1001
    """
    asset_name = build_asset_name(core_name, udim_num)            # e.g. "componenta_c_1001"
    expected_asset_path = f"{dest_folder}/{asset_name}"           # e.g. "/Game/FBX_mat/chr/componenta/componenta_c_1001"

    # 1) 若资产已存在，则通过 find_asset_data 拿到完整“对象路径”
    # if does_asset_exist(expected_asset_path):
    #     existing_data = find_asset_data(expected_asset_path)
    #     if existing_data and existing_data.is_valid():
    #         obj_path = existing_data.get_path_name()  # 例如 "/Game/FBX_mat/chr/componenta/componenta_c_1001.componenta_c_1001"
    #         log(f"贴图已存在: {obj_path}")
    #         return obj_path
    #     else:
    #         log_warn(f"已存在资产路径 {expected_asset_path}，但对象无效")
    #         return None

    # 2) 资产不存在 -> 执行导入
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    import_task = unreal.AssetImportTask()
    import_task.filename = disk_path
    import_task.destination_path = dest_folder
    import_task.destination_name = asset_name
    import_task.automated = True
    import_task.save = True
    import_task.replace_existing = True

    asset_tools.import_asset_tasks([import_task])

    # 3) 导入后，import_task.imported_object_paths 里存的是完整对象路径
    if import_task.imported_object_paths:
        imported_object_path = import_task.imported_object_paths[0]
        imported_data = find_asset_data(imported_object_path)
        if imported_data and imported_data.is_valid():
            log(f"贴图导入成功: {imported_object_path}")
            return imported_object_path
        else:
            log_warn(f"导入失败(AssetData无效): {disk_path}")
            return None
    else:
        log_warn(f"导入失败(无ImportedPaths): {disk_path}")
        return None


# ------------------------------------------
# 导入指定贴图，并在同目录下搜索相同UDIM编号的其他后缀贴图(_sp/_nor/_rou)
# ------------------------------------------
def import_texture_and_variants_if_not_exists(disk_path):
    results = {}  # { 后缀: 对象路径 }
    if not os.path.exists(disk_path):
        log_warn(f"磁盘文件不存在: {disk_path}")
        return results

    core_name, udim_num, file_ext = parse_texture_path(disk_path)
    suffix = find_suffix_from_core_name(core_name)
    if not suffix:
        log_warn(f"无法识别后缀: {core_name} (file={disk_path})")
        return results

    dest_folder = derive_unreal_folder_from_disk_path(disk_path,texturePath)
    create_folder_if_not_exists(dest_folder)

    # 1) 先导入当前这张
    main_obj_path = import_texture_single(disk_path, core_name, udim_num, dest_folder)
    if main_obj_path:
        results[suffix] = main_obj_path

    # 2) 如果主图是_c，则自动搜索同UDIM的_sp/_nor/_rou
    if suffix == "_c" and main_obj_path:
        base_dir = os.path.dirname(disk_path)
        for alt_sfx in ALL_SUFFIXES:
            if alt_sfx == "_c":
                continue
            alt_core_name = core_name.replace("_c", alt_sfx)
            alt_file_name = alt_core_name
            if udim_num:
                alt_file_name += f".{udim_num}"
            alt_file_name += file_ext
            alt_disk_path = os.path.join(base_dir, alt_file_name)

            if not os.path.exists(alt_disk_path):
                continue

            alt_obj_path = import_texture_single(alt_disk_path, alt_core_name, udim_num, dest_folder)
            if alt_obj_path:
                results[alt_sfx] = alt_obj_path

    return results


# ------------------------------------------
# 将贴图连接到材质(根据后缀映射到 BaseColor/Specular/Normal/Roughness)
# 参数 texture_obj_path 为“完整对象路径”
# ------------------------------------------
def connect_texture_to_material(material, texture_obj_path):


    # 示例： texture_obj_path="/Game/FBX_mat/chr/componenta/componenta_c_1006.componenta_c_1006"
    # base_name="componenta_c_1006.componenta_c_1006"
    base_name = os.path.basename(texture_obj_path)

    # 找后缀
    suffix = None
    for sfx in ALL_SUFFIXES:
        if sfx in base_name.lower():
            suffix = sfx
            break

    mat_prop = get_material_property_from_suffix(suffix)
    if not mat_prop:
        return

    node = mat_edit_lib.create_material_expression(material, unreal.MaterialExpressionTextureSample, -300, 0)
    if not node:
        log_warn(f"无法创建 TextureSample 节点: {material.get_name()}")
        return

    # 查找贴图的AssetData
    asset_data = find_asset_data(texture_obj_path)
    if not asset_data or not asset_data.is_valid():
        log_warn(f"无法找到贴图资产: {texture_obj_path}")
        return

    tex_obj = asset_data.get_asset()
    if not tex_obj:
        log_warn(f"无法加载贴图对象: {texture_obj_path}")
        return

    # 设置贴图
    node.texture = tex_obj
    node.sampler_type = get_sampler_type(tex_obj, mat_prop)

    # 连接到对应的材质属性
    mat_edit_lib.connect_material_property(node, "RGB", mat_prop)

    # 为方便查看，在材质节点上标个desc
    node.set_editor_property("desc", base_name)


def get_sampler_type(texture_obj, mat_prop):
    if not texture_obj:
        return unreal.MaterialSamplerType.SAMPLERTYPE_COLOR

    is_virtual = texture_obj.get_editor_property("virtual_texture_streaming")
    is_normal_map = (texture_obj.compression_settings == unreal.TextureCompressionSettings.TC_NORMALMAP)

    if is_normal_map:
        return (unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_NORMAL
                if is_virtual else unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    else:
        return (unreal.MaterialSamplerType.SAMPLERTYPE_VIRTUAL_COLOR
                if is_virtual else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)


def recompile_and_save_material(material):

    mat_edit_lib.recompile_material(material)
    unreal.EditorAssetLibrary.save_asset(material.get_path_name())

def set_color_and_transparency(material, color, transparency):
    """
    设置材质球的颜色和透明度属性
    """
    x_offset = -300
    y_offset = 100

    # 创建颜色节点
    vector_param = create_node(material, unreal.MaterialExpressionVectorParameter, (x_offset, y_offset))
    vector_param.set_editor_property("parameter_name", "BaseColor")
    vector_param.set_editor_property("default_value", unreal.LinearColor(*color, 1.0))

    # 创建透明度节点
    alpha = 1.0 - transparency  # Unreal 中透明度映射
    scalar_param = create_node(material, unreal.MaterialExpressionScalarParameter, (x_offset + 200, y_offset))
    scalar_param.set_editor_property("parameter_name", "Opacity")
    scalar_param.set_editor_property("default_value", alpha)

    # 连接 BaseColor 和 Opacity 到材质属性
    mat_edit_lib.connect_material_property(vector_param, "", unreal.MaterialProperty.MP_BASE_COLOR)
    mat_edit_lib.connect_material_property(scalar_param, "", unreal.MaterialProperty.MP_OPACITY)

    material.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
# 创建节点函数
def create_node( material, node_class, location ):
    node = mat_edit_lib.create_material_expression(material, node_class)
    if node:
        node.material_expression_editor_x = location[0]
        node.material_expression_editor_y = location[1]
    return node
# ------------------------------------------
# 从 JSON 获取贴图路径，对选中的 SkeletalMesh 做贴图导入 & 材质连接
# ------------------------------------------
def process_textures_from_json(fbx_in_uePath,json_path):
    """
    JSON 结构示例：
    {
      "componenta": {
        "textures": [
          "D:/Project/Textures/chr/componenta/componenta_c.1001.png",
          "D:/Project/Textures/chr/componenta/componenta_c.1002.png"
        ]
      }
    }
    """
    if not os.path.exists(json_path):
        log_warn(f"JSON 文件不存在: {json_path}")
        return

    with open(json_path, 'r') as f:
        json_data = json.load(f)

    selected_assets = select_asset_in_content_browser_and_get(fbx_in_uePath)
    if not selected_assets:
        log_warn("未选择任何资产，脚本结束。")
        return

    for asset in selected_assets:
        if not isinstance(asset, unreal.SkeletalMesh):
            continue

        mesh_name = asset.get_name()
        log(f"[处理 SkeletalMesh]: {mesh_name}")

        # 遍历 SkeletalMesh 的材质槽
        for slot_index, slot_info in enumerate(asset.materials):
            mat_interface = slot_info.material_interface
            if not mat_interface or not isinstance(mat_interface, unreal.Material):
                continue

            ue_mat_name = mat_interface.get_name()
            log(f" -> 材质槽 {slot_index}: {ue_mat_name}")

            # 试图在 JSON 中找到 key
            matched_key = None
            for k in json_data.keys():
                print ('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~',k,ue_mat_name)
                if k.split(':')[1] == ue_mat_name:
                    matched_key = k
                    break

            if matched_key:
                tex_list = json_data[matched_key].get("textures", [])
                print ('++++++++++++++++++++++++',tex_list)
                if not tex_list:
                    log_warn(f"{matched_key} 未配置任何 textures.")
                    attributes = json_data[matched_key].get("attributes", {})
                    color = attributes.get("color", [1.0, 1.0, 1.0])  # 默认白色
                    transparency = attributes.get("transparency", 0.0)  # 默认不透明
                    set_color_and_transparency(mat_interface, color[0], transparency[0][0])
                    recompile_and_save_material(mat_interface)
                    continue

                # 依次导入
                for disk_path in tex_list:
                    disk_path = disk_path.replace("\\", "/")
                    # 导入 & 自动导 variants
                    imported_dict = import_texture_and_variants_if_not_exists(disk_path)
                    # 连接到材质
                    for sfx, obj_path in imported_dict.items():
                        connect_texture_to_material(mat_interface, obj_path)
                colorInfo_sg = json_data[matched_key].get("color_correct", None).get('_sg',None)
                colorInfo_hs = json_data[matched_key].get("color_correct", None).get('_hs',None)
                print ('=====================',colorInfo_sg,colorInfo_hs)
                if not colorInfo_sg and not colorInfo_hs:
                    log_warn(f"{matched_key} 未配置任何 textures.")
                    continue
                else:
                    # 节点位置偏移
                    x_offset = -600
                    y_offset = 544
                    #找到color节点
                    input_node = unreal.MaterialEditingLibrary.get_material_property_input_node(mat_interface, unreal.MaterialProperty.MP_BASE_COLOR)
                    input_node_link_attr = unreal.MaterialEditingLibrary.get_material_property_input_node_output_name(
                        mat_interface, unreal.MaterialProperty.MP_BASE_COLOR)
                    # 创建 Vector Parameter 节点
                    vector_param = create_node(mat_interface, unreal.MaterialExpressionVectorParameter, (x_offset, y_offset))
                    vector_param.set_editor_property("parameter_name", "颜色")
                    vector_param.set_editor_property("default_value", unreal.LinearColor(colorInfo_hs/360.0, colorInfo_sg, 1.0, 0.0))


                    # 创建 Clamp 节点 1
                    clamp_1 = create_node(mat_interface, unreal.MaterialExpressionClamp, (x_offset + 288, y_offset))

                    # 创建 HueShift MaterialFunctionCall 节点
                    hue_shift = create_node(mat_interface, unreal.MaterialExpressionMaterialFunctionCall,
                                            (x_offset + 528, y_offset))
                    hue_shift.set_editor_property("material_function", unreal.load_asset(
                        "/Engine/Functions/Engine_MaterialFunctions02/HueShift.HueShift"))

                    # 创建 Desaturation 节点
                    desaturation = create_node(mat_interface, unreal.MaterialExpressionDesaturation,
                                               (x_offset + 768, y_offset))

                    # 创建 Multiply 节点
                    multiply = create_node(mat_interface, unreal.MaterialExpressionMultiply, (x_offset + 960, y_offset))

                    # 创建 Clamp 节点 2
                    clamp_2 = create_node(mat_interface, unreal.MaterialExpressionClamp, (x_offset + 960, y_offset + 144))

                    # 创建 OneMinus 节点
                    one_minus = create_node(mat_interface, unreal.MaterialExpressionOneMinus,
                                            (x_offset + 384, y_offset + 192))

                    # 设置 OneMinus 输入
                    mat_edit_lib.connect_material_expressions(vector_param, "G", one_minus, "Input")

                    # 连接节点
                    mat_edit_lib.connect_material_expressions(vector_param, "R", clamp_1, "")
                    mat_edit_lib.connect_material_expressions(clamp_1, "", hue_shift, "Hue Shift Percentage")
                    mat_edit_lib.connect_material_expressions(hue_shift, "Result", desaturation, "")
                    mat_edit_lib.connect_material_expressions(one_minus, "", desaturation, "Fraction")
                    mat_edit_lib.connect_material_expressions(desaturation, "", multiply, "A")
                    mat_edit_lib.connect_material_expressions(vector_param, "B", clamp_2, "")
                    mat_edit_lib.connect_material_expressions(vector_param, "B", clamp_2, "Max")
                    mat_edit_lib.connect_material_expressions(vector_param, "G", one_minus, "")
                    mat_edit_lib.connect_material_expressions(clamp_2, "", multiply, "B")
                    mat_edit_lib.connect_material_expressions(input_node, input_node_link_attr, hue_shift, "Texture")
                    mat_edit_lib.connect_material_property(multiply, "",unreal.MaterialProperty.MP_BASE_COLOR)
                    mat_interface.set_editor_property("two_sided", True)
                recompile_and_save_material(mat_interface)

            else:
                log_warn(f"材质 {ue_mat_name} 未在 JSON 中找到匹配，跳过")


def import_fbx( fbx_file_path, destination_path ):
    """
    导入指定路径的 FBX 文件到 Unreal Engine，并按照指定的导入选项配置。
    导入后返回 FBX 在 Unreal Engine 中的绝对路径。

    :param fbx_file_path: FBX 文件的完整路径（例如 "D:/models/character.fbx"）
    :param destination_path: 导入到 Unreal 的 Content Browser 中的目标路径（例如 "/Game/Characters"）
    :return: 导入的资产在 Unreal Engine 中的绝对路径（例如 "/Game/Characters/character"）
    """
    # 创建导入任务
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', fbx_file_path)
    task.set_editor_property('destination_path', destination_path)
    task.set_editor_property('automated', True)
    task.set_editor_property('replace_existing', True)
    task.set_editor_property('save', True)

    # 配置导入选项
    options = unreal.FbxImportUI()
    options.set_editor_property('import_mesh', True)
    options.set_editor_property('import_as_skeletal', True)
    options.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH)

    # 配置 Skeletal Mesh 的导入数据
    skeletal_mesh_import_data = options.get_editor_property('skeletal_mesh_import_data')
    skeletal_mesh_import_data.set_editor_property('normal_import_method',
                                                  unreal.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS)
    skeletal_mesh_import_data.set_editor_property('normal_generation_method',
                                                  unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    skeletal_mesh_import_data.set_editor_property('vertex_color_import_option', unreal.VertexColorImportOption.REPLACE)

    # 动画选项
    options.set_editor_property('import_animations', True)  # 启用动画导入
    anim_import_data = options.get_editor_property('anim_sequence_import_data')  # 获取动画导入数据
    anim_import_data.set_editor_property('import_bone_tracks', True)  # 导入骨骼动画

    # 分配导入选项到任务
    task.set_editor_property('options', options)

    # 执行导入任务
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    # 检查导入结果并返回路径
    if task.imported_object_paths:
        imported_object_path = task.imported_object_paths[0]  # 获取第一个导入的资产路径
        unreal.log(f"成功导入文件：{imported_object_path}")
        return imported_object_path
    else:
        unreal.log_error(f"导入失败：{fbx_file_path}")
        return None


def select_asset_in_content_browser_and_get( asset_path ):
    """
    根据给定的资产路径，在内容浏览器中选中该资产，并返回选中的资产。

    :param asset_path: 资产在 Unreal 中的路径（例如 "/Game/Characters/character"）
    :return: 选中的资产对象列表
    """
    try:
        # 检查资产是否存在
        if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
            # 在内容浏览器中选中资产
            unreal.EditorAssetLibrary.sync_browser_to_objects([asset_path])
            unreal.log(f"成功在内容浏览器中选中资产：{asset_path}")

            # 获取资产对象
            asset = unreal.EditorAssetLibrary.load_asset(asset_path)
            if asset:
                # 再次同步并返回选中对象
                unreal.EditorAssetLibrary.sync_browser_to_objects([asset_path])
                selected_assets = [asset]
                unreal.log(f"当前选中的资产：{selected_assets}")
                return selected_assets
            else:
                unreal.log_error(f"无法加载资产：{asset_path}")
                return None
        else:
            unreal.log_error(f"未找到指定资产：{asset_path}")
            return None
    except Exception as e:
        unreal.log_error(f"选择资产时发生错误：{str(e)}")
        return None



def show_in_ue():

    import unreal

    if QApplication.instance():
        for win in QApplication.allWindows():
            if 'toolWindow' in win.objectName():
                win.destroy()
    else:
        QApplication(sys.argv)

    global window
    window = LightRenderWidget()
    dayu_theme.apply(window)
    window.setWindowFlags(Qt.WindowStaysOnTopHint)
    window.show()
    window.setObjectName('toolWindow')
    window.setWindowTitle('Sample Tool')
    unreal.parent_external_window_to_slate(window.winId())

if __name__ == '__main__':
    show_in_ue()
