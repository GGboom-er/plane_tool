import sys
from typing import Tuple, List, Dict, Optional, Any

import maya.cmds as cmds
from dna import DataLayer_All, FileStream, Status, BinaryStreamReader

# --- Dynamic dnacalib import ---
try:
    from dnacalib2 import DNACalibDNAReader
    print("DEBUG: Successfully imported DNACalibDNAReader from dnacalib2.")
except ImportError:
    try:
        from dnacalib import DNACalibDNAReader
        print("DEBUG: Successfully imported DNACalibDNAReader from dnacalib.")
    except ImportError:
        DNACalibDNAReader = None
# --- End dynamic dnacalib import ---

# --- Functions ---

def load_dna_for_editing_and_calib(dna_file_path: str) -> Tuple[Optional[BinaryStreamReader], Optional[Any], Optional[str]]:
    """
    Loads a DNA file and returns the original BinaryStreamReader, a DNACalibDNAReader, and an error message if any.

    Args:
        dna_file_path (str): The absolute path to the DNA file.

    Returns:
        Tuple[Optional[BinaryStreamReader], Optional[DNACalibDNAReader], Optional[str]]:
        A tuple containing (BinaryStreamReader, DNACalibDNAReader, None) on success,
        or (None, None, error_message) on failure.
    """
    if DNACalibDNAReader is None:
        error_msg = "无法导入 DNACalibDNAReader。请确保 dnacalib 或 dnacalib2 库已正确安装并配置。"
        return None, None, error_msg

    try:
        stream = FileStream(dna_file_path, FileStream.AccessMode_Read, FileStream.OpenMode_Binary)
        reader = BinaryStreamReader(stream, DataLayer_All)
        reader.read()

        if not Status.isOk():
            status = Status.get()
            return None, None, f"Error loading DNA file: {status.message}"

        calibrated_reader = DNACalibDNAReader(reader)
        return reader, calibrated_reader, None
    except Exception as e:
        return None, None, f"Failed to load DNA file {dna_file_path}: {e}"

def list_blend_shape_names(dna_binary_reader: Optional[BinaryStreamReader]) -> List[str]:
    """
    Lists all BlendShape names from a DNA BinaryStreamReader.

    Args:
        dna_binary_reader (Optional[BinaryStreamReader]): The loaded DNA BinaryStreamReader object.

    Returns:
        List[str]: A list of all BlendShape names.
    """
    if not dna_binary_reader:
        return []

    blend_shape_names = []
    for i in range(dna_binary_reader.getBlendShapeChannelCount()):
        blend_shape_names.append(dna_binary_reader.getBlendShapeChannelName(i))

    return blend_shape_names

def get_expression_info_from_controller() -> Tuple[Dict[str, List[Dict[str, str]]], Optional[str]]:
    """
    Gets information about expressions (BlendShapes) driven by the currently selected controllers.

    Returns:
        Tuple[Dict[str, List[Dict[str, str]]], Optional[str]]:
        A tuple containing (controller_expression_info, None) on success,
        or ({}, error_message) on failure or if no controllers are selected.
    """
    selected_controllers = cmds.ls(selection=True, type='transform')

    if not selected_controllers:
        return {}, "Please select one or more controllers."

    controller_expression_info = {}
    for controller in selected_controllers:
        driven_blend_shapes = []
        output_connections = cmds.listConnections(controller, source=False, destination=True, plugs=True, connections=True)

        if output_connections:
            for i in range(0, len(output_connections), 2):
                dest_plug = output_connections[i+1]
                node_name, _, attr_name = dest_plug.partition('.')
                if 'weight' in attr_name and cmds.nodeType(node_name) == 'blendShape':
                    driven_blend_shapes.append({
                        'blendShapeNode': node_name,
                        'blendShapeTargetAttr': attr_name
                    })
        controller_expression_info[controller] = driven_blend_shapes

    return controller_expression_info, None

# --- Test Code (executed when the script is run directly) ---
if __name__ == "__main__":
    # IMPORTANT: Replace with your actual DNA file path
    dna_file_path = "U:/ywm/MHC/Downloaded/DHI/5jd1XPwC_asset/2k/asset_source/MetaHumans/yy/SourceAssets/yy.dna"

    # Test DNA loading and BlendShape listing
    print("\n--- Testing DNA Loading and BlendShape Listing ---")
    original_reader, calibrated_reader = load_dna_for_editing_and_calib(dna_file_path)

    if original_reader and calibrated_reader:
        print("DNA文件加载成功！")
        blend_shape_names = list_blend_shape_names(original_reader)

        if blend_shape_names:
            print("\nDNA文件中的BlendShape名称:")
            for name in blend_shape_names:
                print(name)
        else:
            print("\nDNA文件中没有找到BlendShape。")
    else:
        print("DNA文件加载失败。请检查文件路径和错误信息。")

    # Test getting expression info from controller
    print("\n--- Testing Controller Expression Info ---")
    print("请在Maya中选择一个或多个控制器，然后再次运行此脚本。")
    expression_info = get_expression_info_from_controller()

    if expression_info:
        for controller, bs_info_list in expression_info.items():
            print(f"\n控制器: {controller}")
            if bs_info_list:
                print("驱动的BlendShape:")
                for bs_info in bs_info_list:
                    print(f"  节点: {bs_info['blendShapeNode']}, 目标属性: {bs_info['blendShapeTargetAttr']}")
            else:
                print("  没有驱动任何BlendShape。")
    else:
        print("没有选择控制器，或选择的控制器没有驱动任何BlendShape。")