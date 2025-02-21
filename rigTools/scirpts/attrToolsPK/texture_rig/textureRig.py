# _*_ coding:cp936 _*_
"""
Scripts :    python.tools.rigging.textureConvertor
Author  :    JesseChou
Date    :    2022/6/28
QQ      :    375714316
E-Mail  :    JesseChou0612@gmail.com or 375714316@qq.com
"""
import re
import math
import os
import collections
import maya.cmds as mc
from maya import cmds
from python.tools.check import scenesApiNodes
from maya.api import OpenMaya
import meshTools.senceInfoFn as ss
import pymel.core as pm

def getUvMainSection( apiNode ):
    """
    # 通过所给的mesh api 节点，获取其所属uv象限
    :param apiNode: mesh api 节点，MObject类型
    :return: [u,v]
    """
    mesh = OpenMaya.MFnMesh(apiNode)
    us, vs = mesh.getUVs()
    uInfos = collections.Counter([int(math.floor(x)) for x in us])
    vInfos = collections.Counter([int(math.floor(x)) for x in vs])
    uValues = uInfos.values()
    vValues = vInfos.values()
    if uValues and vValues:
        uMax = max(uInfos.values())
        vMax = max(vInfos.values())
        u, v = 0, 0
        for key, value in uInfos.iteritems():
            if value == uMax:
                u = key
                break
        for key, value in vInfos.iteritems():
            if value == vMax:
                v = key
                break
        return [u, v]
def getUvMainSectionFn( mesh ):
    """
    # 通过所给的mesh api 节点，获取其所属uv象限
    :param apiNode: mesh api 节点，MObject类型
    :return: [u,v]
    """
    us, vs = mesh.getUVs()
    uInfos = collections.Counter([int(math.floor(x)) for x in us])
    vInfos = collections.Counter([int(math.floor(x)) for x in vs])
    uValues = uInfos.values()
    vValues = vInfos.values()
    if uValues and vValues:
        uMax = max(uInfos.values())
        vMax = max(vInfos.values())
        u, v = 0, 0
        for key, value in uInfos.iteritems():
            if value == uMax:
                u = key
                break
        for key, value in vInfos.iteritems():
            if value == vMax:
                v = key
                break
        return [u, v]
def getCacheMeshUvInfo(cache = 'cache'):
    cacheMesh = pm.ls([i for i in mc.listRelatives(cache, ad=1, type='mesh') if mc.ls(i, type='mesh', ni=1)])
    infos = {}
    for node in cacheMesh:
        uvs = getUvMainSectionFn(node)
        if uvs:
            key = '%d_%d' % (uvs[0], uvs[1])
            if key not in infos.keys():
                infos[key] = []
            infos[key].append(node.name())
    return infos
def getMeshUvInfos():
    """
    # 获取场景中所有mesh的uv信息
    :return: {'u_v':[mesh1,mesh2,...]}
    """
    nodes = scenesApiNodes.ScenesNodes()
    infos = {}
    for node in nodes.mesh:
        uvs = getUvMainSection(node.object())
        if uvs:
            key = '%d_%d' % (uvs[0], uvs[1])
            if key not in infos.keys():
                infos[key] = []
            infos[key].append(node.name())
    return infos

