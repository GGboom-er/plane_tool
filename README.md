# plane_tool

import maya.cmds as cmds
print(cmds.moduleInfo(lm=1))  # 列出所有模块
print(cmds.moduleInfo(path=True, moduleName="MetaFacePoses"))  # 检查 MetaFacePoses 的路径
