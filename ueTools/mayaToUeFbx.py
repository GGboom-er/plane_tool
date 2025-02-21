# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import maya.cmds as cmds
import maya.OpenMaya as om
import json
import os
import sys
if sys.version_info[0] == 2:
    import codecs

    open_file = codecs.open
else:
    open_file = open


def get_material_connections():
    """
    查询选中模型的 SG 节点数量，列出所有材质球，每个材质球是否有 colorCorrect 节点连接，并记录其贴图路径。
    如果材质球没有贴图连接，则记录其 color 和 transparency 属性。
    支持从 SG 节点通过 blendColors 等节点递归查找 lambert 材质球。
    """
    selection = [cmds.listRelatives(i, ni=True, s=True)[0] for i in cmds.ls(selection=True, type='transform') if
                 cmds.nodeType(i) != 'joint']
    if not selection:
        om.MGlobal.displayError("请选择模型！")
        return {}

    material_info = {}
    all_sg_nodes = set()
    all_materials = set()

    def find_material_from_sg( sg_node ):
        """递归查找 SG 节点连接的材质球"""
        connections = cmds.listConnections(sg_node, source=True, destination=False) or []
        for node in connections:
            if cmds.nodeType(node) in ["lambert", "blinn", "phong"]:
                return node
            elif cmds.nodeType(node) in ["blendColors", "layeredTexture", "ramp"]:
                return find_material_from_sg(node)
        return None

    def get_material_from_history( node ):
        """从历史节点中查找材质球类型"""
        history_nodes = cmds.listHistory(node) or []
        for hist_node in history_nodes:
            if cmds.nodeType(hist_node) in ["lambert", "blinn", "phong"]:
                return hist_node
        return None

    for shape in selection:
        # 获取 SG 节点
        shading_groups = cmds.listConnections(shape, type='shadingEngine') or []
        try:
            shading_groups.remove('initialShadingGroup')
        except:
            pass
        all_sg_nodes.update(shading_groups)

    for sg in all_sg_nodes:
        # 获取材质球
        material = cmds.listConnections(sg + '.surfaceShader', c=0, d=0)[0]

        if not material:
            material = get_material_from_history(sg)
        if material:
            all_materials.add(material)

    for material in all_materials:
        # 记录材质基本信息
        material_entry = material_info.setdefault(material, {
            "color_correct": {
                "exists": False,
                "_hs"   : None,
                "_sg"   : None
            },
            "textures"     : [],
            "attributes"   : {
                "color"       : None,
                "transparency": None
            }
        })

        # 检查材质球之前的节点
        previous_nodes = cmds.listHistory(material) or []

        # 查找 file 节点并记录贴图路径
        recorded_textures = set()  # 用于记录已处理的贴图路径，避免重复记录
        for node in previous_nodes:
            if cmds.nodeType(node) == 'file':
                file_path = cmds.getAttr("{0}.fileTextureName".format(node))
                if file_path and file_path not in recorded_textures:
                    material_entry["textures"].append(file_path)
                    recorded_textures.add(file_path)

            # 查找 colorCorrect 节点并记录 _hs 和 _sg 属性
            if cmds.nodeType(node) == 'colorCorrect':
                material_entry["color_correct"]["exists"] = True
                if cmds.attributeQuery('_hs', node=node, exists=True):
                    material_entry["color_correct"]["_hs"] = cmds.getAttr("{0}._hs".format(node))
                if cmds.attributeQuery('_sg', node=node, exists=True):
                    material_entry["color_correct"]["_sg"] = cmds.getAttr("{0}._sg".format(node))

        # 如果材质球没有贴图连接，获取 color 和 transparency 属性
        if not material_entry["textures"]:
            if cmds.attributeQuery("color", node=material, exists=True):
                material_entry["attributes"]["color"] = cmds.getAttr("{0}.color".format(material))
            if cmds.attributeQuery("transparency", node=material, exists=True):
                material_entry["attributes"]["transparency"] = cmds.getAttr("{0}.transparency".format(material))

    return material_info


