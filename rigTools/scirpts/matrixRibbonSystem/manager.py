"""
Matrix Ribbon System (MRS) - Rig Manager
Version: 19.0.0
"""
import maya.cmds as cmds
from utils import RigUtils, MrsNaming


def _hierarchy_depth(node):
    """Return hierarchy depth for sorting (deeper = higher number)."""
    long_names = cmds.ls(node, long=True)
    if not long_names: return 0
    return len(long_names[0].split("|"))


class RigManager:

    @staticmethod
    def get_all_rigs():
        return cmds.ls(f"*{MrsNaming.RIG_SET}", type="objectSet") or []

    @staticmethod
    def safe_unbind_batch(joints, restore_pose=False):
        if not joints:
            return

        # 1. Capture Targets
        targets = {}
        for jnt in joints:
            if not cmds.objExists(jnt):
                continue
            
            target_m = None
            if restore_pose and cmds.attributeQuery(MrsNaming.ATTR_BIND_POSE, node=jnt, exists=True):
                target_m = cmds.getAttr(f"{jnt}.{MrsNaming.ATTR_BIND_POSE}")
                # cmds.getAttr on matrix returns nested list [[...]], flatten it
                if target_m and isinstance(target_m[0], (list, tuple)):
                    target_m = list(target_m[0])
            else:
                target_m = cmds.xform(jnt, q=True, ws=True, m=True)
            
            targets[jnt] = target_m

        # 2. Break & Reset OPM
        for jnt in joints:
            if not cmds.objExists(jnt):
                continue
            RigUtils.delete_opm_nodes(jnt) # Re-use robust cleanup

        # 3. Apply Targets
        # Sort by depth to ensure parents are moved before children (though WS xform handles this, it's safer)
        sorted_joints = sorted(list(targets.keys()), key=_hierarchy_depth)
        for jnt in sorted_joints:
            cmds.xform(jnt, ws=True, m=targets[jnt])
        
        # 4. Cleanup Attributes
        for jnt in joints:
            if not cmds.objExists(jnt):
                continue
            if cmds.attributeQuery(MrsNaming.ATTR_BIND_POSE, node=jnt, exists=True):
                cmds.deleteAttr(jnt, at=MrsNaming.ATTR_BIND_POSE)

    def remove_rig(self, set_name: str, restore_pose: bool = False):
        if not cmds.objExists(set_name):
            return
        
        # Robust Validation
        if cmds.nodeType(set_name) != "objectSet" or not set_name.endswith(MrsNaming.RIG_SET):
             print(f"[MRS Manager] Error: {set_name} is not a valid MRS Rig Set.")
             return
             
        print(f"\n[MRS Manager] Removing: {set_name}")
        
        base_name = set_name.replace(MrsNaming.RIG_SET, "")
        
        # 1. Identify Joints
        joints = []
        jnt_set = f"{base_name}{MrsNaming.JNT_SET}"
        if cmds.objExists(jnt_set):
            joints = cmds.sets(jnt_set, q=True) or []
        else:
            members = cmds.sets(set_name, q=True) or []
            joints = cmds.ls(members, type="joint", long=True)

        # 2. Unbind & Unparent Joints
        if joints:
            # Ensure unique and existing
            valid_joints = list(set([j for j in joints if cmds.objExists(j)]))
            self.safe_unbind_batch(valid_joints, restore_pose)

            # Read stored parent_object from FollowMod for unparent check
            follow_mod = f"{base_name}{MrsNaming.MESH_FOLLOW}"
            stored_parent = None
            if cmds.objExists(follow_mod) and cmds.attributeQuery(MrsNaming.ATTR_PARENT_OBJECT, node=follow_mod, exists=True):
                stored_parent = cmds.getAttr(f"{follow_mod}.{MrsNaming.ATTR_PARENT_OBJECT}")

            for j in valid_joints:
                parents = cmds.listRelatives(j, parent=True)
                if parents:
                    p_name = parents[0]
                    # Check if parent is part of rig structure 
                    if p_name.endswith(MrsNaming.GRP_JNT) or p_name.endswith(MrsNaming.GRP_MAIN):
                        # 用户需求：当骨骼没有指定父物体时，移除绑定不应连带骨骼删除。
                        # 我们只需要移除绑定时，将骨骼放置在parent即可，如果没有parent，默认就是世界层级
                        try:
                            if stored_parent and cmds.objExists(stored_parent):
                                cmds.parent(j, stored_parent)
                            else:
                                cmds.parent(j, world=True)
                        except Exception as e:
                            print(f"[MRS Manager] Failed to unparent joint {j}: {e}")

        # 3. Delete Nodes (Priority)
        node_set = f"{base_name}{MrsNaming.NODE_SET}"
        if cmds.objExists(node_set):
            nodes = cmds.sets(node_set, q=True) or []
            valid_nodes = [n for n in nodes if cmds.objExists(n)]
            if valid_nodes:
                cmds.delete(valid_nodes)

        # 4. Delete Structure
        sets_to_check = [
            f"{base_name}{MrsNaming.GEO_SET}",
            f"{base_name}{MrsNaming.CTRL_SET}",
            f"{base_name}{MrsNaming.FK_CTRL_SET}",
            f"{base_name}{MrsNaming.IK_CTRL_SET}",
            f"{base_name}{MrsNaming.GRP_CTRL_SET}"
        ]
        
        objs_to_delete = []
        for s in sets_to_check:
            if cmds.objExists(s):
                members = cmds.sets(s, q=True) or []
                for m in members:
                    if cmds.objExists(m):
                        objs_to_delete.append(m)
        
        # Backup: Find Main Group by name
        main_grp = f"{base_name}{MrsNaming.GRP_MAIN}"
        if cmds.objExists(main_grp):
            objs_to_delete.append(main_grp)

        if objs_to_delete:
            # Sort by hierarchy depth (deepest first) to avoid "already deleted" errors
            unique_objs = list(set(objs_to_delete))
            unique_objs.sort(key=_hierarchy_depth, reverse=True)
            for o in unique_objs:
                if cmds.objExists(o):
                    cmds.delete(o)

        # 5. Delete Sets
        sets_to_delete = sets_to_check + [jnt_set, node_set, set_name]
        for s in sets_to_delete:
            if cmds.objExists(s):
                cmds.delete(s)
                
        print("[MRS Manager] Removal Complete.\n")
