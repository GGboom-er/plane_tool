from __future__ import print_function
import maya.cmds as cmds
import random


def is_file_referenced():
    # 获取所有引用的文件
    references = cmds.file(query=True, reference=True)
    current_file = cmds.file(query=True, location=True)

    # 检查当前文件是否在引用列表中
    if current_file in references:
        return True
    return False


def get_current_namespace():
    # 获取所有引用文件
    references = cmds.file(query=True, reference=True)
    if not references:
        return None

    # 假设最后一个引用的文件是目标文件
    last_reference = references[-1]

    # 获取引用的命名空间
    namespace = cmds.file(last_reference, query=True, namespace=True)

    che_switch_attr = "{}:VisibilityCtr.che_switch".format(namespace)
    cloth_switch_attr = "{}:VisibilityCtr.cloth_switch".format(namespace)

    # 检查属性是否存在
    if cmds.objExists(che_switch_attr) and cmds.objExists(cloth_switch_attr):
        # 随机选择0, 1, 2, 3中的一个值
        random_value = random.choice([0, 1, 2, 3])

        # 设置属性值
        cmds.setAttr(che_switch_attr, random_value)
        cmds.setAttr(cloth_switch_attr, random_value)

    print("File has been referenced. Namespace: {}".format(namespace))


# 如果当前文件是被引用的，才执行获取命名空间的操作
if is_file_referenced():
    get_current_namespace()
