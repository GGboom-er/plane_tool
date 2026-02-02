"""
Matrix Ribbon System (MRS) - Main Entry Point
Version: 5.1.0
"""
import maya.cmds as cmds
import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from builder import RigBuilder
from manager import RigManager

class RibbonRigSystem:
    def __init__(self):
        self.builder = RigBuilder()
        self.manager = RigManager()

    def create_preview_mesh(self, chains, width=None, hold_length=None, loop=False):
        return self.builder.create_preview_mesh(chains, width, hold_length, loop)

    def bind_from_preview(self, preview_mesh, chains):
        return self.builder.finalize_bind(preview_mesh, chains)

    def swap_attachment(self, rig_set, new_mesh):
        return self.manager.swap_attachment(rig_set, new_mesh)

    def remove_rig(self, rig_set, restore_pose=False):
        """
        Removes rig with optional pose restoration.
        """
        return self.manager.remove_rig(rig_set, restore_pose=restore_pose)

    def get_all_rigs(self):
        return self.manager.get_all_rigs()