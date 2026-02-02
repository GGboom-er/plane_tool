"""
Matrix Ribbon System (MRS) - Rig Manager
Version: 9.2.0
Fix: Always clean 'mrsBindPose' attribute upon unbind.
"""
import maya.cmds as cmds

class RigManager:

    @staticmethod
    def get_all_rigs():
        return cmds.ls("*_Rig_Set", type="objectSet") or []

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
            has_stored_pose = cmds.attributeQuery("mrsBindPose", node=jnt, exists=True)
            
            if restore_pose and has_stored_pose:
                target_m = cmds.getAttr(f"{jnt}.mrsBindPose")
            else:
                target_m = cmds.xform(jnt, q=True, ws=True, m=True)
            
            targets[jnt] = target_m

        # 2. Break & Reset OPM
        for jnt in joints:
            if not cmds.objExists(jnt): continue
            conns = cmds.listConnections(f"{jnt}.offsetParentMatrix", s=True, d=False, p=True)
            if conns:
                cmds.disconnectAttr(conns[0], f"{jnt}.offsetParentMatrix")
            
            identity = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
            cmds.setAttr(f"{jnt}.offsetParentMatrix", identity, type="matrix")

        # 3. Apply Targets (Sorted)
        sorted_joints = sorted(list(targets.keys()), key=RigManager.get_hierarchy_depth)
        for jnt in sorted_joints:
            if jnt in targets:
                cmds.xform(jnt, ws=True, m=targets[jnt])
        
        # 4. ALWAYS Clean Attributes
        for jnt in joints:
            if not cmds.objExists(jnt): continue
            if cmds.attributeQuery("mrsBindPose", node=jnt, exists=True):
                cmds.deleteAttr(jnt, at="mrsBindPose")

    def remove_rig(self, set_name, restore_pose=False):
        if not cmds.objExists(set_name): return
        print(f"\n[MRS Manager] Removing: {set_name}")
        
        base_name = set_name.replace("_Rig_Set", "")
        
        # --- 1. Find Joints ---
        joints = []
        jnt_set = f"{base_name}_Jnt_Set"
        node_set = f"{base_name}_Node_Set"
        
        if cmds.objExists(jnt_set):
            joints = cmds.sets(jnt_set, q=True) or []
        elif cmds.objExists(node_set):
            nodes = cmds.sets(node_set, q=True) or []
            for n in nodes:
                if cmds.objExists(n) and cmds.nodeType(n) == "multMatrix":
                    out = cmds.listConnections(f"{n}.matrixSum", s=False, d=True)
                    if out:
                        for o in out:
                            if cmds.nodeType(o) == "joint": joints.append(o)
                            
        # --- 2. Unbind ---
        if joints:
            self.safe_unbind_batch(list(set(joints)), restore_pose)

        # --- 3. Delete Hierarchy ---
        main_grp = f"{base_name}_grp"
        if cmds.objExists(main_grp):
            cmds.delete(main_grp)

        # --- 4. Delete Residual Content ---
        if cmds.objExists(node_set):
            content = cmds.sets(node_set, q=True)
            if content:
                valid_content = [c for c in content if cmds.objExists(c)]
                if valid_content: cmds.delete(valid_content)

        # --- 5. Delete Sets ---
        all_sets = [
            f"{base_name}_Node_Set",
            f"{base_name}_Control_Set",
            f"{base_name}_Geo_Set",
            f"{base_name}_Group_Set",
            f"{base_name}_Jnt_Set",
            set_name
        ]
        
        for s in all_sets:
            if cmds.objExists(s):
                cmds.delete(s)
                
        print("[MRS Manager] Removal Complete.\n")