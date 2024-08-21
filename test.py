from __future__ import print_function
import maya.cmds as cmds
import random


def is_file_referenced():
    # ��ȡ�������õ��ļ�
    references = cmds.file(query=True, reference=True)
    current_file = cmds.file(query=True, location=True)

    # ��鵱ǰ�ļ��Ƿ��������б���
    if current_file in references:
        return True
    return False


def get_current_namespace():
    # ��ȡ���������ļ�
    references = cmds.file(query=True, reference=True)
    if not references:
        return None

    # �������һ�����õ��ļ���Ŀ���ļ�
    last_reference = references[-1]

    # ��ȡ���õ������ռ�
    namespace = cmds.file(last_reference, query=True, namespace=True)

    che_switch_attr = "{}:VisibilityCtr.che_switch".format(namespace)
    cloth_switch_attr = "{}:VisibilityCtr.cloth_switch".format(namespace)

    # ��������Ƿ����
    if cmds.objExists(che_switch_attr) and cmds.objExists(cloth_switch_attr):
        # ���ѡ��0, 1, 2, 3�е�һ��ֵ
        random_value = random.choice([0, 1, 2, 3])

        # ��������ֵ
        cmds.setAttr(che_switch_attr, random_value)
        cmds.setAttr(cloth_switch_attr, random_value)

    print("File has been referenced. Namespace: {}".format(namespace))


# �����ǰ�ļ��Ǳ����õģ���ִ�л�ȡ�����ռ�Ĳ���
if is_file_referenced():
    get_current_namespace()
