#!/usr/bin/env python
# _*_ coding:cp936 _*_

"""
@author: GGboom
@license: MIT
@contact: https://github.com/GGboom-er
@file: setLightValueFn.py
@date: 2024/6/22 13:58
@desc: 
"""
import bpy

def set_light_property_and_keyframe(frame, value, property_name="volume"):
    # Ensure an object is selected
    if not bpy.context.selected_objects:
        print("No object selected")
        return

    # Get the selected object
    for obj in bpy.context.selected_objects:

        # Ensure the selected object is a light
        if obj.type != 'LIGHT':
            print("Selected object is not a light")
            return

        # Access the light data
        light = obj.data

        # Check if the property exists
        try:
            current_value = getattr(light, property_name)
        except AttributeError:
            print(f"The light object does not have the property '{property_name}'")
            return

        # Set the light property
        setattr(light, property_name, value)

        # Insert a keyframe for the property at the specified frame
        light.keyframe_insert(data_path=f"{property_name}", frame=frame)

# Example usage: Set the volume of the selected light to 1.5 at frame 30
set_light_property_and_keyframe(frame=30, value=1.5, property_name="volume_factor")