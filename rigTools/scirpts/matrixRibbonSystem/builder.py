"""
Matrix Ribbon System (MRS) - Rig Builder
Version: 17.3.0
Optimized: Shared _Scale_CM node for all FK_Offsets, reducing DG graph overhead.
"""
import maya.cmds as cmds
import json
from utils import RigUtils, MrsNaming

class RigBuilder:
    NODE_TYPE = "matrixRibbonMesh"

    def create_preview_mesh(self, chains: list, base_name: str = "Ribbon", width: float = None, hold_length: float = None, loop: bool = False, stitch: bool = True, axis: int = 0):
        if not chains:
            raise ValueError("No joint chains provided.")
        auto_w, auto_h = RigUtils.calculate_topology_metrics(chains[0])
        w = width if width is not None else auto_w
        hl = hold_length if hold_length is not None else auto_h

        clean_base = base_name.replace(":", "_")
        node_name = f"{clean_base}{MrsNaming.NODE_PREVIEW}"
        mesh_t_name = f"{clean_base}{MrsNaming.MESH_PREVIEW}"
        mesh_s_name = f"{mesh_t_name}Shape"

        node = cmds.createNode(self.NODE_TYPE, name=node_name)
        
        RigUtils.ensure_attr(node, MrsNaming.ATTR_BASE_NAME, base_name, "string")

        try:
            chains_json = json.dumps(chains)
            RigUtils.ensure_attr(node, MrsNaming.ATTR_CHAINS_DATA, chains_json, "string")
        except Exception: pass

        for attr, val in [(MrsNaming.ATTR_WIDTH, w), (MrsNaming.ATTR_HOLD_LENGTH, hl), (MrsNaming.ATTR_LOOP, loop), (MrsNaming.ATTR_STITCH, stitch), (MrsNaming.ATTR_AXIS, axis)]:
            if cmds.attributeQuery(attr, node=node, exists=True):
                cmds.setAttr(f"{node}.{attr}", val)
        
        for i, chain in enumerate(chains):
            for j, bone in enumerate(chain):
                cmds.connectAttr(f"{bone}.worldMatrix[0]", f"{node}.inChains[{i}].chainMatrices[{j}]")
        
        mesh_t = cmds.createNode("transform", name=mesh_t_name)
        mesh_s = cmds.createNode("mesh", name=mesh_s_name, parent=mesh_t)
        cmds.connectAttr(f"{node}.outMesh", f"{mesh_s}.inMesh")
        cmds.sets(mesh_s, edit=True, forceElement="initialShadingGroup")
        
        RigUtils.ensure_attr(mesh_t, MrsNaming.ATTR_BASE_NAME, base_name, "string")

        # Bake Axis to Transform
        RigUtils.ensure_attr(mesh_t, MrsNaming.ATTR_AXIS, axis, "short")
        
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

                    RigUtils.ensure_attr(mesh_transform, store_name, flat_vals, "doubleArray")
        
        rev_attr = MrsNaming.ATTR_REVERSE_ORDER
        store_rev = MrsNaming.ATTR_MRS_REVERSE
        if cmds.attributeQuery(rev_attr, node=node, exists=True):
            val = cmds.getAttr(f"{node}.{rev_attr}")
            RigUtils.ensure_attr(mesh_transform, store_rev, val, "bool")

    def build_rig_structure(self, mesh_transform: str, chains: list, name: str = "Ribbon", loop: bool = False, enable_fk: bool = True, enable_ik: bool = True, existing_uvpin: str = None, parent_object: str = None, enable_follow: bool = False) -> dict:
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

        # Pre-create DCM for FK OPM scale injection
        scale_plug = None
        inv_scale_mtx_plug = None
        scale_mtx_plug = None
        if parent_object and cmds.objExists(parent_object):
            dcm_name = f"{clean_name}_Parent_DCM"
            if not cmds.objExists(dcm_name):
                dcm = cmds.createNode("decomposeMatrix", name=dcm_name)
            else:
                dcm = dcm_name
            cmds.connectAttr(f"{parent_object}.worldMatrix[0]", f"{dcm}.inputMatrix", force=True)
            comps["nodes"].append(dcm)
            scale_plug = f"{dcm}.outputScale"

            # Shared inverseScale matrix nodes (reused by all child FK_Offsets)
            inv_md_name = f"{clean_name}_InvScale_MD"
            inv_cm_name = f"{clean_name}_InvScale_CM"
            inv_md = cmds.createNode("multiplyDivide", name=inv_md_name)
            cmds.setAttr(f"{inv_md}.operation", 2)  # Divide
            cmds.setAttr(f"{inv_md}.input1", 1, 1, 1)
            cmds.connectAttr(scale_plug, f"{inv_md}.input2")
            comps["nodes"].append(inv_md)

            inv_cm = cmds.createNode("composeMatrix", name=inv_cm_name)
            cmds.connectAttr(f"{inv_md}.output", f"{inv_cm}.inputScale")
            comps["nodes"].append(inv_cm)
            inv_scale_mtx_plug = f"{inv_cm}.outputMatrix"

            # Shared scale matrix node (reused by ALL FK_Offsets)
            scale_cm_name = f"{clean_name}_Scale_CM"
            scale_cm = cmds.createNode("composeMatrix", name=scale_cm_name)
            cmds.connectAttr(scale_plug, f"{scale_cm}.inputScale")
            comps["nodes"].append(scale_cm)
            scale_mtx_plug = f"{scale_cm}.outputMatrix"

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
                    "width": rig_width, "parent_object": parent_object,
                    "scale_plug": scale_plug, "inv_scale_mtx": inv_scale_mtx_plug,
                    "scale_mtx": scale_mtx_plug,
                    "enable_follow": enable_follow
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
        shapes = cmds.listRelatives(mesh_transform, shapes=True)
        if not shapes:
            raise RuntimeError(f"No shape found under: {mesh_transform}")
        mesh_s = shapes[0]
        
        # Determine Axes based on baked attribute
        axis_mode = 0
        if cmds.attributeQuery(MrsNaming.ATTR_AXIS, node=mesh_transform, exists=True):
            axis_mode = cmds.getAttr(f"{mesh_transform}.{MrsNaming.ATTR_AXIS}")
            
        # Map: Mode -> (tangentAxis=Width, normalAxis=Normal)
        # binormal (V direction) automatically becomes the Aim axis
        # UV layout: U=width direction, V=aim direction
        axis_map = {
            0: (2, 1), # X-Aim, Z-Width -> tangent=Z(2), normal=Y(1)
            1: (1, 2), # X-Aim, Y-Width -> tangent=Y(1), normal=Z(2)
            2: (2, 0), # Y-Aim, Z-Width -> tangent=Z(2), normal=X(0)
            3: (0, 2), # Y-Aim, X-Width -> tangent=X(0), normal=Z(2)
            4: (0, 1), # Z-Aim, X-Width -> tangent=X(0), normal=Y(1)
            5: (1, 0), # Z-Aim, Y-Width -> tangent=Y(1), normal=X(0)
        }
        tan_ax, norm_ax = axis_map.get(axis_mode, (2, 1))
        
        if existing_uvpin and cmds.objExists(existing_uvpin):
            uv_pin = existing_uvpin
        else:
            uv_pin = cmds.createNode("uvPin", name=f"{clean_name}_{MrsNaming.UVPIN}")
            cmds.connectAttr(f"{mesh_s}.worldMesh[0]", f"{uv_pin}.deformedGeometry")
            cmds.setAttr(f"{uv_pin}.normalAxis", norm_ax)
            cmds.setAttr(f"{uv_pin}.tangentAxis", tan_ax)

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
                        except Exception: pass

    def _build_fk_component(self, ctx, comps):
        grp_name = RigUtils.generate_name(ctx["base"], ctx["c"], ctx["i"], MrsNaming.FK_OFFSET)
        ctrl_name = RigUtils.generate_name(ctx["base"], ctx["c"], ctx["i"], MrsNaming.FK_CTRL)

        grp = self._ensure_group(grp_name, parent=ctx["prev_fk"])
        comps["groups"].append(grp)

        # OPM connection first (uses raw pin plugs, no blend)
        if ctx["i"] == 0:
            scale_mtx = ctx.get("scale_mtx")
            if scale_mtx:
                self._connect_opm_with_scale(ctx["pin"], grp, scale_mtx, comps["nodes"])
            else:
                self._connect_opm(ctx["pin"], grp)
        else:
            scale_mtx = ctx.get("scale_mtx")
            inv_scale = ctx.get("inv_scale_mtx")
            pre_plugs = [scale_mtx] if scale_mtx else []
            post_plugs = [inv_scale] if inv_scale else []
            self._connect_opm_relative(ctx["pin"], ctx["prev_pin"], grp, comps["nodes"],
                                       pre_plugs=pre_plugs if pre_plugs else None,
                                       post_plugs=post_plugs if post_plugs else None)

        RigUtils.zero_out_local(grp)

        size = ctx["width"] * MrsNaming.FK_CTRL_SCALE
        ctrl = self._ensure_control(ctrl_name, grp, size, "circle")
        comps["ctrls"].append(ctrl)

        # Follow Toggle: insert blendMatrix at OPM output layer
        if ctx.get("enable_follow") and ctx.get("parent_object"):
            self._insert_follow_blend(grp, ctrl, ctx["base"], ctx["c"], ctx["i"], comps["nodes"])

        return {"grp": grp, "ctrl": ctrl}

    def _insert_follow_blend(self, fk_offset, fk_ctrl, base_name, chain_idx, bone_idx, node_list):
        """Insert blendMatrix between OPM source and FK_Offset.OPM.

        Intercepts the complete OPM output (relative transform for i>=1):
        - envelope=1 (Follow_Mesh=1, default): passes through live OPM
        - envelope=0 (Follow_Mesh=0): outputs inputMatrix = frozen OPM snapshot at bind time

        This preserves the relative offset to parent, so Follow=0 means
        the controller maintains its bind-time offset from parent (L-shape behavior).
        """
        blend_name = RigUtils.generate_name(base_name, chain_idx, bone_idx, "_FollowBlend")
        if cmds.objExists(blend_name):
            try: cmds.delete(blend_name)
            except Exception: pass

        opm_plug = f"{fk_offset}.offsetParentMatrix"
        src = cmds.connectionInfo(opm_plug, sourceFromDestination=True)

        # Snapshot current OPM value (at bind time, static == dynamic -> zero-jump)
        static_mtx = cmds.getAttr(src) if src else None
        if src:
            cmds.disconnectAttr(src, opm_plug)

        blend = cmds.createNode("blendMatrix", name=blend_name)
        if static_mtx:
            cmds.setAttr(f"{blend}.inputMatrix", static_mtx, type="matrix")
        if src:
            cmds.connectAttr(src, f"{blend}.target[0].targetMatrix")
        cmds.setAttr(f"{blend}.target[0].weight", 1.0)

        if not cmds.attributeQuery(MrsNaming.ATTR_FOLLOW_MESH, node=fk_ctrl, exists=True):
            cmds.addAttr(fk_ctrl, ln=MrsNaming.ATTR_FOLLOW_MESH, at="float", min=0, max=1, dv=1, k=True)
        cmds.connectAttr(f"{fk_ctrl}.{MrsNaming.ATTR_FOLLOW_MESH}", f"{blend}.envelope")

        cmds.connectAttr(f"{blend}.outputMatrix", opm_plug, force=True)
        node_list.append(blend)

    def _clean_fk_component(self, ctx):
        grp_name = RigUtils.generate_name(ctx["base"], ctx["c"], ctx["i"], MrsNaming.FK_OFFSET)
        if cmds.objExists(grp_name):
            # Clean FollowBlend DG node before deleting transform
            blend_name = RigUtils.generate_name(ctx["base"], ctx["c"], ctx["i"], "_FollowBlend")
            if cmds.objExists(blend_name):
                try: cmds.delete(blend_name)
                except Exception: pass
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
        except Exception: pass
        
        if is_fk_active:
            RigUtils.delete_opm_nodes(grp)
            RigUtils.zero_out_local(grp)
        else:
            RigUtils.delete_opm_nodes(grp)
            cmds.connectAttr(ctx["pin"], f"{grp}.offsetParentMatrix", force=True)
            RigUtils.zero_out_local(grp)
            
        size = ctx["width"] * MrsNaming.IK_CTRL_SCALE
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

    def _connect_opm_with_scale(self, pin_plug, target_node, scale_mtx_plug, node_list):
        """Connect uvPin output to OPM with scale injection via shared composeMatrix + multMatrix."""
        mm_name = f"{target_node}_ScaleMM"
        if cmds.objExists(mm_name):
            try: cmds.delete(mm_name)
            except Exception: pass
        mm = cmds.createNode("multMatrix", name=mm_name)
        cmds.connectAttr(scale_mtx_plug, f"{mm}.matrixIn[0]")
        cmds.connectAttr(pin_plug, f"{mm}.matrixIn[1]")
        node_list.append(mm)

        cmds.connectAttr(f"{mm}.matrixSum", f"{target_node}.offsetParentMatrix", force=True)

    def _connect_opm_relative(self, curr_pin, prev_pin, target_node, node_list, pre_plugs=None, post_plugs=None):
        opm_name = f"{target_node}_OPM"
        inv_name = f"{target_node}_PinInv"

        for old in (opm_name, inv_name):
            if cmds.objExists(old):
                try: cmds.delete(old)
                except Exception: pass

        opm = cmds.createNode("multMatrix", name=opm_name)
        node_list.append(opm)

        slot = 0
        for plug in (pre_plugs or []):
            cmds.connectAttr(plug, f"{opm}.matrixIn[{slot}]")
            slot += 1

        cmds.connectAttr(curr_pin, f"{opm}.matrixIn[{slot}]")
        slot += 1

        inv = cmds.createNode("inverseMatrix", name=inv_name)
        node_list.append(inv)
        cmds.connectAttr(prev_pin, f"{inv}.inputMatrix", force=True)
        cmds.connectAttr(f"{inv}.outputMatrix", f"{opm}.matrixIn[{slot}]")
        slot += 1

        for plug in (post_plugs or []):
            cmds.connectAttr(plug, f"{opm}.matrixIn[{slot}]")
            slot += 1

        cmds.connectAttr(f"{opm}.matrixSum", f"{target_node}.offsetParentMatrix", force=True)

    def _ensure_group(self, name, parent=None):
        if not cmds.objExists(name):
            grp = cmds.group(empty=True, name=name)
        else: grp = name
        
        if parent:
            curr_p = cmds.listRelatives(grp, parent=True)
            if not curr_p or curr_p[0] != parent:
                try: cmds.parent(grp, parent)
                except Exception: pass
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

    def _setup_follow_mesh(self, preview_mesh, clean_base, base_name, ribbon_node, chains):
        follow_mesh = cmds.duplicate(preview_mesh, name=f"{clean_base}{MrsNaming.MESH_FOLLOW}")[0]
        cmds.delete(follow_mesh, ch=True)
        RigUtils.zero_out_local(follow_mesh)
        cmds.setAttr(f"{follow_mesh}.{MrsNaming.ATTR_INHERITS_XFORM}", 0)

        rev_val = RigUtils.get_reverse_state(ribbon_node) if ribbon_node else RigUtils.get_reverse_state(preview_mesh)
        if rev_val:
            RigUtils.ensure_attr(follow_mesh, MrsNaming.ATTR_MRS_REVERSE, rev_val, "bool")

        if ribbon_node:
            RigUtils.ensure_attr(follow_mesh, MrsNaming.ATTR_DRIVER_CONN, None, "message")
            cmds.connectAttr(f"{ribbon_node}.message", f"{follow_mesh}.{MrsNaming.ATTR_DRIVER_CONN}", force=True)

        RigUtils.ensure_attr(follow_mesh, MrsNaming.ATTR_BASE_NAME, base_name, "string")

        try:
            chains_json = json.dumps(chains)
            RigUtils.ensure_attr(follow_mesh, MrsNaming.ATTR_CHAINS_DATA, chains_json, "string")
        except Exception: pass

        return follow_mesh

    def _cleanup_scale_connections(self, chains, clean_base):
        """Disconnects existing scale inputs and removes old/new scale compensate nodes."""
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
                        except Exception: pass
                        # Clean up old compensate nodes and new OPM scale nodes
                        for comp in ["_ParentScale_DCM", "_ScaleComp", "_ScaleCM", "_ScaleMM", "_CtrlInvS_MD", "_CtrlInvS_CM"]:
                            n = f"{grp}{comp}"
                            if cmds.objExists(n):
                                try: cmds.delete(n)
                                except Exception: pass

        # Clean up FollowBlend nodes (named via generate_name pattern)
        for c_idx, chain in enumerate(chains):
            for i in range(len(chain)):
                fb = RigUtils.generate_name(clean_base, c_idx, i, "_FollowBlend")
                if cmds.objExists(fb):
                    try: cmds.delete(fb)
                    except Exception: pass

        # Clean up shared scale nodes
        for suffix in ["_InvScale_MD", "_InvScale_CM", "_Scale_CM"]:
            n = f"{clean_base}{suffix}"
            if cmds.objExists(n):
                try: cmds.delete(n)
                except Exception: pass

    def _connect_scale_driver(self, dcm, chains, enable_fk, enable_ik, clean_base, node_list=None):
        """Pure IK only: connect DCM scale to all IK_Offsets.

        FK scale is handled via OPM injection in build_rig_structure.
        """
        if enable_ik and not enable_fk:
            dcm_scale = f"{dcm}.outputScale"
            for c_idx, chain in enumerate(chains):
                for i in range(len(chain)):
                    ik_grp = RigUtils.generate_name(clean_base, c_idx, i, MrsNaming.IK_OFFSET)
                    if cmds.objExists(ik_grp):
                        cmds.connectAttr(dcm_scale, f"{ik_grp}.scale", force=True)

    def finalize_bind(self, preview_mesh: str, chains: list, enable_fk: bool = True, enable_ik: bool = True, existing_ribbon_node: str = None, existing_base_name: str = None, update_mode: bool = False, existing_follow_mesh: str = None, passed_uvpin: str = None, parent_object: str = None, enable_follow: bool = False) -> str:

        base_name, follow_mesh, uv_pin, ribbon_node = self._resolve_bind_inputs(
            preview_mesh, chains, existing_ribbon_node, existing_base_name,
            update_mode, existing_follow_mesh, passed_uvpin
        )
        clean_base = base_name.replace(":", "_")

        if not update_mode:
            follow_mesh = self._setup_follow_mesh(preview_mesh, clean_base, base_name, ribbon_node, chains)

        # Clean old scale/follow connections BEFORE building new rig structure,
        # so newly created ScaleCM/ScaleMM nodes won't be deleted by cleanup.
        if update_mode or (parent_object and cmds.objExists(parent_object)):
            self._cleanup_scale_connections(chains, clean_base)

        rig_data = self.build_rig_structure(follow_mesh, chains, name=base_name,
                                          enable_fk=enable_fk, enable_ik=enable_ik, existing_uvpin=uv_pin, parent_object=parent_object, enable_follow=enable_follow)

        self._setup_parent_scale(parent_object, clean_base, rig_data, chains, enable_fk, enable_ik)
        self._organize_hierarchy(clean_base, chains, rig_data, follow_mesh, parent_object, update_mode)
        self._bind_bones_to_drivers(chains, rig_data)

        # Persist parent_object to FollowMod for update-mode recovery
        if parent_object and cmds.objExists(parent_object):
            RigUtils.ensure_attr(follow_mesh, MrsNaming.ATTR_PARENT_OBJECT, parent_object, "string")

        self._organize_sets(clean_base, rig_data, follow_mesh, [b for c in chains for b in c], update_mode)

        if not update_mode and preview_mesh and cmds.objExists(preview_mesh):
            plugin_node = RigUtils.find_plugin_node(preview_mesh)
            cmds.delete(preview_mesh)
            if plugin_node and cmds.objExists(plugin_node):
                cmds.delete(plugin_node)

        print(f"[MRS] Bind Complete: {base_name}")
        return rig_data["_main_grp"]

    def _resolve_bind_inputs(self, preview_mesh, chains, existing_ribbon_node, existing_base_name, update_mode, existing_follow_mesh, passed_uvpin):
        """Resolve inputs for bind: returns (base_name, follow_mesh, uv_pin, ribbon_node)."""
        base_name = existing_base_name if existing_base_name else "Ribbon"
        follow_mesh = None
        uv_pin = None
        ribbon_node = None

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

        return base_name, follow_mesh, uv_pin, ribbon_node

    def _setup_parent_scale(self, parent_object, clean_base, rig_data, chains, enable_fk, enable_ik):
        """Handle Pure IK scale connections.

        FK scale is handled via OPM injection in build_rig_structure.
        Cleanup is done before build_rig_structure in finalize_bind.
        """
        if not parent_object or not cmds.objExists(parent_object):
            return
        dcm_name = f"{clean_base}_Parent_DCM"
        if cmds.objExists(dcm_name):
            self._connect_scale_driver(dcm_name, chains, enable_fk, enable_ik, clean_base, rig_data["nodes"])

    def _organize_hierarchy(self, clean_base, chains, rig_data, follow_mesh, parent_object, update_mode):
        """Organize main_grp, jnt_grp hierarchy and parent joints."""
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
        except Exception: pass

        rig_data["groups"].append(main_grp)
        rig_data["_main_grp"] = main_grp

    def _bind_bones_to_drivers(self, chains, rig_data):
        """Connect bones to driver controls via OPM and store bind pose."""
        all_bones = [b for c in chains for b in c]
        for bone, drv in zip(all_bones, rig_data["drivers"]):
            opm = RigUtils.connect_via_opm(drv, bone, maintain_offset=False)
            if opm: rig_data["nodes"].append(opm)

            m_bind = cmds.xform(bone, q=True, ws=True, m=True)
            RigUtils.ensure_attr(bone, MrsNaming.ATTR_BIND_POSE, m_bind, "matrix")

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
            except Exception: pass
            
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
        types = [(MrsNaming.CTRL_SET, data["ctrls"]), (MrsNaming.GRP_SET, data["groups"]), (MrsNaming.NODE_SET, data["nodes"])]

        for set_suffix, members in types:
            s_name = f"{base}{set_suffix}"
            if not cmds.objExists(s_name): s_name = cmds.sets(name=s_name, empty=True)
            # In update mode, clear stale members before repopulating
            if update:
                old = cmds.sets(s_name, q=True) or []
                if old: cmds.sets(old, remove=s_name)
            valid = [m for m in members if cmds.objExists(m)] if members else []
            if valid: cmds.sets(valid, add=s_name)
            sets[set_suffix] = s_name
            
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
        except Exception: pass
            
        proxy_set = f"{clean_base}_Proxy_Set"
        if not cmds.objExists(proxy_set):
            proxy_set = cmds.sets(name=proxy_set, empty=True)
        
        cmds.sets(proxy_grp, add=proxy_set)
        cmds.sets(proxy_mesh, add=proxy_set)
            
        is_reversed = RigUtils.get_reverse_state(target_mesh)
        
        RigUtils.apply_perfect_ribbon_weights(proxy_mesh, chains, pre_follow_parent=True, reverse_order=is_reversed, pure_ik=pure_ik)

        RigUtils.ensure_attr(proxy_mesh, MrsNaming.ATTR_BASE_NAME, base_name, "string")
        RigUtils.ensure_attr(proxy_mesh, MrsNaming.ATTR_MRS_REVERSE, is_reversed, "bool")
        
        return proxy_mesh