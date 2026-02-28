import maya.cmds as cmds
import json

def get_normalized_curve(name):
    if not cmds.objExists(name):
        return None
    shapes = cmds.listRelatives(name, shapes=True, type="nurbsCurve", fullPath=True)
    if not shapes: return None
    shape = shapes[0]
    cvs = cmds.getAttr(f"{shape}.cp", size=True)
    
    all_pts = []
    for i in range(cvs):
        all_pts.append(cmds.xform(f"{shape}.cv[{i}]", q=True, os=True, t=True))
        
    xs = [p[0] for p in all_pts]
    ys = [p[1] for p in all_pts]
    zs = [p[2] for p in all_pts]
    
    max_span = max(max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs))
    if max_span < 0.0001: max_span = 1.0
    
    pts = []
    for p in all_pts:
        pts.append(f"({round(p[0]/max_span, 3)}*size, {round(p[1]/max_span, 3)}*size, {round(p[2]/max_span, 3)}*size)")
        
    pts_str = ", ".join(pts)
    pts_str = pts_str.replace("(-0.0*size", "(0.000*size").replace("(0.0*size", "(0.000*size")
    
    # 获取真正的属性前，确保能 get 到 knots
    # 有时候 shape 名字中有 | 符号，但是 python 的 f"{shape}.knots" 也是支持的
    # 但是我们直接用 cmds.curve(q=True, knot=True, name=shape) 或者 cmds.getAttr
    knots = []
    try:
        knots = cmds.getAttr(f"{shape}.knots")
    except:
        # Fallback getting knots via ls -fl ? 
        pass
        
    k_str = str([round(x, 1) for x in knots]) if knots else "[]"
    
    return {"points": pts_str, "knots": k_str}

def run():
    try:
        data = {
            "FK": get_normalized_curve("Default_FK_Ctrl"),
            "IK": get_normalized_curve("Default_IK_Ctrl")
        }
        res = json.dumps(data)
        return res
    except Exception as e:
        return str(e)
