"""
Matrix Ribbon System (MRS) - Plugin Node
Version: 19.0.0
"""

import maya.api.OpenMaya as om
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
    in_axis = None         # constructionAxis enum (0-5)
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
            axis = data_block.inputValue(MatrixRibbonNode.in_axis).asShort()

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

            points = om.MPointArray()
            counts = om.MIntArray()
            connects = om.MIntArray()
            u_coords = om.MFloatArray()
            v_coords = om.MFloatArray()
            uv_ids = om.MIntArray()
            chain_us = om.MDoubleArray()
            chain_vs = om.MDoubleArray()

            if chains_data:
                self._compute_geometry(chains_data, width, hold_len, loop, flip, stitch, axis, points, counts, connects, u_coords, v_coords, uv_ids, chain_us, chain_vs)
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

    def _compute_geometry(self, chains_data, width, hold_len, loop, flip, stitch, axis, points, counts, connects, u_coords, v_coords, uv_ids, chain_us, chain_vs):
        num_chains = len(chains_data)
        if num_chains == 0: return

        chain_lengths = [len(c) for c in chains_data]
        max_len = max(chain_lengths)
        if max_len < 1: return

        # Axis mapping: mode -> (aim_col_offset, width_col_offset) in matrix row-major layout
        # Matrix columns: col0=(0,1,2), col1=(4,5,6), col2=(8,9,10), translation=(12,13,14)
        _axis_map = {
            0: (0, 8),   # X-Aim, Z-Width
            1: (0, 4),   # X-Aim, Y-Width
            2: (4, 8),   # Y-Aim, Z-Width
            3: (4, 0),   # Y-Aim, X-Width
            4: (8, 0),   # Z-Aim, X-Width
            5: (8, 4),   # Z-Aim, Y-Width
        }
        aim_off, width_off = _axis_map.get(axis, (0, 8))

        point_lookup = [-1] * (num_chains * max_len * 9)

        # --- PHASE 1: GENERATE POINTS (Independent Strips) ---

        for c_idx in range(num_chains):
            chain_len = chain_lengths[c_idx]

            # Pre-calculate Skeleton
            chain_skel = []
            for i in range(chain_len):
                mat = chains_data[c_idx][i]
                pos = om.MVector(mat[12], mat[13], mat[14])
                tan = om.MVector(mat[aim_off], mat[aim_off + 1], mat[aim_off + 2])
                binorm = om.MVector(mat[width_off], mat[width_off + 1], mat[width_off + 2])
                chain_skel.append((pos, tan, binorm))

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

                p_l = pos + (z * max_w_left)
                p_r = pos - (z * max_w_right)

                cols = [(p_l, tan), (pos, tan), (p_r, tan)]
                offsets = [-actual_hold, 0.0, actual_hold]

                for r_sub, offset in enumerate(offsets):
                    base_row_idx = i * 3 + r_sub

                    base_pos_l, base_tan_l = cols[0]
                    base_pos_c, base_tan_c = cols[1]
                    base_pos_r, base_tan_r = cols[2]

                    curr_l = base_pos_l + base_tan_l * offset
                    curr_c = base_pos_c + base_tan_c * offset
                    curr_r = base_pos_r + base_tan_r * offset

                    # --- INDEPENDENT POINTS (No Merging) ---
                    id_l = len(points)
                    points.append(om.MPoint(curr_l))
                    id_c = len(points)
                    points.append(om.MPoint(curr_c))
                    id_r = len(points)
                    points.append(om.MPoint(curr_r))

                    # Flat-array lookup: key = c * max_rows * 3 + r * 3 + col
                    base_key = c_idx * max_len * 3 * 3 + base_row_idx * 3
                    point_lookup[base_key] = id_l
                    point_lookup[base_key + 1] = id_c
                    point_lookup[base_key + 2] = id_r

        # --- PHASE 2: UVs & FACES ---

        max_rows = max_len * 3
        denom_u = float(num_chains * 3) if loop else float(num_chains * 3 - 1)
        if denom_u == 0: denom_u = 1.0
        denom_v = float(max_rows - 1)
        if denom_v == 0: denom_v = 1.0

        u_coords.clear()
        v_coords.clear()

        # UV Generation (Grid-based) — precompute v values
        row_width = num_chains * 3
        inv_denom_u = 1.0 / denom_u
        inv_denom_v = 1.0 / denom_v
        v_table = [float(r) * inv_denom_v for r in range(max_rows)]

        for r in range(max_rows):
            v = v_table[r]
            for c in range(num_chains):
                base_u = c * 3
                for col in range(3):
                    u_coords.append(float(base_u + col) * inv_denom_u)
                    v_coords.append(v)

        if loop:
            for r in range(max_rows):
                u_coords.append(1.0)
                v_coords.append(v_table[r])

        for k in range(num_chains):
            chain_us.append(float(k * 3 + 1) * inv_denom_u)
        for i in range(max_len):
            chain_vs.append(float(i * 3 + 1) * inv_denom_v)

        # Precompute constants for UV ID calculation
        main_uvs = row_width * max_rows
        max_rows_x3 = max_len * 3 * 3  # stride per chain in point_lookup

        for r in range(max_rows - 1):
            r1 = r + 1
            for c in range(num_chains):
                c_base = c * max_rows_x3
                r_base = c_base + r * 3
                r1_base = c_base + r1 * 3

                # Check rows exist via flat lookup
                v_bl = point_lookup[r_base]
                v_tl = point_lookup[r1_base]

                if v_bl != -1 and v_tl != -1:
                    v_br = point_lookup[r_base + 1]
                    v_tr = point_lookup[r1_base + 1]

                    # Q1: L-M
                    if flip:
                        connects.append(v_bl); connects.append(v_br); connects.append(v_tr); connects.append(v_tl)
                    else:
                        connects.append(v_bl); connects.append(v_tl); connects.append(v_tr); connects.append(v_br)
                    counts.append(4)

                    uv_00 = r * row_width + c * 3
                    uv_10 = r1 * row_width + c * 3
                    if flip:
                        uv_ids.append(uv_00); uv_ids.append(uv_00 + 1); uv_ids.append(uv_10 + 1); uv_ids.append(uv_10)
                    else:
                        uv_ids.append(uv_00); uv_ids.append(uv_10); uv_ids.append(uv_10 + 1); uv_ids.append(uv_00 + 1)

                    # Q2: M-R
                    v_bl2 = point_lookup[r_base + 1]
                    v_br2 = point_lookup[r_base + 2]
                    v_tl2 = point_lookup[r1_base + 1]
                    v_tr2 = point_lookup[r1_base + 2]

                    if flip:
                        connects.append(v_bl2); connects.append(v_br2); connects.append(v_tr2); connects.append(v_tl2)
                    else:
                        connects.append(v_bl2); connects.append(v_tl2); connects.append(v_tr2); connects.append(v_br2)
                    counts.append(4)

                    if flip:
                        uv_ids.append(uv_00 + 1); uv_ids.append(uv_00 + 2); uv_ids.append(uv_10 + 2); uv_ids.append(uv_10 + 1)
                    else:
                        uv_ids.append(uv_00 + 1); uv_ids.append(uv_10 + 1); uv_ids.append(uv_10 + 2); uv_ids.append(uv_00 + 2)

                # STITCH FACES (Bridge)
                if not stitch: continue

                c_neighbor = c + 1
                is_loop_wrap = False
                if loop and c == num_chains - 1:
                    c_neighbor = 0
                    is_loop_wrap = True

                if c_neighbor < num_chains:
                    cn_base = c_neighbor * max_rows_x3
                    v_br = point_lookup[r_base + 2]
                    v_tr = point_lookup[r1_base + 2]
                    v_bl = point_lookup[cn_base + r * 3]
                    v_tl = point_lookup[cn_base + r1 * 3]

                    if v_br != -1 and v_tr != -1 and v_bl != -1 and v_tl != -1:
                        if flip:
                            connects.append(v_br); connects.append(v_bl); connects.append(v_tl); connects.append(v_tr)
                        else:
                            connects.append(v_br); connects.append(v_tr); connects.append(v_tl); connects.append(v_bl)
                        counts.append(4)

                        uv_br = r * row_width + c * 3 + 2
                        uv_tr = r1 * row_width + c * 3 + 2

                        if is_loop_wrap:
                            uv_bl = main_uvs + r
                            uv_tl = main_uvs + r1
                        else:
                            uv_bl = r * row_width + c_neighbor * 3
                            uv_tl = r1 * row_width + c_neighbor * 3

                        if flip:
                            uv_ids.append(uv_br); uv_ids.append(uv_bl); uv_ids.append(uv_tl); uv_ids.append(uv_tr)
                        else:
                            uv_ids.append(uv_br); uv_ids.append(uv_tr); uv_ids.append(uv_tl); uv_ids.append(uv_bl)

    @classmethod
    def creator(cls): return MatrixRibbonNode()

    @classmethod
    def initialize(cls):
        n_attr = om.MFnNumericAttribute(); m_attr = om.MFnMatrixAttribute()
        t_attr = om.MFnTypedAttribute(); c_attr = om.MFnCompoundAttribute()
        e_attr = om.MFnEnumAttribute()

        cls.in_width = n_attr.create("width", "w", om.MFnNumericData.kFloat, 2.0); n_attr.keyable = True
        cls.in_hold_length = n_attr.create("holdLength", "hl", om.MFnNumericData.kFloat, 0.5); n_attr.keyable = True
        cls.in_loop = n_attr.create("loop", "lp", om.MFnNumericData.kBoolean, False); n_attr.keyable = True
        cls.in_stitch = n_attr.create("stitch", "st", om.MFnNumericData.kBoolean, True); n_attr.keyable = True
        cls.in_flip_normal = n_attr.create("flipNormal", "fn", om.MFnNumericData.kBoolean, False); n_attr.keyable = True
        cls.in_reverse_order = n_attr.create("reverseOrder", "rev", om.MFnNumericData.kBoolean, False); n_attr.keyable = True

        cls.in_axis = e_attr.create("constructionAxis", "ca", 0)
        e_attr.addField("X-Aim, Z-Width", 0)
        e_attr.addField("X-Aim, Y-Width", 1)
        e_attr.addField("Y-Aim, Z-Width", 2)
        e_attr.addField("Y-Aim, X-Width", 3)
        e_attr.addField("Z-Aim, X-Width", 4)
        e_attr.addField("Z-Aim, Y-Width", 5)
        e_attr.keyable = True

        cls.in_chain_matrices = m_attr.create("chainMatrices", "cm"); m_attr.array = True
        cls.in_chains = c_attr.create("inChains", "ic"); c_attr.array = True; c_attr.addChild(cls.in_chain_matrices)
        cls.out_mesh = t_attr.create("outMesh", "om", om.MFnData.kMesh); t_attr.writable = False

        cls.out_chain_u = n_attr.create("outChainU", "ocu", om.MFnNumericData.kDouble);
        n_attr.array = True; n_attr.usesArrayDataBuilder = True; n_attr.writable = False; n_attr.storable = False

        cls.out_chain_v = n_attr.create("outChainV", "ocv", om.MFnNumericData.kDouble);
        n_attr.array = True; n_attr.usesArrayDataBuilder = True; n_attr.writable = False; n_attr.storable = False

        for attr in [cls.in_width, cls.in_hold_length, cls.in_loop, cls.in_stitch, cls.in_flip_normal, cls.in_reverse_order, cls.in_axis, cls.in_chains]: cls.addAttribute(attr)
        cls.addAttribute(cls.out_mesh)
        cls.addAttribute(cls.out_chain_u)
        cls.addAttribute(cls.out_chain_v)

        for attr in [cls.in_width, cls.in_hold_length, cls.in_loop, cls.in_stitch, cls.in_flip_normal, cls.in_reverse_order, cls.in_axis, cls.in_chains, cls.in_chain_matrices]:
            cls.attributeAffects(attr, cls.out_mesh)
            cls.attributeAffects(attr, cls.out_chain_u)
            cls.attributeAffects(attr, cls.out_chain_v)

def initializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject, "MRS", "18.0.0", "Any")
    try: 
        mplugin.registerNode(MatrixRibbonNode.kPluginNodeName, MatrixRibbonNode.kPluginNodeId, MatrixRibbonNode.creator, MatrixRibbonNode.initialize)
    except Exception as e: om.MGlobal.displayError(f"Register failed: {e}")

def uninitializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject)
    try: mplugin.deregisterNode(MatrixRibbonNode.kPluginNodeId)
    except Exception as e: om.MGlobal.displayError(f"Deregister failed: {e}")
