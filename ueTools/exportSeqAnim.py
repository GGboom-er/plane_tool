#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: exportSeqAnim.py
@date: 2025/10/31 14:53
@desc: 
"""
import unreal
import importlib
import os
import shutil

ll = unreal.LevelSequenceEditorBlueprintLibrary
ues = unreal.EditorLevelLibrary()
level_editor_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
world = level_editor_subsystem.get_current_level()
world = ues.get_editor_world()
s = unreal.SequencerTools

ait = unreal.AssetImportTask()
ait.automated = 1
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

binding = ll.get_selected_bindings()[0]
eul = unreal.EditorUtilityLibrary()
d = eul.get_selected_asset_data()

asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

import path_config as pc

importlib.reload(pc)

main_path = pc.main_path + '/animations'
level_sequence = ll.get_focused_level_sequence()
bindings = ll.get_selected_bindings()


def print_names( object ):
    for i in object: print(i.get_display_name())


def export_anim( path="/Game/" ):
    path = path.replace("/All/", "/")
    # s.export_anim_sequence()
    anim_factory = unreal.AnimSequenceFactory()
    level_sequence = ll.get_focused_level_sequence()
    bindings = ll.get_selected_bindings()
    exported_assets = []

    anim_seqs = []
    cur_assets = asset_registry.get_assets_by_path(path)

    for binding in bindings:
        parent = binding.get_parent()
        parent_name = parent.get_name().replace("(", "_").replace(")", "_")

        object_binding_id = level_sequence.get_binding_id(binding)  # finally got the binding id
        skmc = ll.get_bound_objects(object_binding_id)[0]
        skm = skmc.skeletal_mesh
        name = skm.get_name()
        # name = '_'.join(name.split("_")[0:2])
        name = parent_name + "_" + name
        name = name.replace(" ", "_")
        count = 0
        for asset in cur_assets:
            if (name in str(asset.asset_name)):
                count += 1
        if (count > 0):
            name += "_{0}".format(count)

        sk = skm.skeleton

        anim_factory.preview_skeletal_mesh = skm
        anim_factory.target_skeleton = sk
        anim_factory.set_editor_property("asset_import_task", ait)
        anim_factory.set_editor_property("edit_after_new", False)

        anim_seq_class = unreal.AnimSequence
        anim_sequence = asset_tools.create_asset(name, path, anim_seq_class, anim_factory)
        asset = asset_registry.get_asset_by_object_path(anim_sequence.get_path_name())
        # Anim Sequence Object.. asset? idk

        # anim_sequence = unreal.load_asset("/Game/Anim_test", anim_seq_class)

        export_option = unreal.AnimSeqExportOption()
        export_option.export_transforms = True
        export_option.export_morph_targets = True
        export_option.export_attribute_curves = True
        export_option.export_material_curves = True
        export_option.record_in_world_space = True
        export_option.evaluate_all_skeletal_mesh_components = True
        export_option.transact_recording = True

        s.export_anim_sequence(world, level_sequence, anim_sequence, export_option, binding, create_link=1)
        # link = s.link_anim_sequence(level_sequence, anim_sequence, export_option, binding)
        exported_assets.append(asset)
        anim_seqs.append(anim_sequence)
    export_fbxs(exported_assets=exported_assets, anim_seqs=anim_seqs)
    # export fbx for all exported_assets
    return


def export_fbxs( exported_assets, anim_seqs ):
    asset_tools.export_assets([x.package_name for x in exported_assets],
                              main_path)  # Works but makes stupid path, trying to avoid
    move_game_files(main_path)


def move_game_files( path ):
    base_dir = path
    game_folder = os.path.join(base_dir, "Game")

    # Recursively find all .fbx files in the Game folder
    for root, dirs, files in os.walk(game_folder):

        for filename in files:
            if filename.lower().endswith(".fbx"):
                # Construct full source and destination paths
                source_path = os.path.join(root, filename)
                dest_path = os.path.join(base_dir, filename)

                # Move the file
                shutil.move(source_path, dest_path)
                print(f"Moved: {filename} from {root} to {base_dir}")

    print("All .fbx files have been moved to the animations folder.")
    shutil.rmtree(game_folder)
    print(f"Removed the folder: {game_folder}")