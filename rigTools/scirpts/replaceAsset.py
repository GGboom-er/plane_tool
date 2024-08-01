# _*_ coding:cp936 _*_
"""
Scripts :    python.tools.rigging.replaceAsset
Author  :    JesseChou
Date    :    2022/12/20 
QQ      :    375714316
E-Mail  :    JesseChou0612@gmail.com or 375714316@qq.com
"""

from maya import cmds
from python.tools.rigging import skinToolkit,utils

import os
import python.tools.ywmTools.attrToolsPK.texture_rig.textureRig as att

class ReplaceAsset(object):
    def __init__(self, **kwargs):
        self.namespace = kwargs.get('namespace', kwargs.get('ns', ''))
        self.remove_base = kwargs.get('removeBase', kwargs.get('rb', False))
        self.log = kwargs.get('log', False)
        self.mesh_list = []
        self.transform_list = []
        self.__result = {}

    @property
    def result(self):
        return self.__result

    def log_out(self, text):
        if self.log:
            print (text)

    def analyse_asset(self):
        if self.namespace:
            self.mesh_list = cmds.listRelatives(cmds.ls('%s*' % self.namespace, type='mesh'), p=True)
            self.transform_list = cmds.ls('%s*' % self.namespace, type='transform')

    def close_smooth(self):
        utils.close_poly_smooth(self.namespace, True)

    def replace_skin_weight(self):
        # 替换资产蒙皮
        self.__result['skin'] = skinToolkit.batchSkinAndCopy(self.namespace, self.mesh_list, True)

    def replace_blend_shape(self):
        # 替换资产bs
        base_mesh_list = []
        for mesh in self.mesh_list:
            base_transform = mesh.replace(self.namespace, '')
            if cmds.objExists(base_transform):
                base_mesh_list.append(base_transform)
        bs_infos = utils.get_blend_shape_infos(base_mesh_list)
        replace_infos = []
        for key in bs_infos.keys():
            judge = utils.transfer_blend_shape(key, '%s%s' % (self.namespace, key))
            if not judge:
                replace_infos.append(key)
            if judge == 'asFaceBS':
                print 'a'
                self.log_out(u'%s开始替换 ADV 表情跟随模型bs%s' % ('<' * 25, '>' * 25))
                self.replace_adv_facial_follow()
        self.__result['replace_blend_shape'] = replace_infos

    def replace_visibility(self):
        # 替换资产显隐信息连接
        base_obj = 'visData'
        infos = {}
        if cmds.objExists(base_obj):
            target_obj = '%s%s' % (self.namespace, base_obj)
            attr_list = cmds.listAttr(base_obj, ud=True)
            infos = utils.replace_attributes(base_obj, target_obj, attr_list)
        self.__result['replace_visibility'] = infos
        return infos

    def replace_lod_visibility(self):
        infos = []
        for transform in self.transform_list:
            base_obj = transform.replace(self.namespace, '')
            if cmds.objExists(base_obj):
                temps = utils.replace_attributes(base_obj, transform, ['lodVisibility'])
                success = temps.get('success', [])
                base_none = temps.get('base_none', [])
                target_none = temps.get('target_none', [])
                different = temps.get('different', [])
                if not (len(success) > 0 and len(base_none + target_none + different) == 0):
                    infos.append(transform)
        self.__result['replace_lod_visibility'] = infos

    def replace_sub_attributes(self):
        # 替换资产自定义属性连接
        # infos = {'success': {}, 'failed': {}}
        infos = []
        sub_trans = []
        data = 'data'
        if cmds.objExists(data):
            sub_trans = cmds.listRelatives(data, ad=True)
            if 'visData' in sub_trans:
                sub_trans.remove('visData')
            sub_trans.insert(0, data)
        for tran in sub_trans:
            target_tran = '%s%s' % (self.namespace, tran)
            if cmds.objExists(target_tran):
                attrs = cmds.listAttr(tran, ud=True)
                if attrs:
                    temp = utils.replace_attributes(tran, target_tran, attrs)
                    if temp.get('base_none') or temp.get('target_none') or temp.get('different'):
                        infos.append(tran)
        self.__result['replace_sub_attributes'] = infos
        return infos

    def replace_adv_facial_follow(self):
        bs_node = 'SkinAttachMeshBS'
        if cmds.objExists(bs_node):
            bs_attr = '%s.inputTarget[0].inputTargetGroup[0].inputTargetItem[6000].inputGeomTarget' % bs_node
            cons = cmds.listConnections(bs_attr, s=True, d=False, p=True)
            if cons:
                new_con = '%s%s' % (self.namespace, cons[0])
                cmds.connectAttr(new_con, bs_attr, f=True)

    def replace_deltaMush(self):
        # 替换delta mush 变形器关联和权重
        attr_list = ['envelope', 'smoothingIterations', 'smoothingStep', 'inwardConstraint', 'outwardConstraint',
                     'distanceWeight', 'displacement', 'scaleX', 'scaleY', 'scaleZ', 'scale']
        deform_infos = {}
        dm_list = cmds.ls(type='deltaMush')
        for dm in dm_list:
            attrs = {}
            for attr in attr_list:
                s_cons = cmds.listConnections('%s.%s' % (dm, attr), s=True, d=False, p=True)
                d_cons = cmds.listConnections('%s.%s' % (dm, attr), s=False, d=True, p=True)
                value = cmds.getAttr('%s.%s' % (dm, attr))
                attrs[attr] = {'s_cons': s_cons,
                               'd_cons': d_cons,
                               'value': value}

            geometries = cmds.deformer(dm, q=True, g=True)
            geometries = list(set(cmds.listRelatives(geometries, p=True) or []))
            weights = {}
            for geometry in geometries:
                weights[geometry] = cmds.percent(dm, geometry, q=True, v=True)
            deform_infos[dm] = {'geometries': geometries, 'weights': weights, 'attrs': attrs}

        for name, value in deform_infos.items():
            # 求出原始变形器的新名称
            new_name = name
            i = 0
            while True:
                if not cmds.objExists(new_name):
                    break
                i += 1
                new_name = '%s_replace%d' % (name, i)
            # 重命名原始变形器
            cmds.rename(name, new_name)
            # 获取新模型的列表
            geometries = ['%s%s' % (self.namespace, x) for x in value.get('geometries', [])]
            geometries = [x for x in geometries if cmds.objExists(x)]
            if geometries:
                deform = cmds.deltaMush(geometries, n=name)[0]
                # 获取原始变形器记录的属性
                attrs = value.get('attrs', {})
                for attr, attr_infos in attrs.items():
                    # 设置变形器数值
                    try:
                        if attr == 'scale':
                            cmds.setAttr('%s.%s' % (deform, attr), *attr_infos.get('value')[0], type='double3')
                        else:
                            cmds.setAttr('%s.%s' % (deform, attr), attr_infos.get('value'))
                    except Exception as e:
                        print(e)
                    # 关联变形器输出数值
                    d_cons = attr_infos.get('d_cons') or []
                    for con in d_cons:
                        try:
                            cmds.connectAttr('%s.%s' % (deform, attr), con, f=True)
                        except Exception as e:
                            print (e)
                    # 关联变形器输入数值
                    s_cons = attr_infos.get('s_cons') or []
                    for con in s_cons:
                        try:
                            cmds.connectAttr(con, '%s.%s' % (deform, attr), f=True)
                        except Exception as e:
                            print (e)
                for geometry in geometries:
                    base_geometry = geometry.replace(self.namespace, '')
                    weights = value.get('weights', {}).get(base_geometry, [])
                    # print('geometries======>',geometries)
                    # print('geometry======>',geometry)
                    # print('base_geometry======>', base_geometry)
                    # print('deform======>', deform)
                    if weights:
                        for i in range(len(weights)):
                            cmds.percent(deform, '%s.vtx[%d]' % (geometry, i), mp=True, v=weights[i])

    def replace_adv_facial_layer_mesh(self):
        if cmds.objExists('DeformationLayers'):
            meshes = cmds.listRelatives('DeformationLayers', ad=True, type='mesh', f=True) or []
            for mesh in meshes:
                s_cons = cmds.listConnections('%s.inMesh' % mesh, s=True, d=False, p=True)
                if s_cons:
                    if cmds.nodeType(s_cons[0]) in 'mesh':
                        s_mesh = s_cons[0].split('.')[0]
                        transform = cmds.listRelatives(s_mesh, p=True)[0]
                        target_transform = '%s%s' % (self.namespace, transform)
                        if cmds.objExists(target_transform):
                            shapes = cmds.listRelatives(target_transform, ad=True, type='mesh', f=True)
                            orig = [x for x in shapes if 'Orig' in x]
                            if orig:
                                cmds.connectAttr(s_cons[0].replace(s_mesh, orig[0]), '%s.inMesh' % mesh, f=True)

    def remove_base_objects(self):
        if self.remove_base:
            for obj in ['cache', 'data']:
                cmds.delete(obj, ch=True)
                cmds.delete(obj)

    def optimize_file(self):
        # 将参考进来的文件，放到 Geometry 组内
        for obj in ['cache', 'data']:
            if cmds.objExists('%s%s' % (self.namespace, obj)):
                cmds.parent('%s%s' % (self.namespace, obj), 'Geometry')
        # 删除参考进来的整租
        if cmds.objExists('%sGroup' % self.namespace):
            cmds.delete('%sGroup' % self.namespace)
        if self.remove_base:
            # 移除参考进来的资产的空间名
            cmds.namespace(mnr=1, rm=self.namespace)

    def rename_shading_engine(self):
        sg_nodes = cmds.ls('%s*' % self.namespace, type='shadingEngine')
        for sg in sg_nodes:
            name = sg.replace(self.namespace, '')
            if cmds.objExists(name):
                cmds.rename(name, 'prefix_%s' % name)

    def show_replace_result(self):
        message = u''
        skin_result = self.result.get('skin', [])
        if skin_result:
            message += u'拷贝权重的过程中，以下模型未找到相匹配的对象\r\n'
            for skin in skin_result:
                message += u'\t%s\r\n' % skin
        blend_result = self.result.get('replace_blend_shape', [])
        if blend_result:
            message += u'替换blendshape过程中，以下模型出现了错误\r\n'
            for blend in blend_result:
                message += u'\t%s\r\n' % blend
        vis_result = self.result.get('replace_visibility', [])
        if vis_result:
            message += u'替换 visibility 属性过程中，以下节点出现了错误\r\n'
            for vis in vis_result:
                message += u'\t%s\r\n' % vis
        lod_result = self.result.get('replace_lod_visibility', [])
        if lod_result:
            message += u'替换 lod visibility 属性过程中，以下节点出现了错误\r\n'
            for lod in lod_result:
                message += u'\t%s\r\n' % lod
        sub_result = self.result.get('replace_sub_attributes', [])
        if sub_result:
            message += u'替换data附加属性过程中，以下节点出现了错误\r\n'
            for sub in sub_result:
                message += u'\t%s\r\n' % sub
        if not message:
            message = u'恭喜你，替换资产成功！'
        cmds.confirmDialog(t=u'替换结果', m=message, b=u'确认')

    def do_replace(self):
        if self.namespace:
            self.log_out(u'%s开始分析文件信息%s' % ('<' * 25, '>' * 25))
            self.analyse_asset()
            self.log_out(u'%s开始移除模型的smooth节点%s' % ('<' * 25, '>' * 25))
            self.close_smooth()
            # 重命名原始物体关联的sg节点名称，需输出给ue使用
            self.log_out(u'%s开始重命名 SG 节点%s' % ('<' * 25, '>' * 25))
            self.rename_shading_engine()
            # 替换资产蒙皮信息
            self.log_out(u'%s开始传递蒙皮权重%s' % ('<' * 25, '>' * 25))
            self.replace_skin_weight()
            #替换资产bs信息
            self.log_out(u'%s开始传递Blend Shape 信息%s' % ('<' * 25, '>' * 25))
            self.replace_blend_shape()
            #替换资产显隐信息连接
            self.log_out(u'%s开始替换资产显隐连接信息%s' % ('<' * 25, '>' * 25))
            self.replace_visibility()
            # 替换lod visibility 属性连接
            self.log_out(u'%s开始替换物体 Lod Visibility属性%s' % ('<' * 25, '>' * 25))
            self.replace_lod_visibility()
            # 替换资产自定义属性连接
            self.log_out(u'%s开始替换资产自定义属性连接%s' % ('<' * 25, '>' * 25))
            self.replace_sub_attributes()
            #替换adv表情跟随模型bs
            # self.log_out(u'%s开始替换 ADV 表情跟随模型bs%s' % ('<' * 25, '>' * 25))
            # self.replace_adv_facial_follow()
            # 替换 delta mush 变形器信息
            self.log_out(u'%s开始替换 delta mush 变形器信息%s' % ('<' * 25, '>' * 25))
            self.replace_deltaMush()
            # #替换adv layer mesh
            # self.log_out(u'%s开始替换 adv facial layer 关联模型%s' % ('<' * 25, '>' * 25))
            # self.replace_adv_facial_layer_mesh()
            # 移除原始物体
            self.log_out(u'%s开始移除原始物体%s' % ('<' * 25, '>' * 25))
            self.remove_base_objects()
            # 整理文件
            self.log_out(u'%s开始最终优化文件%s' % ('<' * 25, '>' * 25))
            self.optimize_file()
            # 显示替换结果
            self.log_out(u'%s最终显示替换结果%s' % ('<' * 25, '>' * 25))
            self.show_replace_result()


