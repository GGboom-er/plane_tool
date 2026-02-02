"""
Matrix Ribbon System (MRS) - Plugin Node
Version: 3.6.0
Author: Gemini / Conductor
Description: 
    Supports Flip Normal attribute and robust Multi-Chain topology.
"""

import maya.api.OpenMaya as om
import sys
import traceback

def maya_useNewAPI():
    pass

class MatrixRibbonNode(om.MPxNode):
    
    kPluginNodeId = om.MTypeId(0x8700D) 
    kPluginNodeName = "matrixRibbonMesh"
    
    in_width = None       
    in_hold_length = None 
    in_loop = None        
    in_flip_normal = None # New Attribute
    in_chains = None      
    in_chain_matrices = None
    out_mesh = None

    def __init__(self):
        om.MPxNode.__init__(self)

    def compute(self, plug, data_block):
        if plug != MatrixRibbonNode.out_mesh:
            return 

        try:
            width = data_block.inputValue(MatrixRibbonNode.in_width).asFloat()
            hold_len = data_block.inputValue(MatrixRibbonNode.in_hold_length).asFloat()
            loop = data_block.inputValue(MatrixRibbonNode.in_loop).asBool()
            flip = data_block.inputValue(MatrixRibbonNode.in_flip_normal).asBool()
            output_handle = data_block.outputValue(MatrixRibbonNode.out_mesh)
            
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

            points = om.MPointArray()
            counts = om.MIntArray()
            connects = om.MIntArray()
            u_coords = om.MFloatArray()
            v_coords = om.MFloatArray()
            uv_ids = om.MIntArray()

            if chains_data:
                self._compute_geometry(chains_data, width, hold_len, loop, flip, points, counts, connects, u_coords, v_coords, uv_ids)
            else:
                 output_handle.setMObject(om.MObject.kNullObj)
                 data_block.setClean(plug)
                 return

            mesh_data_fn = om.MFnMeshData()
            new_mesh_data = mesh_data_fn.create()
            mesh_fn = om.MFnMesh()
            mesh_fn.create(points, counts, connects, u_coords, v_coords, new_mesh_data)
            mesh_fn.setUVs(u_coords, v_coords, "map1") 
            mesh_fn.assignUVs(counts, uv_ids, "map1")

            output_handle.setMObject(new_mesh_data)
            data_block.setClean(plug)
            
        except Exception as e:
            om.MGlobal.displayError(f"[MatrixRibbonNode] Compute Error: {e}")
            traceback.print_exc()

    def _compute_geometry(self, chains_data, width, hold_len, loop, flip, points, counts, connects, u_coords, v_coords, uv_ids):
        num_chains = len(chains_data)
        min_len = min([len(c) for c in chains_data])
        if min_len < 2: return 
        
        is_single = (num_chains == 1)
        is_loop = (loop and num_chains > 1)
        has_skirts = (not is_loop and not is_single and width > 0.001)

        col_bases = []
        for i in range(min_len):
            row_skeleton = []
            for c_idx in range(num_chains):
                mat = chains_data[c_idx][i]
                pos = om.MVector(mat[12], mat[13], mat[14])
                tan_x = om.MVector(mat[0], mat[1], mat[2]).normalize()
                binorm_z = om.MVector(mat[8], mat[9], mat[10]).normalize()
                row_skeleton.append((pos, tan_x, binorm_z))
            
            current_cols = []
            if is_single:
                p, t, z = row_skeleton[0]
                current_cols = [(p - z*(width*0.5), t), (p, t), (p + z*(width*0.5), t)]
            elif is_loop:
                current_cols = [(d[0], d[1]) for d in row_skeleton]
            elif has_skirts:
                p0, t0, z0 = row_skeleton[0]; p1 = row_skeleton[1][0]
                ext_dir_s = (z0 * -1.0) if ((p1-p0)*z0) > 0 else z0
                p_start = p0 + (ext_dir_s * width)
                pN, tN, zN = row_skeleton[-1]; pP = row_skeleton[-2][0]
                ext_dir_e = zN if ((pN-pP)*zN) > 0 else (zN * -1.0)
                p_end = pN + (ext_dir_e * width)
                current_cols = [(p_start, t0)] + [(d[0], d[1]) for d in row_skeleton] + [(p_end, tN)]
            else:
                current_cols = [(d[0], d[1]) for d in row_skeleton]

            for offset in [-hold_len, 0.0, hold_len]:
                for base_pos, base_tan in current_cols:
                    points.append(om.MPoint(base_pos + base_tan * offset))
            if i == 0: num_cols = len(current_cols)

        num_rows = min_len * 3
        for r in range(num_rows - 1):
            for c in range(num_cols):
                if is_loop and c == num_cols - 1: c_next = 0
                else:
                    c_next = c + 1
                    if c_next >= num_cols: continue
                
                v_bl, v_br, v_tl, v_tr = (r*num_cols)+c, (r*num_cols)+c_next, ((r+1)*num_cols)+c, ((r+1)*num_cols)+c_next
                
                # Normal Control Logic
                if not flip:
                    face = [v_bl, v_br, v_tr, v_tl] # CCW
                else:
                    face = [v_bl, v_tl, v_tr, v_br] # CW
                
                for idx in face: connects.append(idx); uv_ids.append(idx)
                counts.append(4)

        for r in range(num_rows):
            for c in range(num_cols):
                denom = float(num_cols) if is_loop else float(num_cols - 1)
                u = float(c) / denom if denom > 0 else 0
                v = float(r) / float(num_rows - 1)
                u_coords.append(u); v_coords.append(v)

    @classmethod
    def creator(cls): return MatrixRibbonNode()

    @classmethod
    def initialize(cls):
        n_attr = om.MFnNumericAttribute(); m_attr = om.MFnMatrixAttribute()
        t_attr = om.MFnTypedAttribute(); c_attr = om.MFnCompoundAttribute()

        cls.in_width = n_attr.create("width", "w", om.MFnNumericData.kFloat, 2.0); n_attr.keyable = True
        cls.in_hold_length = n_attr.create("holdLength", "hl", om.MFnNumericData.kFloat, 0.5); n_attr.keyable = True
        cls.in_loop = n_attr.create("loop", "lp", om.MFnNumericData.kBoolean, False); n_attr.keyable = True
        cls.in_flip_normal = n_attr.create("flipNormal", "fn", om.MFnNumericData.kBoolean, False); n_attr.keyable = True
        cls.in_chain_matrices = m_attr.create("chainMatrices", "cm"); m_attr.array = True
        cls.in_chains = c_attr.create("inChains", "ic"); c_attr.array = True; c_attr.addChild(cls.in_chain_matrices)
        cls.out_mesh = t_attr.create("outMesh", "om", om.MFnData.kMesh); t_attr.writable = False

        for attr in [cls.in_width, cls.in_hold_length, cls.in_loop, cls.in_flip_normal, cls.in_chains]: cls.addAttribute(attr)
        cls.addAttribute(cls.out_mesh)
        for attr in [cls.in_width, cls.in_hold_length, cls.in_loop, cls.in_flip_normal, cls.in_chains]: cls.attributeAffects(attr, cls.out_mesh)

def initializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject, "GeminiV2", "3.6.0", "Any")
    try: mplugin.registerNode(MatrixRibbonNode.kPluginNodeName, MatrixRibbonNode.kPluginNodeId, MatrixRibbonNode.creator, MatrixRibbonNode.initialize)
    except Exception as e: om.MGlobal.displayError(f"Register failed: {e}")

def uninitializePlugin(mobject):
    mplugin = om.MFnPlugin(mobject)
    try: mplugin.deregisterNode(MatrixRibbonNode.kPluginNodeId)
    except Exception as e: om.MGlobal.displayError(f"Deregister failed: {e}")