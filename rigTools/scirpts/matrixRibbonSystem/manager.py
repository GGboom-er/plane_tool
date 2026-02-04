"""
Matrix Ribbon System (MRS) - Rig Manager
Version: 10.0.0
Optimized: Using centralized constants and robust deletion logic.
"""
import maya.cmds as cmds
from utils import RigUtils, MrsNaming

class RigManager:

    @staticmethod
    def get_all_rigs():
        return cmds.ls(f"*{MrsNaming.RIG_SET}", type="objectSet") or []

    @staticmethod
    def get_hierarchy_depth(node):
        return len(cmds.ls(node, long=True)[0].split("|"))

    @staticmethod
    def safe_unbind_batch(joints, restore_pose=False):
        if not joints: return

        # 1. Capture Targets
        targets = {}
        for jnt in joints:
            if not cmds.objExists(jnt): continue
            
            target_m = None
            if restore_pose and cmds.attributeQuery(MrsNaming.ATTR_BIND_POSE, node=jnt, exists=True):
                target_m = cmds.getAttr(f"{jnt}.{MrsNaming.ATTR_BIND_POSE}")
            else:
                target_m = cmds.xform(jnt, q=True, ws=True, m=True)
            
            targets[jnt] = target_m

        # 2. Break & Reset OPM
        for jnt in joints:
            if not cmds.objExists(jnt): continue
            RigUtils.delete_opm_nodes(jnt) # Re-use robust cleanup

        # 3. Apply Targets
        sorted_joints = sorted(list(targets.keys()), key=RigManager.get_hierarchy_depth)
        for jnt in sorted_joints:
            if jnt in targets:
                cmds.xform(jnt, ws=True, m=targets[jnt])
        
        # 4. Cleanup Attributes
        for jnt in joints:
            if not cmds.objExists(jnt): continue
            if cmds.attributeQuery(MrsNaming.ATTR_BIND_POSE, node=jnt, exists=True):
                cmds.deleteAttr(jnt, at=MrsNaming.ATTR_BIND_POSE)

    def remove_rig(self, set_name, restore_pose=False):
        if not cmds.objExists(set_name): return
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
            self.safe_unbind_batch(list(set(joints)), restore_pose)
            
            for j in joints:
                if not cmds.objExists(j): continue
                parents = cmds.listRelatives(j, parent=True)
                if parents:
                    p_name = parents[0]
                    # Check if parent is part of rig structure
                    if any(x in p_name for x in [MrsNaming.GRP_JNT, MrsNaming.GRP_MAIN]):
                        try: cmds.parent(j, world=True)
                        except: pass

        # 3. Delete Nodes (Priority)
        node_set = f"{base_name}{MrsNaming.NODE_SET}"
        if cmds.objExists(node_set):
            nodes = cmds.sets(node_set, q=True) or []
            valid_nodes = [n for n in nodes if cmds.objExists(n)]
            if valid_nodes: cmds.delete(valid_nodes)

        # 4. Delete Structure
        sets_to_check = [
            f"{base_name}{MrsNaming.GEO_SET}",
            f"{base_name}{MrsNaming.GRP_SET}",
            f"{base_name}{MrsNaming.CTRL_SET}"
        ]
        
        objs_to_delete = []
        for s in sets_to_check:
            if cmds.objExists(s):
                members = cmds.sets(s, q=True) or []
                for m in members:
                    if cmds.objExists(m): objs_to_delete.append(m)
        
        # Backup: Find Main Group by name
        main_grp = f"{base_name}{MrsNaming.GRP_MAIN}"
        if cmds.objExists(main_grp): objs_to_delete.append(main_grp)

        if objs_to_delete:
            # Unique
            unique_objs = list(set(objs_to_delete))
            # Sort by depth to delete children first? Maya handles delete safely usually.
            cmds.delete(unique_objs)

        # 5. Delete Sets
        sets_to_delete = sets_to_check + [jnt_set, node_set, set_name]
        for s in sets_to_delete:
            if cmds.objExists(s): cmds.delete(s)
                
        print("[MRS Manager] Removal Complete.\n")
