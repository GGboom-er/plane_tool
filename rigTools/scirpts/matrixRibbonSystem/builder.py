"""
Matrix Ribbon System (MRS) - Rig Builder
Version: 16.2.0
Fix: Removed auto-sort (trust user selection). Retained safe attribute setting.
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om
from utils import RigUtils

class RigBuilder:
    NODE_TYPE = "matrixRibbonMesh"

    def create_preview_mesh(self, chains, width=None, hold_length=None, loop=False, stitch=True):
        # 1. Calculate metrics from the first chain
        auto_w, auto_h = RigUtils.calculate_topology_metrics(chains[0])
        w = width if width is not None else auto_w
        hl = hold_length if hold_length is not None else auto_h

        # 2. Create Node
        node = cmds.createNode(self.NODE_TYPE, name="preview_ribbon_node")
        if not node: raise RuntimeError(f"Failed to create {self.NODE_TYPE}")

        # 3. Safe Set Attributes
        node_str = str(node)
        for attr, val in [("width", w), ("holdLength", hl), ("loop", loop), ("stitch", stitch)]:
            if cmds.attributeQuery(attr, node=node_str, exists=True):
                cmds.setAttr(f"{node_str}.{attr}", val)
        
        # 4. Connect Chains (Strict User Order)
        for i, chain in enumerate(chains):
            for j, bone in enumerate(chain):
                cmds.connectAttr(f"{bone}.worldMatrix[0]", f"{node}.inChains[{i}].chainMatrices[{j}]")
        
        # 5. Output Mesh
        mesh_t = cmds.createNode("transform", name="preview_ribbon_mesh")
        mesh_s = cmds.createNode("mesh", name="preview_ribbon_meshShape", parent=mesh_t)
        cmds.connectAttr(f"{node}.outMesh", f"{mesh_s}.inMesh")
        cmds.sets(mesh_s, edit=True, forceElement="initialShadingGroup")
        return mesh_t, node, w, hl

    def build_rig_structure(self, mesh_transform, chains, name="ribbon", loop=False, enable_fk=True, enable_ik=True):
        uv_pin = cmds.createNode("uvPin", name=f"{name}_uvPin")
        mesh_s = cmds.listRelatives(mesh_transform, shapes=True)[0]
        cmds.connectAttr(f"{mesh_s}.worldMesh[0]", f"{uv_pin}.deformedGeometry")
        cmds.setAttr(f"{uv_pin}.normalAxis", 1) 
        cmds.setAttr(f"{uv_pin}.tangentAxis", 2) 
        
        width = 2.0
        hist = cmds.listConnections(f"{mesh_s}.inMesh", s=True)
        ribbon_node = hist[0] if hist else None
        
        if ribbon_node and cmds.attributeQuery("width", node=ribbon_node, exists=True):
            width = cmds.getAttr(f"{ribbon_node}.width")

        # Attempt to read exact chain U values from the node
        chain_u_values = []
        if ribbon_node and cmds.attributeQuery("outChainU", node=ribbon_node, exists=True):
            chain_u_values = cmds.getAttr(f"{ribbon_node}.outChainU")
            
        # Attempt to read exact chain V values from the node
        chain_v_values = []
        if ribbon_node and cmds.attributeQuery("outChainV", node=ribbon_node, exists=True):
            chain_v_values = cmds.getAttr(f"{ribbon_node}.outChainV")

        rig_grp = cmds.group(empty=True, name=f"{name}_ctrl_grp")
        comps = {"ctrls": [], "groups": [rig_grp], "nodes": [uv_pin], "drivers": []}
        
        cmds.refresh()
        pin_offset = 0
        
        for c_idx, chain in enumerate(chains):
            chain_grp = cmds.group(empty=True, name=f"{name}_chain_{c_idx}_grp", parent=rig_grp)
            comps["groups"].append(chain_grp)
            
            num_chains = len(chains)
            is_single = (num_chains == 1)
            has_skirts = (not loop and not is_single and width > 0.001)
            
            # Smart U Calculation: Use Node Data if available, else exact math fallback
            if chain_u_values and c_idx < len(chain_u_values):
                u = chain_u_values[c_idx]
            else:
                # Fallback: Exact Math matching Plugin Topology (3 cols per chain)
                # Standard: Denom = (num_chains * 3) - 1
                # Loop: Denom = (num_chains * 3)
                center_col = c_idx * 3 + 1
                total_cols = num_chains * 3
                
                if loop:
                    denom_u = float(total_cols)
                else:
                    denom_u = float(total_cols - 1)
                
                u = float(center_col) / denom_u if denom_u > 0 else 0.5
            
            prev_fk_ctrl = chain_grp
            prev_pin_plug = None
            prev_offset_inv = None
            
            # Calculate Min Length for safe V fallback (Plugin truncates to shortest chain)
            min_len = min([len(c) for c in chains]) if chains else 0

            for i, bone in enumerate(chain):
                # Stop processing if we exceed the valid mesh topology length
                if i >= min_len: break

                # Smart V Calculation: Use Node Data if available, else exact math fallback
                if chain_v_values and i < len(chain_v_values):
                    v = chain_v_values[i]
                else:
                    # Fallback: Exact Math matching Plugin Topology (3 rows per bone)
                    total_rows = min_len * 3
                    denom_v = float(total_rows - 1)
                    center_row = i * 3 + 1
                    v = float(center_row) / denom_v if denom_v > 0 else 0.5
                
                idx = pin_offset + i
                cmds.setAttr(f"{uv_pin}.coordinate[{idx}].coordinateU", u)
                cmds.setAttr(f"{uv_pin}.coordinate[{idx}].coordinateV", v)
                
                curr_pin_plug = f"{uv_pin}.outputMatrix[{idx}]"
                m_pin_init = om.MMatrix(cmds.getAttr(curr_pin_plug))
                m_bone_init = om.MMatrix(cmds.xform(bone, q=True, ws=True, m=True))
                m_offset = m_bone_init * m_pin_init.inverse()
                
                current_driver = None
                
                if enable_fk:
                    fk_grp = cmds.group(empty=True, name=f"{name}_c{c_idx}_{i}_FK_Grp")
                    cmds.parent(fk_grp, prev_fk_ctrl)
                    comps["groups"].append(fk_grp)
                    
                    opm_mult = cmds.createNode("multMatrix", name=f"{fk_grp}_OPM")
                    comps["nodes"].append(opm_mult)
                    
                    if i == 0:
                        cmds.setAttr(f"{opm_mult}.matrixIn[0]", list(m_offset), type="matrix")
                        cmds.connectAttr(curr_pin_plug, f"{opm_mult}.matrixIn[1]")
                    else:
                        cmds.setAttr(f"{opm_mult}.matrixIn[0]", list(m_offset), type="matrix")
                        cmds.connectAttr(curr_pin_plug, f"{opm_mult}.matrixIn[1]")
                        inv_pin = cmds.createNode("inverseMatrix", name=f"{fk_grp}_pinInv")
                        comps["nodes"].append(inv_pin)
                        cmds.connectAttr(prev_pin_plug, f"{inv_pin}.inputMatrix")
                        cmds.connectAttr(f"{inv_pin}.outputMatrix", f"{opm_mult}.matrixIn[2]")
                        cmds.setAttr(f"{opm_mult}.matrixIn[3]", list(prev_offset_inv), type="matrix")
                    
                    cmds.connectAttr(f"{opm_mult}.matrixSum", f"{fk_grp}.offsetParentMatrix")
                    RigUtils.zero_out_local(fk_grp)
                    
                    fk_ctrl = RigUtils.create_control_shape(f"{name}_c{c_idx}_{i}_FK", size=1.0)
                    cmds.parent(fk_ctrl, fk_grp)
                    RigUtils.zero_out_local(fk_ctrl)
                    comps["ctrls"].append(fk_ctrl)
                    current_driver = fk_ctrl
                    
                    if enable_ik:
                        ik_grp = cmds.group(empty=True, name=f"{name}_c{c_idx}_{i}_IK_Grp")
                        cmds.parent(ik_grp, fk_ctrl)
                        RigUtils.zero_out_local(ik_grp)
                        comps["groups"].append(ik_grp)
                        
                        ik_ctrl = RigUtils.create_control_shape(f"{name}_c{c_idx}_{i}_IK", shape_type="square", size=0.6)
                        cmds.parent(ik_ctrl, ik_grp)
                        RigUtils.zero_out_local(ik_ctrl)
                        cmds.setAttr(f"{ik_ctrl}.overrideColor", 13)
                        comps["ctrls"].append(ik_ctrl)
                        current_driver = ik_ctrl
                    
                    prev_fk_ctrl = fk_ctrl
                    prev_pin_plug = curr_pin_plug
                    prev_offset_inv = m_offset.inverse()

                else:
                    ik_grp = cmds.group(empty=True, name=f"{name}_c{c_idx}_{i}_IK_Grp")
                    cmds.parent(ik_grp, chain_grp)
                    comps["groups"].append(ik_grp)
                    
                    cmds.connectAttr(curr_pin_plug, f"{ik_grp}.offsetParentMatrix")
                    RigUtils.zero_out_local(ik_grp)
                    
                    ik_ctrl = RigUtils.create_control_shape(f"{name}_c{c_idx}_{i}_IK", shape_type="square", size=0.6)
                    cmds.parent(ik_ctrl, ik_grp)
                    cmds.setAttr(f"{ik_ctrl}.offsetParentMatrix", list(m_offset), type="matrix")
                    RigUtils.zero_out_local(ik_ctrl)
                    cmds.setAttr(f"{ik_ctrl}.overrideColor", 13)
                    comps["ctrls"].append(ik_ctrl)
                    current_driver = ik_ctrl

                if current_driver: comps["drivers"].append(current_driver)
                
            pin_offset += len(chain)
            
        return comps

    def finalize_bind(self, preview_mesh, chains, enable_fk=True, enable_ik=True):
        name = chains[0][0] + "_rig"
        static_mesh = cmds.duplicate(preview_mesh, name=f"{name}_mesh")[0]
        cmds.delete(static_mesh, ch=True)
        
        rig_data = self.build_rig_structure(static_mesh, chains, name=name, 
                                          enable_fk=enable_fk, enable_ik=enable_ik)
        
        all_bones = [b for c in chains for b in c]
        for bone, drv in zip(all_bones, rig_data["drivers"]):
            drv_node = RigUtils.connect_via_opm(drv, bone)
            if drv_node: rig_data["nodes"].append(drv_node)
            
            if not cmds.attributeQuery("mrsBindPose", node=bone, exists=True):
                cmds.addAttr(bone, longName="mrsBindPose", attributeType="matrix")
            m_bind = cmds.xform(bone, q=True, ws=True, m=True)
            cmds.setAttr(f"{bone}.mrsBindPose", m_bind, type="matrix")
            
        main_grp = cmds.group(static_mesh, rig_data["groups"][0], name=f"{name}_grp")
        cmds.setAttr(f"{static_mesh}.template", 1)
        rig_data["groups"].append(main_grp)
        
        sets = {}
        for s_type in ["Rig", "Control", "Group", "Node", "Geo", "Jnt"]:
            s_name = f"{name}_{s_type}_Set"
            if cmds.objExists(s_name): cmds.delete(s_name)
            sets[s_type] = cmds.sets(name=s_name, empty=True)
        
        if rig_data["ctrls"]: cmds.sets(rig_data["ctrls"], add=sets["Control"])
        if rig_data["groups"]: cmds.sets(rig_data["groups"], add=sets["Group"])
        if rig_data["nodes"]: cmds.sets(rig_data["nodes"], add=sets["Node"])
        cmds.sets(static_mesh, add=sets["Geo"])
        cmds.sets(all_bones, add=sets["Jnt"])
        
        sub_sets = [sets["Control"], sets["Group"], sets["Node"], sets["Geo"], sets["Jnt"]]
        cmds.sets(sub_sets, add=sets["Rig"])
        
        if cmds.objExists(preview_mesh): cmds.delete(preview_mesh)
        print(f"[MRS] Bind Complete.")
        return main_grp
