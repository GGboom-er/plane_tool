"""
Matrix Ribbon System (MRS) - Rig Builder
Version: 17.1.0
Optimized: Scalable controls, decoupled logic.
"""
import maya.cmds as cmds
import json
from utils import RigUtils, MrsNaming

class RigBuilder:
    NODE_TYPE = "matrixRibbonMesh"

    def create_preview_mesh(self, chains, base_name="Ribbon", width=None, hold_length=None, loop=False, stitch=True):
        auto_w, auto_h = RigUtils.calculate_topology_metrics(chains[0])
        w = width if width is not None else auto_w
        hl = hold_length if hold_length is not None else auto_h

        # Naming
        clean_base = base_name.replace(":", "_")
        node_name = f"{clean_base}{MrsNaming.NODE_PREVIEW}"
        mesh_t_name = f"{clean_base}{MrsNaming.MESH_PREVIEW}"
        mesh_s_name = f"{mesh_t_name}Shape"

        node = cmds.createNode(self.NODE_TYPE, name=node_name)
        
        # Store Metadata
        cmds.addAttr(node, longName=MrsNaming.ATTR_BASE_NAME, dataType="string")
        cmds.setAttr(f"{node}.{MrsNaming.ATTR_BASE_NAME}", base_name, type="string")
        
        try:
            chains_json = json.dumps(chains)
            cmds.addAttr(node, longName=MrsNaming.ATTR_CHAINS_DATA, dataType="string")
            cmds.setAttr(f"{node}.{MrsNaming.ATTR_CHAINS_DATA}", chains_json, type="string")
        except: pass

        # Set Attrs
        for attr, val in [("width", w), ("holdLength", hl), ("loop", loop), ("stitch", stitch)]:
            if cmds.attributeQuery(attr, node=node, exists=True):
                cmds.setAttr(f"{node}.{attr}", val)
        
        # Connect Chains
        for i, chain in enumerate(chains):
            for j, bone in enumerate(chain):
                cmds.connectAttr(f"{bone}.worldMatrix[0]", f"{node}.inChains[{i}].chainMatrices[{j}]")
        
        # Output Mesh
        mesh_t = cmds.createNode("transform", name=mesh_t_name)
        mesh_s = cmds.createNode("mesh", name=mesh_s_name, parent=mesh_t)
        cmds.connectAttr(f"{node}.outMesh", f"{mesh_s}.inMesh")
        cmds.sets(mesh_s, edit=True, forceElement="initialShadingGroup")
        
        # Store Base Name on Transform
        if not cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=mesh_t, exists=True):
            cmds.addAttr(mesh_t, longName=MrsNaming.ATTR_BASE_NAME, dataType="string")
        cmds.setAttr(f"{mesh_t}.{MrsNaming.ATTR_BASE_NAME}", base_name, type="string")
        
        # Store Computed UVs
        self._bake_uv_data(node, mesh_t)
        
        return mesh_t, node, w, hl

    def _bake_uv_data(self, node, mesh_transform):
        # 1. Bake UV Arrays
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
        
        # 2. Bake Reverse Order State
        rev_attr = "reverseOrder"
        store_rev = "mrsReverseOrder"
        if cmds.attributeQuery(rev_attr, node=node, exists=True):
            val = cmds.getAttr(f"{node}.{rev_attr}")
            if not cmds.attributeQuery(store_rev, node=mesh_transform, exists=True):
                cmds.addAttr(mesh_transform, longName=store_rev, attributeType="bool")
            cmds.setAttr(f"{mesh_transform}.{store_rev}", val)

    def build_rig_structure(self, mesh_transform, chains, name="Ribbon", loop=False, enable_fk=True, enable_ik=True, existing_uvpin=None):
        clean_name = name.replace(":", "_")
        
        # 1. Retrieve Width for Sizing
        rig_width = 2.0
        if cmds.attributeQuery("width", node=mesh_transform, exists=True):
            rig_width = cmds.getAttr(f"{mesh_transform}.width")
        else:
            # Try finding driver
            hist = cmds.listConnections(f"{mesh_transform}.inMesh", s=True) or []
            if hist and cmds.attributeQuery("width", node=hist[0], exists=True):
                rig_width = cmds.getAttr(f"{hist[0]}.width")

        # 2. UV Pin Setup
        uv_pin, u_vals, v_vals = self._setup_uv_pin(mesh_transform, clean_name, chains, loop, existing_uvpin)
        
        # 3. Main Groups
        rig_grp = self._ensure_group(f"{clean_name}{MrsNaming.GRP_CTRL}")
        comps = {"ctrls": [], "groups": [rig_grp], "nodes": [uv_pin], "drivers": []}
        
        if not enable_fk:
            self._preserve_ik_offsets(chains, clean_name, rig_grp)

        pin_offset = 0
        for c_idx, chain in enumerate(chains):
            chain_grp = self._ensure_group(f"{clean_name}_{RigUtils.get_alpha_index(c_idx)}{MrsNaming.GRP_MAIN}", parent=rig_grp)
            if chain_grp not in comps["groups"]: comps["groups"].append(chain_grp)
            
            prev_fk_ctrl = chain_grp
            prev_pin_plug = None
            chain_root_fk = None # Track root FK for visibility proxy
            
            for i, bone in enumerate(chain):
                # Update Pin
                idx = pin_offset + i
                u = u_vals[c_idx] if u_vals and c_idx < len(u_vals) else 0.5
                curr_pin_plug = f"{uv_pin}.outputMatrix[{idx}]"
                
                ctx = {
                    "base": clean_name, "c": c_idx, "i": i, 
                    "pin": curr_pin_plug, "prev_pin": prev_pin_plug,
                    "prev_fk": prev_fk_ctrl, "chain_grp": chain_grp,
                    "width": rig_width
                }
                
                current_driver = None
                
                # --- FK ---
                if enable_fk:
                    fk_res = self._build_fk_component(ctx, comps)
                    prev_fk_ctrl = fk_res["ctrl"]
                    current_driver = fk_res["ctrl"]
                    
                    # Visibility Logic
                    if i == 0:
                        chain_root_fk = fk_res["ctrl"]
                        if not cmds.attributeQuery("Show_IK", node=chain_root_fk, exists=True):
                            cmds.addAttr(chain_root_fk, longName="Show_IK", attributeType="bool", keyable=True, defaultValue=1)
                    else:
                        # Add Proxy Attribute
                        if chain_root_fk and not cmds.attributeQuery("Show_IK", node=fk_res["ctrl"], exists=True):
                            cmds.addAttr(fk_res["ctrl"], longName="Show_IK", proxy=f"{chain_root_fk}.Show_IK")
                else:
                    self._clean_fk_component(ctx)

                # --- IK ---
                if enable_ik:
                    parent = prev_fk_ctrl if enable_fk else chain_grp
                    ik_res = self._build_ik_component(ctx, comps, parent, enable_fk)
                    current_driver = ik_res["ctrl"]
                    
                    # Connect Visibility
                    if chain_root_fk:
                        cmds.connectAttr(f"{chain_root_fk}.Show_IK", f"{ik_res['grp']}.visibility", force=True)
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
        
        # Determine Reverse State
        is_reversed = False
        hist = cmds.listConnections(f"{mesh_s}.inMesh", s=True)
        node = hist[0] if hist else None
        if node and cmds.attributeQuery("reverseOrder", node=node, exists=True):
            is_reversed = cmds.getAttr(f"{node}.reverseOrder")
        elif cmds.attributeQuery("mrsReverseOrder", node=mesh_transform, exists=True):
            is_reversed = cmds.getAttr(f"{mesh_transform}.mrsReverseOrder")

        num_chains = len(chains)
        max_len = max([len(c) for c in chains]) if chains else 0
        
        pin_idx = 0
        final_u = []
        final_v = []
        
        for c_idx, chain in enumerate(chains):
            # Handle Reverse Order Mapping
            target_u_idx = (num_chains - 1 - c_idx) if is_reversed else c_idx
            
            if u_vals and target_u_idx < len(u_vals):
                u = u_vals[target_u_idx]
            else:
                denom = float(num_chains * 3) if loop else float(num_chains * 3 - 1)
                base_idx = target_u_idx # Consistent with mapping
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
        
        # Size based on Width
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
        
        if is_fk_active:
            RigUtils.delete_opm_nodes(grp)
            cmds.setAttr(f"{grp}.inheritsTransform", 1)
            RigUtils.zero_out_local(grp)
        else:
            # Pure IK Mode (Optimized)
            # Direct connection requires disabling inheritance to avoid double transformation
            RigUtils.delete_opm_nodes(grp)
            cmds.connectAttr(ctx["pin"], f"{grp}.offsetParentMatrix", force=True)
            cmds.setAttr(f"{grp}.inheritsTransform", 0)
            RigUtils.zero_out_local(grp)
            
        # Size based on Width (IK = 0.6 * FK_Size)
        # FK Size is width * 1.2
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
        if not cmds.objExists(opm_name):
            opm = cmds.createNode("multMatrix", name=opm_name)
            node_list.append(opm)
            inv = cmds.createNode("inverseMatrix", name=f"{target_node}_PinInv")
            node_list.append(inv)
            
            cmds.connectAttr(curr_pin, f"{opm}.matrixIn[0]")
            cmds.connectAttr(prev_pin, f"{inv}.inputMatrix")
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
        
        # Lock and Hide Visibility
        cmds.setAttr(f"{ctrl}.v", lock=True, keyable=False, channelBox=False)
        
        return ctrl

    def finalize_bind(self, preview_mesh, chains, enable_fk=True, enable_ik=True, existing_ribbon_node=None, existing_base_name=None, update_mode=False, existing_follow_mesh=None, passed_uvpin=None):
        
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
            follow_mesh = cmds.duplicate(preview_mesh, name=f"{clean_base}{MrsNaming.MESH_FOLLOW}")[0]
            cmds.delete(follow_mesh, ch=True)
            RigUtils.zero_out_local(follow_mesh)
            cmds.setAttr(f"{follow_mesh}.inheritsTransform", 0)
            
            # Sync Reverse Order from Live Node
            if ribbon_node and cmds.attributeQuery("reverseOrder", node=ribbon_node, exists=True):
                rev_val = cmds.getAttr(f"{ribbon_node}.reverseOrder")
                if not cmds.attributeQuery("mrsReverseOrder", node=follow_mesh, exists=True):
                    cmds.addAttr(follow_mesh, longName="mrsReverseOrder", attributeType="bool")
                cmds.setAttr(f"{follow_mesh}.mrsReverseOrder", rev_val)
            
            if ribbon_node:
                if not cmds.attributeQuery(MrsNaming.ATTR_DRIVER_CONN, node=follow_mesh, exists=True):
                    cmds.addAttr(follow_mesh, longName=MrsNaming.ATTR_DRIVER_CONN, attributeType="message")
                cmds.connectAttr(f"{ribbon_node}.message", f"{follow_mesh}.{MrsNaming.ATTR_DRIVER_CONN}", force=True)
            
            if not cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=follow_mesh, exists=True):
                cmds.addAttr(follow_mesh, longName=MrsNaming.ATTR_BASE_NAME, dataType="string")
            cmds.setAttr(f"{follow_mesh}.{MrsNaming.ATTR_BASE_NAME}", base_name, type="string")

        rig_data = self.build_rig_structure(follow_mesh, chains, name=base_name, 
                                          enable_fk=enable_fk, enable_ik=enable_ik, existing_uvpin=uv_pin)
        
        main_grp = self._ensure_group(f"{clean_base}{MrsNaming.GRP_MAIN}")
        jnt_grp = f"{clean_base}{MrsNaming.GRP_JNT}"
        
        if not update_mode:
            jnt_grp = self._ensure_group(jnt_grp, parent=main_grp)
            roots = [c[0] for c in chains]
            self._parent_joints_safely(roots, jnt_grp)
            
            rig_data["groups"].append(jnt_grp)
            cmds.parent(follow_mesh, main_grp)
            cmds.setAttr(f"{follow_mesh}.visibility", 0)
            
        try: cmds.parent(rig_data["groups"][0], main_grp)
        except: pass
        
        rig_data["groups"].append(main_grp)

        all_bones = [b for c in chains for b in c]
        for bone, drv in zip(all_bones, rig_data["drivers"]):
            opm = RigUtils.connect_via_opm(drv, bone)
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
        cmds.setAttr(f"{proxy_mesh}.inheritsTransform", 0)
        cmds.setAttr(f"{proxy_mesh}.visibility", 1)
        
        # Independent Packaging (Standalone Set)
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
            
        # Detect Reverse Order
        is_reversed = False
        
        # 1. Check baked attribute on Transform (highest priority if exists)
        if cmds.attributeQuery("mrsReverseOrder", node=target_mesh, exists=True):
            is_reversed = cmds.getAttr(f"{target_mesh}.mrsReverseOrder")
        else:
            # 2. Check Upstream History (Live Preview)
            # Ensure we are looking at the Shape node for .inMesh
            check_node = target_mesh
            if cmds.nodeType(target_mesh) == "transform":
                shapes = cmds.listRelatives(target_mesh, shapes=True)
                if shapes: check_node = shapes[0]
            
            # Look for matrixRibbonMesh in history
            if cmds.objExists(check_node):
                # Try direct connection first
                if cmds.attributeQuery("inMesh", node=check_node, exists=True):
                    hist = cmds.listConnections(f"{check_node}.inMesh", s=True) or []
                    for h in hist:
                        if cmds.nodeType(h) == "matrixRibbonMesh":
                            if cmds.attributeQuery("reverseOrder", node=h, exists=True):
                                is_reversed = cmds.getAttr(f"{h}.reverseOrder")
                            break
                            
        print(f"[MRS] Proxy Gen - Detected Reverse Order: {is_reversed} (Source: {target_mesh})")

        RigUtils.apply_perfect_ribbon_weights(proxy_mesh, chains, strategy="hard", pre_follow_parent=True, reverse_order=is_reversed, pure_ik=pure_ik)
        
        if not cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=proxy_mesh, exists=True):
            cmds.addAttr(proxy_mesh, longName=MrsNaming.ATTR_BASE_NAME, dataType="string")
        cmds.setAttr(f"{proxy_mesh}.{MrsNaming.ATTR_BASE_NAME}", base_name, type="string")
        
        # Bake Reverse Order State to Proxy
        if not cmds.attributeQuery("mrsReverseOrder", node=proxy_mesh, exists=True):
            cmds.addAttr(proxy_mesh, longName="mrsReverseOrder", attributeType="bool")
        cmds.setAttr(f"{proxy_mesh}.mrsReverseOrder", is_reversed)
        
        return proxy_mesh