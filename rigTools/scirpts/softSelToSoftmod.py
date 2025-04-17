import maya.cmds as cmds
from maya.api import OpenMaya as om

# === 1. 关闭对称建模，以便正确获取软选择 ===
symmetry_enabled = cmds.symmetricModelling(q=True, symmetry=True)
if symmetry_enabled:
    cmds.symmetricModelling(e=True, symmetry=False)

# === 2. 获取当前软选择（包括权重） ===
# 在 API 2.0 中，直接调用 getRichSelection() 返回 MRichSelection 对象
rich_sel = om.MGlobal.getRichSelection()

# 直接获取 MSelectionList 对象（修正原代码中传参错误）
sel_list = rich_sel.getSelection()

if sel_list.length() == 0:
    cmds.symmetricModelling(e=True, symmetry=symmetry_enabled)
    raise RuntimeError(u"没有检测到软选择的组件，请先选择网格顶点或NURBS CV并启用软选择。")

# === 3. 遍历选择的每个物体及其组件，创建 SoftMod 并赋予软选择权重 ===
softmod_nodes = []   # 存储 SoftMod 变形器节点
softmod_handles = [] # 存储 SoftMod 控制柄

for i in range(sel_list.length()):
    dag_path, component = sel_list.getComponent(i)
    if component.isNull():
        continue

    # 获取物体变换节点名称
    dag_path = om.MDagPath(dag_path)         # 复制 MDagPath 避免修改原对象
    shape_node = dag_path.fullPathName()       # 完整的 Shape 路径
    dag_path.pop()                           # 弹出 shape 以获取父级变换
    transform_name = dag_path.fullPathName()   # 变换节点名称

    # 根据组件类型建立 Function Set
    comp_fn = None
    comp_type = component.apiType()
    # 多边形顶点
    if component.hasFn(om.MFn.kMeshVertComponent):
        comp_fn = om.MFnSingleIndexedComponent(component)
        comp_type_str = "vtx"
        indices = comp_fn.getElements()
    # NURBS 曲线 CV
    elif component.hasFn(om.MFn.kCurveCVComponent):
        comp_fn = om.MFnSingleIndexedComponent(component)
        comp_type_str = "cv"
        indices = comp_fn.getElements()
    # NURBS 曲面 CV
    elif component.hasFn(om.MFn.kSurfaceCVComponent):
        comp_fn = om.MFnDoubleIndexedComponent(component)
        comp_type_str = "cv"
        uv_list = comp_fn.getElements()  # 得到 [(u1, v1), (u2, v2), ...] 列表
        # 获取曲面形状节点的 CV 数量（用于线性索引计算）
        surf_fn = om.MFnNurbsSurface(dag_path.extendToShape())
        v_count = surf_fn.numCVsInV
        # 转换 (u,v) 为单一索引：index = u * v_count + v
        indices = [u * v_count + v for (u, v) in uv_list]
    else:
        continue

    # 获取几何体总点数（用于构造权重数组）
    geom_iter = om.MItGeometry(dag_path.extendToShape())
    point_count = geom_iter.count()

    # 初始化权重数组（长度为点数，未选中点权重为0）
    weights = [0.0] * point_count
    # 遍历选中的组件赋权重
    for j, idx in enumerate(indices):
        # 若组件存在软选择权重则获取，否则默认权重1.0
        w = 1.0
        if comp_fn.hasWeights:
            # 调用 weight() 获取 MWeight 对象，通过 influence() 得到浮点权重
            w = comp_fn.weight(j).influence
        weights[idx] = w

    # 构造组件选择字符串列表，以便 SoftMod 仅影响这些组件
    comp_strings = []
    if comp_type == om.MFn.kSurfaceCVComponent:
        # 对于 NURBS曲面CV，需要使用 (u, v) 标记
        for (u, v) in uv_list:
            comp_strings.append(f"{transform_name}.cv[{u}][{v}]")
    else:
        # 多边形顶点或曲线 CV（单索引）
        for idx in indices:
            comp_strings.append(f"{transform_name}.{comp_type_str}[{idx}]")

    if not comp_strings:
        continue

    # 选择组件并创建 SoftMod 变形器（relative 模式保证独立控制柄）
    cmds.select(cmds.ls(sl =1), r=True)
    soft_mod = cmds.softMod(relative=True,uct =0,par =1)
    cmds.sets(comp_strings,add = soft_mod[0]+'Set')
    softmod_node = soft_mod[0]   # SoftMod 节点
    softmod_handle = soft_mod[1] # SoftMod 控制柄
    softmod_nodes.append(softmod_node)
    softmod_handles.append(softmod_handle)

    # 批量设置 SoftMod 权重数组属性
    # 注意：属性字符串格式中 [0:point_count-1] 指定数据范围
    attr_name = f"{softmod_node}.weightList[0].weights[0:{len(weights)-1}]"
    cmds.setAttr(attr_name, *weights, size=len(weights))

    # === 4. 计算软选择加权中心，并更新 SoftMod 控制柄与衰减属性 ===
    total_w = 0.0
    center = om.MPoint(0, 0, 0)
    comp_iter = om.MItGeometry(dag_path.extendToShape(), component)
    while not comp_iter.isDone():
        idx = comp_iter.index()
        w = weights[idx]
        if w > 0.0:
            pos = comp_iter.position(om.MSpace.kWorld)
            center += pos * w
            total_w += w
        comp_iter.next()
    if total_w > 0.0:
        center /= total_w

    # 更新 SoftMod 的 falloffCenter 属性
    cmds.setAttr(f"{softmod_node}.falloffCenter", center.x, center.y, center.z, type="double3")

    # 计算软选择区域的半径：加权中心至所有选中点的最大距离
    max_dist = 0.0
    comp_iter.reset()
    while not comp_iter.isDone():
        idx = comp_iter.index()
        w = weights[idx]
        if w > 0.0:
            pos = comp_iter.position(om.MSpace.kWorld)
            dist = (pos - center).length()
            max_dist = max(max_dist, dist)
        comp_iter.next()
    cmds.setAttr(f"{softmod_node}.falloffRadius", max_dist)

# === 5. 恢复原对称建模设置 ===
cmds.symmetricModelling(e=True, symmetry=symmetry_enabled)

# 最后，选中 SoftMod 控制柄以便用户后续调整
if softmod_handles:
    cmds.select(softmod_handles, r=True)
