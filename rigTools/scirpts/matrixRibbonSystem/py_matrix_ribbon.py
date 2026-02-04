"""
Matrix Ribbon System (MRS) - Plugin Node
Version: 17.4.0
Fix: 
1. Reverted Pre-row to Local Control.
2. Restored Bridge Faces for Stitching (Fixed "Missing Side" issue).
3. STRICT +Y Up Normals (Removed Auto-Flip Heuristics).
"""

import maya.api.OpenMaya as om
import sys
import math
import traceback

def maya_useNewAPI():
    pass

class MatrixRibbonNode(om.MPxNode):
    
    kPluginNodeId = om.MTypeId(0x8700D) 
    kPluginNodeName = "matrixRibbonMesh"
    
    in_width = None       
    in_hold_length = None 
    in_loop = None        
    in_flip_normal = None
    in_reverse_order = None # Added for consistency
    in_stitch = None
    in_chains = None      
    in_chain_matrices = None
    out_chain_u = None
    out_chain_v = None
    out_mesh = None

    def __init__(self):
        om.MPxNode.__init__(self)

    def compute(self, plug, data_block):
        if plug != MatrixRibbonNode.out_mesh and plug != MatrixRibbonNode.out_chain_u and plug != MatrixRibbonNode.out_chain_v: return 

        try:
            width = data_block.inputValue(MatrixRibbonNode.in_width).asFloat()
            hold_len = data_block.inputValue(MatrixRibbonNode.in_hold_length).asFloat()
            loop = data_block.inputValue(MatrixRibbonNode.in_loop).asBool()
            flip = data_block.inputValue(MatrixRibbonNode.in_flip_normal).asBool()
            reverse = data_block.inputValue(MatrixRibbonNode.in_reverse_order).asBool()
            stitch = data_block.inputValue(MatrixRibbonNode.in_stitch).asBool()
            
            output_handle = data_block.outputValue(MatrixRibbonNode.out_mesh)
            out_u_handle = data_block.outputArrayValue(MatrixRibbonNode.out_chain_u)
            out_v_handle = data_block.outputArrayValue(MatrixRibbonNode.out_chain_v)
            
            chains_data = [] 
            in_chains_handle = data_block.inputArrayValue(MatrixRibbonNode.in_chains)
            num_chains = len(in_chains_handle)
            
            for i in range(num_chains):
                compound_handle = in_chains_handle.inputValue() 
                child_array_handle = om.MArrayDataHandle(compound_handle.child(MatrixRibbonNode.in_chain_matrices))
                current_chain_matrices = []
                for j in range(len(child_array_handle)):
                    current_chain_matrices.append(child_array_handle.inputValue().asMatrix())
                    if j < len(child_array_handle) - 1: child_array_handle.next()
                if current_chain_matrices: chains_data.append(current_chain_matrices)
                if i < num_chains - 1: in_chains_handle.next()

            if reverse:
                chains_data.reverse()

            flips = [0] * num_chains

            points = om.MPointArray()
            counts = om.MIntArray()
            connects = om.MIntArray()
            u_coords = om.MFloatArray()
            v_coords = om.MFloatArray()
            uv_ids = om.MIntArray()
            chain_us = om.MDoubleArray()
            chain_vs = om.MDoubleArray()

            if chains_data:
                self._compute_geometry(chains_data, flips, width, hold_len, loop, flip, stitch, points, counts, connects, u_coords, v_coords, uv_ids, chain_us, chain_vs)
            else:
                 output_handle.setMObject(om.MObject.kNullObj)
                 out_u_handle.setAllClean()
                 out_v_handle.setAllClean()
                 data_block.setClean(plug)
                 data_block.setClean(MatrixRibbonNode.out_mesh)
                 data_block.setClean(MatrixRibbonNode.out_chain_u)
                 data_block.setClean(MatrixRibbonNode.out_chain_v)
                 return
            
            mesh_data_fn = om.MFnMeshData()
            new_mesh_data = mesh_data_fn.create()
            mesh_fn = om.MFnMesh()
            empty_u = om.MFloatArray()
            empty_v = om.MFloatArray()
            mesh_fn.create(points, counts, connects, empty_u, empty_v, new_mesh_data)
            
            mesh_fn.setUVs(u_coords, v_coords, "map1") 
            mesh_fn.assignUVs(counts, uv_ids, "map1")
            output_handle.setMObject(new_mesh_data)
                
            builder_u = out_u_handle.builder()
            for i, val in enumerate(chain_us):
                h = builder_u.addElement(i)
                h.setDouble(val)
            out_u_handle.set(builder_u)
            out_u_handle.setAllClean()

            builder_v = out_v_handle.builder()
            for i, val in enumerate(chain_vs):
                h = builder_v.addElement(i)
                h.setDouble(val)
            out_v_handle.set(builder_v)
            out_v_handle.setAllClean()
                
            data_block.setClean(MatrixRibbonNode.out_mesh)
            data_block.setClean(MatrixRibbonNode.out_chain_u)
            data_block.setClean(MatrixRibbonNode.out_chain_v)
            
        except Exception as e:
            om.MGlobal.displayError(f"[MatrixRibbonNode] Compute Error: {e}")
            traceback.print_exc()
            data_block.setClean(plug)

    def _compute_geometry(self, chains_data, flips, width, hold_len, loop, flip, stitch, points, counts, connects, u_coords, v_coords, uv_ids, chain_us, chain_vs):
        num_chains = len(chains_data)
        if num_chains == 0: return
        
        chain_lengths = [len(c) for c in chains_data]
        max_len = max(chain_lengths)
        if max_len < 1: return 
        
        point_lookup = {} 
        
        # --- PHASE 1: GENERATE POINTS (Independent Strips) ---
        
        for c_idx in range(num_chains):
            chain_len = chain_lengths[c_idx]
            
            # Pre-calculate Skeleton
            chain_skel = []
            for i in range(chain_len):
                mat = chains_data[c_idx][i]
                pos = om.MVector(mat[12], mat[13], mat[14])
                tan_x = om.MVector(mat[0], mat[1], mat[2]) # Scaled
                binorm_z = om.MVector(mat[8], mat[9], mat[10]) # Scaled
                chain_skel.append((pos, tan_x, binorm_z))
                
            for i in range(chain_len):
                pos, tan, z = chain_skel[i]
                
                # --- Clamp Logic ---
                actual_hold = max(hold_len, 0.001)
                ref_dist = 0.0
                
                if i < chain_len - 1:
                    p_curr = chain_skel[i][0]
                    p_next = chain_skel[i+1][0]
                    ref_dist = (p_next - p_curr).length()
                elif i > 0:
                    p_curr = chain_skel[i][0]
                    p_prev = chain_skel[i-1][0]
                    ref_dist = (p_curr - p_prev).length()
                    
                if ref_dist > 0.0001 and actual_hold > ref_dist * 0.49:
                    actual_hold = ref_dist * 0.49

                # --- Calculate Columns ---
                safe_width = max(width, 0.0)
                max_w_left = safe_width * 0.5
                max_w_right = safe_width * 0.5
                
                if c_idx > 0:
                    if i < len(chains_data[c_idx-1]):
                        mat_prev = chains_data[c_idx-1][i]
                        pos_prev = om.MVector(mat_prev[12], mat_prev[13], mat_prev[14])
                        dist = (pos - pos_prev).length()
                        if max_w_left > dist * 0.5: max_w_left = dist * 0.5
                elif loop:
                    if i < len(chains_data[-1]):
                        mat_prev = chains_data[-1][i]
                        pos_prev = om.MVector(mat_prev[12], mat_prev[13], mat_prev[14])
                        dist = (pos - pos_prev).length()
                        if max_w_left > dist * 0.5: max_w_left = dist * 0.5

                if c_idx < num_chains - 1:
                    if i < len(chains_data[c_idx+1]):
                        mat_next = chains_data[c_idx+1][i]
                        pos_next = om.MVector(mat_next[12], mat_next[13], mat_next[14])
                        dist = (pos - pos_next).length()
                        if max_w_right > dist * 0.5: max_w_right = dist * 0.5
                elif loop:
                    if i < len(chains_data[0]):
                        mat_next = chains_data[0][i]
                        pos_next = om.MVector(mat_next[12], mat_next[13], mat_next[14])
                        dist = (pos - pos_next).length()
                        if max_w_right > dist * 0.5: max_w_right = dist * 0.5
                
                # Apply Flip
                p_l = pos + (z * max_w_left)
                p_r = pos - (z * max_w_right)
                
                is_flipped = bool(flips[c_idx])
                if is_flipped:
                    p_l, p_r = p_r, p_l
                
                cols = [(p_l, tan), (pos, tan), (p_r, tan)]
                offsets = [-actual_hold, 0.0, actual_hold]
                
                for r_sub, offset in enumerate(offsets):
                    base_row_idx = i * 3 + r_sub
                    
                    point_lookup.setdefault(c_idx, {}).setdefault(base_row_idx, {})
                    
                    base_pos_l, base_tan_l = cols[0]
                    base_pos_c, base_tan_c = cols[1]
                    base_pos_r, base_tan_r = cols[2]
                    
                    curr_l = base_pos_l + base_tan_l * offset
                    curr_c = base_pos_c + base_tan_c * offset
                    curr_r = base_pos_r + base_tan_r * offset

                    # --- INDEPENDENT POINTS (No Merging) ---
                    # Left (0)
                    id_l = len(points)
                    points.append(om.MPoint(curr_l))
                    point_lookup[c_idx][base_row_idx][0] = id_l
                    
                    # Center (1)
                    id_c = len(points)
                    points.append(om.MPoint(curr_c))
                    point_lookup[c_idx][base_row_idx][1] = id_c
                    
                    # Right (2)
                    id_r = len(points)
                    points.append(om.MPoint(curr_r))
                    point_lookup[c_idx][base_row_idx][2] = id_r

        # --- PHASE 2: UVs & FACES ---
        
        max_rows = max_len * 3
        denom_u = float(num_chains * 3) if loop else float(num_chains * 3 - 1)
        if denom_u == 0: denom_u = 1.0
        denom_v = float(max_rows - 1)
        if denom_v == 0: denom_v = 1.0
        
        u_coords.clear()
        v_coords.clear()
        
        # UV Generation (Grid-based)
        for r in range(max_rows):
            v = float(r) / denom_v
            for c in range(num_chains):
                for col in range(3):
                    u_idx = c * 3 + col
                    u = float(u_idx) / denom_u
                    u_coords.append(u); v_coords.append(v)
                    
        if loop:
            for r in range(max_rows):
                v = float(r) / denom_v
                u_coords.append(1.0); v_coords.append(v)
        
        for k in range(num_chains):
            chain_us.append(float(k * 3 + 1) / denom_u)
        for i in range(max_len):
            chain_vs.append(float(i * 3 + 1) / denom_v)

        def get_vid(c, r, col):
            if c in point_lookup and r in point_lookup[c]:
                return point_lookup[c][r][col]
            return None
            
        def get_uv_id(c, r, col):
            row_width = num_chains * 3
            if loop and stitch and c == num_chains and col == 0:
                 main_uvs = num_chains * 3 * max_rows
                 return main_uvs + r
            return (r * row_width) + (c * 3) + col

        for r in range(max_rows - 1):
            for c in range(num_chains):
                
                # Check rows exist
                v_bl = get_vid(c, r, 0); v_br = get_vid(c, r, 1)
                v_tl = get_vid(c, r+1, 0); v_tr = get_vid(c, r+1, 1)
                
                if v_bl is not None and v_tl is not None:
                    # Q1: L-M
                    ids = [v_bl, v_tl, v_tr, v_br] # +Y Up
                    if flip: ids = [ids[0], ids[3], ids[2], ids[1]]
                    for x in ids: connects.append(x)
                    counts.append(4)
                    
                    uvs = [get_uv_id(c,r,0), get_uv_id(c,r+1,0), get_uv_id(c,r+1,1), get_uv_id(c,r,1)]
                    if flip: uvs = [uvs[0], uvs[3], uvs[2], uvs[1]]
                    for x in uvs: uv_ids.append(x)
                    
                    # Q2: M-R
                    v_bl = get_vid(c, r, 1); v_br = get_vid(c, r, 2)
                    v_tl = get_vid(c, r+1, 1); v_tr = get_vid(c, r+1, 2)
                    
                    ids = [v_bl, v_tl, v_tr, v_br]
                    if flip: ids = [ids[0], ids[3], ids[2], ids[1]]
                    for x in ids: connects.append(x)
                    counts.append(4)
                    
                    uvs = [get_uv_id(c,r,1), get_uv_id(c,r+1,1), get_uv_id(c,r+1,2), get_uv_id(c,r,2)]
                    if flip: uvs = [uvs[0], uvs[3], uvs[2], uvs[1]]
                    for x in uvs: uv_ids.append(x)
                
                # 2. STITCH FACES (Bridge)
                if not stitch: continue
                
                c_neighbor = c + 1
                is_loop_wrap = False
                if loop and c == num_chains - 1: 
                    c_neighbor = 0
                    is_loop_wrap = True
                
                if c_neighbor < num_chains:
                    v_br = get_vid(c, r, 2)      # C.Right
                    v_tr = get_vid(c, r+1, 2)    # C.Right.Next
                    v_bl = get_vid(c_neighbor, r, 0)   # N.Left
                    v_tl = get_vid(c_neighbor, r+1, 0) # Neighbor Top-Left
                    
                    if v_br is not None and v_tr is not None and v_bl is not None and v_tl is not None:
                        # Create Stitch Quad
                        ids = [v_br, v_tr, v_tl, v_bl] # +Y Up
                        if flip: ids = [ids[0], ids[3], ids[2], ids[1]]
                        for x in ids: connects.append(x)
                        counts.append(4)
                        
                        # UVs
                        uv_br = get_uv_id(c, r, 2)
                        uv_tr = get_uv_id(c, r+1, 2)
                        
                        if is_loop_wrap:
                            # Use extra column for right side of stitch face
                            uv_bl = get_uv_id(num_chains, r, 0)
                            uv_tl = get_uv_id(num_chains, r+1, 0)
                        else:
                            uv_bl = get_uv_id(c_neighbor, r, 0)
                            uv_tl = get_uv_id(c_neighbor, r+1, 0)
                            
                        uvs = [uv_br, uv_tr, uv_tl, uv_bl]
                        if flip: uvs = [uvs[0], uvs[3], uvs[2], uvs[1]]
                        for x in uvs: uv_ids.append(x)

    @classmethod
    def creator(cls): return MatrixRibbonNode()

    @classmethod
    def initialize(cls):
        n_attr = om.MFnNumericAttribute(); m_attr = om.MFnMatrixAttribute()
        t_attr = om.MFnTypedAttribute(); c_attr = om.MFnCompoundAttribute()

        cls.in_width = n_attr.create("width", "w", om.MFnNumericData.kFloat, 2.0); n_attr.keyable = True
        cls.in_hold_length = n_attr.create("holdLength", "hl", om.MFnNumericData.kFloat, 0.5); n_attr.keyable = True
        cls.in_loop = n_attr.create("loop", "lp", om.MFnNumericData.kBoolean, False); n_attr.keyable = True
        cls.in_stitch = n_attr.create("stitch", "st", om.MFnNumericData.kBoolean, True); n_attr.keyable = True 
        cls.in_flip_normal = n_attr.create("flipNormal", "fn", om.MFnNumericData.kBoolean, False); n_attr.keyable = True
        cls.in_reverse_order = n_attr.create("reverseOrder", "rev", om.MFnNumericData.kBoolean, False); n_attr.keyable = True
        
        cls.in_chain_matrices = m_attr.create("chainMatrices", "cm"); m_attr.array = True
        cls.in_chains = c_attr.create("inChains", "ic"); c_attr.array = True; c_attr.addChild(cls.in_chain_matrices)
        cls.out_mesh = t_attr.create("outMesh", "om", om.MFnData.kMesh); t_attr.writable = False
        
        cls.out_chain_u = n_attr.create("outChainU", "ocu", om.MFnNumericData.kDouble); 
        n_attr.array = True; n_attr.usesArrayDataBuilder = True; n_attr.writable = False; n_attr.storable = False
        
        cls.out_chain_v = n_attr.create("outChainV", "ocv", om.MFnNumericData.kDouble); 
        n_attr.array = True; n_attr.usesArrayDataBuilder = True; n_attr.writable = False; n_attr.storable = False

        for attr in [cls.in_width, cls.in_hold_length, cls.in_loop, cls.in_stitch, cls.in_flip_normal, cls.in_reverse_order, cls.in_chains]: cls.addAttribute(attr)
        cls.addAttribute(cls.out_mesh)
        cls.addAttribute(cls.out_chain_u)
        cls.addAttribute(cls.out_chain_v)
        
        for attr in [cls.in_width, cls.in_hold_length, cls.in_loop, cls.in_stitch, cls.in_flip_normal, cls.in_reverse_order, cls.in_chains, cls.in_chain_matrices]: 
            cls.attributeAffects(attr, cls.out_mesh)
            cls.attributeAffects(attr, cls.out_chain_u)
            cls.attributeAffects(attr, cls.out_chain_v)

def initializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject, "GeminiV2", "17.4.0", "Any")
    try: 
        mplugin.registerNode(MatrixRibbonNode.kPluginNodeName, MatrixRibbonNode.kPluginNodeId, MatrixRibbonNode.creator, MatrixRibbonNode.initialize)
    except Exception as e: om.MGlobal.displayError(f"Register failed: {e}")

def uninitializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject)
    try: mplugin.deregisterNode(MatrixRibbonNode.kPluginNodeId)
    except Exception as e: om.MGlobal.displayError(f"Deregister failed: {e}")
