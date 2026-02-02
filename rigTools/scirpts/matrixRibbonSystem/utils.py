"""
Matrix Ribbon System (MRS) - Utilities
Version: 6.2.0
Fix: Return created nodes to allow proper cleanup tracking.
"""
import maya.cmds as cmds
import maya.api.OpenMaya as om

class RigUtils:
    
    @staticmethod
    def zero_out_local(node):
        for attr in ['t', 'r']:
            if not cmds.getAttr(f"{node}.{attr}", lock=True):
                cmds.setAttr(f"{node}.{attr}", 0, 0, 0)
        for attr in ['s']:
            if not cmds.getAttr(f"{node}.{attr}", lock=True):
                cmds.setAttr(f"{node}.{attr}", 1, 1, 1)
        if cmds.nodeType(node) == 'joint':
            if not cmds.getAttr(f"{node}.jointOrient", lock=True):
                cmds.setAttr(f"{node}.jointOrient", 0, 0, 0)

    @staticmethod
    def connect_via_opm(driver, driven):
        """
        Drives 'driven' via OPM. Returns the created multMatrix node.
        """
        if not cmds.objExists(driver) or not cmds.objExists(driven): return None

        # 1. Clean
        conns = cmds.listConnections(f"{driven}.offsetParentMatrix", s=True, d=False, p=True)
        if conns:
            try: cmds.disconnectAttr(conns[0], f"{driven}.offsetParentMatrix")
            except: pass

        # 2. Calc
        m_driven = om.MMatrix(cmds.xform(driven, q=True, ws=True, m=True))
        m_driver = om.MMatrix(cmds.xform(driver, q=True, ws=True, m=True))
        m_offset = m_driven * m_driver.inverse()
        
        # 3. Create
        mult = cmds.createNode("multMatrix", name=f"{driven}_opm_driver")
        cmds.setAttr(f"{mult}.matrixIn[0]", list(m_offset), type="matrix")
        cmds.connectAttr(f"{driver}.worldMatrix[0]", f"{mult}.matrixIn[1]")
        
        parents = cmds.listRelatives(driven, parent=True)
        if parents:
            cmds.connectAttr(f"{parents[0]}.worldInverseMatrix[0]", f"{mult}.matrixIn[2]")
            
        cmds.connectAttr(f"{mult}.matrixSum", f"{driven}.offsetParentMatrix")
        
        # 4. Zero
        RigUtils.zero_out_local(driven)
        
        return mult

    @staticmethod
    def calculate_topology_metrics(bones):
        if len(bones) < 2: return 2.0, 0.5
        try:
            p_start = om.MPoint(cmds.xform(bones[0], q=True, ws=True, t=True))
            p_end = om.MPoint(cmds.xform(bones[-1], q=True, ws=True, t=True))
            total_len = (p_start - p_end).length()
        except: return 2.0, 0.5
        avg_len = total_len / (len(bones) - 1) if len(bones) > 1 else 1.0
        return max(avg_len * 0.4, 0.01), max(avg_len * 0.05, 0.001)

    @staticmethod
    def create_control_shape(name, size=1.0, shape_type="circle"):
        if shape_type == "circle":
            ctrl = cmds.circle(name=name, nr=(1, 0, 0), r=size, ch=False)[0]
        else: 
            ctrl = cmds.curve(name=name, d=1, p=[(-size, -size, 0), (size, -size, 0), (size, size, 0), (-size, size, 0), (-size, -size, 0)])
            cmds.setAttr(f"{ctrl}.rotateY", 90)
            cmds.makeIdentity(ctrl, apply=True, r=True)
        
        cmds.setAttr(f"{ctrl}.overrideEnabled", 1)
        color = 17 if shape_type == "circle" else 13
        cmds.setAttr(f"{ctrl}.overrideColor", color)
        return ctrl
