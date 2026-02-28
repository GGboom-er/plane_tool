"""
Matrix Ribbon System (MRS) - Rig Builder
Version: 19.0.0
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om
import json
from dataclasses import dataclass
from utils import RigUtils, MrsNaming


@dataclass
class BindConfig:
    """Bind/Update 配置参数包。"""
    enable_fk: bool = True
    enable_ik: bool = True
    enable_follow: bool = False
    parent_object: str = None
    update_mode: bool = False
    existing_base_name: str = None
    existing_follow_mesh: str = None
    existing_ribbon_node: str = None
    passed_uvpin: str = None


class _BuildContext:
    """Per-bone build state passed between component builders."""
    __slots__ = ('base', 'c', 'i', 'pin', 'prev_pin', 'prev_fk', 'prev_target',
                 'chain_grp', 'width', 'parent_object', 'scale_plug',
                 'inv_scale_mtx', 'scale_mtx', 'enable_follow', 'chain')

    def __init__(self, base, c, i, pin, prev_pin, prev_fk, prev_target,
                 chain_grp, width, parent_object, scale_plug,
                 inv_scale_mtx, scale_mtx, enable_follow, chain):
        self.base = base
        self.c = c
        self.i = i
        self.pin = pin
        self.prev_pin = prev_pin
        self.prev_fk = prev_fk
        self.prev_target = prev_target
        self.chain_grp = chain_grp
        self.width = width
        self.parent_object = parent_object
        self.scale_plug = scale_plug
        self.inv_scale_mtx = inv_scale_mtx
        self.scale_mtx = scale_mtx
        self.enable_follow = enable_follow
        self.chain = chain




class GeometryNodeBuilder:
    """Geometric creation and topological querying (UV, Ribbon Mesh)."""
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

        node = cmds.createNode(MrsNaming.NODE_PLUGIN, name=node_name)
        
        RigUtils.ensure_attr(node, MrsNaming.ATTR_BASE_NAME, base_name, "string")

        chains_json = json.dumps(chains)
        RigUtils.ensure_attr(node, MrsNaming.ATTR_CHAINS_DATA, chains_json, "string")

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
                    for item in (vals if isinstance(vals, (list, tuple)) else [vals]):
                        if isinstance(item, (list, tuple)):
                            flat_vals.extend(item)
                        else:
                            flat_vals.append(item)
                    flat_vals = [float(x) for x in flat_vals]

                    RigUtils.ensure_attr(mesh_transform, store_name, flat_vals, "doubleArray")
        
        rev_attr = MrsNaming.ATTR_REVERSE_ORDER
        store_rev = MrsNaming.ATTR_MRS_REVERSE
        if cmds.attributeQuery(rev_attr, node=node, exists=True):
            val = cmds.getAttr(f"{node}.{rev_attr}")
            RigUtils.ensure_attr(mesh_transform, store_rev, val, "bool")

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

        chains_json = json.dumps(chains)
        RigUtils.ensure_attr(follow_mesh, MrsNaming.ATTR_CHAINS_DATA, chains_json, "string")

        return follow_mesh


class MathNetworkBuilder:
    """Directed Acyclic Graph (DAG) construction for Matrix blending and OPM."""
    def _preserve_ik_offsets(self, chains, clean_name, rig_grp):
        for c_idx, chain in enumerate(chains):
            for i in range(len(chain)):
                ik_grp = RigUtils.generate_name(clean_name, c_idx, i, MrsNaming.IK_OFFSET)
                if cmds.objExists(ik_grp):
                    if cmds.listRelatives(ik_grp, parent=True) != [rig_grp]:
                        cmds.parent(ik_grp, rig_grp)

    def _build_spatial_opm(self, ctx, ctrl, grp, comps, enable_follow, comp_type="FK"):
        import maya.api.OpenMaya as om
        
        if ctx.scale_mtx:
            live_mm_name = RigUtils.generate_name(ctx.base, ctx.c, ctx.i, f"_{comp_type}_LiveWorldMM")
            if cmds.objExists(live_mm_name): cmds.delete(live_mm_name)
            live_mm = cmds.createNode("multMatrix", name=live_mm_name)
            cmds.connectAttr(ctx.scale_mtx, f"{live_mm}.matrixIn[0]")
            cmds.connectAttr(ctx.pin, f"{live_mm}.matrixIn[1]")
            target_mesh = f"{live_mm}.matrixSum"
            comps["nodes"].append(live_mm)
        else:
            target_mesh = ctx.pin

        bind_mesh_raw = cmds.getAttr(target_mesh)
        if bind_mesh_raw and isinstance(bind_mesh_raw[0], (list, tuple)): bind_mesh_raw = list(bind_mesh_raw[0])
        
        is_root = (ctx.i == 0) or (comp_type == "IK")
        
        if is_root:
            if ctx.parent_object and cmds.objExists(ctx.parent_object):
                prev_target_bind = cmds.getAttr(f"{ctx.parent_object}.worldMatrix[0]")
                prev_target_plug = f"{ctx.parent_object}.worldMatrix[0]"
            else:
                prev_target_bind = list(om.MMatrix.kIdentity)
                prev_target_plug = f"{ctx.chain_grp}.worldMatrix[0]"
        else:
            prev_target_bind = cmds.getAttr(ctx.prev_target)
            prev_target_plug = ctx.prev_target
            
        if prev_target_bind and isinstance(prev_target_bind[0], (list, tuple)): prev_target_bind = list(prev_target_bind[0])
        
        offset_bind_mm = list(om.MMatrix(bind_mesh_raw) * om.MMatrix(prev_target_bind).inverse())

        live_local_mm = cmds.createNode("multMatrix", name=RigUtils.generate_name(ctx.base, ctx.c, ctx.i, f"_{comp_type}_LiveLocal"))
        comps["nodes"].append(live_local_mm)
        cmds.connectAttr(target_mesh, f"{live_local_mm}.matrixIn[0]")
        
        prev_inv_node = cmds.createNode("inverseMatrix", name=RigUtils.generate_name(ctx.base, ctx.c, ctx.i, f"_{comp_type}_PrevTargetInv"))
        comps["nodes"].append(prev_inv_node)
        cmds.connectAttr(prev_target_plug, f"{prev_inv_node}.inputMatrix")
        cmds.connectAttr(f"{prev_inv_node}.outputMatrix", f"{live_local_mm}.matrixIn[1]")
        
        opm_output_plug = f"{live_local_mm}.matrixSum"

        if enable_follow:
            opm_blend = cmds.createNode("blendMatrix", name=RigUtils.generate_name(ctx.base, ctx.c, ctx.i, f"_{comp_type}_OPMBlend"))
            comps["nodes"].append(opm_blend)
            cmds.setAttr(f"{opm_blend}.inputMatrix", offset_bind_mm, type="matrix")        
            cmds.connectAttr(f"{live_local_mm}.matrixSum", f"{opm_blend}.target[0].targetMatrix")
            cmds.setAttr(f"{opm_blend}.target[0].weight", 1.0)
            
            if not cmds.attributeQuery(MrsNaming.ATTR_FOLLOW_MESH, node=ctrl, exists=True):
                cmds.addAttr(ctrl, ln=MrsNaming.ATTR_FOLLOW_MESH, at="float", min=0, max=1, dv=1, k=True)
            cmds.connectAttr(f"{ctrl}.{MrsNaming.ATTR_FOLLOW_MESH}", f"{opm_blend}.envelope")
            opm_output_plug = f"{opm_blend}.outputMatrix"
        
        if is_root:
            out_p = ctx.prev_fk if cmds.objExists(ctx.prev_fk) else ctx.chain_grp
            opm_final_mm = cmds.createNode("multMatrix", name=RigUtils.generate_name(ctx.base, ctx.c, ctx.i, f"_{comp_type}_OPMInject"))
            comps["nodes"].append(opm_final_mm)
            cmds.connectAttr(opm_output_plug, f"{opm_final_mm}.matrixIn[0]")
            cmds.connectAttr(prev_target_plug, f"{opm_final_mm}.matrixIn[1]")
            cmds.connectAttr(f"{out_p}.worldInverseMatrix[0]", f"{opm_final_mm}.matrixIn[2]")
            cmds.connectAttr(f"{opm_final_mm}.matrixSum", f"{grp}.offsetParentMatrix")
        else:
            cmds.connectAttr(opm_output_plug, f"{grp}.offsetParentMatrix")
        
        target_out_node = cmds.createNode("multMatrix", name=RigUtils.generate_name(ctx.base, ctx.c, ctx.i, f"_{comp_type}_TargetOutput"))
        comps["nodes"].append(target_out_node)
        cmds.connectAttr(opm_output_plug, f"{target_out_node}.matrixIn[0]")
        cmds.connectAttr(prev_target_plug, f"{target_out_node}.matrixIn[1]")

        RigUtils.zero_out_local(grp)

        return f"{target_out_node}.matrixSum"

    def _build_fk_component(self, ctx, comps):
        grp_name = RigUtils.generate_name(ctx.base, ctx.c, ctx.i, MrsNaming.FK_OFFSET)
        ctrl_name = RigUtils.generate_name(ctx.base, ctx.c, ctx.i, MrsNaming.FK_CTRL)
        
        for suf in ["_TargetFallback", "_TargetOutput", "_OPM", "_OPMBlend", "_PrevTargetInv", "_LiveLocal", "_LiveWorldMM", "_OPMInject"]:
            node = RigUtils.generate_name(ctx.base, ctx.c, ctx.i, f"_FK{suf}")
            if cmds.objExists(node): cmds.delete(node)
            old_node = RigUtils.generate_name(ctx.base, ctx.c, ctx.i, suf)
            if cmds.objExists(old_node): cmds.delete(old_node)

        grp = self._ensure_group(grp_name, parent=ctx.prev_fk)
        comps["groups"].append(grp)

        size = self._calculate_adaptive_size(ctx, MrsNaming.FK_CTRL_SCALE)
        ctrl = self._ensure_control(ctrl_name, grp, size, "circle")
        comps["ctrls"].append(ctrl)

        target_pin = self._build_spatial_opm(ctx, ctrl, grp, comps, ctx.enable_follow, comp_type="FK")
        return {"grp": grp, "ctrl": ctrl, "target_pin": target_pin}

    def _clean_fk_component(self, ctx):
        grp_name = RigUtils.generate_name(ctx.base, ctx.c, ctx.i, MrsNaming.FK_OFFSET)
        
        # 对于存在于无形的大纲（DG 层级）中的独立数学算子，无论物理父壳还在不在，都必须强杀
        for suf in ["_TargetFallback", "_TargetOutput", "_OPM", "_OPMBlend", "_PrevTargetInv", "_LiveLocal", "_LiveWorldMM"]:
            node = RigUtils.generate_name(ctx.base, ctx.c, ctx.i, suf)
            if cmds.objExists(node):
                cmds.delete(node)
                
        if cmds.objExists(grp_name):
            RigUtils.delete_opm_nodes(grp_name)
            cmds.delete(grp_name)

    def _build_ik_component(self, ctx, comps, parent, is_fk_active):
        grp_name = RigUtils.generate_name(ctx.base, ctx.c, ctx.i, MrsNaming.IK_OFFSET)
        ctrl_name = RigUtils.generate_name(ctx.base, ctx.c, ctx.i, MrsNaming.IK_CTRL)
        
        for suf in ["_TargetFallback", "_TargetOutput", "_OPM", "_OPMBlend", "_PrevTargetInv", "_LiveLocal", "_LiveWorldMM", "_OPMInject"]:
            node = RigUtils.generate_name(ctx.base, ctx.c, ctx.i, f"_IK{suf}")
            if cmds.objExists(node): cmds.delete(node)
            old_node = RigUtils.generate_name(ctx.base, ctx.c, ctx.i, suf)
            if cmds.objExists(old_node): cmds.delete(old_node)

        grp = self._ensure_group(grp_name, parent=parent)
        comps["groups"].append(grp)
        
        # Reset Visibility: Ensure visible by default (Fix for FIK -> Pure IK transition)
        v_plug = f"{grp}.visibility"
        if cmds.connectionInfo(v_plug, isDestination=True):
            src = cmds.connectionInfo(v_plug, sourceFromDestination=True)
            cmds.disconnectAttr(src, v_plug)
        if not cmds.getAttr(v_plug, lock=True):
            cmds.setAttr(v_plug, 1)

        size = self._calculate_adaptive_size(ctx, MrsNaming.IK_CTRL_SCALE)
        ctrl = self._ensure_control(ctrl_name, grp, size, "square")
        comps["ctrls"].append(ctrl)

        target_pin = None
        if is_fk_active:
            RigUtils.delete_opm_nodes(grp)
            RigUtils.zero_out_local(grp)
        else:
            RigUtils.delete_opm_nodes(grp)
            # Pure IK: build the full spatial OPM matrix to inherit parent scales and support exact follow envelope!
            target_pin = self._build_spatial_opm(ctx, ctrl, grp, comps, ctx.enable_follow, comp_type="IK")
            
        return {"grp": grp, "ctrl": ctrl, "target_pin": target_pin}

    def _clean_ik_component(self, ctx):
        grp_name = RigUtils.generate_name(ctx.base, ctx.c, ctx.i, MrsNaming.IK_OFFSET)
        if cmds.objExists(grp_name):
            RigUtils.delete_opm_nodes(grp_name)
            cmds.delete(grp_name)




class HierarchyNodeBuilder:
    """Outliner hierarchy, control shapes, and DG/DAG housekeeping."""
    def _ensure_group(self, name, parent=None):
        if not cmds.objExists(name):
            grp = cmds.group(empty=True, name=name)
        else: grp = name
        
        if parent:
            curr_p = cmds.listRelatives(grp, parent=True)
            if not curr_p or curr_p[0] != parent:
                cmds.parent(grp, parent)
        return grp

    def _calculate_adaptive_size(self, ctx, scale_ratio: float) -> float:
        """Calculate local size based on distance between current bone and next bone."""
        if not ctx.chain:
            return ctx.width * scale_ratio

        curr_bone = ctx.chain[ctx.i]
        
        # 1. 尝试找下一根骨骼求距离
        if ctx.i + 1 < len(ctx.chain):
            next_bone = ctx.chain[ctx.i + 1]
            dist = RigUtils.get_bone_distance(curr_bone, next_bone)
        # 2. 如果是末端，且存在上一根骨骼，则继承上一根骨架的测距
        elif ctx.i - 1 >= 0:
            prev_bone = ctx.chain[ctx.i - 1]
            dist = RigUtils.get_bone_distance(prev_bone, curr_bone)
        # 3. 如果这串链条里只有孤零零的一根骨骼，退回到使用全局/面片宽度
        else:
            dist = ctx.width
            
        return dist * scale_ratio

    def _ensure_control(self, name, parent, size, shape_type="circle"):
        if not cmds.objExists(name):
            ctrl = RigUtils.create_control_shape(name, size=size, shape_type=shape_type)
        else: ctrl = name
        
        curr_p = cmds.listRelatives(ctrl, parent=True)
        if not curr_p or curr_p[0] != parent:
            cmds.parent(ctrl, parent)
        
        RigUtils.zero_out_local(ctrl)
        
        cmds.setAttr(f"{ctrl}.v", lock=True, keyable=False, channelBox=False)
        
        return ctrl

    def _cleanup_scale_connections(self, chains, clean_base):
        """Disconnects existing scale inputs and removes old/new scale compensate nodes."""
        for c_idx, chain in enumerate(chains):
            for i in range(len(chain)):
                # FK/IK offset: disconnect scale, delete old scale nodes
                for suffix in [MrsNaming.FK_OFFSET, MrsNaming.IK_OFFSET]:
                    grp = RigUtils.generate_name(clean_base, c_idx, i, suffix)
                    if cmds.objExists(grp):
                        scale_plug = f"{grp}.scale"
                        if cmds.connectionInfo(scale_plug, isDestination=True):
                            src = cmds.connectionInfo(scale_plug, sourceFromDestination=True)
                            cmds.disconnectAttr(src, scale_plug)
                        if not cmds.getAttr(scale_plug, lock=True):
                            cmds.setAttr(scale_plug, 1, 1, 1)
                        for comp in ["_ParentScale_DCM", "_ScaleComp", "_ScaleCM", "_ScaleMM", "_CtrlInvS_MD", "_CtrlInvS_CM"]:
                            n = f"{grp}{comp}"
                            if cmds.objExists(n):
                                cmds.delete(n)
                # FollowBlend/FallbackMM cleanup
                for suf in ["_FollowBlend", "_FallbackMM"]:
                    node = RigUtils.generate_name(clean_base, c_idx, i, suf)
                    if cmds.objExists(node):
                        cmds.delete(node)

        # Clean up shared scale nodes
        for suffix in ["_InvScale_MD", "_InvScale_CM", "_Scale_CM"]:
            n = f"{clean_base}{suffix}"
            if cmds.objExists(n):
                cmds.delete(n)

    def _organize_hierarchy(self, clean_base, chains, rig_data, follow_mesh, parent_object, update_mode):
        """Organize main_grp, jnt_grp hierarchy and parent joints."""
        main_grp = self._ensure_group(f"{clean_base}{MrsNaming.GRP_MAIN}")
        if cmds.attributeQuery("inheritsTransform", node=main_grp, exists=True):
            cmds.setAttr(f"{main_grp}.inheritsTransform", 0)

        # 标记 baseName 以支持层级遍历查找 rig（get_rig_from_selection step 2）
        RigUtils.ensure_attr(main_grp, MrsNaming.ATTR_BASE_NAME, clean_base, "string")

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

        ctrl_grp = rig_data["groups"][0]
        curr_p = cmds.listRelatives(ctrl_grp, parent=True)
        if not curr_p or curr_p[0] != main_grp:
            cmds.parent(ctrl_grp, main_grp)

        rig_data["groups"].append(main_grp)
        rig_data["_main_grp"] = main_grp

    def _parent_joints_safely(self, roots, jnt_grp):
        for root in roots:
            if not cmds.objExists(root): continue
            parents = cmds.listRelatives(root, parent=True)
            if parents and parents[0] == jnt_grp: continue
            
            m = cmds.xform(root, q=True, ws=True, m=True)
            jo = cmds.getAttr(f"{root}.jointOrient")[0]
            ra = cmds.getAttr(f"{root}.rotateAxis")[0]
            ssc = cmds.getAttr(f"{root}.segmentScaleCompensate")

            new_root = cmds.parent(root, jnt_grp)[0]

            cmds.setAttr(f"{new_root}.jointOrient", *jo)
            cmds.setAttr(f"{new_root}.rotateAxis", *ra)
            cmds.setAttr(f"{new_root}.segmentScaleCompensate", ssc)
            cmds.xform(new_root, ws=True, m=m)

    def _migrate_metadata(self, follow_mesh):
        drivers = []
        if cmds.attributeQuery(MrsNaming.ATTR_DRIVER_CONN, node=follow_mesh, exists=True):
            drivers = cmds.listConnections(f"{follow_mesh}.{MrsNaming.ATTR_DRIVER_CONN}")
        
        if drivers:
            print(f"[MRS] Migrating Data from {drivers[0]}...")
            self._bake_uv_data(drivers[0], follow_mesh)

    def _organize_sets(self, base, data, geo, joints, update):
        sets = {}
        # 控制器 + Offset 组合并到 CTRL_SET
        ctrl_members = data["ctrls"] + data["groups"]
        types = [(MrsNaming.CTRL_SET, ctrl_members), (MrsNaming.NODE_SET, data["nodes"])]

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


class ProxyNodeBuilder:
    """Standalone weighted proxy mechanics."""
    def create_standalone_proxy(self, target_mesh, chains, base_name="Ribbon", pure_ik=False):
        clean_base = base_name.replace(":", "_")
        proxy_mesh = cmds.duplicate(target_mesh, name=f"{clean_base}{MrsNaming.MESH_PROXY}")[0]

        cmds.delete(proxy_mesh, ch=True)
        RigUtils.zero_out_local(proxy_mesh)
        cmds.setAttr(f"{proxy_mesh}.{MrsNaming.ATTR_INHERITS_XFORM}", 0)
        cmds.setAttr(f"{proxy_mesh}.visibility", 1)

        # 确保在世界层级下
        if cmds.listRelatives(proxy_mesh, parent=True):
            cmds.parent(proxy_mesh, world=True)

        is_reversed = RigUtils.get_reverse_state(target_mesh)

        RigUtils.apply_perfect_ribbon_weights(proxy_mesh, chains, pre_follow_parent=True, reverse_order=is_reversed, pure_ik=pure_ik)

        RigUtils.ensure_attr(proxy_mesh, MrsNaming.ATTR_BASE_NAME, base_name, "string")
        RigUtils.ensure_attr(proxy_mesh, MrsNaming.ATTR_MRS_REVERSE, is_reversed, "bool")

        return proxy_mesh

class RigBuilder(GeometryNodeBuilder, MathNetworkBuilder, HierarchyNodeBuilder, ProxyNodeBuilder):
    """God Class Facade (Safely decoupled via SRP-focused mixins for maintenance)."""
    def build_rig_structure(self, mesh_transform: str, chains: list, name: str = "Ribbon", loop: bool = False, config: BindConfig = None) -> dict:
        if config is None:
            config = BindConfig()
        clean_name = name.replace(":", "_")

        rig_width = 2.0
        if cmds.attributeQuery(MrsNaming.ATTR_WIDTH, node=mesh_transform, exists=True):
            rig_width = cmds.getAttr(f"{mesh_transform}.{MrsNaming.ATTR_WIDTH}")
        else:
            hist = cmds.listConnections(f"{mesh_transform}.inMesh", s=True) or []
            if hist and cmds.attributeQuery(MrsNaming.ATTR_WIDTH, node=hist[0], exists=True):
                rig_width = cmds.getAttr(f"{hist[0]}.{MrsNaming.ATTR_WIDTH}")

        uv_pin, u_vals, v_vals = self._setup_uv_pin(mesh_transform, clean_name, chains, loop, config.passed_uvpin)

        rig_grp = self._ensure_group(f"{clean_name}{MrsNaming.GRP_CTRL}")
        comps = {"ctrls": [], "groups": [rig_grp], "nodes": [uv_pin], "drivers": []}

        if not config.enable_fk:
            self._preserve_ik_offsets(chains, clean_name, rig_grp)

        # Pre-create DCM for FK OPM scale injection
        scale_plug = None
        inv_scale_mtx_plug = None
        scale_mtx_plug = None
        if config.parent_object and cmds.objExists(config.parent_object):
            dcm_name = f"{clean_name}_Parent_DCM"
            if not cmds.objExists(dcm_name):
                dcm = cmds.createNode("decomposeMatrix", name=dcm_name)
            else:
                dcm = dcm_name
            cmds.connectAttr(f"{config.parent_object}.worldMatrix[0]", f"{dcm}.inputMatrix", force=True)
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
            prev_pin_plug = None
            prev_target_plug = None
            chain_root_fk = None

            for i, bone in enumerate(chain):
                idx = pin_offset + i
                u = u_vals[c_idx] if u_vals and c_idx < len(u_vals) else 0.5
                curr_pin_plug = f"{uv_pin}.outputMatrix[{idx}]"

                ctx = _BuildContext(
                    base=clean_name, c=c_idx, i=i,
                    pin=curr_pin_plug, prev_pin=prev_pin_plug,
                    prev_fk=prev_fk_ctrl, prev_target=prev_target_plug, chain_grp=chain_grp,
                    width=rig_width, parent_object=config.parent_object,
                    scale_plug=scale_plug, inv_scale_mtx=inv_scale_mtx_plug,
                    scale_mtx=scale_mtx_plug, enable_follow=config.enable_follow,
                    chain=chain
                )

                current_driver = None

                if config.enable_fk:
                    fk_res = self._build_fk_component(ctx, comps)
                    prev_fk_ctrl = fk_res["ctrl"]
                    prev_target_plug = fk_res["target_pin"]
                    current_driver = fk_res["ctrl"]

                    if i == 0:
                        chain_root_fk = fk_res["ctrl"]
                        if config.enable_ik and not cmds.attributeQuery(MrsNaming.ATTR_SHOW_IK, node=chain_root_fk, exists=True):
                            cmds.addAttr(chain_root_fk, longName=MrsNaming.ATTR_SHOW_IK, attributeType="bool", keyable=True, defaultValue=1)
                    else:
                        if chain_root_fk and config.enable_ik and not cmds.attributeQuery(MrsNaming.ATTR_SHOW_IK, node=fk_res["ctrl"], exists=True):
                            cmds.addAttr(fk_res["ctrl"], longName=MrsNaming.ATTR_SHOW_IK, proxy=f"{chain_root_fk}.{MrsNaming.ATTR_SHOW_IK}")
                else:
                    self._clean_fk_component(ctx)

                if config.enable_ik:
                    parent = prev_fk_ctrl if config.enable_fk else chain_grp
                    ik_res = self._build_ik_component(ctx, comps, parent, config.enable_fk)
                    current_driver = ik_res["ctrl"]
                    
                    if chain_root_fk:
                        cmds.connectAttr(f"{chain_root_fk}.{MrsNaming.ATTR_SHOW_IK}", f"{ik_res['grp']}.visibility", force=True)
                else:
                    self._clean_ik_component(ctx)
                
                if current_driver: comps["drivers"].append(current_driver)
                prev_pin_plug = curr_pin_plug
                
            pin_offset += len(chain)
            
        return comps

    def finalize_bind(self, preview_mesh: str, chains: list, config: BindConfig = None) -> str:
        if config is None:
            config = BindConfig()

        base_name, follow_mesh, uv_pin, ribbon_node = self._resolve_bind_inputs(
            preview_mesh, chains, config
        )
        clean_base = base_name.replace(":", "_")

        if not config.update_mode:
            follow_mesh = self._setup_follow_mesh(preview_mesh, clean_base, base_name, ribbon_node, chains)

        # Clean old scale/follow connections BEFORE building new rig structure,
        # so newly created ScaleCM/ScaleMM nodes won't be deleted by cleanup.
        if config.update_mode or (config.parent_object and cmds.objExists(config.parent_object)):
            self._cleanup_scale_connections(chains, clean_base)

        build_config = BindConfig(
            enable_fk=config.enable_fk, enable_ik=config.enable_ik,
            enable_follow=config.enable_follow, parent_object=config.parent_object,
            passed_uvpin=uv_pin
        )
        rig_data = self.build_rig_structure(follow_mesh, chains, name=base_name, config=build_config)

        self._organize_hierarchy(clean_base, chains, rig_data, follow_mesh, config.parent_object, config.update_mode)
        self._bind_bones_to_drivers(chains, rig_data)

        # Persist parent_object to FollowMod for update-mode recovery
        if config.parent_object and cmds.objExists(config.parent_object):
            RigUtils.ensure_attr(follow_mesh, MrsNaming.ATTR_PARENT_OBJECT, config.parent_object, "string")

        self._organize_sets(clean_base, rig_data, follow_mesh, [b for c in chains for b in c], config.update_mode)

        if not config.update_mode and preview_mesh and cmds.objExists(preview_mesh):
            plugin_node = RigUtils.find_plugin_node(preview_mesh)
            cmds.delete(preview_mesh)
            if plugin_node and cmds.objExists(plugin_node):
                cmds.delete(plugin_node)

        print(f"[MRS] Bind Complete: {base_name}")
        return rig_data["_main_grp"]

    def _resolve_bind_inputs(self, preview_mesh, chains, config: BindConfig):
        """Resolve inputs for bind: returns (base_name, follow_mesh, uv_pin, ribbon_node)."""
        base_name = config.existing_base_name if config.existing_base_name else "Ribbon"
        follow_mesh = None
        uv_pin = None
        ribbon_node = None

        if config.update_mode and config.existing_follow_mesh:
            follow_mesh = config.existing_follow_mesh
            if config.passed_uvpin: uv_pin = config.passed_uvpin
            else:
                shapes = cmds.listRelatives(follow_mesh, shapes=True) or []
                if shapes:
                    conns = cmds.listConnections(f"{shapes[0]}.worldMesh", type="uvPin")
                    if conns: uv_pin = conns[0]

            if not uv_pin: raise RuntimeError("UVPin missing.")

            if not cmds.attributeQuery(MrsNaming.ATTR_STORED_U, node=follow_mesh, exists=True):
                self._migrate_metadata(follow_mesh)

        elif config.existing_ribbon_node:
            ribbon_node = config.existing_ribbon_node
        else:
            if not preview_mesh: raise RuntimeError("No Preview Mesh.")

            hist = cmds.listConnections(f"{preview_mesh}.inMesh", s=True)
            ribbon_node = hist[0] if hist else None

            if cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=preview_mesh, exists=True):
                base_name = cmds.getAttr(f"{preview_mesh}.{MrsNaming.ATTR_BASE_NAME}")
            elif ribbon_node and cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=ribbon_node, exists=True):
                base_name = cmds.getAttr(f"{ribbon_node}.{MrsNaming.ATTR_BASE_NAME}")

        return base_name, follow_mesh, uv_pin, ribbon_node

    def _bind_bones_to_drivers(self, chains, rig_data):
        """Connect bones to driver controls via OPM and store bind pose."""
        all_bones = [b for c in chains for b in c]
        for bone, drv in zip(all_bones, rig_data["drivers"]):
            bone_node = bone.split('|')[-1]
            opm = RigUtils.connect_via_opm(drv, bone_node, maintain_offset=False)
            if opm: rig_data["nodes"].append(opm)

            m_bind = cmds.xform(bone_node, q=True, ws=True, m=True)
            RigUtils.ensure_attr(bone_node, MrsNaming.ATTR_BIND_POSE, m_bind, "matrix")