def write_to_json( data, filepath ):
    """
    将数据写入 JSON 文件。
    """
    with open_file(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    om.MGlobal.displayInfo(u"材质信息已保存到: %s" % filepath)


def export_selected_to_fbx_python( filepath ):
    """
    导出选中的物体为 FBX 文件。
    """
    selected_objs = cmds.ls(selection=True)
    if not selected_objs:
        om.MGlobal.displayError(u"请先选择要导出的模型！")
        return

    try:
        cmds.loadPlugin("fbxmaya", quiet=True)
    except Exception:
        om.MGlobal.displayWarning(u"无法加载FBX插件，请检查是否安装了FBX插件。")
        return

    start_frame = int(cmds.playbackOptions(q=True, minTime=True))
    end_frame = int(cmds.playbackOptions(q=True, maxTime=True))

    cmds.FBXExportSmoothingGroups("-v", True)
    cmds.FBXExportTangents("-v", False)
    cmds.FBXExportSmoothMesh("-v", True)
    cmds.FBXExportTriangulate("-v", False)
    cmds.FBXExportReferencedAssetsContent("-v", True)

    cmds.FBXExportBakeComplexAnimation("-v", True)
    cmds.FBXExportBakeComplexStart("-v", start_frame)
    cmds.FBXExportBakeComplexEnd("-v", end_frame)
    cmds.FBXExportBakeComplexStep("-v", 1)

    cmds.FBXExportUseSceneName("-v", False)
    cmds.FBXExportSkins("-v", True)
    cmds.FBXExportShapes("-v", True)
    cmds.FBXExportConstraints("-v", False)
    cmds.FBXExportSkeletonDefinitions("-v", True)
    cmds.FBXExportInputConnections("-v", False)
    cmds.FBXExportIncludeChildren("-v", True)
    cmds.FBXExportEmbeddedTextures("-v", False)
    cmds.FBXExportCameras("-v", False)
    cmds.FBXExportLights("-v", False)
    cmds.FBXExportAudio("-v", False)

    cmds.FBXExportConvertUnitString("cm")
    cmds.FBXExportInAscii("-v", False)

    try:
        cmds.FBXExport("-f", filepath, "-s")
        om.MGlobal.displayInfo(u"FBX 导出成功: %s" % filepath)
    except Exception:
        om.MGlobal.displayError(u"FBX 导出失败，请检查导出设置或路径。")


def main( output_dir ):
    """
    执行核心逻辑：
    1. 获取材质信息并输出到指定路径的 JSON 文件；
    2. 将选中物体导出为 FBX 到指定路径。
    """
    current_scene = cmds.file(q=True, sceneName=True)
    if not current_scene:
        om.MGlobal.displayError(u"请先保存当前Maya文件！")
        return

    scene_name = os.path.splitext(os.path.basename(current_scene))[0]
    scene_folder = os.path.join(output_dir, scene_name)

    # 创建导出文件夹
    if not os.path.exists(scene_folder):
        os.makedirs(scene_folder)

    # JSON 文件路径
    json_filepath = os.path.join(scene_folder, "%s_material_connections.json" % scene_name)
    material_data = get_material_connections()
    if material_data:
        write_to_json(material_data, json_filepath)

    # FBX 文件路径
    fbx_filepath = os.path.join(scene_folder, "%s.FBX" % scene_name)
    export_selected_to_fbx_python(fbx_filepath)

    # 显示提示弹窗
    cmds.confirmDialog(
        title=u"导出完成",
        message=u"文件已成功导出到:\n%s" % scene_folder,
        button=[u"确定"],
        defaultButton=u"确定",
    )


def create_ui():
    """
    创建一个简单的 UI，用于执行 main()。
    """
    window_name = "materialExportUI"
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    output_dir = r"U:\ywm\crowds\FBX"

    cmds.window(window_name, title=u"导出材质与FBX", widthHeight=(500, 200), sizeable=False)
    cmds.columnLayout(adjustableColumn=True)

    cmds.text(label=u"默认导出路径为：", align="left")
    cmds.textField("exportPathField", text=output_dir, editable=False, width=480)

    def on_export_button( *args ):
        main(output_dir)

    cmds.separator(height=10, style="none")
    cmds.button(label=u"开始导出", height=40, command=on_export_button)
    cmds.separator(height=10, style="none")
    cmds.setParent("..")
    cmds.showWindow(window_name)


# 直接运行 UI
create_ui()