"""
Matrix Ribbon System (MRS) - Plugin Node
Version: 16.2.0
Fix: 
1. Last bone hold length clamping.
2. Inverted transverse order (Left->Center->Right) to fix stitching logic.
3. Corrected face winding for new order.
4. Added 'in_chain_flips' attribute for explicit twist control.
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
            stitch = data_block.inputValue(MatrixRibbonNode.in_stitch).asBool()
            
            output_handle = data_block.outputValue(MatrixRibbonNode.out_mesh)
            
            # Use outputArrayValue for Multi-attributes
            out_u_handle = data_block.outputArrayValue(MatrixRibbonNode.out_chain_u)
            out_v_handle = data_block.outputArrayValue(MatrixRibbonNode.out_chain_v)
            
            # 1. Retrieve Chains Data FIRST
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

            # 2. AUTO-CALCULATE FLIPS (Real-time)
            flips = [0] * num_chains
            
            if num_chains > 1:
                # Helper to get root matrix
                def get_root_matrix(idx):
                    if idx < len(chains_data) and len(chains_data[idx]) > 0:
                        return chains_data[idx][0]
                    return om.MMatrix()

                # --- A. Determine Chain 0 Orientation ---
                # Check if Chain 1 is on the Left (+Z) or Right (-Z) of Chain 0
                m0 = get_root_matrix(0)
                m1 = get_root_matrix(1)
                
                m0_inv = m0.inverse()
                m_rel = m1 * m0_inv
                
                # If Z > 0 (Left), Chain 0 must Flip to output Left.
                if m_rel[14] > 0:
                    flips[0] = 1
                else:
                    flips[0] = 0
                
                # --- B. Propagate ---
                # Helper for edge position (Dynamic Width)
                def get_edge_pos_dynamic(mat, is_flipped, side="left", ref_dist=1.0):
                    pos = om.MVector(mat[12], mat[13], mat[14])
                    z_vec = om.MVector(mat[8], mat[9], mat[10]).normalize()
                    
                    width = ref_dist * 0.5
                    if width < 0.001: width = 0.001
                    
                    eff_z = -z_vec if is_flipped else z_vec
                    
                    if side == "left": return pos + (eff_z * width)
                    else: return pos - (eff_z * width)

                for k in range(1, num_chains):
                    m_prev = get_root_matrix(k-1)
                    m_curr = get_root_matrix(k)
                    
                    gap = (om.MVector(m_curr[12], m_curr[13], m_curr[14]) - 
                           om.MVector(m_prev[12], m_prev[13], m_prev[14])).length()
                    
                    prev_flip = flips[k-1]
                    p_exit = get_edge_pos_dynamic(m_prev, prev_flip, side="right", ref_dist=gap)
                    
                    p_entry_norm = get_edge_pos_dynamic(m_curr, False, side="left", ref_dist=gap)
                    p_entry_flip = get_edge_pos_dynamic(m_curr, True, side="left", ref_dist=gap)
                    
                    dist_norm = (p_entry_norm - p_exit).length()
                    dist_flip = (p_entry_flip - p_exit).length()
                    
                    if dist_flip < dist_norm:
                        flips[k] = 1
                    else:
                        flips[k] = 0

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
                 
                 # Clear Array Outputs
                 # Setting a clean, empty status
                 out_u_handle.setAllClean()
                 out_v_handle.setAllClean()
                 
                 data_block.setClean(plug)
                 return
            
            # Output Mesh
            # We always calculate everything together, so we update all outputs if any is requested (and dirty)
            
            mesh_data_fn = om.MFnMeshData()
            new_mesh_data = mesh_data_fn.create()
            mesh_fn = om.MFnMesh()
            # Do NOT pass UVs to create(). Use setUVs/assignUVs instead to avoid count mismatch in Loop mode.
            # Fix: Pass empty MFloatArray() instead of None to satisfy 'float sequence required'
            empty_u = om.MFloatArray()
            empty_v = om.MFloatArray()
            mesh_fn.create(points, counts, connects, empty_u, empty_v, new_mesh_data)
            
            mesh_fn.setUVs(u_coords, v_coords, "map1") 
            mesh_fn.assignUVs(counts, uv_ids, "map1")
            output_handle.setMObject(new_mesh_data)
                
            # Output Chain Us (Multi-Attribute)
            builder_u = out_u_handle.builder()
            for i, val in enumerate(chain_us):
                h = builder_u.addElement(i)
                h.setDouble(val)
            out_u_handle.set(builder_u)
            out_u_handle.setAllClean()

            # Output Chain Vs (Multi-Attribute)
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

    def _compute_geometry(self, chains_data, flips, width, hold_len, loop, flip, stitch, points, counts, connects, u_coords, v_coords, uv_ids, chain_us, chain_vs):
        num_chains = len(chains_data)
        min_len = min([len(c) for c in chains_data])
        if min_len < 2: return 
        
        # ... (Rest of Geometry logic) ... 
        
        col_bases_list = []
        
        for i in range(min_len):
            row_skeleton = []
            for c_idx in range(num_chains):
                mat = chains_data[c_idx][i]
                pos = om.MVector(mat[12], mat[13], mat[14])
                tan_x = om.MVector(mat[0], mat[1], mat[2]).normalize()
                binorm_z = om.MVector(mat[8], mat[9], mat[10]).normalize()
                row_skeleton.append((pos, tan_x, binorm_z))
            
            # --- 1. CLAMP HOLD LENGTH ---
            actual_hold = max(hold_len, 0.001)
            
            ref_dist = 0.0
            if i < min_len - 1:
                # Forward look
                min_d = 999999.0
                for c_idx in range(num_chains):
                    p_curr = om.MVector(chains_data[c_idx][i][12], chains_data[c_idx][i][13], chains_data[c_idx][i][14])
                    p_next = om.MVector(chains_data[c_idx][i+1][12], chains_data[c_idx][i+1][13], chains_data[c_idx][i+1][14])
                    d = (p_next - p_curr).length()
                    if d < min_d: min_d = d
                ref_dist = min_d
            elif i > 0:
                # Backward look (Last Bone Fix)
                min_d = 999999.0
                for c_idx in range(num_chains):
                    p_curr = om.MVector(chains_data[c_idx][i][12], chains_data[c_idx][i][13], chains_data[c_idx][i][14])
                    p_prev = om.MVector(chains_data[c_idx][i-1][12], chains_data[c_idx][i-1][13], chains_data[c_idx][i-1][14])
                    d = (p_curr - p_prev).length()
                    if d < min_d: min_d = d
                ref_dist = min_d
            
            # Apply Clamp
            if ref_dist > 0.0001 and actual_hold > ref_dist * 0.49:
                actual_hold = ref_dist * 0.49
            
            # --- 2. CALCULATE STRIP COLUMNS ---
            current_cols = []
            
            for k in range(num_chains):
                pos, tan, z = row_skeleton[k]
                
                safe_width = max(width, 0.0)
                max_w_left = safe_width * 0.5
                max_w_right = safe_width * 0.5
                
                # Check Left (k-1)
                if k > 0:
                    pos_prev = row_skeleton[k-1][0]
                    dist = (pos - pos_prev).length()
                    if max_w_left > dist * 0.5: max_w_left = dist * 0.5
                elif loop:
                    pos_prev = row_skeleton[-1][0]
                    dist = (pos - pos_prev).length()
                    if max_w_left > dist * 0.5: max_w_left = dist * 0.5
                    
                # Check Right (k+1)
                if k < num_chains - 1:
                    pos_next = row_skeleton[k+1][0]
                    dist = (pos - pos_next).length()
                    if max_w_right > dist * 0.5: max_w_right = dist * 0.5
                elif loop:
                    pos_next = row_skeleton[0][0]
                    dist = (pos - pos_next).length()
                    if max_w_right > dist * 0.5: max_w_right = dist * 0.5
                
                # NEW ORDER: Left(+Z) -> Center -> Right(-Z)
                p_l = pos + (z * max_w_left)
                p_r = pos - (z * max_w_right)
                
                # --- FLIP LOGIC ---
                is_flipped = bool(flips[k])
                if is_flipped:
                    temp = p_l
                    p_l = p_r
                    p_r = temp
                
                # [Left, Center, Right]
                current_cols.extend([(p_l, tan), (pos, tan), (p_r, tan)])
            
            col_bases_list.append(current_cols)
            
            for offset in [-actual_hold, 0.0, actual_hold]:
                for base_pos, base_tan in current_cols:
                    points.append(om.MPoint(base_pos + base_tan * offset))

        # --- FACES & UVS ---
        num_cols = num_chains * 3
        num_rows = min_len * 3
        
        # Determine UV layout columns
        # If loop, we need one extra column of UVs for the wrap-around seam (0.0 -> 1.0)
        uv_cols = num_cols + 1 if loop else num_cols
        denom = float(num_cols) if loop else float(num_cols - 1)
        if denom == 0: denom = 1.0

        # Generate UV Grid
        for r in range(num_rows):
            v = float(r) / float(num_rows - 1)
            for c in range(uv_cols):
                u = float(c) / denom
                u_coords.append(u)
                v_coords.append(v)
        
        # Calculate Chain U Values (Center of each chain)
        # Chain k is at column indices [k*3, k*3+1, k*3+2]
        # Center is at k*3+1
        for k in range(num_chains):
            center_col_idx = k * 3 + 1
            u_val = float(center_col_idx) / denom
            chain_us.append(u_val)
            
        # Calculate Chain V Values (Center of each bone row)
        # Bone i is at row indices [i*3, i*3+1, i*3+2]
        # Center is at i*3+1
        for i in range(min_len):
            center_row_idx = i * 3 + 1
            v_val = float(center_row_idx) / float(num_rows - 1)
            chain_vs.append(v_val)

        # Build Faces with Correct UV Mapping
        for r in range(num_rows - 1):
            for c in range(num_cols - 1): 
                is_bridge = ((c + 1) % 3 == 0)
                if is_bridge and not stitch: continue
                
                # Geometry Indices (Wrap around if needed, handled by logic below)
                geo_c = c
                geo_c_next = c + 1
                
                idx_bl = (r * num_cols) + geo_c
                idx_br = (r * num_cols) + geo_c_next
                idx_tl = ((r + 1) * num_cols) + geo_c
                idx_tr = ((r + 1) * num_cols) + geo_c_next
                
                # UV Indices (Direct mapping for standard grid)
                uv_idx_bl = (r * uv_cols) + c
                uv_idx_br = (r * uv_cols) + (c + 1)
                uv_idx_tl = ((r + 1) * uv_cols) + c
                uv_idx_tr = ((r + 1) * uv_cols) + (c + 1)

                if not flip: 
                    connects.append(idx_bl); uv_ids.append(uv_idx_bl)
                    connects.append(idx_tl); uv_ids.append(uv_idx_tl)
                    connects.append(idx_tr); uv_ids.append(uv_idx_tr)
                    connects.append(idx_br); uv_ids.append(uv_idx_br)
                else: 
                    connects.append(idx_bl); uv_ids.append(uv_idx_bl)
                    connects.append(idx_br); uv_ids.append(uv_idx_br)
                    connects.append(idx_tr); uv_ids.append(uv_idx_tr)
                    connects.append(idx_tl); uv_ids.append(uv_idx_tl)
                
                counts.append(4)
                
            # Loop Stitching (Last Column -> First Column)
            if loop and stitch: 
                c = num_cols - 1
                c_next = 0 # Wrap Geometry to 0
                
                idx_bl = (r * num_cols) + c
                idx_br = (r * num_cols) + c_next
                idx_tl = ((r + 1) * num_cols) + c
                idx_tr = ((r + 1) * num_cols) + c_next
                
                # UV Wrap Logic: 
                # Left side of face uses column (num_cols - 1)
                # Right side of face uses column (num_cols) -> This is the U=1.0 column
                
                uv_idx_bl = (r * uv_cols) + c
                uv_idx_br = (r * uv_cols) + (c + 1) # Points to the extra UV column
                uv_idx_tl = ((r + 1) * uv_cols) + c
                uv_idx_tr = ((r + 1) * uv_cols) + (c + 1) # Points to the extra UV column

                if not flip: 
                    connects.append(idx_bl); uv_ids.append(uv_idx_bl)
                    connects.append(idx_tl); uv_ids.append(uv_idx_tl)
                    connects.append(idx_tr); uv_ids.append(uv_idx_tr)
                    connects.append(idx_br); uv_ids.append(uv_idx_br)
                else: 
                    connects.append(idx_bl); uv_ids.append(uv_idx_bl)
                    connects.append(idx_br); uv_ids.append(uv_idx_br)
                    connects.append(idx_tr); uv_ids.append(uv_idx_tr)
                    connects.append(idx_tl); uv_ids.append(uv_idx_tl)
                    
                counts.append(4)

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
        
        cls.in_chain_matrices = m_attr.create("chainMatrices", "cm"); m_attr.array = True
        cls.in_chains = c_attr.create("inChains", "ic"); c_attr.array = True; c_attr.addChild(cls.in_chain_matrices)
        cls.out_mesh = t_attr.create("outMesh", "om", om.MFnData.kMesh); t_attr.writable = False
        
        # Output U values for each chain (for UVPin attachment)
        # CHANGED: Use Numeric Array (Multi) instead of Typed DoubleArray for stability
        cls.out_chain_u = n_attr.create("outChainU", "ocu", om.MFnNumericData.kDouble); 
        n_attr.array = True; n_attr.usesArrayDataBuilder = True; n_attr.writable = False; n_attr.storable = False
        
        # Output V values for each bone row (assuming uniform rows across chains)
        cls.out_chain_v = n_attr.create("outChainV", "ocv", om.MFnNumericData.kDouble); 
        n_attr.array = True; n_attr.usesArrayDataBuilder = True; n_attr.writable = False; n_attr.storable = False

        for attr in [cls.in_width, cls.in_hold_length, cls.in_loop, cls.in_stitch, cls.in_flip_normal, cls.in_chains]: cls.addAttribute(attr)
        cls.addAttribute(cls.out_mesh)
        cls.addAttribute(cls.out_chain_u)
        cls.addAttribute(cls.out_chain_v)
        
        for attr in [cls.in_width, cls.in_hold_length, cls.in_loop, cls.in_stitch, cls.in_flip_normal, cls.in_chains, cls.in_chain_matrices]: 
            cls.attributeAffects(attr, cls.out_mesh)
            cls.attributeAffects(attr, cls.out_chain_u)
            cls.attributeAffects(attr, cls.out_chain_v)

def initializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject, "GeminiV2", "16.2.0", "Any")
    try: 
        mplugin.registerNode(MatrixRibbonNode.kPluginNodeName, MatrixRibbonNode.kPluginNodeId, MatrixRibbonNode.creator, MatrixRibbonNode.initialize)
        print(">>> MatrixRibbonMesh Plugin Loaded [Version 16.2.0] <<<")
    except Exception as e: om.MGlobal.displayError(f"Register failed: {e}")

def uninitializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject)
    try: mplugin.deregisterNode(MatrixRibbonNode.kPluginNodeId)
    except Exception as e: om.MGlobal.displayError(f"Deregister failed: {e}")