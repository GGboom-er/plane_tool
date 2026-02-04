"""
Matrix Ribbon System (MRS) - Utilities
Version: 7.1.0
Optimized: Safe OPM cleanup (prevents bone snapping), robust selection ID, correct shape naming.
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om
import json

class MrsNaming:
    """Centralized Naming Conventions"""
    # Suffixes
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
    
    # Component Suffixes (Underscores included for precise stripping)
    FK_CTRL = "_FK_Ctrl"
    FK_OFFSET = "_FK_Offset"
    IK_CTRL = "_IK_Ctrl"
    IK_OFFSET = "_IK_Offset"
    UVPIN = "_uvPin"
    
    # Attributes
    ATTR_BASE_NAME = "mrsBaseName"
    ATTR_DRIVER_CONN = "mrsDriverConnection"
    ATTR_BIND_POSE = "mrsBindPose"
    ATTR_CHAINS_DATA = "mrsChainsData"
    ATTR_STORED_U = "mrsStoredU"
    ATTR_STORED_V = "mrsStoredV"

class RigUtils:
    
    @staticmethod
    def get_rig_from_selection(selection):
        """
        Identifies the Rig Set from any selected part of the rig using rigorous topology checks.
        """
        if not selection: return None
        
        for obj in selection:
            if not cmds.objExists(obj): continue
            
            # --- Strategy 1: Object Sets (Most Accurate) ---
            sets = cmds.listSets(object=obj) or []
            for s in sets:
                if s.endswith(MrsNaming.RIG_SET):
                    return s
                # Check Sub-Sets (e.g., Ribbon_Control_Set -> Ribbon_Rig_Set)
                for suffix in [MrsNaming.CTRL_SET, MrsNaming.GRP_SET, MrsNaming.GEO_SET, MrsNaming.JNT_SET, MrsNaming.NODE_SET]:
                    if s.endswith(suffix):
                        base = s[:-len(suffix)] # Exact slice
                        candidate = f"{base}{MrsNaming.RIG_SET}"
                        if cmds.objExists(candidate): return candidate

            # --- Strategy 2: Attribute Lookup (Metadata) ---
            # Walk up hierarchy to find base name attribute
            curr = obj
            while curr:
                if cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=curr, exists=True):
                    base = cmds.getAttr(f"{curr}.{MrsNaming.ATTR_BASE_NAME}")
                    candidate = f"{base}{MrsNaming.RIG_SET}"
                    if cmds.objExists(candidate): return candidate
                
                parents = cmds.listRelatives(curr, parent=True)
                curr = parents[0] if parents else None

            # --- Strategy 3: Name Suffix Stripping (Fallback) ---
            obj_name = obj.split("|")[-1]
            
            # Specific Control Suffixes
            target_suffixes = [
                MrsNaming.FK_CTRL, MrsNaming.IK_CTRL, 
                MrsNaming.FK_OFFSET, MrsNaming.IK_OFFSET,
                MrsNaming.GRP_MAIN, MrsNaming.MESH_FOLLOW
            ]
            
            for suf in target_suffixes:
                if obj_name.endswith(suf):
                    base = obj_name[:-len(suf)]
                    # Check for namespace handling if needed (Group_A_0_FK_Ctrl -> Ribbon_A_0 -> Ribbon)
                    # This is tricky with Group IDs (A, B).
                    # Heuristic: Try to find the Rig Set.
                    
                    # Try direct base
                    candidate = f"{base}{MrsNaming.RIG_SET}"
                    if cmds.objExists(candidate): return candidate
                    
                    # Try stripping Group ID (e.g. Ribbon_A_0 -> Ribbon)
                    # "Ribbon_A_0" split by "_" -> ["Ribbon", "A", "0"]
                    parts = base.rsplit("_", 2) 
                    if len(parts) > 1:
                        # Try "Ribbon"
                        candidate_root = f"{parts[0]}{MrsNaming.RIG_SET}"
                        if cmds.objExists(candidate_root): return candidate_root
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
        # Suffix usually comes with underscore from MrsNaming, or passed without?
        # builder passes MrsNaming.FK_CTRL which has underscore.
        # We need to ensure we don't double underscore.
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
            if cmds.attributeQuery(attr, node=node, exists=True) and not cmds.getAttr(f"{node}.{attr}", lock=True):
                cmds.setAttr(f"{node}.{attr}", 0, 0, 0)
        if not cmds.getAttr(f"{node}.s", lock=True):
            cmds.setAttr(f"{node}.s", 1, 1, 1)

    @staticmethod
    def delete_opm_nodes(driven_node):
        """
        Safely removes OPM driver nodes.
        CRITICAL FIX: Restores the object's World Matrix to prevent snapping to origin.
        """
        if not cmds.objExists(driven_node): return

        plug = f"{driven_node}.offsetParentMatrix"
        conns = cmds.listConnections(plug, s=True, d=False)
        if not conns: return
        
        # 1. Capture World Matrix (Before breaking connection)
        m_current = cmds.xform(driven_node, q=True, ws=True, m=True)
        
        opm_node = conns[0]
        nodes_to_delete = []
        
        # Identify nodes
        if cmds.nodeType(opm_node) == "multMatrix":
            if any(x in opm_node.lower() for x in ["_opm", "opm_driver"]):
                nodes_to_delete.append(opm_node)
                inputs = cmds.listConnections(opm_node, s=True, d=False) or []
                for inp in inputs:
                    if cmds.nodeType(inp) == "inverseMatrix" and any(x in inp.lower() for x in ["pininv", "parentinv", "inv"]):
                        nodes_to_delete.append(inp)
        
        # Break & Delete
        src = cmds.connectionInfo(plug, sourceFromDestination=True)
        if src: cmds.disconnectAttr(src, plug)
            
        if nodes_to_delete:
            valid_del = [n for n in nodes_to_delete if cmds.objExists(n)]
            if valid_del: cmds.delete(valid_del)
            
        # Reset OPM to Identity
        cmds.setAttr(plug, [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1], type="matrix")
        
        # 2. Restore Position (Compensate for OPM loss)
        try:
            cmds.xform(driven_node, ws=True, m=m_current)
        except Exception as e:
            print(f"[MRS] Warning: Could not restore pose for {driven_node}: {e}")

    @staticmethod
    def connect_via_opm(driver, driven):
        if not cmds.objExists(driver) or not cmds.objExists(driven): return None

        plug = f"{driven}.offsetParentMatrix"

        # Cleanup existing
        src = cmds.connectionInfo(plug, sourceFromDestination=True)
        if src:
            src_node = src.split(".")[0]
            cmds.disconnectAttr(src, plug)
            if "opm_driver" in src_node and cmds.objExists(src_node):
                try: cmds.delete(src_node)
                except: pass

        # Calc
        m_driven = om.MMatrix(cmds.xform(driven, q=True, ws=True, m=True))
        m_driver = om.MMatrix(cmds.xform(driver, q=True, ws=True, m=True))
        m_offset = m_driven * m_driver.inverse()
        
        # Optimize Direct
        is_identity = True
        for i in range(16):
            target = 1.0 if (i % 5) == 0 else 0.0
            if abs(m_offset[i] - target) > 0.001: is_identity = False; break
        
        parents = cmds.listRelatives(driven, parent=True)
        
        if is_identity and not parents:
            cmds.connectAttr(f"{driver}.worldMatrix[0]", plug, force=True)
            RigUtils.zero_out_local(driven)
            return None
        
        # MultMatrix
        mult = cmds.createNode("multMatrix", name=f"{driven}_opm_driver")
        
        if is_identity:
            # Shift inputs: Driver -> 0, ParentInv -> 1
            cmds.connectAttr(f"{driver}.worldMatrix[0]", f"{mult}.matrixIn[0]")
            if parents:
                cmds.connectAttr(f"{parents[0]}.worldInverseMatrix[0]", f"{mult}.matrixIn[1]")
        else:
            # Standard: Offset -> 0, Driver -> 1, ParentInv -> 2
            cmds.setAttr(f"{mult}.matrixIn[0]", list(m_offset), type="matrix")
            cmds.connectAttr(f"{driver}.worldMatrix[0]", f"{mult}.matrixIn[1]")
            if parents:
                cmds.connectAttr(f"{parents[0]}.worldInverseMatrix[0]", f"{mult}.matrixIn[2]")
            
        cmds.connectAttr(f"{mult}.matrixSum", plug, force=True)
        RigUtils.zero_out_local(driven)
        return mult

    @staticmethod
    def calculate_topology_metrics(bones):
        if not bones: return 2.0, 0.5
        if len(bones) < 2: return 2.0, 1.0

        total_len = 0.0
        try:
            # Calculate Arc Length
            for i in range(len(bones) - 1):
                p1 = om.MPoint(cmds.xform(bones[i], q=True, ws=True, t=True))
                p2 = om.MPoint(cmds.xform(bones[i+1], q=True, ws=True, t=True))
                total_len += (p1 - p2).length()
        except: 
            return 2.0, 0.5
        
        # Average segment length
        num_segments = len(bones) - 1
        avg_len = total_len / num_segments if num_segments > 0 else 1.0
        
        # New Heuristics:
        # Width: 25% of average length (was 40%)
        # Hold: 10% of average length (was 5%, but user felt it was big? Maybe due to inaccurate total_len before)
        return max(avg_len * 0.25, 0.01), max(avg_len * 0.1, 0.001)

    @staticmethod
    def get_chains_from_ribbon_node(node):
        if not cmds.objExists(node): return []
        if cmds.attributeQuery(MrsNaming.ATTR_CHAINS_DATA, node=node, exists=True):
            try:
                data = cmds.getAttr(f"{node}.{MrsNaming.ATTR_CHAINS_DATA}")
                if data: return json.loads(data)
            except: pass
        
        # Fallback
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
    def create_control_shape(name, size=1.0, shape_type="circle"):
        """Creates control with correct Shape naming."""
        if shape_type == "circle":
            ctrl = cmds.circle(name=name, nr=(1, 0, 0), r=size, ch=False)[0]
            color = 17
        else: 
            ctrl = cmds.curve(name=name, d=1, p=[(-size, -size, 0), (size, -size, 0), (size, size, 0), (-size, size, 0), (-size, -size, 0)])
            cmds.setAttr(f"{ctrl}.rotateY", 90)
            cmds.makeIdentity(ctrl, apply=True, r=True)
            color = 13
        
        # Rename Shape
        shapes = cmds.listRelatives(ctrl, shapes=True, fullPath=True)
        if shapes:
            cmds.rename(shapes[0], f"{name}Shape")
        
        cmds.setAttr(f"{ctrl}.overrideEnabled", 1)
        cmds.setAttr(f"{ctrl}.overrideColor", color)
        return ctrl

    @staticmethod
    def apply_perfect_ribbon_weights(mesh, chains, strategy="hard", pre_follow_parent=True, reverse_order=False, pure_ik=False):
        if not cmds.objExists(mesh) or not chains: return
        all_bones = [b for c in chains for b in c]
        sc = cmds.skinCluster(all_bones, mesh, toSelectedBones=True, maximumInfluences=3)[0]
        
        working_chains = list(chains)
        if reverse_order:
            working_chains.reverse()
            
        if not working_chains: return
        print(f"[MRS] Weighting Order: {[c[0] for c in working_chains]}")

        g_off = 0
        for c_idx, chain in enumerate(working_chains):
            for b_idx, bone in enumerate(chain):
                pre = [g_off+i for i in range(3)]
                mine = [g_off+i for i in range(3,9)]
                
                # Assign Mine
                vtx = [f"{mesh}.vtx[{i}]" for i in mine]
                if vtx: cmds.skinPercent(sc, vtx, transformValue=[(bone, 1.0)])
                
                # Assign Pre
                target = bone
                # If FK (default), Pre follows parent. If Pure IK, Pre follows current bone.
                if b_idx > 0 and pre_follow_parent and not pure_ik: 
                    target = chain[b_idx-1]
                
                vtx_p = [f"{mesh}.vtx[{i}]" for i in pre]
                if vtx_p: cmds.skinPercent(sc, vtx_p, transformValue=[(target, 1.0)])
                
                g_off += 9
