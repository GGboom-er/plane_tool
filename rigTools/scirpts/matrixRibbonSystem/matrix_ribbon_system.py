"""
Matrix Ribbon System (MRS) - Main Entry Point
Version: 5.2.0
"""
import maya.cmds as cmds
import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from manager import RigManager
import builder
from utils import MrsNaming

class RibbonRigSystem:
    """
    Main Facade for the Matrix Ribbon System (MRS).
    Provides high-level API for creating previews, binding rigs, and managing proxies.
    """
    def __init__(self):
        self.builder = builder.RigBuilder()
        self.manager = RigManager()

    def create_preview_mesh(self, chains, base_name="Ribbon", width=None, hold_length=None, loop=False):
        return self.builder.create_preview_mesh(chains, base_name, width, hold_length, loop)

    def bind_from_preview(self, preview_mesh, chains, enable_fk=True, enable_ik=True, existing_ribbon_node=None, existing_base_name=None, update_mode=False, existing_follow_mesh=None, passed_uvpin=None, parent_object=None):
        return self.builder.finalize_bind(preview_mesh, chains, enable_fk, enable_ik, existing_ribbon_node, existing_base_name, update_mode, existing_follow_mesh, passed_uvpin, parent_object)

    def create_proxy_from_preview(self, preview_mesh, chains, pure_ik=False):
        # Base Name Logic
        base_name = "Ribbon"
        if cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=preview_mesh, exists=True):
            base_name = cmds.getAttr(f"{preview_mesh}.{MrsNaming.ATTR_BASE_NAME}")
        
        return self.builder.create_standalone_proxy(preview_mesh, chains, base_name, pure_ik)

    def remove_rig(self, rig_set, restore_pose=False):
        return self.manager.remove_rig(rig_set, restore_pose=restore_pose)

    def get_all_rigs(self):
        return self.manager.get_all_rigs()
