"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: addDirve.py
@date: 2024/9/9 16:19
@desc:
"""
import bpy
def add_driver_to_selected_node( input_index, driver_object_name, driver_property, expression ):
    """
    为选中材质的选中节点的某个输入添加驱动

    :param input_index: 节点的输入索引，指定哪个输入将被驱动
    :param driver_object_name: 驱动对象的名称（例如 "Group"）
    :param driver_property: 驱动属性的数据路径（例如 "prop"）
    :param expression: 表达式，用来驱动节点输入（例如 "var * 0.1"）
    """

    # 获取当前选中对象
    obj = bpy.context.active_object
    if obj is None:
        raise Exception("没有选中的对象")

    # 确保对象有材质
    if not obj.active_material:
        raise Exception("选中的对象没有活跃材质")

    material = obj.active_material

    # 确保材质使用节点
    if not material.use_nodes:
        raise Exception(f"材质 {material.name} 没有使用节点系统")

    # 获取选中的节点
    node = material.node_tree.nodes.active
    if node is None:
        raise Exception("没有选中的节点")

    # 获取目标输入
    try:
        target_input = node.inputs[input_index]
    except IndexError:
        raise Exception(f"输入索引 {input_index} 不存在于节点 {node.name}")

    # 移除现有驱动（如果存在）
    if target_input.default_value != None and target_input.driver_remove('default_value'):
        target_input.driver_remove('default_value')

    # 添加驱动到输入的 default_value 属性
    driver = target_input.driver_add("default_value").driver

    # 创建驱动变量
    var = driver.variables.new()
    var.name = "var"
    var.targets[0].id = bpy.data.objects.get(driver_object_name)
    if var.targets[0].id is None:
        raise Exception(f"找不到驱动对象 {driver_object_name}")
    var.targets[0].data_path = '["%s"]'% driver_property

    # 设置驱动的表达式
    driver.expression = expression

    print(f"成功为材质 {material.name} 的节点 {node.name} 的输入 {input_index} 添加驱动")


# 示例调用：
# 选中物体，选中节点后调用该函数
add_driver_to_selected_node(1, "Group", "prop", "var * 0.1")
