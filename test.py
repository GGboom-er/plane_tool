from dna import DataLayer_All, FileStream, Status, BinaryStreamReader, BinaryStreamWriter
import maya.cmds as cmds
import pymel.core as pm
import json
from dna_viewer import DNA, RigConfig, build_rig, build_meshes
from dnacalib import (
    CommandSequence,
    DNACalibDNAReader,
    SetNeutralJointRotationsCommand,
    SetNeutralJointTranslationsCommand,
    SetVertexPositionsCommand,
    VectorOperation_Add,
)
def load_dna_reader(path):
    stream = FileStream(path, FileStream.AccessMode_Read, FileStream.OpenMode_Binary)
    reader = BinaryStreamReader(stream, DataLayer_All)
    reader.read()
    if not Status.isOk():
        status = Status.get()
        raise RuntimeError(f"Error loading DNA: {status.message}")
    return reader
CHARACTER_DNA = r'Y:\GGbommer\scripts\MetaHumanDNACalibration\output\Ada_with_lods_1_and_3.dna'

reader = load_dna_reader(CHARACTER_DNA)
calibrated = DNACalibDNAReader(reader)

def get_controller_index(dna_reader, controller_name):
    print(f"Searching for controller: {controller_name}")
    gui_control_count = dna_reader.getGUIControlCount()
    print(f"Total number of GUI controls: {gui_control_count}")
    for i in range(gui_control_count):
        if dna_reader.getGUIControlName(i) == controller_name:
            print(f"Controller {controller_name} found at index: {i}")
            return i
    print(f"Controller {controller_name} not found.")
    return None

get_controller_index(calibrated, 'CTRL_R_brow_down.ty')

def get_behavior_curve_for_controller(dna_reader, controller_index):
    behavior_count = dna_reader.getRawControlCount()
    for i in range(behavior_count):
        input_indices = dna_reader.getJointGroupInputIndices(i)
        output_indices = dna_reader.getJointGroupOutputIndices(i)
        if controller_index in input_indices:
            return output_indices
    return []

get_behavior_curve_for_controller(calibrated, 1)










jointGroupIndex = calibrated.getJointVariableAttributeIndices(0)

calibrated.getGUIToRawInputIndices()

calibrated.getGUIToRawOutputIndices()

#获取所有控制器名称
ctrlNameList = [calibrated.getGUIControlName(i) for i in range(calibrated.getGUIControlCount())]


# 获取dna节点表达式组
calibrated.getRawControlCount()

# 获取所有骨骼组_整个关节矩阵中存在的关节组的数量
calibrated.getJointGroupCount()
# 获取骨骼组中的骨骼
calibrated.getJointGroupJointIndices(77)

# 获取骨骼名称
calibrated.getJointName(43)
# 获取骨骼buildPose
calibrated.getNeutralJointTranslation(43)

# 可获取每个骨骼组运用到那些表情
calibrated.getJointGroupInputIndices(77)

# 获取每个骨骼组内骨骼参与运用的属性
calibrated.getJointGroupOutputIndices(77)

# 获取骨骼组下每个骨骼属性在对应表情下的驱动值
valueList = calibrated.getJointGroupValues(77)

tr = [valueList[387], valueList[388], valueList[389], valueList[390], valueList[391], valueList[392]]

calibrated.getGUIToRawInputIndices()

calibrated.getGUIToRawOutputIndices()

calibrated.getNeutralJointTranslation(43)

calibrated.getPSDCount()

for jointGroupIndex in range(calibrated.getJointGroupCount()):
    jointIndices = calibrated.getJointGroupJointIndices(jointGroupIndex)
    for jointIndex in jointIndices:
        jointName = calibrated.getJointName(jointIndex)
        print(jointName)



from dna import DataLayer_All, FileStream, Status, BinaryStreamReader, BinaryStreamWriter
import maya.cmds as cmds
import pymel.core as pm
import json
from dna_viewer import DNA, RigConfig, build_rig, build_meshes
from dnacalib import (
    CommandSequence,
    DNACalibDNAReader,
    SetNeutralJointRotationsCommand,
    SetNeutralJointTranslationsCommand,
    SetVertexPositionsCommand,
    VectorOperation_Add,
)
# initial
def load_dna_reader(path):
    stream = FileStream(path, FileStream.AccessMode_Read, FileStream.OpenMode_Binary)
    reader = BinaryStreamReader(stream, DataLayer_All)
    reader.read()
    if not Status.isOk():
        status = Status.get()
        raise RuntimeError(f"Error loading DNA: {status.message}")
    return reader
CHARACTER_DNA = r'Y:\GGbommer\scripts\MetaHumanDNACalibration\output\Ada_with_lods_1_and_3.dna'

reader = DNACalibDNAReader(load_dna_reader(CHARACTER_DNA))
ctrlNameList = [(reader.getGUIControlName(i)) for i in range(reader.getGUIControlCount())]
reader.getGUIControlCount()

reader.getRawControlCount()

len(reader.getGUIToRawInputIndices())

len(reader.getGUIToRawOutputIndices())

ctrlToExpList = list()
len(ctrlToExpList)
for ctrl,exp,min,max,k,v in zip(reader.getGUIToRawInputIndices(),reader.getGUIToRawOutputIndices(),reader.getGUIToRawFromValues(),reader.getGUIToRawToValues(),reader.getGUIToRawSlopeValues(),reader.getGUIToRawCutValues()):
    ctrlToExpList.append(((ctrl,reader.getGUIControlName(ctrl)),(exp,reader.getRawControlName(exp)),min,max,k,v))

ctrlToExpDict = dict()
for i in ctrlToExpList:
    if i[0] not in ctrlToExpDict:
        ctrlToExpDict[i[0]] = [{i[1]:i[2:]}]
    else:
        ctrlToExpDict[i[0]].append({i[1]:i[2:]})
for k,v in ctrlToExpDict.items():
    print (k,v)


ctrlToExpDict['CTRL_R_mouth_suckBlow.ty']
for i in range(257):
    if reader.getRawControlName(i) == 'CTRL_expressions.mouthCheekBlowR':
        print (i)
len(ctrlNameList)
joints = []
len(joints)
joints_attr_list = []
len(joints_attr_list)

joint_group_dict = {}
raw_controls = []
len(raw_controls)
# get joint index
for i in range(reader.getJointCount()):
    joint_name = reader.getJointName(i)
    joints.append(joint_name)
    for attr in ['tx', 'ty', 'tz', 'rx', 'ry', 'rz', 'sx', 'sy', 'sz']:
        joints_attr_list.append('%s.%s' % (joint_name, attr))

# joint group
joint_group_count = reader.getJointGroupCount()
for group_index in range(joint_group_count):
    joint_index = reader.getJointGroupJointIndices(group_index)
    for ji in joint_index:
        joint_name = joints[ji]
        joint_group_dict.setdefault(joint_name, group_index)

# expression index
for i in range(reader.getRawControlCount()):
    expression_name = reader.getRawControlName(i)
    raw_controls.append(expression_name)


group_index = 77
raw_control_list = reader.getJointGroupInputIndices(group_index)  # column
joint_attr_list = reader.getJointGroupOutputIndices(group_index)  # row
value_table = reader.getJointGroupValues(group_index)

num_rows = 6
# 每列的列数，从 0 开始计数，第 5 列是索引 4
column_index = 119
# 总列数为 10
num_columns = 291

# 提取第 E 列的数据
column_e_data = [value_table[row * num_columns + column_index] for row in range(num_rows)]

reader.getJointName(43)