def get_rigPublish_file(project='', rigType='asset_lib', asset_type='', asset_name='', selfPath=''):
    file_path = ''
    folder = 'X:/Project/%s/pub/%s/%s/%s/%s' % (project, rigType, asset_type, asset_name, selfPath)
    if os.path.isdir(folder):
        file_list = [x for x in os.listdir(folder) if x.endswith('.ma')]
        if file_list:
            file_list.sort()
            file_path = '%s/%s' % (folder, file_list[-1])
    return file_path


def checkFileTime(fileA, fileB):
    timeA = os.stat(fileA).st_mtime
    timeB = os.stat(fileB).st_mtime
    if timeA > timeB:
        return fileA
    else:
        return fileB


def replaceAsset(log=False):
    judge = 0
    task_infos = utils.get_task_info()
    if task_infos:
        judge = 1
        project = task_infos.get('project_db', '').replace('proj_', '')
        assetType = task_infos.get('sequence', '')
        asset = task_infos.get('shot', '')
        if project and assetType and asset:
            judge = 2
            atpFilePath = utils.get_standardization_file(project, assetType, asset)
            assetLibFilePath = get_rigPublish_file(project, 'asset_lib', assetType, asset, r'rig\task_master')
            print (atpFilePath)
            print (assetLibFilePath)
            if atpFilePath and assetLibFilePath:
                assetLibFileTime = os.stat(assetLibFilePath).st_mtime
                atpFileTime = os.stat(atpFilePath).st_mtime
                returninfo = None
                if assetLibFileTime < atpFileTime:
                    returninfo='Yes'
                else:
                    judge = 3
                    returninfo = cmds.confirmDialog(title='绑定与Atp文件对比', message=u'atp 晚于绑定入库文件，是否替换资产？',
                                                    button=['Yes', 'No'],
                                                    defaultButton='Yes', cancelButton='No', dismissString='No')
                if returninfo == 'Yes':
                    judge = 4
                    namespace = 'replace_asset'
                    try:
                        cmds.file(atpFilePath, i=1, ns=namespace, type="mayaAscii", options='v=0;', ignoreVersion=1,
                                  mergeNamespacesOnClash=0, ra=True, pr=True)
                    except Exception as e:
                        print (e)
                    if cmds.objExists('%s:cache' % namespace):
                        rc = ReplaceAsset(ns='%s:' % namespace)
                        rc.do_replace()
                        addPrefix = ['cache', 'data']
                        for i in addPrefix:
                            if cmds.objExists(i):
                                children = cmds.listRelatives(i, pa=1, ad=1) or []
                                for child in children:
                                    cmds.rename(child, 'prefix_' + child)
                        att.convertTexture('replace_asset:cache')
                        judge = 5

    if log:
        if judge in [0, 1]:
            cmds.confirmDialog(t=u'提示信息', m=u'未获取到任务相关信息或任务信息不全!!!')
        if judge == 2:
            cmds.confirmDialog(t=u'提示信息', m=u'未找到对应的ATP提交文件!!!')
        if judge == 3:
            cmds.confirmDialog(t=u'提示信息', m=u'atp文件晚于assetLib!!!')
        if judge == 4:
            cmds.confirmDialog(t=u'提示信息', m=u'文件导入失败!!!')
        if judge == 5:
            cmds.confirmDialog(t=u'提示信息', m=u'绑定资产替换成功!!!')
    return judge


if __name__ == '__main__':
    namespace = 'tbx_chr_xman_atp_atp_v030:'
    self = ReplaceAsset(ns=namespace, rb=True, log=True)
    self.do_replace()