def duplicateShaderNet( node, u, v ):
    """
    复制材质链接树
    :param node: 起始节点名称
    :param u: 贴图所属u象限
    :param v: 贴图所属v象限
    :return: 复制出来的新节点
    """
    noExitPath = list()
    if cmds.nodeType(node) not in ['transform', 'mesh', 'colorManagementGlobals', 'place2dTexture']:
        newNode = '%s_u%d_v%d_' % (node, u, v)
        if not cmds.objExists(newNode):
            try:
                newNode = cmds.duplicate(node, n=newNode)[0]
            except Exception as e:
                print(e)
        if cmds.objExists(newNode):
            if cmds.nodeType(newNode) == 'file':
                value = cmds.getAttr('%s.uvTilingMode' % node)

                if value == 3:
                    num = 1001 + v * 10 + u
                    path = cmds.getAttr('%s.fileTextureName' % node)
                    newPath = path.replace('<UDIM>', str(num))
                    search = re.search(r'\d{4}\.tif', path)
                    if search:
                        newPath = path.replace(search.group(), '%04d.tif' % num)

                    cmds.setAttr('%s.uvTilingMode' % newNode, 0)
                    if os.path.exists(newPath):
                        cmds.setAttr('%s.fileTextureName' % newNode, newPath, type='string')
                    else:
                        noExitPath.append((newNode,newPath))
                else:
                    mc.delete(newNode)
                    return node,noExitPath

            cons = cmds.listConnections(node, s=True, d=False, p=True) or []
            sourceNodes = []

            for con in cons:
                temps = con.split('.')
                if temps[0] not in sourceNodes:
                    sourceNodes.append(temps[0])
            for temp in sourceNodes:
                nod = duplicateShaderNet(temp, u, v)[0]

                if nod:
                    for con in cons:
                        if con.startswith('%s.' % temp):

                            attrs = cmds.listConnections(con, s=False, d=True, p=True) or []
                            for attr in attrs:
                                if attr.startswith('%s.' % node):

                                    connectList = mc.listConnections(con.replace(temp, nod), s=1, p=1) or []
                                    if attr.replace(node, newNode) not in connectList:

                                        if attr.replace(node, newNode).split('.')[1] == 'colorGain':
                                            pass

                                        else:
                                            cmds.connectAttr(con.replace(temp, nod), attr.replace(node, newNode),
                                                             f=True)
                                            if mc.nodeType(nod) == 'RedshiftRaySwitch':
                                                preNode = mc.listConnections(nod + '.cameraColorBack', s=1)[-1]
                                                nexNode = mc.listConnections(nod + '.outColor', type='RedshiftMaterial')
                                                if preNode and nexNode:
                                                    mc.connectAttr(preNode + '.outColor',
                                                                   nexNode[-1] + '.diffuse_color', f=1)

            return newNode,noExitPath
        else:
            return node,noExitPath
    return node,noExitPath
def convertShader( uvInfos ):
    """
    根据给出的模型uv信息，和材质贴图，分配不同不同uv象限的模型不同的材质球
    :param uvInfos: 模型的uv象限信息
    :return: None
    """
    for key, value in uvInfos.iteritems():
        temp = key.split('_')
        u = int(temp[0])
        v = int(temp[1])

        sgInfos = getMeshShadingGroup(value)
        for k, m in sgInfos.iteritems():
            try:
                newSg = cmds.duplicate(k, n='%s_u%d_v%d_' % (k, u, v))[0]
            except:
                pass
            for n in m:
                cons = cmds.listConnections('%s.instObjGroups[0]' % n, s=False, d=True, p=True) or []
                for con in cons:
                    cmds.disconnectAttr('%s.instObjGroups[0]' % n, con)

                try:
                    cmds.sets(n, e=1, forceElement=newSg)
                except Exception as e:
                    print(e)
            cons = cmds.listConnections('%s.surfaceShader' % k, s=True, d=False, p=True)
            if cons:
                node = cons[0].split('.')[0]
                newShader = duplicateShaderNet(node, u, v)[0]
                cmds.connectAttr(cons[0].replace(node, newShader), '%s.surfaceShader' % newSg, f=True)

def getMeshShadingGroup( meshes ):
    """
    # 获取指定模型匹配的shadingGroup节点
    :param meshes: 指定的mesh节点列表
    :return: 匹配信息 {shadingGroup:[mesh1,mesh2...]}
    """
    infos = {}
    for mesh in meshes:
        cons = cmds.listConnections(mesh, s=False, d=True, type='shadingEngine')
        if cons:
            if cons[0] not in infos.keys():
                infos[cons[0]] = []
            infos[cons[0]].append(mesh)
    return infos

def convertTexture(cache):
    delSmoothNode = ss.deleteSmoothNode(ss.getMesh())
    delRsColorCorrectionNode = ss.delRsColorCorrectionNode()
    infos = getCacheMeshUvInfo(cache)
    convertShader(infos)

def convertor( force=0 ):
    judge = 1
    if force == 0:
        text = cmds.confirmDialog(m=u'执行此命令前，请先保存文件，以防数据丢失，造成不可恢复的损失！',
                                  b=[u'确认已存储', u'取消'])
        if text == u'取消':
            judge = 0
    if judge:
        convertTexture('cache')






if __name__ == '__main__':
    import texture_rig.textureRig as tt
    tt.convertor()




























