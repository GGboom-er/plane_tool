#!/usr/bin/env python
# _*_ coding:utf-8 _*_

import os
import hou

# --- 工具函数 ---

def safe_set_parm(node, parm_name, value):
    """设置参数的通用包装器，处理由于节点类型变化导致的参数缺失"""
    p = node.parm(parm_name)
    if not p:
        return False
    try:
        p.set(value)
        return True
    except TypeError:
        # 尝试菜单索引匹配
        if isinstance(value, str):
            for i, label in enumerate(p.menuLabels()):
                if value.lower() in label.lower():
                    p.set(i)
                    return True
                    break
    except Exception as e:
        print(f"Warning: Failed to set {node.name()}.{parm_name} = {value}: {e}")
        return False

def set_clean_tolerance(clean_node, tol_val):
    """统一设置 Clean 节点的参数"""
    params = {
        "consolidation": 1,
        "consoldist": tol_val,
        "fusedist": tol_val,   # H21
        "degentol": tol_val,   # H21
        "dodelscript": 1,
        "fixoverlaps": 1
    }
    for k, v in params.items():
        safe_set_parm(clean_node, k, v)

def ensure_wrangle_parms(wrangle_node):
    """为 Wrangle 节点添加控制参数"""
    pg = wrangle_node.parmTemplateGroup()
    defs = [
        ("min_curve", "Min Curve", 0.0, 0.0, 1.0),
        ("max_curve", "Max Curve", 1.0, 0.0, 1.0),
        ("hard_threshold", "Hard Threshold", 1.2, 0.0, 3.0)
    ]
    
    changed = False
    for name, label, val, mn, mx in defs:
        if not pg.find(name):
            pt = hou.FloatParmTemplate(name, label, 1, default_value=[val], min=mn, max=mx)
            pg.append(pt)
            changed = True
            
    if changed:
        wrangle_node.setParmTemplateGroup(pg)

# --- 节点构建逻辑 ---

def build_smart_reduce_chain(parent_geo, input_node, base_name):
    nodes_list = []  # 收集节点用于布局
    
    # 1. 预处理 (Clean & Normal)
    clean_node = parent_geo.createNode("clean", f"pre_clean_{base_name}")
    clean_node.setInput(0, input_node)
    set_clean_tolerance(clean_node, 0.0001)
    nodes_list.append(clean_node)
    
    pre_normal = parent_geo.createNode("normal", f"pre_normal_{base_name}")
    pre_normal.setInput(0, clean_node)
    safe_set_parm(pre_normal, "cuspangle", 60)
    nodes_list.append(pre_normal)
    
    # 2. 特征检测 (Measure)
    measure_node = parent_geo.createNode("measure", f"curv_{base_name}")
    measure_node.setInput(0, pre_normal)
    
    # [Houdini 21 修正] Element Type设置
    p_grouptype = measure_node.parm("grouptype")
    if p_grouptype:
        # H21使用字符串值 "points" 或 "prims"
        try:
            p_grouptype.set("points")
        except:
            # 如果是菜单参数，尝试设置索引
            menu_items = p_grouptype.menuItems() if hasattr(p_grouptype, 'menuItems') else []
            if "points" in menu_items:
                p_grouptype.set("points")
            else:
                p_grouptype.set(0)  # Points通常是第一个选项
    else:
        # 回退兼容旧版本
        safe_set_parm(measure_node, "class", 0)  # Points = 0

    # 设置测量类型
    if not safe_set_parm(measure_node, "measure", "curvature"):
        safe_set_parm(measure_node, "type", "curvature")  # 旧版本回退
    
    if not safe_set_parm(measure_node, "curvature", "curvedness"):
        safe_set_parm(measure_node, "curvaturetype", "curvedness")  # 旧版本回退
    
    safe_set_parm(measure_node, "attribname", "mask")
    nodes_list.append(measure_node)

    # 3. 权重计算 (Wrangle & Blur)
    wrangle_node = parent_geo.createNode("attribwrangle", f"calc_{base_name}")
    wrangle_node.setInput(0, measure_node)
    ensure_wrangle_parms(wrangle_node)
    
    vex_code = """
    i@group_hard_corners = 0;
    float c = abs(f@mask);
    f@mask = fit(c, chf('min_curve'), chf('max_curve'), 0.1, 1.0);
    f@mask = pow(f@mask, 0.5);
    if(c > chf('hard_threshold')) { 
        @group_hard_corners = 1; 
        f@mask = 50.0; 
    }
    """
    wrangle_node.parm("snippet").set(vex_code)
    nodes_list.append(wrangle_node)
    
    blur_node = parent_geo.createNode("attribblur", f"blur_{base_name}")
    blur_node.setInput(0, wrangle_node)
    # [H21修正] attribblur参数名可能是 "attribs" 或 "attributes"
    if not safe_set_parm(blur_node, "attribs", "mask"):
        safe_set_parm(blur_node, "attributes", "mask")
    safe_set_parm(blur_node, "iterations", 5)
    nodes_list.append(blur_node)
    
    # 4. 减面 (PolyReduce)
    reduce_type = "polyreduce::2.0" if hou.nodeType(hou.sopNodeTypeCategory(), "polyreduce::2.0") else "polyreduce"
    reduce_node = parent_geo.createNode(reduce_type, f"red_{base_name}")
    reduce_node.setInput(0, blur_node)
    safe_set_parm(reduce_node, "percentage", 15)
    safe_set_parm(reduce_node, "retainattrib", "mask")
    safe_set_parm(reduce_node, "retainattribweight", 1.0)
    safe_set_parm(reduce_node, "hardfeaturepoints", 1)
    safe_set_parm(reduce_node, "hardfeaturepointsgroup", "hard_corners")
    nodes_list.append(reduce_node)
    
    # 5. 拓扑修复 (PolyFill & Divide)
    polyfill = parent_geo.createNode("polyfill", f"fill_{base_name}")
    polyfill.setInput(0, reduce_node)
    # [H21修正] fillmode有效值: "poly", "triangles", "trianglefan", "quadfan", "quads", "quadgrid"
    safe_set_parm(polyfill, "fillmode", "poly")  # 单个多边形填充模式
    nodes_list.append(polyfill)
    
    divide_node = parent_geo.createNode("divide", f"tri_{base_name}")
    divide_node.setInput(0, polyfill)
    nodes_list.append(divide_node)
    
    # 6. 法线传递与最终清理
    promote_n = parent_geo.createNode("attribpromote", f"promote_N_{base_name}")
    promote_n.setInput(0, pre_normal)
    safe_set_parm(promote_n, "inname", "N")
    
    # [H21修正] inclass/outclass可能接受字符串或整数
    # H21: "point"=2, "vertex"=3 或直接使用字符串
    if not safe_set_parm(promote_n, "inclass", "point"):
        safe_set_parm(promote_n, "inclass", 2)  # Point
    if not safe_set_parm(promote_n, "outclass", "vertex"):
        safe_set_parm(promote_n, "outclass", 3)  # Vertex
    nodes_list.append(promote_n)
    
    transfer_node = parent_geo.createNode("attribtransfer", f"xfer_N_{base_name}")
    transfer_node.setInput(0, divide_node)
    transfer_node.setInput(1, promote_n)
    
    # [H21修正] attribtransfer参数可能变化
    if not safe_set_parm(transfer_node, "pointattribs", "*"):
        safe_set_parm(transfer_node, "pointattribs", 1)
        safe_set_parm(transfer_node, "pointattriblist", "N")
    safe_set_parm(transfer_node, "thresholddist", 10000.0)
    nodes_list.append(transfer_node)
    
    final_clean = parent_geo.createNode("clean", f"fin_{base_name}")
    final_clean.setInput(0, transfer_node)
    safe_set_parm(final_clean, "delattribs", 1)
    safe_set_parm(final_clean, "keepattribs", "N uv Cd")
    safe_set_parm(final_clean, "delgroups", 1)
    set_clean_tolerance(final_clean, 0.0001)
    nodes_list.append(final_clean)

    # [布局修正] 传入节点列表进行布局
    parent_geo.layoutChildren(nodes_list)
    
    return final_clean

