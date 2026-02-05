"""
Matrix Ribbon System (MRS) - Rig Builder
Version: 17.2.0
Optimized: Modular scale logic, cleaner architecture.
"""
import maya.cmds as cmds
import json
from utils import RigUtils, MrsNaming

class RigBuilder:
    NODE_TYPE = "matrixRibbonMesh"

    def create_preview_mesh(self, chains: list, base_name: str = "Ribbon", width: float = None, hold_length: float = None, loop: bool = False, stitch: bool = True):
        auto_w, auto_h = RigUtils.calculate_topology_metrics(chains[0])
        w = width if width is not None else auto_w
        hl = hold_length if hold_length is not None else auto_h

        clean_base = base_name.replace(":", "_")
        node_name = f"{clean_base}{MrsNaming.NODE_PREVIEW}"
        mesh_t_name = f"{clean_base}{MrsNaming.MESH_PREVIEW}"
        mesh_s_name = f"{mesh_t_name}Shape"

        node = cmds.createNode(self.NODE_TYPE, name=node_name)
        
        cmds.addAttr(node, longName=MrsNaming.ATTR_BASE_NAME, dataType="string")
        cmds.setAttr(f"{node}.{MrsNaming.ATTR_BASE_NAME}", base_name, type="string")
        
        try:
            chains_json = json.dumps(chains)
            cmds.addAttr(node, longName=MrsNaming.ATTR_CHAINS_DATA, dataType="string")
            cmds.setAttr(f"{node}.{MrsNaming.ATTR_CHAINS_DATA}", chains_json, type="string")
        except: pass

        for attr, val in [(MrsNaming.ATTR_WIDTH, w), (MrsNaming.ATTR_HOLD_LENGTH, hl), (MrsNaming.ATTR_LOOP, loop), (MrsNaming.ATTR_STITCH, stitch)]:
            if cmds.attributeQuery(attr, node=node, exists=True):
                cmds.setAttr(f"{node}.{attr}", val)
        
        for i, chain in enumerate(chains):
            for j, bone in enumerate(chain):
                cmds.connectAttr(f"{bone}.worldMatrix[0]", f"{node}.inChains[{i}].chainMatrices[{j}]")
        
        mesh_t = cmds.createNode("transform", name=mesh_t_name)
        mesh_s = cmds.createNode("mesh", name=mesh_s_name, parent=mesh_t)
        cmds.connectAttr(f"{node}.outMesh", f"{mesh_s}.inMesh")
        cmds.sets(mesh_s, edit=True, forceElement="initialShadingGroup")
        
        if not cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=mesh_t, exists=True):
            cmds.addAttr(mesh_t, longName=MrsNaming.ATTR_BASE_NAME, dataType="string")
        cmds.setAttr(f"{mesh_t}.{MrsNaming.ATTR_BASE_NAME}", base_name, type="string")
        
        self._bake_uv_data(node, mesh_t)
        
        return mesh_t, node, w, hl

    def _bake_uv_data(self, node, mesh_transform):
        for attr, store_name in [("outChainU", MrsNaming.ATTR_STORED_U), ("outChainV", MrsNaming.ATTR_STORED_V)]:
            if cmds.attributeQuery(attr, node=node, exists=True):
                vals = cmds.getAttr(f"{node}.{attr}")
                if vals:
                    flat_vals = []
                    if isinstance(vals, (list, tuple)):
                        def _flatten(lst):
                            for item in lst:
                                if isinstance(item, (list, tuple)): _flatten(item)
                                else: flat_vals.append(item)
                        _flatten(vals)
                    else: flat_vals.append(vals)
                    
                    flat_vals = [float(x) for x in flat_vals]

                    if not cmds.attributeQuery(store_name, node=mesh_transform, exists=True):
                        cmds.addAttr(mesh_transform, longName=store_name, dataType="doubleArray")
                    cmds.setAttr(f"{mesh_transform}.{store_name}", flat_vals, type="doubleArray")
        
        rev_attr = MrsNaming.ATTR_REVERSE_ORDER
        store_rev = MrsNaming.ATTR_MRS_REVERSE
        if cmds.attributeQuery(rev_attr, node=node, exists=True):
            val = cmds.getAttr(f"{node}.{rev_attr}")
            if not cmds.attributeQuery(store_rev, node=mesh_transform, exists=True):
                cmds.addAttr(mesh_transform, longName=store_rev, attributeType="bool")
            cmds.setAttr(f"{mesh_transform}.{store_rev}", val)

    def build_rig_structure(self, mesh_transform: str, chains: list, name: str = "Ribbon", loop: bool = False, enable_fk: bool = True, enable_ik: bool = True, existing_uvpin: str = None, parent_object: str = None) -> dict:
        clean_name = name.replace(":", "_")
        
        rig_width = 2.0
        if cmds.attributeQuery(MrsNaming.ATTR_WIDTH, node=mesh_transform, exists=True):
            rig_width = cmds.getAttr(f"{mesh_transform}.{MrsNaming.ATTR_WIDTH}")
        else:
            hist = cmds.listConnections(f"{mesh_transform}.inMesh", s=True) or []
            if hist and cmds.attributeQuery(MrsNaming.ATTR_WIDTH, node=hist[0], exists=True):
                rig_width = cmds.getAttr(f"{hist[0]}.{MrsNaming.ATTR_WIDTH}")

        uv_pin, u_vals, v_vals = self._setup_uv_pin(mesh_transform, clean_name, chains, loop, existing_uvpin)
        
        rig_grp = self._ensure_group(f"{clean_name}{MrsNaming.GRP_CTRL}")
        comps = {"ctrls": [], "groups": [rig_grp], "nodes": [uv_pin], "drivers": []}
        
        if not enable_fk:
            self._preserve_ik_offsets(chains, clean_name, rig_grp)

        pin_offset = 0
        for c_idx, chain in enumerate(chains):
            chain_grp = self._ensure_group(f"{clean_name}_{RigUtils.get_alpha_index(c_idx)}{MrsNaming.GRP_MAIN}", parent=rig_grp)
            if chain_grp not in comps["groups"]: comps["groups"].append(chain_grp)
            
            prev_fk_ctrl = chain_grp
            prev_fk_grp = None
            prev_pin_plug = None
            chain_root_fk = None 
            
            for i, bone in enumerate(chain):
                idx = pin_offset + i
                u = u_vals[c_idx] if u_vals and c_idx < len(u_vals) else 0.5
                curr_pin_plug = f"{uv_pin}.outputMatrix[{idx}]"
                
                ctx = {
                    "base": clean_name, "c": c_idx, "i": i, 
                    "pin": curr_pin_plug, "prev_pin": prev_pin_plug,
                    "prev_fk": prev_fk_ctrl, "prev_fk_grp": prev_fk_grp, "chain_grp": chain_grp,
                    "width": rig_width, "parent_object": parent_object
                }
                
                current_driver = None
                
                if enable_fk:
                    fk_res = self._build_fk_component(ctx, comps)
                    prev_fk_ctrl = fk_res["ctrl"]
                    prev_fk_grp = fk_res["grp"]
                    current_driver = fk_res["ctrl"]
                    
                    if i == 0:
                        chain_root_fk = fk_res["ctrl"]
                        if not cmds.attributeQuery(MrsNaming.ATTR_SHOW_IK, node=chain_root_fk, exists=True):
                            cmds.addAttr(chain_root_fk, longName=MrsNaming.ATTR_SHOW_IK, attributeType="bool", keyable=True, defaultValue=1)
                    else:
                        if chain_root_fk and not cmds.attributeQuery(MrsNaming.ATTR_SHOW_IK, node=fk_res["ctrl"], exists=True):
                            cmds.addAttr(fk_res["ctrl"], longName=MrsNaming.ATTR_SHOW_IK, proxy=f"{chain_root_fk}.{MrsNaming.ATTR_SHOW_IK}")
                else:
                    self._clean_fk_component(ctx)

                if enable_ik:
                    parent = prev_fk_ctrl if enable_fk else chain_grp
                    ik_res = self._build_ik_component(ctx, comps, parent, enable_fk)
                    current_driver = ik_res["ctrl"]
                    
                    if chain_root_fk:
                        cmds.connectAttr(f"{chain_root_fk}.{MrsNaming.ATTR_SHOW_IK}", f"{ik_res['grp']}.visibility", force=True)
                else:
                    self._clean_ik_component(ctx)
                
                if current_driver: comps["drivers"].append(current_driver)
                prev_pin_plug = curr_pin_plug
                
            pin_offset += len(chain)
            
        return comps

    def _setup_uv_pin(self, mesh_transform, clean_name, chains, loop, existing_uvpin):
        mesh_s = cmds.listRelatives(mesh_transform, shapes=True)[0]
        
        if existing_uvpin and cmds.objExists(existing_uvpin):
            uv_pin = existing_uvpin
        else:
            uv_pin = cmds.createNode("uvPin", name=f"{clean_name}_{MrsNaming.UVPIN}")
            cmds.connectAttr(f"{mesh_s}.worldMesh[0]", f"{uv_pin}.deformedGeometry")
            cmds.setAttr(f"{uv_pin}.normalAxis", 1); cmds.setAttr(f"{uv_pin}.tangentAxis", 2)

        u_vals, v_vals = self._get_stored_uvs(mesh_transform, mesh_s)
        
        is_reversed = RigUtils.get_reverse_state(mesh_transform)

        num_chains = len(chains)
        max_len = max([len(c) for c in chains]) if chains else 0
        
        pin_idx = 0
        final_u = []
        final_v = []
        
        for c_idx, chain in enumerate(chains):
            target_u_idx = (num_chains - 1 - c_idx) if is_reversed else c_idx
            
            if u_vals and target_u_idx < len(u_vals):
                u = u_vals[target_u_idx]
            else:
                denom = float(num_chains * 3) if loop else float(num_chains * 3 - 1)
                base_idx = target_u_idx
                u = float(base_idx * 3 + 1) / denom if denom > 0 else 0.5
            final_u.append(u)
            
            for i in range(len(chain)):
                if v_vals and pin_idx < len(v_vals): v = v_vals[pin_idx]
                else:
                    denom = float(max_len * 3 - 1)
                    v = float(i * 3 + 1) / denom if denom > 0 else 0.5
                
                cmds.setAttr(f"{uv_pin}.coordinate[{pin_idx}].coordinateU", u)
                cmds.setAttr(f"{uv_pin}.coordinate[{pin_idx}].coordinateV", v)
                pin_idx += 1
                
        return uv_pin, final_u, final_v

    def _get_stored_uvs(self, mesh, shape):
        u, v = [], []
        if cmds.attributeQuery(MrsNaming.ATTR_STORED_U, node=mesh, exists=True):
            u = cmds.getAttr(f"{mesh}.{MrsNaming.ATTR_STORED_U}")
        if cmds.attributeQuery(MrsNaming.ATTR_STORED_V, node=mesh, exists=True):
            v = cmds.getAttr(f"{mesh}.{MrsNaming.ATTR_STORED_V}")
        if not u or not v:
            hist = cmds.listConnections(f"{shape}.inMesh", s=True)
            node = hist[0] if hist else None
            if node:
                if not u and cmds.attributeQuery("outChainU", node=node, exists=True):
                    u = cmds.getAttr(f"{node}.outChainU")
                if not v and cmds.attributeQuery("outChainV", node=node, exists=True):
                    v = cmds.getAttr(f"{node}.outChainV")
        
        if u and isinstance(u[0], (list, tuple)): u = [x[0] for x in u]
        if v and isinstance(v[0], (list, tuple)): v = [x[0] for x in v]
        return u, v

    def _preserve_ik_offsets(self, chains, clean_name, rig_grp):
        for c_idx, chain in enumerate(chains):
            for i in range(len(chain)):
                ik_grp = RigUtils.generate_name(clean_name, c_idx, i, MrsNaming.IK_OFFSET)
                if cmds.objExists(ik_grp):
                    if cmds.listRelatives(ik_grp, parent=True) != [rig_grp]:
                        try: cmds.parent(ik_grp, rig_grp)
                        except: pass

    def _build_fk_component(self, ctx, comps):
        grp_name = RigUtils.generate_name(ctx["base"], ctx["c"], ctx["i"], MrsNaming.FK_OFFSET)
        ctrl_name = RigUtils.generate_name(ctx["base"], ctx["c"], ctx["i"], MrsNaming.FK_CTRL)
        
        grp = self._ensure_group(grp_name, parent=ctx["prev_fk"])
        comps["groups"].append(grp)
        
        if ctx["i"] == 0:
            self._connect_opm(ctx["pin"], grp)
        else:
            self._connect_opm_relative(ctx["pin"], ctx["prev_pin"], grp, comps["nodes"])
            
        RigUtils.zero_out_local(grp)
        
        size = ctx["width"] * 1.2
        ctrl = self._ensure_control(ctrl_name, grp, size, "circle")
        comps["ctrls"].append(ctrl)
        
        return {"grp": grp, "ctrl": ctrl}

    def _clean_fk_component(self, ctx):
        grp_name = RigUtils.generate_name(ctx["base"], ctx["c"], ctx["i"], MrsNaming.FK_OFFSET)
        if cmds.objExists(grp_name):
            RigUtils.delete_opm_nodes(grp_name)
            cmds.delete(grp_name)

    def _build_ik_component(self, ctx, comps, parent, is_fk_active):
        grp_name = RigUtils.generate_name(ctx["base"], ctx["c"], ctx["i"], MrsNaming.IK_OFFSET)
        ctrl_name = RigUtils.generate_name(ctx["base"], ctx["c"], ctx["i"], MrsNaming.IK_CTRL)
        
        grp = self._ensure_group(grp_name, parent=parent)
        comps["groups"].append(grp)
        
        # Reset Visibility: Ensure visible by default (Fix for FIK -> Pure IK transition)
        v_plug = f"{grp}.visibility"
        if cmds.connectionInfo(v_plug, isDestination=True):
            src = cmds.connectionInfo(v_plug, sourceFromDestination=True)
            cmds.disconnectAttr(src, v_plug)
        try: cmds.setAttr(v_plug, 1)
        except: pass
        
        if is_fk_active:
            RigUtils.delete_opm_nodes(grp)
            RigUtils.zero_out_local(grp)
        else:
            RigUtils.delete_opm_nodes(grp)
            cmds.connectAttr(ctx["pin"], f"{grp}.offsetParentMatrix", force=True)
            RigUtils.zero_out_local(grp)
            
        size = (ctx["width"] * 1.2) * 0.6 
        ctrl = self._ensure_control(ctrl_name, grp, size, "square")
        comps["ctrls"].append(ctrl)
        
        return {"grp": grp, "ctrl": ctrl}

    def _clean_ik_component(self, ctx):
        grp_name = RigUtils.generate_name(ctx["base"], ctx["c"], ctx["i"], MrsNaming.IK_OFFSET)
        if cmds.objExists(grp_name):
            RigUtils.delete_opm_nodes(grp_name)
            cmds.delete(grp_name)

    def _connect_opm(self, source_plug, target_node):
        cmds.connectAttr(source_plug, f"{target_node}.offsetParentMatrix", force=True)

    def _connect_opm_relative(self, curr_pin, prev_pin, target_node, node_list):
        opm_name = f"{target_node}_OPM"
        
        if cmds.objExists(opm_name):
            try: cmds.delete(opm_name)
            except: pass
            
        opm = cmds.createNode("multMatrix", name=opm_name)
        node_list.append(opm)
        
        cmds.connectAttr(curr_pin, f"{opm}.matrixIn[0]")
        
        inv = cmds.createNode("inverseMatrix", name=f"{target_node}_PinInv")
        node_list.append(inv)
        cmds.connectAttr(prev_pin, f"{inv}.inputMatrix", force=True)
        cmds.connectAttr(f"{inv}.outputMatrix", f"{opm}.matrixIn[1]")
        
        cmds.connectAttr(f"{opm}.matrixSum", f"{target_node}.offsetParentMatrix", force=True)

    def _ensure_group(self, name, parent=None):
        if not cmds.objExists(name):
            grp = cmds.group(empty=True, name=name)
        else: grp = name
        
        if parent:
            curr_p = cmds.listRelatives(grp, parent=True)
            if not curr_p or curr_p[0] != parent:
                try: cmds.parent(grp, parent)
                except: pass
        return grp

    def _ensure_control(self, name, parent, size, shape_type):
        if not cmds.objExists(name):
            ctrl = RigUtils.create_control_shape(name, size=size, shape_type=shape_type)
        else: ctrl = name
        
        curr_p = cmds.listRelatives(ctrl, parent=True)
        if not curr_p or curr_p[0] != parent:
            cmds.parent(ctrl, parent)
        
        RigUtils.zero_out_local(ctrl)
        
        cmds.setAttr(f"{ctrl}.v", lock=True, keyable=False, channelBox=False)
        
        return ctrl

    def _setup_follow_mesh(self, preview_mesh, clean_base, base_name, ribbon_node):
        follow_mesh = cmds.duplicate(preview_mesh, name=f"{clean_base}{MrsNaming.MESH_FOLLOW}")[0]
        cmds.delete(follow_mesh, ch=True)
        RigUtils.zero_out_local(follow_mesh)
        cmds.setAttr(f"{follow_mesh}.{MrsNaming.ATTR_INHERITS_XFORM}", 0)
        
        rev_val = RigUtils.get_reverse_state(ribbon_node) if ribbon_node else RigUtils.get_reverse_state(preview_mesh)
        if rev_val:
            if not cmds.attributeQuery(MrsNaming.ATTR_MRS_REVERSE, node=follow_mesh, exists=True):
                cmds.addAttr(follow_mesh, longName=MrsNaming.ATTR_MRS_REVERSE, attributeType="bool")
            cmds.setAttr(f"{follow_mesh}.{MrsNaming.ATTR_MRS_REVERSE}", rev_val)
        
        if ribbon_node:
            if not cmds.attributeQuery(MrsNaming.ATTR_DRIVER_CONN, node=follow_mesh, exists=True):
                cmds.addAttr(follow_mesh, longName=MrsNaming.ATTR_DRIVER_CONN, attributeType="message")
            cmds.connectAttr(f"{ribbon_node}.message", f"{follow_mesh}.{MrsNaming.ATTR_DRIVER_CONN}", force=True)
        
        if not cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=follow_mesh, exists=True):
            cmds.addAttr(follow_mesh, longName=MrsNaming.ATTR_BASE_NAME, dataType="string")
        cmds.setAttr(f"{follow_mesh}.{MrsNaming.ATTR_BASE_NAME}", base_name, type="string")
        
        return follow_mesh

    def _cleanup_scale_connections(self, chains, clean_base):
        """Disconnects existing scale inputs from all control groups to prevent conflicts."""
        for c_idx, chain in enumerate(chains):
            for i in range(len(chain)):
                for suffix in [MrsNaming.FK_OFFSET, MrsNaming.IK_OFFSET]:
                    grp = RigUtils.generate_name(clean_base, c_idx, i, suffix)
                    if cmds.objExists(grp):
                        scale_plug = f"{grp}.scale"
                        if cmds.connectionInfo(scale_plug, isDestination=True):
                            src = cmds.connectionInfo(scale_plug, sourceFromDestination=True)
                            cmds.disconnectAttr(src, scale_plug)
                        try: cmds.setAttr(scale_plug, 1, 1, 1)
                        except: pass

    def _connect_scale_driver(self, dcm, chains, enable_fk, enable_ik, clean_base):
        """Connects parent scale to specific groups based on rig mode."""
        if enable_fk:
            for c_idx, chain in enumerate(chains):
                for i in range(len(chain)):
                    # FK Mode: Connect scale to the ROOT of each FK chain only.
                    # Children inherit scale naturally via hierarchy.
                    if i == 0:
                        fk_grp = RigUtils.generate_name(clean_base, c_idx, i, MrsNaming.FK_OFFSET)
                        if cmds.objExists(fk_grp):
                            cmds.connectAttr(f"{dcm}.outputScale", f"{fk_grp}.scale", force=True)
        
        if enable_ik and not enable_fk:
            for c_idx, chain in enumerate(chains):
                for i in range(len(chain)):
                    # Pure IK Mode: Connect scale to ALL IK offsets (no hierarchy inheritance)
                    ik_grp = RigUtils.generate_name(clean_base, c_idx, i, MrsNaming.IK_OFFSET)
                    if cmds.objExists(ik_grp):
                        cmds.connectAttr(f"{dcm}.outputScale", f"{ik_grp}.scale", force=True)

    def finalize_bind(self, preview_mesh: str, chains: list, enable_fk: bool = True, enable_ik: bool = True, existing_ribbon_node: str = None, existing_base_name: str = None, update_mode: bool = False, existing_follow_mesh: str = None, passed_uvpin: str = None, parent_object: str = None) -> str:
        
        base_name = existing_base_name if existing_base_name else "Ribbon"
        follow_mesh = None
        uv_pin = None
        
        if update_mode and existing_follow_mesh:
             follow_mesh = existing_follow_mesh
             if passed_uvpin: uv_pin = passed_uvpin
             else:
                 shapes = cmds.listRelatives(follow_mesh, shapes=True) or []
                 if shapes:
                     conns = cmds.listConnections(f"{shapes[0]}.worldMesh", type="uvPin")
                     if conns: uv_pin = conns[0]
             
             if not uv_pin: raise RuntimeError("UVPin missing.")
             
             if not cmds.attributeQuery(MrsNaming.ATTR_STORED_U, node=follow_mesh, exists=True):
                 self._migrate_metadata(follow_mesh)
             
        elif existing_ribbon_node:
            ribbon_node = existing_ribbon_node
        else:
            if not preview_mesh: raise RuntimeError("No Preview Mesh.")
            
            hist = cmds.listConnections(f"{preview_mesh}.inMesh", s=True)
            ribbon_node = hist[0] if hist else None

            if cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=preview_mesh, exists=True):
                base_name = cmds.getAttr(f"{preview_mesh}.{MrsNaming.ATTR_BASE_NAME}")
            elif ribbon_node and cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=ribbon_node, exists=True):
                base_name = cmds.getAttr(f"{ribbon_node}.{MrsNaming.ATTR_BASE_NAME}")

        clean_base = base_name.replace(":", "_")
        
        if not update_mode:
            follow_mesh = self._setup_follow_mesh(preview_mesh, clean_base, base_name, ribbon_node)

        rig_data = self.build_rig_structure(follow_mesh, chains, name=base_name, 
                                          enable_fk=enable_fk, enable_ik=enable_ik, existing_uvpin=uv_pin, parent_object=parent_object)
        
        if parent_object and cmds.objExists(parent_object):
            dcm = cmds.createNode("decomposeMatrix", name=f"{clean_base}_Parent_DCM")
            cmds.connectAttr(f"{parent_object}.worldMatrix[0]", f"{dcm}.inputMatrix", force=True)
            rig_data["nodes"].append(dcm)
            
            self._cleanup_scale_connections(chains, clean_base)
            self._connect_scale_driver(dcm, chains, enable_fk, enable_ik, clean_base)

        main_grp = self._ensure_group(f"{clean_base}{MrsNaming.GRP_MAIN}")
        if cmds.attributeQuery("inheritsTransform", node=main_grp, exists=True):
            cmds.setAttr(f"{main_grp}.inheritsTransform", 0)
        
        jnt_grp = f"{clean_base}{MrsNaming.GRP_JNT}"
        
        target_jnt_parent = None
        if parent_object and cmds.objExists(parent_object):
            target_jnt_parent = parent_object
        elif not update_mode:
            jnt_grp = self._ensure_group(jnt_grp, parent=main_grp)
            rig_data["groups"].append(jnt_grp)
            target_jnt_parent = jnt_grp
            
        if target_jnt_parent:
            roots = [c[0] for c in chains]
            self._parent_joints_safely(roots, target_jnt_parent)

        if not update_mode:
            cmds.parent(follow_mesh, main_grp)
            cmds.setAttr(f"{follow_mesh}.visibility", 0)
            
        try: cmds.parent(rig_data["groups"][0], main_grp)
        except: pass
        
        rig_data["groups"].append(main_grp)

        all_bones = [b for c in chains for b in c]

        for bone, drv in zip(all_bones, rig_data["drivers"]):
            opm = RigUtils.connect_via_opm(drv, bone, maintain_offset=False)
            if opm: rig_data["nodes"].append(opm)
            
            if not cmds.attributeQuery(MrsNaming.ATTR_BIND_POSE, node=bone, exists=True):
                cmds.addAttr(bone, longName=MrsNaming.ATTR_BIND_POSE, attributeType="matrix")
            m_bind = cmds.xform(bone, q=True, ws=True, m=True)
            cmds.setAttr(f"{bone}.{MrsNaming.ATTR_BIND_POSE}", m_bind, type="matrix")

        self._organize_sets(clean_base, rig_data, follow_mesh, all_bones, update_mode)
        
        if not update_mode and preview_mesh and cmds.objExists(preview_mesh):
            cmds.delete(preview_mesh)
            
        print(f"[MRS] Bind Complete: {base_name}")
        return main_grp

    def _parent_joints_safely(self, roots, jnt_grp):
        for root in roots:
            if not cmds.objExists(root): continue
            parents = cmds.listRelatives(root, parent=True)
            if parents and parents[0] == jnt_grp: continue
            
            m = cmds.xform(root, q=True, ws=True, m=True)
            jo = cmds.getAttr(f"{root}.jointOrient")[0]
            ra = cmds.getAttr(f"{root}.rotateAxis")[0]
            ssc = cmds.getAttr(f"{root}.segmentScaleCompensate")
            
            try: cmds.parent(root, jnt_grp)
            except: pass
            
            cmds.setAttr(f"{root}.jointOrient", *jo)
            cmds.setAttr(f"{root}.rotateAxis", *ra)
            cmds.setAttr(f"{root}.segmentScaleCompensate", ssc)
            cmds.xform(root, ws=True, m=m)

    def _migrate_metadata(self, follow_mesh):
        drivers = []
        if cmds.attributeQuery(MrsNaming.ATTR_DRIVER_CONN, node=follow_mesh, exists=True):
            drivers = cmds.listConnections(f"{follow_mesh}.{MrsNaming.ATTR_DRIVER_CONN}")
        
        if drivers:
            print(f"[MRS] Migrating Data from {drivers[0]}...")
            self._bake_uv_data(drivers[0], follow_mesh)

    def _organize_sets(self, base, data, geo, joints, update):
        sets = {}
        types = [("Control", data["ctrls"]), ("Group", data["groups"]), ("Node", data["nodes"])]
        
        for suffix, members in types:
            s_name = f"{base}_{suffix}_Set"
            if not cmds.objExists(s_name): s_name = cmds.sets(name=s_name, empty=True)
            if members: cmds.sets(members, add=s_name)
            sets[suffix] = s_name
            
        if not update:
            s_geo = cmds.sets(name=f"{base}{MrsNaming.GEO_SET}", empty=True)
            cmds.sets(geo, add=s_geo)
            sets["Geo"] = s_geo
            
            s_jnt = cmds.sets(name=f"{base}{MrsNaming.JNT_SET}", empty=True)
            cmds.sets(joints, add=s_jnt)
            sets["Jnt"] = s_jnt
        else:
            sets["Geo"] = f"{base}{MrsNaming.GEO_SET}"
            sets["Jnt"] = f"{base}{MrsNaming.JNT_SET}"
            
        main_set = f"{base}{MrsNaming.RIG_SET}"
        if not cmds.objExists(main_set): main_set = cmds.sets(name=main_set, empty=True)
        
        for k in sets:
            if cmds.objExists(sets[k]): cmds.sets(sets[k], add=main_set)

    def create_standalone_proxy(self, target_mesh, chains, base_name="Ribbon", pure_ik=False):
        clean_base = base_name.replace(":", "_")
        proxy_mesh = cmds.duplicate(target_mesh, name=f"{clean_base}{MrsNaming.MESH_PROXY}")[0]
        
        cmds.delete(proxy_mesh, ch=True)
        RigUtils.zero_out_local(proxy_mesh)
        cmds.setAttr(f"{proxy_mesh}.{MrsNaming.ATTR_INHERITS_XFORM}", 0)
        cmds.setAttr(f"{proxy_mesh}.visibility", 1)
        
        proxy_grp = f"{clean_base}_Proxy_Grp"
        if not cmds.objExists(proxy_grp):
            proxy_grp = cmds.group(empty=True, name=proxy_grp)
            
        try: cmds.parent(proxy_mesh, proxy_grp)
        except: pass
            
        proxy_set = f"{clean_base}_Proxy_Set"
        if not cmds.objExists(proxy_set):
            proxy_set = cmds.sets(name=proxy_set, empty=True)
        
        cmds.sets(proxy_grp, add=proxy_set)
        cmds.sets(proxy_mesh, add=proxy_set)
            
        is_reversed = RigUtils.get_reverse_state(target_mesh)
        
        RigUtils.apply_perfect_ribbon_weights(proxy_mesh, chains, strategy="hard", pre_follow_parent=True, reverse_order=is_reversed, pure_ik=pure_ik)
        
        if not cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=proxy_mesh, exists=True):
            cmds.addAttr(proxy_mesh, longName=MrsNaming.ATTR_BASE_NAME, dataType="string")
        cmds.setAttr(f"{proxy_mesh}.{MrsNaming.ATTR_BASE_NAME}", base_name, type="string")
        
        if not cmds.attributeQuery(MrsNaming.ATTR_MRS_REVERSE, node=proxy_mesh, exists=True):
            cmds.addAttr(proxy_mesh, longName=MrsNaming.ATTR_MRS_REVERSE, attributeType="bool")
        cmds.setAttr(f"{proxy_mesh}.{MrsNaming.ATTR_MRS_REVERSE}", is_reversed)
        
        return proxy_mesh