"""
Matrix Ribbon System (MRS) - Main Entry Point
Version: 19.0.0
"""
import maya.cmds as cmds
import os
import sys
from typing import List, Optional, Tuple

CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from manager import RigManager
import builder
from builder import BindConfig
from utils import MrsNaming, RigUtils, _resolve_transform


class RibbonRigSystem:
    """
    Main Facade for the Matrix Ribbon System (MRS).
    Provides high-level API for creating previews, binding rigs, and managing proxies.
    """
    def __init__(self):
        self.builder = builder.RigBuilder()
        self.manager = RigManager()

    def create_preview_mesh(self, chains: List[List[str]], base_name: str = "Ribbon",
                            width: Optional[float] = None, hold_length: Optional[float] = None,
                            loop: bool = False, stitch: bool = True, axis: int = 0) -> tuple:
        return self.builder.create_preview_mesh(chains, base_name, width, hold_length, loop, stitch=stitch, axis=axis)

    def bind_from_preview(self, preview_mesh: Optional[str], chains: List[List[str]],
                          enable_fk: bool = True, enable_ik: bool = True,
                          existing_ribbon_node: Optional[str] = None,
                          existing_base_name: Optional[str] = None,
                          update_mode: bool = False,
                          existing_follow_mesh: Optional[str] = None,
                          passed_uvpin: Optional[str] = None,
                          parent_object: Optional[str] = None,
                          enable_follow: bool = False) -> str:
        config = BindConfig(
            enable_fk=enable_fk, enable_ik=enable_ik,
            enable_follow=enable_follow, parent_object=parent_object,
            update_mode=update_mode, existing_base_name=existing_base_name,
            existing_follow_mesh=existing_follow_mesh,
            existing_ribbon_node=existing_ribbon_node,
            passed_uvpin=passed_uvpin
        )
        return self.builder.finalize_bind(preview_mesh, chains, config)

    def create_proxy_from_preview(self, preview_mesh: str, chains: List[List[str]],
                                  pure_ik: bool = False) -> str:
        base_name = "Ribbon"
        if cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=preview_mesh, exists=True):
            base_name = cmds.getAttr(f"{preview_mesh}.{MrsNaming.ATTR_BASE_NAME}")
        return self.builder.create_standalone_proxy(preview_mesh, chains, base_name, pure_ik)

    def remove_rig(self, rig_set: str, restore_pose: bool = False) -> None:
        return self.manager.remove_rig(rig_set, restore_pose=restore_pose)

    def get_all_rigs(self) -> List[str]:
        return self.manager.get_all_rigs()

    def validate_preview_selection(self, selection: list) -> Tuple[str, List[List[str]], str]:
        """Extract preview mesh info from user selection. Returns (preview_mesh, chains, base_name)."""
        if not selection:
            raise ValueError("Selection is empty.")
        raw_sel = selection[0]
        t_node = _resolve_transform(raw_sel)
        s_node = None

        if cmds.nodeType(raw_sel) == "transform":
            shapes = cmds.listRelatives(raw_sel, s=True)
            if shapes: s_node = shapes[0]
        elif cmds.nodeType(raw_sel) == "mesh":
            s_node = raw_sel

        if not s_node or not t_node:
            raise ValueError("Invalid Selection: A Mesh or Transform is required.")

        node = RigUtils.find_plugin_node(t_node)
        if not node:
            raise ValueError("Invalid Selection: No Driver Node found behind the mesh.")

        chains = RigUtils.get_chains_from_ribbon_node(node)
        if not chains:
            raise ValueError("Chain Data Missing on the setup.")

        base_name = "Ribbon"
        if cmds.attributeQuery(MrsNaming.ATTR_BASE_NAME, node=t_node, exists=True):
            base_name = cmds.getAttr(f"{t_node}.{MrsNaming.ATTR_BASE_NAME}")

        return t_node, chains, base_name

    def process_preview_generation(self, base_name: str) -> str:
        """High-level facade to handle preview generation from viewport selection."""
        sel = cmds.ls(sl=True, type=["transform", "joint"])
        if not sel:
            raise ValueError("Please select Root Joints in the viewport.")

        chains = RigUtils.get_chains_from_selection(sel)
        if not chains:
            raise ValueError("No valid hierarchical joint chains found in selection.")

        if cmds.objExists(f"{base_name}{MrsNaming.RIG_SET}"):
            raise ValueError(f"A rigorous rig set named '{base_name}' already exists. Please choose a different name.")

        p_mesh = f"{base_name}{MrsNaming.MESH_PREVIEW}"
        p_node = f"{base_name}{MrsNaming.NODE_PREVIEW}"
        if cmds.objExists(p_mesh): cmds.delete(p_mesh)
        if cmds.objExists(p_node): cmds.delete(p_node)

        mesh, _, _, _ = self.create_preview_mesh(chains, base_name=base_name)
        cmds.select(mesh)
        
        parent_obj = RigUtils.detect_parent_object(base_name, chains)
        return parent_obj

    def get_bind_context(self) -> dict:
        """Determines the current selection's bind context for UI routing."""
        sel = cmds.ls(sl=True)
        if not sel:
            raise ValueError("Select a Preview Mesh or an existing Rig component.")

        rig_set = RigUtils.get_rig_from_selection(sel)
        if rig_set:
            base = rig_set.replace(MrsNaming.RIG_SET, "")
            return {"mode": "UPDATE", "base_name": base, "rig_set": rig_set}

        t_node, chains, base = self.validate_preview_selection(sel)
        return {"mode": "NEW", "base_name": base, "t_node": t_node, "chains": chains}

    def process_update_rig(self, base_name: str, enable_fk: bool, enable_ik: bool, enable_follow: bool, parent_obj: Optional[str] = None):
        follow_mod = RigUtils.find_follow_mesh(base_name)
        if not follow_mod:
            raise ValueError(f"Substrate Mesh missing for rig '{base_name}'.")

        chains = RigUtils.get_chains_from_mesh(follow_mod)
        if not chains:
            raise ValueError("Chain Data Lost on the substrate mesh.")

        if not parent_obj:
            parent_obj = RigUtils.detect_parent_object(base_name, chains)

        self.bind_from_preview(
            preview_mesh=None, chains=chains,
            enable_fk=enable_fk, enable_ik=enable_ik,
            update_mode=True, existing_follow_mesh=follow_mod,
            existing_base_name=base_name, parent_object=parent_obj,
            enable_follow=enable_follow
        )

    def process_proxy_generation(self, is_pure_ik: bool):
        sel = cmds.ls(sl=True)
        if not sel:
            raise ValueError("Select a Ribbon Mesh or a valid Rig component.")

        target = None
        rig_set = RigUtils.get_rig_from_selection(sel)
        if rig_set:
            base = rig_set.replace(MrsNaming.RIG_SET, "")
            target = RigUtils.find_follow_mesh(base)

        if not target: target = sel[0]
        if not cmds.objExists(target):
            raise ValueError("Target proxy mesh not found in scene.")

        chains = RigUtils.get_chains_from_mesh(target)
        if not chains:
            node = RigUtils.find_plugin_node(target)
            if node:
                chains = RigUtils.get_chains_from_ribbon_node(node)

        if not chains:
            raise ValueError("No procedural chain data found on the target mesh.")

        self.create_proxy_from_preview(target, chains, pure_ik=is_pure_ik)
