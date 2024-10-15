#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: exportCache.py
@date: 2024/8/28 18:45
@desc: 
"""
#!/usr/bin/env python
# _*_ coding:cp936 _*_

__author__ = 'yangzhuo'

import json

import sys
sys.path.append(r'C:\workspace\ppas')
sys.path.append(r'P:\pipeline\ppas')
sys.path.append(r'P:\pipeline\python39_python_lib')

import maya.cmds as cmds
import pymel.core as pm
from dayu_path import DayuPath


def set_reference_node_infos(node, info_dict):
    """
    写入 流程秘密信息
    """

    cmds.lockNode(node, l=False)

    if not cmds.objExists('%s.PPS_SECRET' % node):
        base_dict = {}
        cmds.addAttr(node, ln='PPS_SECRET', dt='string')
    else:
        base_dict = eval(cmds.getAttr('%s.PPS_SECRET' % node)) if cmds.getAttr('%s.PPS_SECRET' % node) else {}

    base_dict.update(info_dict)
    cmds.setAttr('%s.PPS_SECRET' % node, e=True, l=False)
    cmds.setAttr('%s.PPS_SECRET' % node, str(base_dict), typ='string')
    cmds.setAttr('%s.PPS_SECRET' % node, e=True, l=True)
    cmds.lockNode(node, l=True)


def write_asset_info():
    """
    写入 流程秘密信息
    """
    ref_list = []
    for ref_node in getReferenceList():
        if ref_node not in ['sharedReferenceNode', '_UNKNOWN_REF_NODE_']:
            ref_filename = ''
            try:
                ref_nodes = cmds.referenceQuery(ref_node, n=True)
                ref_filename = cmds.referenceQuery(ref_node, f=1)
                namespace_ = cmds.referenceQuery(ref_node, ns=1)
            except Exception as e:
                print('error:', e)
                namespace_ = ''
                ref_nodes = None

            print ('---' * 30)
            print ('ref_filename', ref_filename)
            if ref_nodes and ('asset_lib' in ref_filename or 'pub/rig' in ref_filename.replace('\\', '/')):
                top_name_list = ['group', 'bg', 'sc01']
                top_node = next((node_str for node_str in ref_nodes
                                 if node_str.split(':')[-1].lower() in top_name_list), None)
                if not top_node:
                    continue

                # parent = cmds.listRelatives(top_node, p=True)
                if ref_filename:
                    ref_list.append(ref_node)
                    rig_stem = DayuPath(ref_filename).stem
                    if len(rig_stem.split('_')) == 6:
                        project, sequence, shot, step, task, version = rig_stem.split('_')
                        if sequence == 'env':
                            continue
                        asset_info = {
                            'project': project,
                            'asset_type': sequence,
                            'asset': shot,
                            'step': step,
                            'task': task,
                            'version': version,
                            'file': ref_filename,
                            'namespace_': namespace_
                        }
                        set_reference_node_infos(ref_node, asset_info)

    return ref_list


def maya_export_usd(hierarchy, export_file, is_ani=0, start=1001, end=1001, strip_namespace=1):
    """
    选择指定的层级导出usd
    subdiv_type: catmullClark | none
    """
    import maya.cmds as cmds
    options = (';exportUVs=1;exportSkels=none;exportSkin=none'
               ';exportBlendShapes=0;exportDisplayColor=0;exportColorSets=0'
               ';defaultMeshScheme=none;defaultUSDFormat=usdc;animation={is_ani}'
               ';eulerFilter=1;staticSingleSample=1'
               ';startTime={start};endTime={end};frameStride=1;frameSample=0.0'
               ';parentScope=;shadingMode=none;exportInstances=1'
               ';exportVisibility=1;mergeTransformAndShape=1;stripNamespaces={strip_namespace}'.format(is_ani=is_ani,
                                                                                                       start=70,
                                                                                                       end=end,
                                                                                                       strip_namespace=strip_namespace
                                                                                                       ))
    cmds.select(cl=1)
    cmds.select(hierarchy)
    cmds.file(export_file, force=1, options=options, typ='USD Export', preserveReferences=1, exportSelected=1)


def _get_info(node, attr_name):
    import ast
    import pymel.core as pm
    node = pm.PyNode(node)
    if node:
        attr = getattr(node, attr_name, None)
        if attr:
            return ast.literal_eval(attr.get())
    return None


def get_camera_position():
    """
    相机嵌套  会导致数值变化
    :return:
    """
    import pymel.core as pm
    import maya.cmds as cmds
    cam_list = pm.ls('anim_camera')
    ani_camera = cam_list[0] if cam_list else None
    if not ani_camera:
        return None
    return cmds.xform(ani_camera.name(), q=True, ws=True, t=True)


def get_obj_close_position_length(cam_pos, obj_name):
    import maya.api.OpenMaya as om
    fn_mesh = om.MFnMesh(om.MSelectionList().add(obj_name).getDagPath(0))
    source_pt = om.MPoint(cam_pos)
    target_pt = fn_mesh.getClosestPoint(source_pt, space=om.MSpace.kWorld)[0]
    length = (source_pt - target_pt).length()
    return length


def get_ref_node_dict(project):
    import pymel.core as pm
    asset_dict = {}
    cam_position = get_camera_position()

    for node in pm.ls(type='reference'):
        ref_file = node.referenceFile()
        if not ref_file:
            continue

        # 如果是未加载的ref文件 跳过
        if not node.isLoaded():
            continue

        # 如果是未勾选的ref  则跳过
        if not node.nodes():
            continue

        if _get_info(node, 'PPS_SECRET'):
            data = _get_info(node, 'PPS_SECRET')
            # 如果是场景文件  跳过
            if data.get('asset_type_entity') == 'env' or data.get('asset.asset_tag'):
                continue
            cache_level = node.nodes()[0].name().replace('Group', 'cache')

            if pm.objExists(cache_level):
                mesh_list = [m for m in pm.ls(cache_level, dag=True, type='mesh') if 'Orig' not in m.name()]
                distance_list = []
                for mesh_ in mesh_list:
                    temp_distance = get_obj_close_position_length(cam_position, mesh_.name()) if mesh_ else 0
                    distance_list.append(temp_distance)
                distance_camera = min(distance_list) if distance_list else 1000
                print ('distance_camera', distance_camera)
            else:
                distance_camera = 0

            print ('--' * 30)
            print (node.name().split(':')[-1])
            data.update(
                {
                    'referenceNode': node.name().split(':')[-1],
                    'namespace': node.nodes()[0].namespace(),
                    'cache': cache_level if pm.objExists(cache_level) else '',
                    'project': project,
                    'distance_camera': distance_camera
                }
            )
            asset_dict.setdefault(node.name(), data)
    return asset_dict


def ani_auto_update():
    import pymel.core as pm
    from dayu_path import DayuPath
    if len(pm.sceneName().name.split('_')) != 6:
        return
    if pm.sceneName().name and pm.sceneName().name.split('_')[3] in ['ani', 'ly']:
        for ref in pm.ls(type='reference'):
            if ref and pm.attributeQuery('PPS_SECRET', node=ref, exists=True):
                ref_file = str(ref.referenceFile())
                if not ref_file or ref_file == 'None':
                    continue
                infos = eval(pm.getAttr('%s.PPS_SECRET' % ref))
                asset_type = infos.get('assetType') if infos.get('assetType') else infos.get('asset_type_entity')
                asset = infos.get('asset') if infos.get('asset') else infos.get('asset_entity')
                folder = DayuPath('X:/Project/%s/pub/rig/rig_asset/%s/%s/ue'%(infos.get('project'), asset_type, asset))
                if not folder.exists():
                    folder = DayuPath(ref_file).parent
                version_list = [x for x in folder.listdir() if x.ext in ['.ma', '.mb'] and x.version]
                version_list = sorted(version_list, key=lambda y: y.version)
                if version_list and str(version_list[-1]) != str(DayuPath(ref_file)):
                    # 求出最新的rig名字
                    rig_ma = version_list[-1]
                    pm.FileReference(ref).replaceWith(rig_ma)


def setShowAllGeometryKeyframe():
    import maya.cmds as cmds
    # 在70帧设置显示所有模型的关键帧
    visibilityCtrs = cmds.ls('*:VisibilityCtr')
    visibilityCtrs += cmds.ls('*:Prop')
    visibilityCtrs += cmds.ls('*:Prp')
    for ctr in visibilityCtrs:
        if cmds.objExists('%s.showAllGeometry' % ctr):
            cmds.setKeyframe(ctr, attribute='showAllGeometry', t=[70], v=1)
            cmds.setKeyframe(ctr, attribute='showAllGeometry', t=[71], v=0)


def getReferenceList():
    infos = []
    import pymel.core as pm

    nodes = pm.ls(regex=".*:cache")
    for node in nodes:
        ref_file = node.referenceFile()
        if not ref_file:
            continue
        infos.append(ref_file.refNode.name())

    return infos


def getDataHierarchyInfos():
    """
    # 获取data组别及其子物体的自定义属性信息
    :return: {node1:[attr1,attr2,...]},
              node2:[...]]}
    """
    infos = {}
    refNodes = getReferenceList()
    for refNode in refNodes:
        attrs = {}
        ns = cmds.referenceQuery(refNode, ns=True)[1:]
        data = '%s:data' % ns
        if cmds.objExists(data):
            nodes = cmds.listRelatives(data, ad=True) or []
            nodes.insert(0, data)
            for node in nodes:
                customAttrs = cmds.listAttr(node, ud=True) or []
                attrs[node.split(':')[-1]] = customAttrs
        infos[refNode] = attrs
    return infos


def getAnimationInfos(attrInfos, frame):
    """
    # 获取指定物体指定属性的动画/静态信息
    :param node: 物体节点名称
    :param attr: 属性名称
    :return: {node1:{attr1:{frame1:value1,
                            frame2:value2,
                            ...},
                    attr2:{...}}
              ...}
    """
    infos = {}
    cmds.currentTime(frame)
    for ref, refAttrs in list(attrInfos.items()):
        refInfos = {}
        ns = cmds.referenceQuery(ref, ns=True)[1:]
        for node, value in list(refAttrs.items()):
            temps = {}
            for attr in value:
                if attr not in list(temps.keys()):
                    temps[attr] = {}
                temps[attr][frame] = cmds.getAttr('%s:%s.%s' % (ns, node, attr))
            refInfos[node] = temps
        infos[ref] = refInfos
    return infos


def getDataHierarchyAnimation():
    """
    # 获取data组别及其子物体的自定义属性信息
    :return: {node1:{attr1:{key1:value1,
                            key2:value2,
                            ...},
                    attr2:{...}},
              node2:{...}}
    """
    infos = {}
    attrs = getDataHierarchyInfos()
    start = int(cmds.playbackOptions(q=True, min=True))
    end = int(cmds.playbackOptions(q=True, max=True))
    for i in range(start, end + 1):
        temps = getAnimationInfos(attrs, i)
        for ref, refInfos in list(temps.items()):
            if ref not in list(infos.keys()):
                infos[ref] = {}
            for node, value in list(refInfos.items()):
                if node not in list(infos[ref].keys()):
                    infos[ref][node] = {}
                for attr, v in list(value.items()):
                    if attr not in list(infos[ref][node].keys()):
                        infos[ref][node][attr] = {}
                    for frame, n in list(v.items()):
                        infos[ref][node][attr][frame] = n
    return infos


def get_hierarchy_frame_vis_infos(node, frame, value=True, infos={}):
    if int(cmds.currentTime(q=True)) != frame:
        cmds.currentTime(frame)
    attr_key = '%s__vis__' % node.split(':')[-1]
    if attr_key not in list(infos.keys()):
        infos[attr_key] = {}
    if value:
        value = cmds.getAttr('%s.v' % node)
    infos[attr_key].update({frame: value})
    children = cmds.listRelatives(node, c=True, type='transform', f=True) or []
    for child in children:
        infos = get_hierarchy_frame_vis_infos(child, frame, value, infos)
    return infos


def get_reference_vis_infos():
    infos = {}
    cache_nodes = {}
    ref_nodes = getReferenceList()
    for node in ref_nodes:
        ns = cmds.referenceQuery(node, ns=True)[1:]
        cache_node = '%s:cache' % ns
        if cmds.objExists(cache_node):
            cache_nodes[node] = cache_node
    start = int(cmds.playbackOptions(q=True, min=True))
    end = int(cmds.playbackOptions(q=True, max=True))
    for i in range(start, end + 1):
        for node, cache_node in list(cache_nodes.items()):
            if node not in list(infos.keys()):
                infos[node] = {'visData': {}}
            temps = infos[node]['visData']
            temps = get_hierarchy_frame_vis_infos(cache_node, i, True, temps)
            infos[node]['visData'].update(temps)

    return optimize_vis_infos(infos)


def getCameraFocalLengthAnimation():
    """
    获取场景中相机的focal length 的 key帧信息
    :return: {frame1:value1,frame2:value2,...}
    """
    infos = {}
    camera = 'anim_camera'
    if cmds.objExists(camera):
        shapes = cmds.listRelatives(camera, s=True)
        if shapes:
            attr = '%s.focalLength' % shapes[0]
            if cmds.objExists(attr):
                start = int(cmds.playbackOptions(q=True, min=True))
                end = int(cmds.playbackOptions(q=True, max=True))
                for frame in range(start, end + 1):
                    cmds.currentTime(frame)
                    infos[frame] = cmds.getAttr(attr)
    return infos


def get_custom_attrs():
    infos = getDataHierarchyAnimation()
    vis_infos = get_reference_vis_infos()
    camera_infos = getCameraFocalLengthAnimation()
    for key, value in vis_infos.items():
        infos[key]['visData'] = value.get('visData')
    infos['anim_camera'] = {'focalLength': camera_infos}
    return infos


def optimize_vis_infos(infos):
    new_infos = {}
    for ref, ref_infos in infos.items():
        new_ref = {}
        for attr, attr_infos in ref_infos.items():
            if attr == 'visData':
                vis_infos = {}
                for key, value in attr_infos.items():
                    vis_infos[key] = optimize_dict(value)
                new_ref[attr] = vis_infos
            else:
                new_ref[attr] = attr_infos
        new_infos[ref] = new_ref
    return new_infos


def optimize_dict(infos):
    new_infos = {}
    frames = list(infos.keys())
    frames.sort()
    new_infos[frames[0]] = infos[frames[0]]
    new_infos[frames[-1]] = infos[frames[-1]]
    for i in range(1, len(frames) - 1):
        base_value = infos[frames[i - 1]]
        current_value = infos[frames[i]]
        if current_value != base_value:
            new_infos[frames[i]] = current_value
    return new_infos


def write_default_object_info(node, data_dict):

    for attr, value in data_dict.items():
        if isinstance(value, bool):
            if not pm.attributeQuery(attr, node=node, exists=True):
                node.addAttr(attr, at='bool', hidden=False)
            node.attr(attr).set(value)
        elif isinstance(value, int):
            if not pm.attributeQuery(attr, node=node, exists=True):
                node.addAttr(attr, at='long', hidden=False)
            node.attr(attr).set(value)
        else:
            if not pm.attributeQuery(attr, node=node, exists=True):
                node.addAttr(attr, dt='string', hidden=False)
            node.attr(attr).set(str(value))


def get_newest_folder(project, sequence, shot, style):
    """
    获取缓存最新文件夹
    :param project: 项目名称
    :param sequence: 场次
    :param shot: 镜头号
    :param style: 获取类型,ani/sim
    :return: 指定参数下最新的文件夹
    """
    import os
    import re
    folder = ''
    path = ''
    if style == 'sim':
        path = 'X:\\Project\\%s\\cache\\shot\\%s\\%s\\sim\\task_sim' % (project, sequence, shot)
    if style == 'ani':
        path = 'X:\\Project\\%s\\cache\\shot\\%s\\%s\\ani\\task_ani' % (project, sequence, shot)
    if style == 'ue':
        path = 'X:\\Project\\%s\\cache\\shot\\%s\\%s\\ue\\task_ue' % (project, sequence, shot)
    if style == 'ly':
        path = 'X:\\Project\\%s\\cache\\shot\\%s\\%s\\ani\\task_ly' % (project, sequence, shot)
    if os.path.isdir(path):
        folder_list = [x for x in os.listdir(path) if os.path.isdir('%s\\%s' % (path, x))]
        folder_list = [x for x in folder_list if re.match(r'v\d+', x)]
        folder_list.sort()
        folder = '%s\\%s' % (path, folder_list[-1])
    return folder


def get_cache_infos(project, sequence, shot):
    import os
    import json
    infos = {}
    ani_path = get_newest_folder(project, sequence, shot, 'ani')
    info_file = '%s/cache.json' % ani_path
    if os.path.isfile(info_file):
        with open('%s/cache.json' % ani_path, 'r') as f:
            infos = json.loads(f.read())
    return infos


def export_fbx_camera(project, sequence, shot):
    import os
    import maya.cmds as cmds

    # 检测并加载fbx导出插件
    if not cmds.pluginInfo("fbxmaya", loaded=1, q=1):
        cmds.loadPlugin("fbxmaya")

    ani_path = get_newest_folder(project, sequence, shot, 'ani')
    if os.path.isdir(ani_path):
        cache_infos = get_cache_infos(project, sequence, shot)
        camera_path = '%s/anim_camera.abc' % ani_path

        if os.path.isfile(camera_path):
            cmds.file(new=True, f=True)
            args = {
                'i': True,
                'itr': 'combine',
                'iv': True,
                'mnc': False,
                'ns': '__cache__',
                'pr': True,
                'ra': True,
                'type': 'Alembic'
            }
            cmds.file(camera_path, **args)
            cmds.createNode('camera', n='anim_cameraShape')
            trans_attrs = ['t',
                           'r',
                           's',
                           'v',
                           'rotatePivot',
                           'rotatePivotTranslate',
                           'scalePivot',
                           'scalePivotTranslate',
                           'shear']
            for attr in trans_attrs:
                cmds.connectAttr('__cache__:anim_camera.%s' % attr, 'anim_camera.%s' % attr, f=True)

            shape_attrs = ["centerOfInterest",
                           "horizontalFilmAperture",
                           "verticalFilmAperture",
                           "focalLength",
                           "lensSqueezeRatio",
                           "fStop",
                           "focusDistance",
                           "shutterAngle"]
            for attr in shape_attrs:
                cmds.currentTime(71)
                value = cmds.getAttr('__cache__:anim_cameraShape.%s' % attr)
                cmds.connectAttr('__cache__:anim_cameraShape.%s' % attr, 'anim_cameraShape.%s' % attr, f=True)
                try:
                    cmds.setKeyframe('__cache__:anim_cameraShape', at=attr, v=value, t=(71,))
                    cmds.setKeyframe('__cache__:anim_cameraShape', at=attr, v=value * 0.99, t=(70,))
                except Exception as e:
                    print (e)

            end_frame = cache_infos.get('local', {}).get('endFrame', 102)
            cmds.bakeResults(['anim_camera'], simulation=True, t=(70, end_frame), hierarchy='below',
                             sampleBy=1,
                             oversamplingRate=1, disableImplicitControl=True, preserveOutsideKeys=True,
                             sparseAnimCurveBake=False, removeBakedAttributeFromLayer=False,
                             removeBakedAnimFromLayer=False, bakeOnOverrideLayer=False, minimizeRotation=True,
                             controlPoints=False, shape=True)
            cmds.delete('__cache__:anim_camera')
            cmds.select('anim_camera', r=True)
            fbx_path = '%s/anim_camera.fbx' % ani_path
            cmds.file(fbx_path, f=True, options="v=0;", typ="FBX export", pr=True, es=True)


def export_camera_abc(start, end, abc_path):
    import maya.cmds as cmds
    camera_list = pm.ls(type='camera')
    ani_cam = next((cam.getTransform().fullPath() for cam in camera_list if cam.name() == 'anim_cameraShape'), None)

    if ani_cam:
        args = "-frameRange {start} {end} -stripNamespaces -uvWrite -writeColorSets -writeFaceSets -wholeFrameGeo " \
               "-worldSpace -writeVisibility -eulerFilter -autoSubd -writeUVSets -dataFormat ogawa " \
               "-root {cam_level} -file {abc_path}".format(
            start=start, end=end, cam_level=ani_cam, abc_path=abc_path
        )
        cmds.AbcExport(verbose=0, jobArg=args)


def export_components(grp_name, components_usd_file, _ani_usd_file, _fps, _start, _end):
    from pxr import Usd, UsdGeom, Sdf

    stage = Usd.Stage.CreateNew(components_usd_file)
    root_layer = stage.GetRootLayer()
    root_layer.subLayerPaths.append(_ani_usd_file)

    stage.SetTimeCodesPerSecond(_fps)
    stage.SetFramesPerSecond(_fps)
    stage.SetStartTimeCode(70)
    stage.SetEndTimeCode(_end)

    edits = Sdf.BatchNamespaceEdit()
    traverse_list = stage.Traverse()
    grp_list = next((str(p.GetPath()).split('/') for p in traverse_list if grp_name == str(p.GetName())), None)

    for prim in stage.Traverse():
        grp_short_name = str(prim.GetPath()).split('/')[-1]
        if grp_short_name in grp_list:
            UsdGeom.Imageable(prim).GetVisibilityAttr().Set(UsdGeom.Tokens.inherited)
        else:
            UsdGeom.Imageable(prim).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)

    stage.GetRootLayer().Apply(edits)
    stage.Save()


def export_asset_components(custom_json_file, cache_json_file):
    import json
    from dayu_path import DayuPath

    with open(custom_json_file, 'r') as r:
        custom_data = json.load(r)

    with open(cache_json_file, 'r') as r:
        cache_data = json.load(r)

    fps = cache_data.get('local').get('fps')
    start = cache_data.get('local').get('startFrame')
    end = cache_data.get('local').get('endFrame')

    for ref_name, all_data in custom_data.items():
        vis_data = all_data.get('visData')
        if not vis_data:
            continue

        for vis_grp, frame_dict in vis_data.items():
            value_list = frame_dict.values()
            if False in value_list and len(set(value_list)) == 2:
                maya_grp_name = vis_grp.replace('__vis__', '')
                component_file = DayuPath(custom_json_file).parent.child('.components').child(ref_name).child('%s.usd' % maya_grp_name)
                component_file.parent.mkdir(parents=True)
                ani_usd_file = DayuPath(custom_json_file).parent.child('%s.usd' % ref_name)
                export_components(maya_grp_name, component_file, ani_usd_file, fps, start, end)


if __name__ == '__main__':
    print('start export usd cache....')
    if not cmds.pluginInfo("mayaUsdPlugin", q=True, l=True):
        cmds.loadPlugin("mayaUsdPlugin")

    # 1. 外包回来的ani文件  强制写入 流程秘密信息
    write_asset_info()

    # 2. 自动更新rig
    ani_auto_update()

    # 4. 显示所有
    setShowAllGeometryKeyframe()
    ma_filename = pm.sceneName().__str__()
    stem = DayuPath(ma_filename).stem
    project, sequence, shot, step, task, version = stem.split('_')

    save_as_path = DayuPath(r'U:\plane_export_ani_cache_temp_folder').child(DayuPath(ma_filename).name)
    save_as_path.parent.mkdir(parents=True)
    pm.currentTime(101)
    pm.saveAs(save_as_path)

    export_root = r'X:\Project\{project}\cache\shot\{sequence}\{shot}\ani\task_{step}'.format(
        project=project, sequence=sequence, shot=shot, step=step
    )
    if step == 'ly':
        export_root = r'X:\Project\{project}\cache\shot\{sequence}\{shot}\ani\task_{task}'.format(
            project=project, sequence=sequence, shot=shot, step=step, task=task
        )

    new_ver = 'v001'
    if DayuPath(export_root).exists():
        version_list = sorted([v for v in DayuPath(export_root).listdir() if v.isdir() and v.version])
        if version_list:
            new_ver = 'v%03d' % int(int(version_list[-1].version.replace('v', '')))
    version_root = DayuPath(export_root).child(new_ver)
    version_root.mkdir(parents=True)

    default_node = pm.PyNode('defaultObjectSet')
    assets_attr_exists = pm.objExists('defaultObjectSet.assets')
    cache_json = version_root.child('cache.json')
    custom_json = version_root.child('custom.json')
    start, end = cmds.playbackOptions(q=True, min=True), cmds.playbackOptions(q=True, max=True)
    width = cmds.getAttr('defaultResolution.width')
    height = cmds.getAttr('defaultResolution.height')

    is_simulation = True
    is_motion_blur = False
    linear = pm.currentUnit(query=True, linear=True)
    angular = pm.currentUnit(fullName=True, query=True, angle=True)

    info_dict = {
        'project': project,
        'sequence': sequence,
        'shot': shot,
        'step': step,
        'task': task,
        'version': version,

        'linear': linear,
        'angular': angular,
        'fps': int(pm.mel.currentTimeUnitToFPS()),

        'startFrame': int(cmds.playbackOptions(q=True, min=True)),
        'endFrame': int(cmds.playbackOptions(q=True, max=True)),
        'width': int(cmds.getAttr('defaultResolution.width')),
        'height': int(cmds.getAttr('defaultResolution.height')),
        'is_simulation': default_node.is_simulation.get() if default_node.hasAttr('is_simulation') and assets_attr_exists else is_simulation,
        'is_motion_blur': default_node.is_motion_blur.get() if default_node.hasAttr('is_motion_blur') and assets_attr_exists else is_motion_blur,
        'preFrame': 61 if assets_attr_exists and default_node.hasAttr('is_simulation') and default_node.is_simulation.get() else 0,
        'postFrame': cmds.playbackOptions(q=True, max=True) + 1 if assets_attr_exists and default_node.hasAttr('is_motion_blur') and default_node.is_motion_blur.get() else cmds.playbackOptions(q=True, max=True),
        'offsetFrame': 0,
        'assets': get_ref_node_dict(project),
    }

    write_default_object_info(default_node, info_dict)

    # 5. 输出 custom info 和 cache json
    DayuPath(custom_json).parent.mkdir(parents=True)
    DayuPath(cache_json).parent.mkdir(parents=True)

    custom_infos = get_custom_attrs()
    with open(custom_json, 'w') as w:
        json.dump(custom_infos, w, indent=5)

    assets_dict = info_dict.get('assets')
    info_dict.update({'assets': {}})

    cache_data = {
        "camera": ["anim_camera"],
        'local': info_dict,
        'asset': assets_dict
    }
    with open(cache_json, 'w') as w:
        json.dump(cache_data, w, indent=5)
    print("cache_json", cache_json)

    save_as_path.remove()


