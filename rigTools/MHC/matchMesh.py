#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: matchMesh.py
@date: 2024/9/29 18:18
@desc: 
"""
def show_meshes(dna_path, add_skinning=False, add_blend_shapes=False):
    cmds.file(force=True, new=True)

    dna = DNA(dna_path)

    # Builds and returns the created mesh paths in the scene
    config = Config(
        add_joints=True,
        add_blend_shapes=add_blend_shapes,
        add_skin_cluster=add_skinning,
        add_ctrl_attributes_on_root_joint=True,
        add_animated_map_attributes_on_root_joint=True,
        add_mesh_name_to_blend_shape_channel_name=True,
        add_key_frames=True
    )

    # Build meshes
    build_meshes(dna, config)

# Starts here
show_meshes(character_dna)
reader = read_dna(character_dna)
calibrated = DNACalibDNAReader(reader)

# Update neutral mesh LOD0 based on provided model
# Add model into scene
cmds.file(model, i=True, mergeNamespacesOnClash=True, namespace=":")

run_vertices_command(
    calibrated, get_mesh_vertex_positions_from_scene("head_lod0_mesh"),
    get_mesh_vertex_positions_from_scene("Mesh"), 0
)

# Save DNA
save_dna(calibrated, mesh_dna)
show_meshes(mesh_dna)