"""
Matrix Ribbon System (MRS) - Utilities
Version: 7.1.0
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om
import json
import re

class MrsNaming:
    RIG_SET = "_Rig_Set"
    GEO_SET = "_Geo_Set"
    GRP_SET = "_Group_Set"
    CTRL_SET = "_Control_Set"
    NODE_SET = "_Node_Set"
    JNT_SET = "_Jnt_Set"
    
    GRP_MAIN = "_Grp"
    GRP_JNT = "_Jnt_Grp"
    GRP_CTRL = "_Ctrl_Grp"
    
    MESH_PREVIEW = "_preview_mesh"
    NODE_PREVIEW = "_preview_node"
    MESH_FOLLOW = "_FollowMod"
    MESH_PROXY = "_SkinClusterMod"
    
    FK_CTRL = "_FK_Ctrl"
    FK_OFFSET = "_FK_Offset"
    IK_CTRL = "_IK_Ctrl"
    IK_OFFSET = "_IK_Offset"
    UVPIN = "_uvPin"
    
    ATTR_BASE_NAME = "mrsBaseName"
    ATTR_DRIVER_CONN = "mrsDriverConnection"
    ATTR_BIND_POSE = "mrsBindPose"
    ATTR_CHAINS_DATA = "mrsChainsData"
    ATTR_STORED_U = "mrsStoredU"
    ATTR_STORED_V = "mrsStoredV"
    
    ATTR_SHOW_IK = "Show_IK"
    ATTR_REVERSE_ORDER = "reverseOrder"
    ATTR_MRS_REVERSE = "mrsReverseOrder"
    ATTR_INHERITS_XFORM = "inheritsTransform"
    
    ATTR_WIDTH = "width"
    ATTR_HOLD_LENGTH = "holdLength"
    ATTR_LOOP = "loop"
    ATTR_STITCH = "stitch"
    
    NODE_PLUGIN = "matrixRibbonMesh"

class RigUtils:
    
    NAME_PATTERN = re.compile(r"^(.*)_([A-Za-z0-9]+)(?:_(\d+))?$")
    
    @staticmethod
    def get_reverse_state(node: str) -> bool:
        if not cmds.objExists(node): return False
        
        if cmds.nodeType(node) == MrsNaming.NODE_PLUGIN:
            if cmds.attributeQuery(MrsNaming.ATTR_REVERSE_ORDER, node=node, exists=True):
                return cmds.getAttr(f"{node}.{MrsNaming.ATTR_REVERSE_ORDER}")
        
        check_node = node
        if cmds.nodeType(node) == "transform":
            shapes = cmds.listRelatives(node, shapes=True)
            if shapes: check_node = shapes[0]
            
        if cmds.objExists(check_node) and cmds.attributeQuery("inMesh", node=check_node, exists=True):
            hist = cmds.listConnections(f"{check_node}.inMesh", s=True) or []
            for h in hist:
                if cmds.nodeType(h) == MrsNaming.NODE_PLUGIN:
                    if cmds.attributeQuery(MrsNaming.ATTR_REVERSE_ORDER, node=h, exists=True):
                        return cmds.getAttr(f"{h}.{MrsNaming.ATTR_REVERSE_ORDER}")

        if cmds.attributeQuery(MrsNaming.ATTR_MRS_REVERSE, node=node, exists=True):
            return cmds.getAttr(f"{node}.{MrsNaming.ATTR_MRS_REVERSE}")
            
        return False

    @staticmethod
    def get_rig_from_selection(selection: list) -> str:
        if not selection: return None
        
        for obj in selection:
            if not cmds.objExists(obj): continue
            
            sets = cmds.listSets(object=obj) or []
            for s in sets:
                if s.endswith(MrsNaming.RIG_SET):
                    return s
                for suffix in [MrsNaming.CTRL_SET, MrsNaming.GRP_SET, MrsNaming.GEO_SET, MrsNaming.JNT_SET, MrsNaming.NODE_SET]:
                    if s.endswith(suffix):
                        base = s[:-len(suffix)]
                        candidate = f"{base}{MrsNaming.RIG_SET}"
                        if cmds.objExists(candidate): return candidate

            curr = obj
            while curr:
                if cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=curr, exists=True):
                    base = cmds.getAttr(f"{curr}.{MrsNaming.ATTR_BASE_NAME}")
                    candidate = f"{base}{MrsNaming.RIG_SET}"
                    if cmds.objExists(candidate): return candidate
                
                parents = cmds.listRelatives(curr, parent=True)
                curr = parents[0] if parents else None

            obj_name = obj.split("|")[-1]
            
            target_suffixes = [
                MrsNaming.FK_CTRL, MrsNaming.IK_CTRL, 
                MrsNaming.FK_OFFSET, MrsNaming.IK_OFFSET,
                MrsNaming.GRP_MAIN, MrsNaming.MESH_FOLLOW
            ]
            
            for suf in target_suffixes:
                if obj_name.endswith(suf):
                    trimmed_name = obj_name[:-len(suf)]
                    
                    match = RigUtils.NAME_PATTERN.match(trimmed_name)
                    if match:
                        true_base = match.group(1)
                        candidate_root = f"{true_base}{MrsNaming.RIG_SET}"
                        if cmds.objExists(candidate_root): return candidate_root
                        
                    candidate = f"{trimmed_name}{MrsNaming.RIG_SET}"
                    if cmds.objExists(candidate): return candidate
                        
        return None

    @staticmethod
    def get_alpha_index(index):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        char_idx = index % 26
        num_suffix = index // 26
        return f"{letters[char_idx]}{num_suffix if num_suffix > 0 else ''}"

    @staticmethod
    def generate_name(base_name, chain_idx, bone_idx, suffix):
        clean_base = base_name.replace(":", "_")
        group_id = RigUtils.get_alpha_index(chain_idx)
        if suffix.startswith("_"):
            return f"{clean_base}_{group_id}_{bone_idx}{suffix}"
        return f"{clean_base}_{group_id}_{bone_idx}_{suffix}"

    @staticmethod
    def get_chains_from_selection(selection, treat_as_one_chain=False):
        if not selection: return []
        chains = []
        if treat_as_one_chain:
            valid_sel = [s for s in selection if cmds.nodeType(s) in ["joint", "transform"]]
            if valid_sel: chains.append(valid_sel)
        else:
            for root in selection:
                if not cmds.objExists(root): continue
                chain = [root]
                curr = root
                while True:
                    children = cmds.listRelatives(curr, c=True, type="joint") or []
                    if not children: break
                    curr = children[0]
                    chain.append(curr)
                chains.append(chain)
        return chains

    @staticmethod
    def zero_out_local(node):
        for attr in ['t', 'r', 'jointOrient']:
            plug = f"{node}.{attr}"
            if cmds.attributeQuery(attr, node=node, exists=True):
                is_locked = cmds.getAttr(plug, lock=True)
                is_connected = cmds.connectionInfo(plug, isDestination=True)
                if not is_locked and not is_connected:
                    try: cmds.setAttr(plug, 0, 0, 0)
                    except: pass # Failsafe for partial connections
                    
        scale_plug = f"{node}.s"
        is_s_locked = cmds.getAttr(scale_plug, lock=True)
        is_s_connected = cmds.connectionInfo(scale_plug, isDestination=True)
        
        if not is_s_locked and not is_s_connected:
            try: cmds.setAttr(scale_plug, 1, 1, 1)
            except: pass

    @staticmethod
    def delete_opm_nodes(driven_node):
        if not cmds.objExists(driven_node): return

        plug = f"{driven_node}.offsetParentMatrix"
        conns = cmds.listConnections(plug, s=True, d=False)
        if not conns: return
        
        m_current = cmds.xform(driven_node, q=True, ws=True, m=True)
        
        opm_node = conns[0]
        nodes_to_delete = []
        
        if cmds.nodeType(opm_node) == "multMatrix":
            if any(x in opm_node.lower() for x in ["_opm", "opm_driver"]):
                nodes_to_delete.append(opm_node)
                inputs = cmds.listConnections(opm_node, s=True, d=False) or []
                for inp in inputs:
                    if cmds.nodeType(inp) == "inverseMatrix" and any(x in inp.lower() for x in ["pininv", "parentinv", "inv"]):
                        nodes_to_delete.append(inp)
        
        src = cmds.connectionInfo(plug, sourceFromDestination=True)
        if src: cmds.disconnectAttr(src, plug)
            
        if nodes_to_delete:
            valid_del = [n for n in nodes_to_delete if cmds.objExists(n)]
            if valid_del: cmds.delete(valid_del)
            
        cmds.setAttr(plug, [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1], type="matrix")
        
        try:
            cmds.xform(driven_node, ws=True, m=m_current)
        except Exception as e:
            print(f"[MRS] Warning: Could not restore pose for {driven_node}: {e}")

    @staticmethod
    def connect_via_opm(driver, driven, maintain_offset=True):
        if not cmds.objExists(driver) or not cmds.objExists(driven): return None

        plug = f"{driven}.offsetParentMatrix"
        opm_name = f"{driven}_opm_driver"

        src = cmds.connectionInfo(plug, sourceFromDestination=True)
        if src:
            cmds.disconnectAttr(src, plug)
            
        if cmds.objExists(opm_name):
            try: cmds.delete(opm_name)
            except: pass

        m_offset = om.MMatrix.kIdentity
        
        if maintain_offset:
            m_driven = om.MMatrix(cmds.xform(driven, q=True, ws=True, m=True))
            m_driver = om.MMatrix(cmds.xform(driver, q=True, ws=True, m=True))
            m_offset = m_driven * m_driver.inverse()
        
        is_identity = True
        for i in range(16):
            target = 1.0 if (i % 5) == 0 else 0.0
            if abs(m_offset[i] - target) > 0.001: is_identity = False; break
        
        parents = cmds.listRelatives(driven, parent=True)
        
        if is_identity and not parents:
            cmds.connectAttr(f"{driver}.worldMatrix[0]", plug, force=True)
            RigUtils.zero_out_local(driven)
            return None
        
        mult = cmds.createNode("multMatrix", name=opm_name)
        
        if is_identity:
            cmds.connectAttr(f"{driver}.worldMatrix[0]", f"{mult}.matrixIn[0]")
            if parents:
                cmds.connectAttr(f"{parents[0]}.worldInverseMatrix[0]", f"{mult}.matrixIn[1]")
        else:
            cmds.setAttr(f"{mult}.matrixIn[0]", list(m_offset), type="matrix")
            cmds.connectAttr(f"{driver}.worldMatrix[0]", f"{mult}.matrixIn[1]")
            if parents:
                cmds.connectAttr(f"{parents[0]}.worldInverseMatrix[0]", f"{mult}.matrixIn[2]")
            
        cmds.connectAttr(f"{mult}.matrixSum", plug, force=True)
        RigUtils.zero_out_local(driven)
        return mult

    @staticmethod
    def calculate_topology_metrics(bones: list) -> tuple:
        if not bones: return 2.0, 0.5
        if len(bones) < 2: return 2.0, 1.0

        total_len = 0.0
        try:
            for i in range(len(bones) - 1):
                p1 = om.MPoint(cmds.xform(bones[i], q=True, ws=True, t=True))
                p2 = om.MPoint(cmds.xform(bones[i+1], q=True, ws=True, t=True))
                total_len += (p1 - p2).length()
        except: 
            return 2.0, 0.5
        
        num_segments = len(bones) - 1
        avg_len = total_len / num_segments if num_segments > 0 else 1.0
        
        return max(avg_len * 0.25, 0.01), max(avg_len * 0.1, 0.001)

    @staticmethod
    def get_chains_from_ribbon_node(node: str) -> list:
        if not cmds.objExists(node): return []
        if cmds.attributeQuery(MrsNaming.ATTR_CHAINS_DATA, node=node, exists=True):
            try:
                data = cmds.getAttr(f"{node}.{MrsNaming.ATTR_CHAINS_DATA}")
                if data: return json.loads(data)
            except: pass
        
        chains = []
        c_ind = cmds.getAttr(f"{node}.inChains", multiIndices=True) or []
        for c in sorted(c_ind):
            curr = []
            m_ind = cmds.getAttr(f"{node}.inChains[{c}].chainMatrices", multiIndices=True) or []
            for m in sorted(m_ind):
                conns = cmds.listConnections(f"{node}.inChains[{c}].chainMatrices[{m}]", s=True, d=False)
                if conns: curr.append(conns[0])
            if curr: chains.append(curr)
        return chains

    @staticmethod
    def create_control_shape(name: str, size: float = 1.0, shape_type: str = "circle") -> str:
        if shape_type == "circle":
            ctrl = cmds.circle(name=name, nr=(1, 0, 0), r=size, ch=False)[0]
            color = 17
        else: 
            ctrl = cmds.curve(name=name, d=1, p=[(-size, -size, 0), (size, -size, 0), (size, size, 0), (-size, size, 0), (-size, -size, 0)])
            cmds.setAttr(f"{ctrl}.rotateY", 90)
            cmds.makeIdentity(ctrl, apply=True, r=True)
            color = 13
        
        shapes = cmds.listRelatives(ctrl, shapes=True, fullPath=True)
        if shapes:
            cmds.rename(shapes[0], f"{name}Shape")
        
        cmds.setAttr(f"{ctrl}.overrideEnabled", 1)
        cmds.setAttr(f"{ctrl}.overrideColor", color)
        return ctrl

    @staticmethod
    def apply_perfect_ribbon_weights(mesh: str, chains: list, strategy: str = "hard", pre_follow_parent: bool = True, reverse_order: bool = False, pure_ik: bool = False) -> None:
        if not cmds.objExists(mesh) or not chains: return
        all_bones = [b for c in chains for b in c]
        sc = cmds.skinCluster(all_bones, mesh, toSelectedBones=True, maximumInfluences=3)[0]
        
        working_chains = list(chains)
        if reverse_order:
            working_chains.reverse()
            
        if not working_chains: return

        g_off = 0
        for c_idx, chain in enumerate(working_chains):
            for b_idx, bone in enumerate(chain):
                pre = [g_off+i for i in range(3)]
                mine = [g_off+i for i in range(3,9)]
                
                vtx = [f"{mesh}.vtx[{i}]" for i in mine]
                if vtx: cmds.skinPercent(sc, vtx, transformValue=[(bone, 1.0)])
                
                target = bone
                if b_idx > 0 and pre_follow_parent and not pure_ik: 
                    target = chain[b_idx-1]
                
                vtx_p = [f"{mesh}.vtx[{i}]" for i in pre]
                if vtx_p: cmds.skinPercent(sc, vtx_p, transformValue=[(target, 1.0)])
                
                g_off += 9