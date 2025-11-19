#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: getBSCtrlExpInfo.py
@date: 2025/8/11 14:54
@desc: 
"""
import maya.cmds as cmds
from dna import DataLayer_All, FileStream, Status, BinaryStreamReader, BinaryStreamWriter
import maya.cmds as cmds
import pymel.core as pm
import json
from dnacalib2 import (
    CommandSequence,
    DNACalibDNAReader,
    SetNeutralJointRotationsCommand,
    SetNeutralJointTranslationsCommand,
    SetVertexPositionsCommand,
    VectorOperation_Add,
)

def load_dna_reader( path ):
    stream = FileStream(path, FileStream.AccessMode_Read, FileStream.OpenMode_Binary)
    reader = BinaryStreamReader(stream, DataLayer_All)
    reader.read()
    if not Status.isOk():
        status = Status.get()
        raise RuntimeError(f"Error loading DNA: {status.message}")
    return reader

def combine_lists_to_dict( A, B ):
    """
    将两个等长列表组合为字典，A的元素为键，对应B元素组成值列表
    参数:
        A (list): 包含重复元素的键列表
        B (list): 对应值元素的列表
    返回:
        dict: 结构为 {A元素: [对应B元素列表]}
    异常:
        ValueError: 当输入列表长度不相等时
    """
    if len(A) != len(B):
        raise ValueError("输入列表必须等长")

    result_dict = {}
    for key, value in zip(A, B):
        if key in result_dict:
            result_dict[key].append(value)
        else:
            result_dict[key] = [value]
    return result_dict


def getDNABsName( index, calibrated ):
    input_indices = calibrated.getBlendShapeChannelInputIndices()
    try:
        return calibrated.getBlendShapeChannelName(input_indices.index(index))
    except:
        return None


CHARACTER_DNA = r'U:\ywm\MHC\Downloaded\DHI\5jd1XPwC_asset\1k\asset_source\MetaHumans\yy\SourceAssets\yy.dna'
reader = load_dna_reader(CHARACTER_DNA)
calibrated = DNACalibDNAReader(reader)
AUlist = combine_lists_to_dict(calibrated.getPSDRowIndices(), calibrated.getPSDColumnIndices())
AuBsInfo = dict()
BsInfo = dict()
AuBsMapInfo = dict()
for AuIndex in sorted(AUlist.keys()):
    AuBsName = getDNABsName(AuIndex, calibrated)
    AuBsComName = [getDNABsName(i, calibrated) for i in AUlist[AuIndex]]
    AuBsExpName = [calibrated.getRawControlName(i) for i in AUlist[AuIndex]]

    AuBsInfo[AuIndex] = {AuBsName: AuBsExpName}
    AuBsMapInfo[AuIndex] = {AuBsName: AuBsComName}
for expIndex in range(calibrated.getRawControlCount()):
    expName = calibrated.getRawControlName(expIndex)
    bsName = getDNABsName(expIndex, calibrated)
    try:
        ctrlName = reader.getGUIControlName(
            reader.getGUIToRawInputIndices()[reader.getGUIToRawOutputIndices().index(expIndex)])
    except:
        ctrlName = None
    BsInfo[expIndex] = {bsName: [ctrlName, expName]}
AllBsInfo = {**BsInfo, **AuBsInfo}

{'mouth_lowerLipBite_L': ['CTRL_L_mouth_lipBiteD.ty',
                          #                                 'CTRL_expressions.mouthLowerLipBiteL']},
                          ctrlToExpList = list()
len(ctrlToExpList)
for ctrl, exp, min, max, k, v in zip(reader.getGUIToRawInputIndices(), reader.getGUIToRawOutputIndices(),
                                     reader.getGUIToRawFromValues(), reader.getGUIToRawToValues()):
    ctrlToExpList.append(((ctrl, reader.getGUIControlName(ctrl)), (exp, reader.getRawControlName(exp)), min, max))






