# --- 执行逻辑 ---

def get_ui_nodes(container):
    """映射 UI 需要控制的关键节点"""
    nodes = {}
    mapping = {
        "pre_clean_": "pre_clean",
        "curv_": "measure",
        "calc_": "wrangle",
        "blur_": "blur",
        "red_": "reduce",
        "fin_": "final_clean"
    }
    for child in container.children():
        name = child.name()
        for prefix, key in mapping.items():
            if name.startswith(prefix):
                nodes[key] = child
                break
    return nodes

def process_file(file_path, output_dir, parent_geo, parms):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return None

    # 清理旧节点
    parent_geo.deleteItems(parent_geo.children())
    
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # 构建新网络
    read_node = parent_geo.createNode("file", f"in_{base_name}")
    read_node.parm("file").set(file_path)
    
    final_node = build_smart_reduce_chain(parent_geo, read_node, base_name)
    ui_nodes = get_ui_nodes(parent_geo)
    
    # 应用参数
    if 'reduce' in ui_nodes:
        reduce_node = ui_nodes['reduce']
        if reduce_node.parm('percentage'):
            reduce_node.parm('percentage').set(parms.get('percentage', 15))
        if reduce_node.parm('retainattribweight'):
            reduce_node.parm('retainattribweight').set(parms.get('mask_weight', 20))
        
    if 'wrangle' in ui_nodes:
        wrangle_node = ui_nodes['wrangle']
        if wrangle_node.parm('hard_threshold'):
            wrangle_node.parm('hard_threshold').set(parms.get('hard_threshold', 1.2))
        
    if 'blur' in ui_nodes:
        blur_node = ui_nodes['blur']
        if blur_node.parm('iterations'):
            blur_node.parm('iterations').set(parms.get('blur_iter', 5))
    
    tol = parms.get('tolerance', 0.0001)
    if 'pre_clean' in ui_nodes: 
        set_clean_tolerance(ui_nodes['pre_clean'], tol)
    if 'final_clean' in ui_nodes: 
        set_clean_tolerance(ui_nodes['final_clean'], tol)
    
    final_node.setDisplayFlag(True)
    final_node.setRenderFlag(True)

    # 导出
    out_name = f"{base_name}_R{int(parms.get('percentage',15))}_M{int(parms.get('mask_weight',20))}.obj"
    out_path = os.path.join(output_dir, out_name).replace(os.sep, "/")
    
    rop = parent_geo.createNode("rop_geometry", f"out_{base_name}")
    rop.setInput(0, final_node)
    rop.parm("sopoutput").set(out_path)
    
    try:
        rop.parm("execute").pressButton()
        print(f"Export successful: {out_path}")
    except Exception as e:
        print(f"Export failed: {e}")
        
    return ui_nodes