"""
Matrix Ribbon System (MRS) - Rig Builder
Version: 12.1.0
Fix: Capture 'mrsBindPose' BEFORE driving the bone to ensure original pose is saved.
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om
from utils import RigUtils

class RigBuilder:
    NODE_TYPE = "matrixRibbonMesh"

    def create_preview_mesh(self, chains, width=None, hold_length=None, loop=False):
        auto_w, auto_h = RigUtils.calculate_topology_metrics(chains[0])
        w = width if width is not None else auto_w
        hl = hold_length if hold_length is not None else auto_h

        node = cmds.createNode(self.NODE_TYPE, name="preview_ribbon_node")
        cmds.setAttr(f"{node}.width", w)
        cmds.setAttr(f"{node}.holdLength", hl)
        cmds.setAttr(f"{node}.loop", loop)
        
        for i, chain in enumerate(chains):
            for j, bone in enumerate(chain):
                cmds.connectAttr(f"{bone}.worldMatrix[0]", f"{node}.inChains[{i}].chainMatrices[{j}]")
        
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
        if hist: width = cmds.getAttr(f"{hist[0]}.width")

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
            
            if is_single: u = 0.5
            elif loop: u = float(c_idx) / float(num_chains)
            elif has_skirts: u = float(c_idx + 1) / float(num_chains + 1)
            else: u = float(c_idx) / float(num_chains - 1) if num_chains > 1 else 0.5
            
            prev_fk_ctrl = chain_grp
            prev_pin_plug = None

            for i, bone in enumerate(chain):
                v = float(i * 3 + 1) / float(len(chain) * 3 - 1)
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
                        cmds.connectAttr(curr_pin_plug, f"{opm_mult}.matrixIn[0]")
                    else:
                        cmds.connectAttr(curr_pin_plug, f"{opm_mult}.matrixIn[0]")
                        inv_pin = cmds.createNode("inverseMatrix", name=f"{fk_grp}_pinInv")
                        comps["nodes"].append(inv_pin)
                        cmds.connectAttr(prev_pin_plug, f"{inv_pin}.inputMatrix")
                        cmds.connectAttr(f"{inv_pin}.outputMatrix", f"{opm_mult}.matrixIn[1]")
                    
                    cmds.connectAttr(f"{opm_mult}.matrixSum", f"{fk_grp}.offsetParentMatrix")
                    RigUtils.zero_out_local(fk_grp)
                    
                    fk_ctrl = RigUtils.create_control_shape(f"{name}_c{c_idx}_{i}_FK", size=1.0)
                    cmds.parent(fk_ctrl, fk_grp)
                    cmds.setAttr(f"{fk_ctrl}.offsetParentMatrix", list(m_offset), type="matrix")
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
        
        # --- FIX: CAPTURE POSE BEFORE DRIVING ---
        for bone in all_bones:
            if not cmds.attributeQuery("mrsBindPose", node=bone, exists=True):
                cmds.addAttr(bone, longName="mrsBindPose", attributeType="matrix")
            # Capture NOW, while bone is still in original state
            m_bind = cmds.xform(bone, q=True, ws=True, m=True)
            cmds.setAttr(f"{bone}.mrsBindPose", m_bind, type="matrix")
            
        # Drive Bones
        for bone, drv in zip(all_bones, rig_data["drivers"]):
            drv_node = RigUtils.connect_via_opm(drv, bone)
            if drv_node: rig_data["nodes"].append(drv_node)
            
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
        print(f"[MRS] Bind Complete. Bind Pose Snapshot Stored (Pre-Drive).")
        return main_grp